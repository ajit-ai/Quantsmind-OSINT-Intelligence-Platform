# Data Model

## ER Diagram (textual)
```
Source 1--* CollectionPolicy 1--* CollectedDocument *--* EntityMention
Source 1--* CollectedDocument
CollectedDocument 1--1 Enrichment
CollectedDocument *--1 RawArtifact (S3)
User *--* Role, User 1--* Watchlist 1--* WatchlistRule
WatchlistRule *--* Alert, Alert *--1 User
AuditLog (user, action, resource, timestamp)
```

## Tables

### source.Source
- id, name, slug, source_type (rss/news_api/scrape/social), url, config (JSON), is_active, created_at
### source.CollectionPolicy
- id, source_id, respects_robots, rate_limit_rps, allowed_domains[], block_auth_required, block_paywall, jurisdiction, notes
### ingestion.CollectedDocument
- id, source_id, url, canonical_url, title, content_text, content_html_s3_key, language, published_at, collected_at, hash (sha256), status (raw/enriched/indexed/failed)
### ingestion.RawArtifact
- id, document_id, s3_bucket, s3_key, content_type, size_bytes
### processing.Enrichment
- id, document_id, entities (JSON: [{text,type,start,end}]), sentiment (label+score), topics (JSON), language, summary, geo_locations (JSON), processed_at
### processing.Entity (normalized)
- id, name, entity_type (PERSON/ORG/GPE/EVENT), first_seen, last_seen
### accounts.User (custom)
- id, email, role (admin/analyst/viewer), is_active, created_at
### alerts.Watchlist
- id, user_id, name, is_active
### alerts.WatchlistRule
- id, watchlist_id, rule_type (keyword/entity/topic/sentiment), value, threshold
### alerts.Alert
- id, rule_id, document_id, triggered_at, is_read, severity
### audit.AuditLog
- id, user_id, action, resource_type, resource_id, ip, user_agent, timestamp, payload (JSON)

## Elasticsearch Index: osint-documents-YYYY.MM
- doc_id, title, text, source, language, entities, sentiment, topics, geo, published_at, collected_at

## Retention & Indexing
- Postgres: primary store (years). ES: rolling monthly indices. S3: raw immutable.
- Deduplication: sha256(content_text) + canonical_url unique constraint.
