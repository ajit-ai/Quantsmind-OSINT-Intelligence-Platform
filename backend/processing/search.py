import datetime
import hashlib
import requests
from django.conf import settings

ES_URL = getattr(settings, "ELASTICSEARCH_URL", "http://elasticsearch:9200").rstrip("/")
INDEX_PREFIX = "osint-documents"
ALIAS = f"{INDEX_PREFIX}-current"

def index_name():
    return f"{INDEX_PREFIX}-{datetime.datetime.utcnow().strftime('%Y.%m')}"

# --- Index template + alias + ILM (monthly rollover) ---
def ensure_index():
    # Template for monthly indices + alias
    try:
        # Put index template
        requests.put(f"{ES_URL}/_index_template/{INDEX_PREFIX}", json={
            "index_patterns": [f"{INDEX_PREFIX}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {"analyzer": {"default": {"type": "standard"}}}
                },
                "mappings": {
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "text": {"type": "text"},
                        "source": {"type": "keyword"},
                        "language": {"type": "keyword"},
                        "entities": {"type": "nested", "properties": {"text": {"type": "keyword"}, "type": {"type": "keyword"}}},
                        "sentiment": {"type": "object", "properties": {"label": {"type": "keyword"}, "score": {"type": "float"}}},
                        "topics": {"type": "keyword"},
                        "geo": {"type": "nested", "properties": {"name": {"type":"keyword"},"lat":{"type":"float"},"lon":{"type":"float"}}},
                        "published_at": {"type": "date"},
                        "collected_at": {"type": "date"},
                        "hash": {"type": "keyword"},
                    }
                }
            },
            "priority": 500
        }, timeout=5)
    except Exception as e:
        print(f"[es] template put failed: {e}")
    # Create concrete monthly index if missing
    idx = index_name()
    try:
        resp = requests.put(f"{ES_URL}/{idx}", json={}, timeout=5)
        # Alias current -> this month (best-effort)
        if resp.status_code in (200, 201):
            try:
                requests.post(f"{ES_URL}/_aliases", json={"actions":[{"add":{"index": idx, "alias": ALIAS}}]}, timeout=5)
            except Exception:
                pass
    except Exception as e:
        print(f"[es] ensure index {idx} failed: {e}")

def index_document(doc):
    ensure_index()
    enrichment = getattr(doc, "enrichment", None)
    body = {
        "doc_id": str(doc.id),
        "title": doc.title or "",
        "text": (doc.content_text or "")[:10000],
        "source": doc.source.slug if doc.source_id else "",
        "language": (enrichment.language if enrichment else "") or doc.language or "en",
        "entities": enrichment.entities if enrichment else [],
        "sentiment": enrichment.sentiment if enrichment else {},
        "topics": enrichment.topics if enrichment else [],
        "geo": enrichment.geo_locations if enrichment and hasattr(enrichment, "geo_locations") else (getattr(enrichment, "geo_locations", []) if enrichment else []),
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "collected_at": doc.collected_at.isoformat() if doc.collected_at else None,
        "hash": doc.hash or hashlib.sha256((doc.content_text or "").encode()[:10000]).hexdigest(),
    }
    # Use alias for writes so rollover is transparent
    target = ALIAS
    try:
        # check alias exists, else fallback to concrete
        r = requests.head(f"{ES_URL}/{ALIAS}", timeout=2)
        if r.status_code != 200:
            target = index_name()
    except Exception:
        target = index_name()
    try:
        resp = requests.post(f"{ES_URL}/{target}/_doc/{doc.id}", json=body, timeout=8)
        if resp.status_code not in (200,201):
            print(f"[es] index write {resp.status_code}: {resp.text[:500]}")
    except Exception as e:
        print(f"[es] index_document failed {doc.id}: {e}")
        raise

def bulk_index(docs):
    ensure_index()
    # NDJSON bulk API for throughput
    lines = []
    idx = ALIAS
    try:
        r = requests.head(f"{ES_URL}/{ALIAS}", timeout=2)
        if r.status_code != 200: idx = index_name()
    except Exception:
        idx = index_name()
    for doc in docs:
        enrichment = getattr(doc, "enrichment", None)
        meta = {"index": {"_index": idx, "_id": str(doc.id)}}
        body = {
            "doc_id": str(doc.id), "title": doc.title or "", "text": (doc.content_text or "")[:5000],
            "source": doc.source.slug if doc.source_id else "",
            "language": (enrichment.language if enrichment else "") or "en",
            "entities": enrichment.entities if enrichment else [],
            "sentiment": enrichment.sentiment if enrichment else {},
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "collected_at": doc.collected_at.isoformat() if doc.collected_at else None,
        }
        import json as _json
        lines.append(_json.dumps(meta))
        lines.append(_json.dumps(body))
    if not lines: return
    try:
        ndjson = "\n".join(lines) + "\n"
        resp = requests.post(f"{ES_URL}/_bulk", data=ndjson, headers={"Content-Type":"application/x-ndjson"}, timeout=15)
        if resp.status_code != 200:
            print(f"[es] bulk {resp.status_code}: {resp.text[:800]}")
    except Exception as e:
        print(f"[es] bulk_index failed: {e}")

def search_es(query, filters=None, size=20, sort="collected_at", enrich_filters=None):
    # enrich_filters: {sentiment: positive, entity: "London"}
    try:
        must = []
        filt = []
        if query:
            must.append({"multi_match": {"query": query, "fields": ["title^3","text"], "type":"best_fields", "operator":"and"}})
        if filters:
            for k,v in filters.items():
                if "." in k:
                    # nested e.g. sentiment.label
                    path = k.split(".")[0]
                    filt.append({"nested": {"path": path, "query": {"term": {k: v}}}} if path in ("entities","sentiment","geo") else {"term":{k:v}})
                else:
                    filt.append({"term": {k: v}})
        if enrich_filters:
            for k,v in enrich_filters.items():
                filt.append({"term": {k: v}})
        body = {
            "query": {"bool": {"must": must or [{"match_all":{}}], "filter": filt}},
            "size": size,
            "sort": [{sort: "desc"}],
            "highlight": {"fields": {"text": {}, "title": {}}},
            "aggs": {
                "by_source": {"terms": {"field":"source"}},
                "by_sentiment": {"terms": {"field":"sentiment.label"}},
                "by_language": {"terms": {"field":"language"}},
            }
        }
        # search across monthly indices
        resp = requests.post(f"{ES_URL}/{INDEX_PREFIX}-*/_search", json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[es] search failed q={query}: {e}")
        return {"error": str(e), "hits": {"hits": [], "total": {"value":0}}, "aggregations": {}}
