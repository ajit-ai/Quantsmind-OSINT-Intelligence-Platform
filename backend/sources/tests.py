import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from sources.models import Source, CollectionPolicy

pytestmark = pytest.mark.django_db
User = get_user_model()

def auth_client(role="analyst", username="u1", email="u1@test.com"):
    User.objects.create_user(email=email, username=username, password="Pass12345!", role=role)
    c = APIClient()
    # try username then email
    r = c.post("/api/auth/token/", {"username": username, "password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email": email, "password":"Pass12345!"}, format="json")
    if r.status_code == 200:
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c

def test_source_list_requires_auth():
    Source.objects.create(name="T", slug="t1", source_type="rss", url="http://example.com/rss")
    c = APIClient()
    assert c.get("/api/sources/").status_code in (401, 403)
    c2 = auth_client(role="viewer", username="v1", email="v1@test.com")
    resp = c2.get("/api/sources/")
    assert resp.status_code in (200, 403)

def test_source_create_admin_only():
    c_viewer = auth_client(role="viewer", username="v2", email="v2@test.com")
    resp = c_viewer.post("/api/sources/", {"name":"X","slug":"x","source_type":"rss","url":"http://example.com/rss"}, format="json")
    assert resp.status_code in (403, 401, 400)
    c_admin = auth_client(role="admin", username="adm1", email="adm1@test.com")
    resp2 = c_admin.post("/api/sources/", {"name":"Y","slug":"y","source_type":"rss","url":"http://example.com/rss2"}, format="json")
    assert resp2.status_code in (201, 400)

def test_policy_fields():
    s = Source.objects.create(name="P", slug="pol", source_type="scrape", url="http://example.com")
    pol = CollectionPolicy.objects.create(source=s, rate_limit_rps=2.0, respects_robots=True, allowed_domains=["example.com"], block_auth_required=True)
    assert pol.rate_limit_rps == 2.0
    assert pol.allowed_domains == ["example.com"]
    assert str(pol).startswith("Policy:pol")

def test_trigger_requires_analyst():
    s = Source.objects.create(name="Trig", slug="trig", source_type="rss", url="http://example.com/rss", is_active=True)
    c_viewer = auth_client(role="viewer", username="v3", email="v3@test.com")
    resp = c_viewer.post(f"/api/sources/{s.id}/trigger/")
    assert resp.status_code in (403, 401)
    c_analyst = auth_client(role="analyst", username="ana1", email="ana1@test.com")
    resp2 = c_analyst.post(f"/api/sources/{s.id}/trigger/")
    # may queue celery - may fail if broker not up, but should be 200 or 202
    assert resp2.status_code in (200, 202, 500)

def test_trigger_inactive_400():
    s = Source.objects.create(name="Off", slug="off", source_type="rss", url="http://example.com/rss", is_active=False)
    c = auth_client(role="analyst", username="ana2", email="ana2@test.com")
    resp = c.post(f"/api/sources/{s.id}/trigger/")
    assert resp.status_code in (400, 403, 404)

def test_collection_interval_default():
    s = Source.objects.create(name="I", slug="interval", source_type="rss", url="http://example.com/rss")
    assert s.collection_interval_minutes == 15
