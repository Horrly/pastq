import io
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from . import ai
from .models import Explanation, ExplanationRequest, Paper, PaperPage, Question

logger = logging.getLogger(__name__)

MAX_SIDE = 1800  # px; plenty for reading, small enough for phones and AI limits
JPEG_QUALITY = 80


class UploadError(Exception):
    """Something the uploader can fix (wrong file type, too many pages, ...)."""


class LimitReached(Exception):
    pass


# --- Files -> page images ---------------------------------------------------------------


def _to_jpeg(img):
    img = ImageOps.exif_transpose(img)  # respect phone camera rotation
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue(), img.size


def _pdf_pages(data):
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise UploadError("That PDF couldn't be opened.") from exc
    if len(pdf) > settings.MAX_PAGES_PER_PAPER:
        raise UploadError(f"PDFs can have at most {settings.MAX_PAGES_PER_PAPER} pages.")
    for page in pdf:
        yield page.render(scale=2).to_pil()


def files_to_pages(files):
    """Turn uploaded images/PDFs into a list of (jpeg_bytes, (width, height))."""
    pages = []
    for f in files:
        if f.size > settings.MAX_FILE_MB * 1024 * 1024:
            raise UploadError(f"{f.name} is larger than {settings.MAX_FILE_MB} MB.")
        data = f.read()
        if data[:4] == b"%PDF":
            pages.extend(_to_jpeg(img) for img in _pdf_pages(data))
        else:
            try:
                img = Image.open(io.BytesIO(data))
                img.load()
            except (UnidentifiedImageError, OSError) as exc:
                raise UploadError(f"{f.name} isn't an image or PDF.") from exc
            pages.append(_to_jpeg(img))
        if len(pages) > settings.MAX_PAGES_PER_PAPER:
            raise UploadError(f"A paper can have at most {settings.MAX_PAGES_PER_PAPER} pages.")
    if not pages:
        raise UploadError("Add at least one photo or PDF of the paper.")
    return pages


# --- Papers ------------------------------------------------------------------------------


def check_upload_limit(user):
    since = timezone.now() - timedelta(days=1)
    if Paper.objects.filter(uploaded_by=user, created_at__gte=since).count() >= settings.UPLOADS_PER_USER_PER_DAY:
        raise LimitReached("You've uploaded a lot today, thank you! Please continue tomorrow.")


def create_paper(*, user, course, year, semester, kind, files):
    check_upload_limit(user)
    pages = files_to_pages(files)  # validate everything before touching the database
    try:
        with transaction.atomic():
            paper = Paper.objects.create(
                course=course, year=year, semester=semester, kind=kind, uploaded_by=user,
                status=Paper.Status.PROCESSING if ai.enabled() else Paper.Status.NEEDS_TEXT,
            )
            for order, (jpeg, (w, h)) in enumerate(pages):
                page = PaperPage(paper=paper, order=order, width=w, height=h)
                page.image.save(f"page-{order + 1}.jpg", ContentFile(jpeg), save=False)
                page.save()
    except IntegrityError as exc:
        raise UploadError("This paper has already been uploaded.") from exc

    if ai.enabled():
        if settings.RUN_TASKS_INLINE:
            read_paper(paper.id)
        else:  # start reading only once the pages are safely saved
            transaction.on_commit(lambda: run_in_background(read_paper, paper.id))
    return paper


def known_topics(course):
    return set(
        Question.objects.filter(paper__course=course).exclude(topic="").values_list("topic", flat=True).distinct()
    )


def read_paper(paper_id):
    """Use AI to turn the page images into questions."""
    paper = Paper.objects.select_related("course__university").get(pk=paper_id)
    images = []
    for page in paper.pages.all():
        with page.image.open("rb") as fh:
            images.append(fh.read())
    try:
        instructions, questions = ai.read_paper(str(paper.course) + f" — {paper.course.title}", images,
                                                known_topics(paper.course))
    except ai.AIError as exc:
        logger.warning("Reading paper %s failed: %s", paper_id, exc)
        paper.status, paper.processing_error = Paper.Status.NEEDS_TEXT, str(exc)[:300]
        paper.save(update_fields=["status", "processing_error"])
        return

    with transaction.atomic():
        replace_questions(paper, questions)
        paper.instructions = instructions
        paper.status = Paper.Status.READY if questions else Paper.Status.NEEDS_TEXT
        paper.processing_error = "" if questions else "No questions were found. Please type them in."
        paper.save(update_fields=["instructions", "status", "processing_error"])


def replace_questions(paper, questions):
    """Replace a paper's questions. Explanations of questions whose text didn't change are kept."""
    old = {(q.number, q.text): q for q in paper.questions.select_related("explanation")}
    keep_ids = []
    for order, data in enumerate(questions):
        existing = old.pop((data["number"], data["text"]), None)
        if existing:
            existing.order, existing.marks, existing.topic = order, data.get("marks"), data.get("topic", "")
            existing.save(update_fields=["order", "marks", "topic"])
            keep_ids.append(existing.id)
        else:
            keep_ids.append(Question.objects.create(paper=paper, order=order, **data).id)
    paper.questions.exclude(id__in=keep_ids).delete()


def run_in_background(func, *args):
    if settings.RUN_TASKS_INLINE:
        func(*args)
        return

    def target():
        try:
            func(*args)
        except Exception:
            logger.exception("Background task %s failed", func.__name__)
        finally:
            close_old_connections()

    threading.Thread(target=target, daemon=True).start()


# --- Explanations ------------------------------------------------------------------------


def get_or_create_explanation(question, user):
    """Return the cached explanation, generating it once if needed."""
    existing = Explanation.objects.filter(question=question).first()
    if existing:
        return existing, False

    since = timezone.now() - timedelta(days=1)
    if ExplanationRequest.objects.filter(user=user, created_at__gte=since).count() >= settings.EXPLANATIONS_PER_USER_PER_DAY:
        raise LimitReached("You've reached today's limit for new explanations. Explanations others have unlocked are still free.")
    ExplanationRequest.objects.create(user=user)

    course = question.paper.course
    text = ai.explain(f"{course} — {course.title}", question)
    try:
        with transaction.atomic():
            return Explanation.objects.create(question=question, text=text, model=settings.AI_MODEL, requested_by=user), True
    except IntegrityError:  # someone else generated it at the same moment
        return Explanation.objects.get(question=question), False


def vote(explanation, user, value):
    from .models import ExplanationVote

    with transaction.atomic():
        vote_obj, created = ExplanationVote.objects.get_or_create(explanation=explanation, user=user, defaults={"value": value})
        if not created and vote_obj.value != value:
            vote_obj.value = value
            vote_obj.save(update_fields=["value"])
        explanation.helpful = explanation.votes.filter(value=1).count()
        explanation.not_helpful = explanation.votes.filter(value=-1).count()
        explanation.save(update_fields=["helpful", "not_helpful"])
    return explanation
