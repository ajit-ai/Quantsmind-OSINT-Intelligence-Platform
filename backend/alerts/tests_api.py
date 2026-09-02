import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from sources.models import Source
from ingestion.models import CollectedDocument

pytestmark = pytest.mark.django_db
User = get_user_model()

def auth_client(username="alertuser", email="alert@test.com", role="analyst"):
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(email=email, username=username, password="Pass12345!", role=role)
    c = APIClient()
    r = c.post("/api/auth/token/", {"username":username,"password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email":email,"password":"Pass12345!"}, format="json")
    if r.status_code==200:
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c

def test_create_watchlist_and_rule():
    c = auth_client()
    resp = c.post("/api/alerts/watchlists/", {"name":"My Watchlist"}, format="json")
    assert resp.status_code in (201, 200)
    wl_id = resp.data["id"]
    resp2 = c.post(f"/api/alerts/watchlists/{wl_id}/rules/", {"watchlist": wl_id, "rule_type":"keyword", "value":"election"}, format="json")
    assert resp2.status_code in (201, 200)
    resp3 = c.get(f"/api/alerts/watchlists/{wl_id}/rules/")
    assert resp3.status_code == 200
    assert len(resp3.data) >= 1

def test_watchlist_scoped_to_user():
    c1 = auth_client(username="uA", email="a_alert@test.com", role="analyst")
    c2 = auth_client(username="uB", email="b_alert@test.com", role="analyst")
    r1 = c1.post("/api/alerts/watchlists/", {"name":"WL A"}, format="json")
    r2 = c2.post("/api/alerts/watchlists/", {"name":"WL B"}, format="json")
    # each sees at least own
    lst1 = c1.get("/api/alerts/watchlists/")
    ids1 = [x["id"] for x in (lst1.data.get("results", lst1.data) if isinstance(lst1.data, dict) else lst1.data)]
    assert r1.data["id"] in ids1

def test_alert_trigger_on_keyword(monkeypatch):
    from unittest.mock import MagicMock, patch
    c = auth_client(username="trig", email="trig@test.com")
    wl = c.post("/api/alerts/watchlists/", {"name":"Trig WL"}, format="json").data
    rule = c.post(f"/api/alerts/watchlists/{wl['id']}/rules/", {"watchlist": wl["id"], "rule_type":"keyword","value":"election"}, format="json").data
    s = Source.objects.create(name="AS", slug="alertsrc", source_type="rss", url="http://example.com/rss")
    doc = CollectedDocument.objects.create(source=s, url="http://example.com/30", title="Election results", content_text="election results in London")
    # enrich mock then check alerts
    from alerts.tasks import check_alerts_for_document
    with patch("alerts.tasks.get_channel_layer") as mock_chan:
        mock_chan.return_value.group_send = MagicMock()
        # run directly
        try:
            check_alerts_for_document.run(str(doc.id))
        except Exception:
            check_alerts_for_document(str(doc.id))
    from alerts.models import Alert
    assert Alert.objects.filter(rule_id=rule["id"], document=doc).exists()

def test_mark_read():
    c = auth_client(username="readu", email="read@test.com")
    wl = c.post("/api/alerts/watchlists/", {"name":"Read WL"}, format="json").data
    s = Source.objects.create(name="RS", slug="readsrc", source_type="rss", url="http://example.com/rssr2")
    doc = CollectedDocument.objects.create(source=s, url="http://example.com/31", title="X", content_text="election")
    from alerts.models import WatchlistRule, Alert
    rule = WatchlistRule.objects.create(watchlist_id=wl["id"], rule_type="keyword", value="election")
    alert = Alert.objects.create(rule=rule, document=doc)
    resp = c.post(f"/api/alerts/{alert.id}/read/")
    assert resp.status_code in (200, 204)
    alert.refresh_from_db()
    assert alert.is_read

def test_owner_cannot_delete_others_watchlist():
    c1 = auth_client(username="owner1", email="owner1@test.com")
    c2 = auth_client(username="owner2", email="owner2@test.com")
    wl = c1.post("/api/alerts/watchlists/", {"name":"Owner1 WL"}, format="json").data
    resp = c2.delete(f"/api/alerts/watchlists/{wl['id']}/")
    # either 404 (filtered) or 403
    assert resp.status_code in (404, 403, 401)
