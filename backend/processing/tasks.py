from celery import shared_task
from ingestion.models import CollectedDocument
from .models import Enrichment
from .nlp import enrich_text

@shared_task
def enrich_document(doc_id):
    doc = CollectedDocument.objects.get(id=doc_id)
    result = enrich_text(f"{doc.title} {doc.content_text}")
    Enrichment.objects.update_or_create(document=doc, defaults={
        "entities": result["entities"],
        "sentiment": result["sentiment"],
        "topics": result["topics"],
        "language": result["language"],
    })
    doc.status = CollectedDocument.Status.ENRICHED
    doc.save(update_fields=["status"])
    # index to ES (best-effort)
    try:
        from .search import index_document
        index_document(doc)
        doc.status = CollectedDocument.Status.INDEXED
        doc.save(update_fields=["status"])
    except Exception as e:
        print(f"ES index failed: {e}")
    # check alerts
    try:
        from alerts.tasks import check_alerts_for_document
        check_alerts_for_document.delay(str(doc.id))
    except: pass
    return str(doc.id)

@shared_task
def enrich_pending():
    ids = CollectedDocument.objects.filter(status="raw").values_list("id", flat=True)[:20]
    for doc_id in ids:
        enrich_document.delay(str(doc_id))
    return len(list(ids))
