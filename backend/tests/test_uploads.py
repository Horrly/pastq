import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from conftest import image_file, pdf_file
from papers import ai
from papers.models import Paper

pytestmark = pytest.mark.django_db


def test_upload_reads_questions_with_ai(upload):
    res = upload(files=[image_file(), image_file()])
    assert res.status_code == 201
    paper = Paper.objects.get()
    assert paper.status == "ready"
    assert paper.pages.count() == 2
    assert paper.questions.count() == 4  # the fake provider writes 2 per page
    assert paper.instructions.startswith("Answer any FOUR")
    assert set(paper.questions.values_list("topic", flat=True)) >= {"Data structures", "Algorithms"}


def test_pages_are_resized_jpegs(upload):
    upload(files=[image_file(size=(3000, 4000), fmt="PNG", name="page.png")])
    page = Paper.objects.get().pages.get()
    assert max(page.width, page.height) == 1800
    with page.image.open("rb") as fh:
        assert Image.open(fh).format == "JPEG"


def test_pdf_becomes_page_images(upload):
    res = upload(files=[pdf_file(pages=3)])
    assert res.status_code == 201
    assert Paper.objects.get().pages.count() == 3


def test_rejects_non_images(upload):
    res = upload(files=[SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")])
    assert res.status_code == 400 and "isn't an image or PDF" in res.data["detail"]
    assert Paper.objects.count() == 0


def test_rejects_too_many_pages(upload, settings):
    settings.MAX_PAGES_PER_PAPER = 2
    res = upload(files=[pdf_file(pages=3)])
    assert res.status_code == 400


def test_requires_files(upload):
    assert upload(files=[]).status_code == 400


def test_requires_login(upload, anon):
    assert upload(client=anon).status_code == 401


def test_duplicate_paper_points_to_existing(upload):
    first = upload().data["id"]
    res = upload()
    assert res.status_code == 409 and res.data["paper_id"] == first


def test_future_year_rejected(upload):
    assert upload(year=2999).status_code == 400


def test_without_ai_paper_needs_typing(upload, settings):
    settings.AI_PROVIDER, settings.AI_ENABLED = "", False
    res = upload()
    assert res.data["status"] == "needs_text"
    assert Paper.objects.get().questions.count() == 0


def test_ai_failure_falls_back_to_typing(upload, monkeypatch):
    def boom(*args, **kwargs):
        raise ai.AIError("AI provider error 500")

    monkeypatch.setattr(ai, "complete", boom)
    upload()
    paper = Paper.objects.get()
    assert paper.status == "needs_text" and "500" in paper.processing_error


def test_daily_upload_limit(upload, settings):
    settings.UPLOADS_PER_USER_PER_DAY = 1
    assert upload().status_code == 201
    assert upload(year=2022).status_code == 429
