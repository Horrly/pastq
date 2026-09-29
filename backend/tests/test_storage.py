"""The production storage path: pages go to an S3-compatible bucket (mocked with moto)."""

import boto3
import pytest
from django.core.files.storage import storages
from moto import mock_aws

from papers.models import Paper

pytestmark = pytest.mark.django_db


@pytest.fixture
def s3_storage(settings):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="pastq-test")
        settings.STORAGES = {
            **settings.STORAGES,
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {"bucket_name": "pastq-test", "region_name": "us-east-1", "access_key": "x",
                            "secret_key": "y", "default_acl": None, "querystring_auth": True, "file_overwrite": False},
            },
        }
        storages._storages = {}  # rebuild storage objects from the new settings
        yield boto3.client("s3", region_name="us-east-1")
        storages._storages = {}


def test_pages_are_uploaded_to_the_bucket_and_served_with_signed_urls(s3_storage, upload, anon):
    res = upload()
    assert res.status_code == 201
    paper = Paper.objects.get()
    assert paper.status == "ready"  # the AI step read the page back from the bucket

    keys = [o["Key"] for o in s3_storage.list_objects_v2(Bucket="pastq-test")["Contents"]]
    assert keys == [paper.pages.get().image.name]
    assert keys[0].startswith("papers/oau-csc-201/")

    url = anon.get(f"/api/papers/{paper.id}/").data["pages"][0]["url"]
    assert "pastq-test" in url
    assert "Signature" in url  # signed, time-limited link to a private bucket
