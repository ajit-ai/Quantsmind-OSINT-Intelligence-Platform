from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from ingestion.models import CollectedDocument
from processing.models import Enrichment
from processing.nlp import enrich_text, simhash_near_dup
import hashlib

@shared_task(bind=True, max_retries=2, default_retry_delay=30, acks_late=True)
def enrich_document(self, doc_id):
    try:
        doc = CollectedDocument.objects.select_related("source").get(id=doc_id)
    except Exception as e:
        print(f"[enrich] doc not found {doc_id}: {e}")
        return {"error":"not_found"}
    # near-dup simhash check against recent 100 docs
    try:
        recent_hashes = list(CollectedDocument.objects.order_by("-collected_at").values_list("hash", flat=True)[:100])
        is_dup, new_hash = simhash_near_dup(doc.content_text or "", recent_hashes)
        # store canonical hash if missing
        if not doc.hash and new_hash:
            doc.hash = new_hash
            doc.save(update_fields=["hash"])
        if is_dup:
            print(f"[enrich] near-dup detected {doc_id}")
            # still enrich but mark
    except Exception as e:
        print(f"[enrich] simhash check failed {doc_id}: {e}")
    # run NLP — combine title+content for better signal
    text = f"{doc.title}\n{doc.content_text}"[:8000]
    try:
        result = enrich_text(text)
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=30)
        except MaxRetriesExceededError:
            doc.status = CollectedDocument.Status.FAILED
            doc.save(update_fields=["status"])
            return {"error": str(exc)}
    # persist enrichment
    Enrichment.objects.update_or_create(document=doc, defaults={
        "entities": result.get("entities", []),
        "sentiment": result.get("sentiment", {}),
        "topics": result.get("topics", []),
        "language": result.get("language","en"),
        "geo_locations": result.get("geo_locations", []),
    })
    doc.status = CollectedDocument.Status.ENRICHED
    # update language on doc for filtering
    if result.get("language"):
        doc.language = result["language"]
    doc.save(update_fields=["status","language","hash"] if doc.language else ["status","hash"])
    # index to ES (retry on failure, but don't mark failed if ES down)
    try:
        from processing.search import index_document
        index_document(doc)
        doc.status = CollectedDocument.Status.INDEXED
        doc.save(update_fields=["status"])
    except Exception as e:
        print(f"[enrich] ES index failed {doc_id}: {e}")
        # keep ENRICHED so it can be retried by periodic reindex
    # fire alerts
    try:
        from alerts.tasks import check_alerts_for_document
        check_alerts_for_document.delay(str(doc.id))
    except Exception as e:
        print(f"[enrich] alert dispatch failed {doc_id}: {e}")
    return str(doc.id)

@shared_task
def enrich_pending(batch=20):
    ids = list(CollectedDocument.objects.filter(status="raw").order_by("collected_at").values_list("id", flat=True)[:batch])
    for doc_id in ids:
        enrich_document.delay(str(doc_id))
    if ids:
        print(f"[enrich_pending] queued {len(ids)} docs")
    return len(ids)

@shared_task
def reindex_failed(limit=50):
    # Re-attempt ES index for ENRICHED but not INDEXED
    from processing.search import index_document
    docs = CollectedDocument.objects.filter(status="enriched").select_related("source").prefetch_related("enrichment")[:limit]
    ok = 0
    for doc in docs:
        try:
            index_document(doc)
            doc.status = CollectedDocument.Status.INDEXED
            doc.save(update_fields=["status"])
            ok += 1
        except Exception as e:
            print(f"[reindex] failed {doc.id}: {e}")
    return {"reindexed": ok}
