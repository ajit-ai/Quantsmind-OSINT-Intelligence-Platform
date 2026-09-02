from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ingestion.models import CollectedDocument
from .models import WatchlistRule, Alert

@shared_task
def check_alerts_for_document(doc_id):
    doc = CollectedDocument.objects.select_related("source").get(id=doc_id)
    text = f"{doc.title} {doc.content_text}".lower()
    enrichment = getattr(doc, "enrichment", None)
    entities = [e["text"].lower() for e in (enrichment.entities if enrichment else [])]
    for rule in WatchlistRule.objects.select_related("watchlist").filter(watchlist__is_active=True):
        triggered = False
        if rule.rule_type == "keyword" and rule.value.lower() in text: triggered = True
        elif rule.rule_type == "entity" and rule.value.lower() in entities: triggered = True
        elif rule.rule_type == "topic" and enrichment and rule.value.lower() in [t.lower() for t in enrichment.topics]: triggered = True
        elif rule.rule_type == "sentiment" and enrichment and enrichment.sentiment.get("label") == rule.value: triggered = True
        if triggered:
            alert = Alert.objects.create(rule=rule, document=doc)
            # push via WebSocket
            try:
                ch = get_channel_layer()
                async_to_sync(ch.group_send)(f"user_{rule.watchlist.user_id}", {"type":"alert.message", "data": {"alert_id": str(alert.id), "document": doc.title, "rule": rule.value}})
            except: pass
    return True
