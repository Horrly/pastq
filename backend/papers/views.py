import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ai, services
from .models import Course, Explanation, Flag, Paper, Question, University, normalize_code
from .serializers import (
    CourseSerializer,
    ExplanationSerializer,
    PaperDetailSerializer,
    PaperSummarySerializer,
    PaperUploadSerializer,
    QuestionInputSerializer,
    QuestionSerializer,
    UniversitySerializer,
)


def visible_papers(user):
    qs = Paper.objects.select_related("course__university", "uploaded_by")
    if user.is_authenticated and user.is_staff:
        return qs
    if user.is_authenticated:
        return qs.filter(Q(is_hidden=False) | Q(uploaded_by=user))
    return qs.filter(is_hidden=False)


def with_question_count(qs):
    return qs.annotate(question_count=Count("questions"))


class ConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"ai_enabled": ai.enabled(), "fake_ai": settings.AI_PROVIDER == "fake",
                         "max_pages": settings.MAX_PAGES_PER_PAPER, "max_file_mb": settings.MAX_FILE_MB})


class StatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        papers = Paper.objects.filter(is_hidden=False)
        User = get_user_model()
        top = (
            User.objects.annotate(uploads=Count("papers", filter=Q(papers__is_hidden=False)))
            .filter(uploads__gt=0)
            .order_by("-uploads", "username")[:5]
        )
        recent = with_question_count(visible_papers(request.user)).order_by("-created_at")[:6]
        return Response({
            "papers": papers.count(),
            "questions": Question.objects.filter(paper__is_hidden=False).count(),
            "courses": Course.objects.filter(papers__is_hidden=False).distinct().count(),
            "explanations": Explanation.objects.count(),
            "top_contributors": [{"username": u.username, "uploads": u.uploads} for u in top],
            "recent_papers": PaperSummarySerializer(recent, many=True).data,
        })


class UniversityListView(generics.ListAPIView):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class CourseListView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer

    def get_queryset(self):
        qs = Course.objects.select_related("university").annotate(
            paper_count=Count("papers", filter=Q(papers__is_hidden=False))
        )
        params = self.request.query_params
        if uni := params.get("university"):
            qs = qs.filter(university__slug=uni)
        if q := params.get("q", "").strip():
            # "csc201", "CSC-201" and "csc 201" all find "CSC 201".
            qs = qs.filter(Q(code__icontains=normalize_code(q)) | Q(code__icontains=q) | Q(title__icontains=q))
        return qs.order_by("-paper_count", "code")[:40]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CourseDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        course = get_object_or_404(Course.objects.select_related("university"), slug=slug)
        papers = with_question_count(visible_papers(request.user).filter(course=course))
        topics = (
            Question.objects.filter(paper__in=papers).exclude(topic="")
            .values("topic")
            .annotate(questions=Count("id"), papers=Count("paper", distinct=True))
            .order_by("-papers", "-questions", "topic")[:12]
        )
        data = CourseSerializer(course).data
        data.update({
            "papers": PaperSummarySerializer(papers, many=True).data,
            "top_topics": list(topics),
            "paper_total": papers.count(),
        })
        return Response(data)


