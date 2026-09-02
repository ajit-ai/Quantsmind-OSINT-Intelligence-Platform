import os, requests, datetime
from django.conf import settings

ES_URL = getattr(settings, "ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX_PREFIX = "osint-documents"

def index_name():
    return f"{INDEX_PREFIX}-{datetime.datetime.utcnow().strftime('%Y.%m')}"

def ensure_index():
    try:
        requests.put(f"{ES_URL}/{index_name()}", json={
            "mappings": {"properties": {
                "doc_id": {"type": "keyword"},
                "title": {"type": "text"},
                "text": {"type": "text"},
                "source": {"type": "keyword"},
                "language": {"type": "keyword"},
                "entities": {"type": "nested", "properties": {"text": {"type": "keyword"}, "type": {"type": "keyword"}}},
                "sentiment": {"type": "object", "properties": {"label": {"type": "keyword"}, "score": {"type": "float"}}},
                "published_at": {"type": "date"},
                "collected_at": {"type": "date"},
            }}
        }, timeout=5)
    except: pass

def index_document(doc):
    ensure_index()
    enrichment = getattr(doc, "enrichment", None)
    body = {
        "doc_id": str(doc.id),
        "title": doc.title,
        "text": doc.content_text[:10000],
        "source": doc.source.slug if doc.source_id else "",
        "language": enrichment.language if enrichment else doc.language,
        "entities": enrichment.entities if enrichment else [],
        "sentiment": enrichment.sentiment if enrichment else {},
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "collected_at": doc.collected_at.isoformat() if doc.collected_at else None,
    }
    requests.post(f"{ES_URL}/{index_name()}/_doc/{doc.id}", json=body, timeout=5)

def search_es(query, filters=None):
    try:
        must = []
        if query: must.append({"multi_match": {"query": query, "fields": ["title^2","text"]}})
        if filters:
            for k,v in filters.items(): must.append({"term": {k: v}})
        resp = requests.post(f"{ES_URL}/{INDEX_PREFIX}-*/_search", json={"query": {"bool": {"must": must or [{"match_all":{}}]}}, "size": 20, "sort": [{"collected_at":"desc"}]}, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "hits": {"hits": []}}
