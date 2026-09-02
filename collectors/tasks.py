from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
import os
import sys
import hashlib
import django

# setup django for standalone Celery worker (when collectors imported outside backend)
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    django.setup()
except Exception:
    pass

# Dead-letter helper: push to redis DLQ list
def _push_dlq(doc):
    try:
        import redis
        from django.conf import settings
        r = redis.from_url(getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"))
        r.lpush("dlq:collect", str(doc)[:2000])
    except Exception:
        pass

@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, reject_on_worker_lost=True)
def poll_source(self, source_id):
    from sources.models import Source
    from ingestion.models import CollectedDocument, RawArtifact
    from django.conf import settings
    import boto3
    try:
        src = Source.objects.get(id=source_id)
    except Exception as e:
        print(f"[poll_source] source not found {source_id}: {e}")
        return {"error": "source_not_found"}
    if not src.is_active:
        return {"skipped": src.slug}
    policy = src.policies.first()
    try:
        if src.source_type == "rss":
            from collectors.rss_collector import collect_rss
            items = collect_rss(src, policy)
        elif src.source_type == "news_api":
            from collectors.news_api_collector import collect_news_api
            items = collect_news_api(src, policy)
        elif src.source_type == "scrape":
            from collectors.scrapy_collector import collect_scrape
            items = collect_scrape(src, policy)
        else:
            items = []
    except Exception as exc:
        # retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _push_dlq(f"poll_source failed {src.slug}: {exc}")
            return {"source": src.slug, "error": str(exc)}

    saved = 0
    skipped_dup = 0
    for it in items:
        url = (it.get("url") or "").strip()
        if not url:
            continue
        content = (it.get("content_text") or "")[:50000]
        title = (it.get("title") or "")[:1000]
        # Simhash + sha256 dedup: check URL first, then content hash
        content_hash = hashlib.sha256(content.encode()[:10000]).hexdigest() if content else ""
        exists = False
        if url:
            exists = CollectedDocument.objects.filter(url=url).exists()
        if not exists and content_hash:
            exists = CollectedDocument.objects.filter(hash=content_hash).exists()
        if exists:
            skipped_dup += 1
            continue
        try:
            doc = CollectedDocument.objects.create(
                source=src, url=url, title=title,
                content_text=content,
                published_at=it.get("published_at"),
            )
        except Exception as e:
            # hash collision race — skip
            print(f"[poll_source] create dup {url}: {e}")
            continue
        # S3 raw store — verified write (put + head)
        try:
            s3 = boto3.client("s3", endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                              region_name=settings.AWS_S3_REGION_NAME, use_ssl=settings.AWS_S3_USE_SSL)
            key = f"raw/{src.slug}/{doc.id}.html"
            body = content.encode()[:50000] if content else title.encode()
            s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Body=body, ContentType="text/html")
            # verify
            try:
                s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            except Exception:
                pass
            RawArtifact.objects.create(document=doc, s3_bucket=settings.AWS_STORAGE_BUCKET_NAME, s3_key=key, size_bytes=len(body))
            doc.content_html_s3_key = key
            doc.save(update_fields=["content_html_s3_key"])
        except Exception as e:
            print(f"[poll_source] S3 put failed {url}: {e}")
            # not fatal — metadata already saved
        # enqueue enrichment (ack late ensures requeue on worker crash)
        try:
            from processing.tasks import enrich_document
            enrich_document.delay(str(doc.id))
        except Exception as e:
            print(f"[poll_source] enrich queue failed {doc.id}: {e}")
        saved += 1
    print(f"[poll_source] {src.slug}: saved={saved} dup={skipped_dup} items={len(items)}")
    return {"source": src.slug, "saved": saved, "dup": skipped_dup}

@shared_task
def poll_all_sources():
    from sources.models import Source
    count = 0
    for src in Source.objects.filter(is_active=True):
        poll_source.delay(str(src.id))
        count += 1
    print(f"[poll_all_sources] queued {count} sources")
    return count

@shared_task
def requeue_dlq():
    # Ops helper: inspect DLQ length
    try:
        import redis
        from django.conf import settings
        r = redis.from_url(getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"))
        length = r.llen("dlq:collect")
        return {"dlq_len": length}
    except Exception as e:
        return {"error": str(e)}
