from celery import shared_task
import os, sys, django
# setup django
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try: django.setup()
except: pass

@shared_task
def poll_source(source_id):
    from sources.models import Source
    from ingestion.models import CollectedDocument, RawArtifact
    from django.conf import settings
    import boto3
    src = Source.objects.get(id=source_id)
    policy = src.policies.first()
    # dispatch to correct collector
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
    saved = 0
    for it in items:
        if not it.get("url"): continue
        # dedup via URL + hash check
        exists = CollectedDocument.objects.filter(url=it["url"]).exists()
        if exists: continue
        doc = CollectedDocument.objects.create(
            source=src, url=it["url"], title=it.get("title","")[:1000],
            content_text=it.get("content_text","")[:50000],
            published_at=it.get("published_at"),
        )
        # store raw to S3 (best-effort)
        try:
            s3 = boto3.client("s3", endpoint_url=settings.AWS_S3_ENDPOINT_URL, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, region_name=settings.AWS_S3_REGION_NAME, use_ssl=settings.AWS_S3_USE_SSL)
            key = f"raw/{src.slug}/{doc.id}.html"
            s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Body=it.get("content_text","").encode()[:50000])
            RawArtifact.objects.create(document=doc, s3_bucket=settings.AWS_STORAGE_BUCKET_NAME, s3_key=key, size_bytes=len(it.get("content_text","")))
            doc.content_html_s3_key = key
            doc.save(update_fields=["content_html_s3_key"])
        except Exception as e:
            print(f"S3 put failed: {e}")
        # enqueue enrichment
        try:
            from processing.tasks import enrich_document
            enrich_document.delay(str(doc.id))
        except: pass
        saved += 1
    return {"source": src.slug, "saved": saved}

@shared_task
def poll_all_sources():
    from sources.models import Source
    count = 0
    for src in Source.objects.filter(is_active=True):
        poll_source.delay(str(src.id))
        count += 1
    return count
