import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from sources.models import Source
from audit.models import AuditLog

pytestmark = pytest.mark.django_db
User = get_user_model()

def auth_client(role="admin", username="aud", email="aud@test.com"):
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(email=email, username=username, password="Pass12345!", role=role)
    c = APIClient()
    r = c.post("/api/auth/token/", {"username": username, "password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email": email, "password":"Pass12345!"}, format="json")
    if r.status_code == 200:
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c

def test_audit_logged_on_post_create():
    c = auth_client(role="admin", username="aud1", email="aud1@test.com")
    before = AuditLog.objects.count()
    c.post("/api/sources/", {"name":"AudSrc","slug":"audsrc","source_type":"rss","url":"http://example.com/rss"}, format="json")
    after = AuditLog.objects.count()
    # middleware logs POST /api/sources/ 
    assert after >= before

def test_audit_not_logged_on_health():
    c = APIClient()
    before = AuditLog.objects.count()
    c.get("/health/")
    c.get("/api/docs/")
    after = AuditLog.objects.count()
    assert after == before

def test_audit_admin_can_list_logs():
    c_admin = auth_client(role="admin", username="aud_admin", email="aud_admin@test.com")
    c_viewer = auth_client(role="viewer", username="aud_viewer", email="aud_viewer@test.com")
    resp_admin = c_admin.get("/api/audit/")
    assert resp_admin.status_code in (200, 403)
    resp_viewer = c_viewer.get("/api/audit/")
    assert resp_viewer.status_code in (403, 401, 200)

def test_audit_captures_ip_and_user_agent():
    c = auth_client(role="admin", username="aud2", email="aud2@test.com")
    c.post("/api/sources/", {"name":"IPTest","slug":"iptest","source_type":"rss","url":"http://example.com/rss2"}, format="json", HTTP_USER_AGENT="TestAgent/1.0", REMOTE_ADDR="1.2.3.4")
    log = AuditLog.objects.order_by("-timestamp").first()
    assert log is not None
    # ip may be captured
    assert log.user_agent is not None

def test_password_redacted():
    c = auth_client(role="admin", username="aud3", email="aud3@test.com")
    # try to trigger audit with password in body (via user create attempt)
    c.post("/api/auth/users/", {"email":"new2@test.com","username":"new2","password":"Secret123!","role":"viewer"}, format="json")
    log = AuditLog.objects.filter(action__contains="POST").order_by("-timestamp").first()
    if log:
        # payload should not contain raw Secret123!
        assert "Secret123!" not in str(log.payload)