class PracticeView(APIView):
    """A shuffled set of questions from a course's past papers (optionally one topic)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        qs = Question.objects.filter(paper__course=course, paper__is_hidden=False).select_related("paper")
        if topic := request.query_params.get("topic"):
            qs = qs.filter(topic__iexact=topic)
        ids = list(qs.values_list("id", flat=True))
        count = max(1, min(int(request.query_params.get("n", 10)), 30))
        chosen = random.sample(ids, min(count, len(ids)))
        questions = (
            Question.objects.filter(id__in=chosen)
            .select_related("paper", "explanation")
            .prefetch_related("explanation__votes")
        )
        by_id = {q.id: q for q in questions}
        return Response([
            {**QuestionSerializer(by_id[i], context={"request": request}).data,
             "paper": {"id": by_id[i].paper_id, "session": by_id[i].paper.session,
                       "kind": by_id[i].paper.get_kind_display()}}
            for i in chosen
        ])


class PaperUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        data = PaperUploadSerializer(data=request.data)
        if not data.is_valid():
            errors = data.errors
            if "paper_id" in errors:  # duplicate: point to the existing paper
                return Response({"detail": errors["detail"][0], "paper_id": int(errors["paper_id"][0])},
                                status=status.HTTP_409_CONFLICT)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            paper = services.create_paper(user=request.user, files=request.FILES.getlist("files"), **data.validated_data)
        except services.LimitReached as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except services.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        paper = with_question_count(Paper.objects.all()).get(pk=paper.pk)
        return Response(PaperDetailSerializer(paper, context={"request": request}).data, status=status.HTTP_201_CREATED)


def paper_detail_queryset(user):
    return with_question_count(visible_papers(user)).prefetch_related(
        "pages",
        Prefetch("questions", queryset=Question.objects.select_related("explanation").prefetch_related("explanation__votes")),
    )


def editable_paper(request, pk):
    paper = get_object_or_404(visible_papers(request.user), pk=pk)
    if not (request.user.is_staff or paper.uploaded_by_id == request.user.id):
        raise PermissionDenied("Only the uploader can edit this paper.")
    return paper


class PaperDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        paper = get_object_or_404(paper_detail_queryset(request.user), pk=pk)
        return Response(PaperDetailSerializer(paper, context={"request": request}).data)


class PaperQuestionsView(APIView):
    """PUT the full list of questions (after reviewing what the AI read, or typing them in)."""

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        paper = editable_paper(request, pk)
        data = QuestionInputSerializer(data=request.data.get("questions", []), many=True)
        data.is_valid(raise_exception=True)
        if len(data.validated_data) > 80:
            return Response({"detail": "A paper can have at most 80 questions."}, status=400)
        questions = [
            {**q, "number": q["number"] or str(i + 1), "topic": ai.clean_topic(q.get("topic", "")), "text": q["text"].strip()}
            for i, q in enumerate(data.validated_data)
        ]
        services.replace_questions(paper, questions)
        paper.status = Paper.Status.READY if questions else Paper.Status.NEEDS_TEXT
        paper.processing_error = ""
        paper.save(update_fields=["status", "processing_error"])
        paper = paper_detail_queryset(request.user).get(pk=pk)
        return Response(PaperDetailSerializer(paper, context={"request": request}).data)


class PaperRetryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        paper = editable_paper(request, pk)
        if not ai.enabled():
            return Response({"detail": "AI isn't available on this server."}, status=400)
        paper.status, paper.processing_error = Paper.Status.PROCESSING, ""
        paper.save(update_fields=["status", "processing_error"])
        services.run_in_background(services.read_paper, paper.id)
        return Response({"status": paper.status})


class PaperFlagView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        paper = get_object_or_404(visible_papers(request.user), pk=pk)
        reason = str(request.data.get("reason", "")).strip()[:300]
        if not reason:
            return Response({"detail": "Tell us what's wrong."}, status=400)
        Flag.objects.update_or_create(paper=paper, user=request.user, defaults={"reason": reason, "resolved": False})
        return Response({"flagged": True}, status=status.HTTP_201_CREATED)


class ExplainView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        question = get_object_or_404(
            Question.objects.select_related("paper__course__university").filter(paper__in=visible_papers(request.user)),
            pk=pk,
        )
        if not ai.enabled():
            return Response({"detail": "Explanations aren't available on this server yet."}, status=503)
        try:
            explanation, created = services.get_or_create_explanation(question, request.user)
        except services.LimitReached as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except ai.AIError:
            return Response({"detail": "The AI tutor is busy right now. Please try again in a minute."}, status=503)
        return Response(ExplanationSerializer(explanation, context={"request": request}).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class VoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        explanation = get_object_or_404(Explanation, pk=pk)
        value = request.data.get("value")
        if value not in (1, -1):
            return Response({"detail": "value must be 1 or -1."}, status=400)
        explanation = services.vote(explanation, request.user, value)
        return Response(ExplanationSerializer(explanation, context={"request": request}).data)
