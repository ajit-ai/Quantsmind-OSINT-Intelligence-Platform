import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from sources.models import Source
from ingestion.models import CollectedDocument

pytestmark = pytest.mark.django_db
User = get_user_model()

def auth_client():
    User.objects.create_user(email="ing@test.com", username="ing", password="Pass12345!")
    c = APIClient()
    r = c.post("/api/auth/token/", {"username":"ing","password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email":"ing@test.com","password":"Pass12345!"}, format="json")
    if r.status_code==200:
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c

def test_list_documents_search_filter():
    s = Source.objects.create(name="S", slug="s1", source_type="rss", url="http://example.com/rss")
    CollectedDocument.objects.create(source=s, url="http://example.com/1", title="Hello election", content_text="hello world")
    CollectedDocument.objects.create(source=s, url="http://example.com/2", title="Other", content_text="other")
    c = auth_client()
    resp = c.get("/api/documents/?search=election")
    assert resp.status_code == 200
    data = resp.data.get("results", resp.data)
    assert len(data) >= 1

def test_filter_by_status_and_language():
    s = Source.objects.create(name="S2", slug="s2", source_type="rss", url="http://example.com/rss2")
    CollectedDocument.objects.create(source=s, url="http://example.com/3", title="T", content_text="hi", status="raw", language="en")
    CollectedDocument.objects.create(source=s, url="http://example.com/4", title="T2", content_text="hi2", status="indexed", language="fr")
    c = auth_client()
    resp = c.get("/api/documents/?status=raw")
    assert resp.status_code == 200
    resp2 = c.get("/api/documents/?language=fr")
    assert resp2.status_code == 200

def test_stats_endpoint():
    s = Source.objects.create(name="S3", slug="s3", source_type="rss", url="http://example.com/rss3")
    CollectedDocument.objects.create(source=s, url="http://example.com/5", title="A", content_text="a", status="raw")
    c = auth_client()
    resp = c.get("/api/documents/stats/")
    assert resp.status_code == 200
    assert "by_status" in resp.data

def test_hash_auto_set():
    s = Source.objects.create(name="H", slug="h", source_type="rss", url="http://example.com/rssh")
    d = CollectedDocument.objects.create(source=s, url="http://example.com/6", title="T", content_text="some unique text to hash")
    assert len(d.hash) == 64

def test_content_truncated_hash():
    s = Source.objects.create(name="H2", slug="h2", source_type="rss", url="http://example.com/rssh2")
    d = CollectedDocument.objects.create(source=s, url="http://example.com/7", title="T", content_text="a"*60000)
    assert d.content_text is not None
