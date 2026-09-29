import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from papers.models import Course, University

User = get_user_model()


@pytest.fixture(autouse=True)
def test_settings(settings, tmp_path):
    settings.RUN_TASKS_INLINE = True
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.AI_PROVIDER = "fake"
    settings.AI_ENABLED = True
    settings.AI_MODEL = "fake-model"


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client


@pytest.fixture
def ada(db):
    return User.objects.create_user(username="ada", email="ada@example.com", password="Str0ng-pass-123")


@pytest.fixture
def tunde(db):
    return User.objects.create_user(username="tunde", email="tunde@example.com", password="Str0ng-pass-123")


@pytest.fixture
def ada_api(ada):
    return client_for(ada)


@pytest.fixture
def tunde_api(tunde):
    return client_for(tunde)


@pytest.fixture
def anon():
    return client_for()


@pytest.fixture
def oau(db):
    return University.objects.create(name="Obafemi Awolowo University", short_name="OAU")


@pytest.fixture
def csc201(oau):
    return Course.objects.create(university=oau, code="csc201", title="Computer Programming I", level=200)


def image_file(name="page.jpg", size=(2400, 3200), color="white", fmt="JPEG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def pdf_file(pages=2, name="paper.pdf"):
    buffer = io.BytesIO()
    images = [Image.new("RGB", (600, 800), "white") for _ in range(pages)]
    images[0].save(buffer, "PDF", save_all=True, append_images=images[1:])
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/pdf")


@pytest.fixture
def upload(ada_api, csc201):
    def _upload(files=None, client=None, **fields):
        data = {"course": csc201.slug, "year": 2023, "semester": "first", "kind": "exam", **fields}
        data["files"] = files if files is not None else [image_file()]
        return (client or ada_api).post("/api/papers/", data, format="multipart")

    return _upload
