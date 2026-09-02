import pytest
import types
from unittest.mock import patch, MagicMock
from django.test.utils import override_settings

pytestmark = pytest.mark.django_db

def _src_db(slug="tasksrc", source_type="rss"):
    from sources.models import Source
    return Source.objects.create(name=slug, slug=slug, source_type=source_type, url="http://example.com/rss")

@patch("collectors.tasks.boto3.client")
@patch("processing.tasks.enrich_document.delay")
def test_poll_source_saves_docs_and_s3(mock_enrich_delay, mock_boto):
    from collectors.tasks import poll_source
    src = _src_db(slug="s3test")
    mock_boto.return_value.put_object.return_value = {}
    mock_boto.return_value.head_object.return_value = {}
    fake_items = [{"url":"http://example.com/new1","title":"T1","content_text":"content one","published_at": None}]
    with patch("collectors.rss_collector.collect_rss", return_value=fake_items):
        res = poll_source.run(str(src.id)) if hasattr(poll_source, 'run') else poll_source(str(src.id))
        assert res["saved"] == 1 or res.get("saved")==1
        from ingestion.models import CollectedDocument
        assert CollectedDocument.objects.filter(url="http://example.com/new1").exists()
        assert mock_boto.return_value.put_object.called

@patch("collectors.tasks.boto3.client")
def test_poll_source_skips_dup(mock_boto):
    from collectors.tasks import poll_source
    src = _src_db(slug="duptest")
    mock_boto.return_value.put_object.return_value = {}
    mock_boto.return_value.head_object.return_value = {}
    fake_items = [{"url":"http://example.com/dup","title":"T","content_text":"same","published_at": None}]
    with patch("collectors.rss_collector.collect_rss", return_value=fake_items), \
         patch("processing.tasks.enrich_document.delay", new=MagicMock()):
        poll_source.run(str(src.id))
        # second poll same URL should be skipped
        with patch("collectors.rss_collector.collect_rss", return_value=fake_items):
            res2 = poll_source.run(str(src.id))
            assert res2["dup"] >= 1 or res2["saved"]==0

def test_poll_all_sources_queues():
    from collectors.tasks import poll_all_sources
    _src_db(slug="all1")
    _src_db(slug="all2")
    with patch("collectors.tasks.poll_source.delay") as mock_delay:
        mock_delay.return_value = None
        count = poll_all_sources.run() if hasattr(poll_all_sources, 'run') else poll_all_sources()
        assert mock_delay.call_count >= 2

def test_requeue_dlq():
    from collectors.tasks import requeue_dlq
    with patch("redis.from_url") as mock_redis:
        mock_redis.return_value.llen.return_value = 3
        res = requeue_dlq.run() if hasattr(requeue_dlq, 'run') else requeue_dlq()
        assert res["dlq_len"] == 3
