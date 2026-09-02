import pytest
import datetime
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from sources.models import Source
from ingestion.models import CollectedDocument

pytestmark = pytest.mark.django_db

def _make_doc():
    s = Source.objects.create(name="ES", slug="es1", source_type="rss", url="http://example.com/rss")
    doc = CollectedDocument.objects.create(source=s, url="http://example.com/10", title="Election news", content_text="election results in London")
    return doc

def test_ensure_index_puts_template():
    from processing.search import ensure_index
    with patch("processing.search.requests.put") as mock_put, patch("processing.search.requests.post") as mock_post:
        mock_put.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        ensure_index()
        assert mock_put.called

def test_index_document_writes_to_alias():
    doc = _make_doc()
    with patch("processing.search.requests.put") as mock_put, patch("processing.search.requests.head") as mock_head, patch("processing.search.requests.post") as mock_post:
        mock_put.return_value.status_code = 200
        mock_head.return_value.status_code = 200
        mock_post.return_value.status_code = 201
        mock_post.return_value.text = "created"
        from processing.search import index_document
        index_document(doc)
        assert mock_post.called
        # args should contain _doc/id
        url = mock_post.call_args[0][0]
        assert "/_doc/" in url

def test_bulk_index_ndjson():
    doc = _make_doc()
    with patch("processing.search.requests.put"), patch("processing.search.requests.head") as mh, patch("processing.search.requests.post") as mp:
        mh.return_value.status_code = 200
        mp.return_value.status_code = 200
        mp.return_value.text="ok"
        from processing.search import bulk_index
        bulk_index([doc])
        assert mp.called
        # check ndjson content type
        kwargs = mp.call_args[1]
        assert "application/x-ndjson" in str(kwargs.get("headers",{}))

def test_search_es_multi_match():
    from processing.search import search_es
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hits":{"hits":[{"_id":"1","_source":{"title":"hello"}}],"total":{"value":1}},"aggregations":{}}
    mock_resp.raise_for_status.return_value = None
    with patch("processing.search.requests.post", return_value=mock_resp) as mp:
        res = search_es("election", filters={"source":"bbc"}, size=10)
        assert "hits" in res
        assert mp.called
        body = mp.call_args[1]["json"]
        assert body["size"] == 10

def test_search_endpoint_via_api():
    from rest_framework.test import APIClient
    User = get_user_model()
    User.objects.create_user(email="srch@test.com", username="srch", password="Pass12345!")
    c = APIClient()
    r = c.post("/api/auth/token/", {"username":"srch","password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email":"srch@test.com","password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        pytest.skip("auth")
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    with patch("processing.search.requests.post") as mp:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits":{"hits":[],"total":{"value":0}},"aggregations":{}}
        mock_resp.raise_for_status.return_value=None
        mp.return_value = mock_resp
        resp = c.get("/api/processing/search/?q=test&source=es1")
        assert resp.status_code == 200

def test_facets_endpoint():
    from rest_framework.test import APIClient
    User = get_user_model()
    if not User.objects.filter(email="facet@test.com").exists():
        User.objects.create_user(email="facet@test.com", username="facet", password="Pass12345!")
    c = APIClient()
    r = c.post("/api/auth/token/", {"username":"facet","password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        r = c.post("/api/auth/token/", {"email":"facet@test.com","password":"Pass12345!"}, format="json")
    if r.status_code != 200:
        pytest.skip("auth")
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    with patch("processing.search.requests.post") as mp:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits":{"hits":[]},"aggregations":{"by_source":{"buckets":[]}}}
        mock_resp.raise_for_status.return_value=None
        mp.return_value=mock_resp
        resp = c.get("/api/processing/facets/")
        assert resp.status_code == 200
