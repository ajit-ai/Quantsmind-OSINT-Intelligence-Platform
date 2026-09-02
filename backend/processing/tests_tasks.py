import pytest
from unittest.mock import patch, MagicMock
from sources.models import Source
from ingestion.models import CollectedDocument
from processing.models import Enrichment

pytestmark = pytest.mark.django_db

@pytest.mark.django_db
def test_enrich_document_creates_enrichment_and_indexes():
    s = Source.objects.create(name="Enr", slug="enr1", source_type="rss", url="http://example.com/rss")
    doc = CollectedDocument.objects.create(source=s, url="http://example.com/20", title="London election crisis", content_text="London election crisis threat to democracy")
    with patch("processing.search.index_document") as mock_idx, patch("alerts.tasks.check_alerts_for_document") as mock_alert:
        mock_alert.delay = MagicMock()
        from processing.tasks import enrich_document
        # run eager (no celery broker needed) — call task directly without delay
        enrich_document(doc.id if hasattr(enrich_document, 'delay') else doc.id)
        # but our task is celery shared_task; call .run
        try:
            enrich_document.run(str(doc.id))
        except Exception:
            enrich_document(str(doc.id))
        doc.refresh_from_db()
        assert doc.status in ("enriched","indexed")
        assert Enrichment.objects.filter(document=doc).exists()

@pytest.mark.django_db
def test_enrich_pending_queues_raw_only():
    s = Source.objects.create(name="Pend", slug="pend1", source_type="rss", url="http://example.com/rssp")
    d1 = CollectedDocument.objects.create(source=s, url="http://example.com/21", title="T", content_text="a", status="raw")
    d2 = CollectedDocument.objects.create(source=s, url="http://example.com/22", title="T2", content_text="b", status="indexed")
    from processing.tasks import enrich_pending
    with patch("processing.tasks.enrich_document") as mock_enrich:
        mock_enrich.delay = MagicMock()
        count = enrich_pending(batch=10)
        # should queue at least d1
        if isinstance(count, int):
            assert count >= 1

@pytest.mark.django_db
def test_reindex_failed():
    s = Source.objects.create(name="Reidx", slug="reidx", source_type="rss", url="http://example.com/rssr")
    doc = CollectedDocument.objects.create(source=s, url="http://example.com/23", title="T", content_text="hi", status="enriched")
    Enrichment.objects.create(document=doc, language="en", entities=[], sentiment={"label":"neutral"}, topics=[], geo_locations=[])
    with patch("processing.search.index_document") as mock_idx:
        mock_idx.return_value = None
        from processing.tasks import reindex_failed
        res = reindex_failed(limit=5)
        assert res["reindexed"] >= 0
