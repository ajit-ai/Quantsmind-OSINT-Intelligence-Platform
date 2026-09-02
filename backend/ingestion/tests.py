import pytest
from sources.models import Source
from ingestion.models import CollectedDocument
pytestmark = pytest.mark.django_db
def test_dedup_hash():
    s = Source.objects.create(name="T", slug="t", source_type="rss", url="http://example.com/rss")
    d1 = CollectedDocument.objects.create(source=s, url="http://example.com/1", title="hello", content_text="same content")
    d2 = CollectedDocument.objects.create(source=s, url="http://example.com/2", title="hello2", content_text="same content")
    assert d1.hash == d2.hash
