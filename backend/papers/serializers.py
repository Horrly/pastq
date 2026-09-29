from datetime import date

from rest_framework import serializers

from .models import Course, Explanation, Paper, PaperPage, Question, University, normalize_code


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "short_name", "slug"]


class CourseSerializer(serializers.ModelSerializer):
    university = serializers.SlugRelatedField(slug_field="slug", queryset=University.objects.all())
    university_name = serializers.CharField(source="university.short_name", read_only=True)
    paper_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Course
        fields = ["slug", "university", "university_name", "code", "title", "department", "level", "paper_count"]
        read_only_fields = ["slug"]

    def validate_code(self, value):
        code = normalize_code(value)
        if not any(ch.isdigit() for ch in code) or len(code) > 12:
            raise serializers.ValidationError("Use the course code as written, e.g. CSC 201.")
        return code

    def validate_level(self, value):
        if value is not None and value not in (100, 200, 300, 400, 500, 600, 700, 800):
            raise serializers.ValidationError("Level should be 100, 200, ... 800.")
        return value

    def validate(self, attrs):
        if Course.objects.filter(university=attrs["university"], code=attrs["code"]).exists():
            raise serializers.ValidationError({"code": f"{attrs['code']} already exists for this university."})
        return attrs


class PageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PaperPage
        fields = ["order", "url", "width", "height"]

    def get_url(self, page):
        url = page.image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and url.startswith("/") else url


class ExplanationSerializer(serializers.ModelSerializer):
    my_vote = serializers.SerializerMethodField()

    class Meta:
        model = Explanation
        fields = ["id", "text", "helpful", "not_helpful", "created_at", "my_vote"]

    def get_my_vote(self, explanation):
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return 0
        vote = next((v for v in explanation.votes.all() if v.user_id == user.id), None)
        return vote.value if vote else 0


class QuestionSerializer(serializers.ModelSerializer):
    explanation = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "number", "text", "marks", "topic", "explanation"]

    def get_explanation(self, question):
        explanation = getattr(question, "explanation", None)
        return ExplanationSerializer(explanation, context=self.context).data if explanation else None


class QuestionInputSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=12, allow_blank=True)
    text = serializers.CharField(max_length=6000)
    marks = serializers.IntegerField(min_value=1, max_value=999, required=False, allow_null=True)
    topic = serializers.CharField(max_length=60, allow_blank=True, required=False, default="")


class PaperSummarySerializer(serializers.ModelSerializer):
    session = serializers.CharField(read_only=True)
    semester_label = serializers.CharField(source="get_semester_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    question_count = serializers.IntegerField(read_only=True, default=0)
    uploaded_by = serializers.CharField(source="uploaded_by.username", default=None, read_only=True)
    course = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = ["id", "course", "year", "session", "semester", "semester_label", "kind", "kind_label", "status",
                  "question_count", "uploaded_by", "created_at"]

    def get_course(self, paper):
        return {"slug": paper.course.slug, "code": paper.course.code, "title": paper.course.title,
                "university": paper.course.university.short_name}


class PaperDetailSerializer(PaperSummarySerializer):
    pages = PageSerializer(many=True, read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta(PaperSummarySerializer.Meta):
        fields = PaperSummarySerializer.Meta.fields + ["instructions", "processing_error", "pages", "questions", "can_edit"]

    def get_can_edit(self, paper):
        request = self.context.get("request")
        user = request.user if request else None
        return bool(user and user.is_authenticated and (user.is_staff or paper.uploaded_by_id == user.id))


class PaperUploadSerializer(serializers.Serializer):
    course = serializers.SlugRelatedField(slug_field="slug", queryset=Course.objects.all())
    year = serializers.IntegerField(min_value=1970)
    semester = serializers.ChoiceField(choices=Paper.Semester.choices)
    kind = serializers.ChoiceField(choices=Paper.Kind.choices)

    def validate_year(self, value):
        if value > date.today().year:
            raise serializers.ValidationError("That session hasn't started yet.")
        return value

    def validate(self, attrs):
        existing = Paper.objects.filter(
            course=attrs["course"], year=attrs["year"], semester=attrs["semester"], kind=attrs["kind"]
        ).first()
        if existing:
            raise serializers.ValidationError({"detail": "This paper has already been uploaded.", "paper_id": existing.id})
        return attrs
