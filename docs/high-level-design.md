# High-Level Design (HLD) — Quantsmind OSINT Platform

> This document is the authoritative HLD and follows the approved diagram exactly. No layer is added, removed, or reordered.

## 1. Diagram

![HLD](./diagrams/high-level-design.svg)

> Source: `docs/diagrams/high-level-design.svg` (dark background, faithful to the approved image) and `docs/diagrams/high-level-design.mmd` (Mermaid, version-controlled, renders on GitHub/mermaid.live).

### Mermaid (copy-paste to https://mermaid.live)

```mermaid
flowchart TD
    A[Public data sources<br/><sub>Websites, news, social media, forums, public APIs, RSS</sub>]
    B[Collection layer (Python)<br/><sub>Scrapy, Playwright, API connectors — scheduled by Celery beat</sub>]
    C[Ingestion queue<br/><sub>Redis / RabbitMQ / Kafka</sub>]
    D{{Storage layer}} --> D1[(PostgreSQL<br/><sub>Structured records</sub>)] & D2[(Elasticsearch<br/><sub>Full-text search</sub>)] & D3[(Object storage<br/><sub>Raw HTML, media, S3/MinIO</sub>)]
    E[Processing and NLP layer<br/><sub>Entity extraction, sentiment, topic modeling, dedup, language ID</sub>]
    F[Backend API (Django + DRF)<br/><sub>REST + WebSocket (Django Channels) for real-time updates</sub>]
    G[Frontend (Vue.js)<br/><sub>Dashboards, geo maps, trend charts, alerts</sub>]
    H[Security (cross-cutting)<br/><sub>Auth OAuth2/JWT, RBAC · Encryption in transit/at rest · Audit logging</sub>]
    I[DevOps (cross-cutting)<br/><sub>Docker + Compose/Kubernetes · Git + CI/CD · Prometheus/Grafana</sub>]
    A --> B --> C --> D --> E --> F --> G
```

## 2. Layers (top → bottom, as in diagram)

| # | Diagram box | Responsibility | Concrete components in this repo |
|---|-------------|----------------|----------------------------------|
| 1 | **Public data sources** | External, public-only inputs | Websites, news, social media, forums, public APIs, RSS — configured via `sources.Source` (`backend/sources/models.py:1`) |
| 2 | **Collection layer (Python)** — *Scrapy, Playwright, API connectors — scheduled by Celery beat* | Scheduled/on-demand scraping & API polling | `collectors/rss_collector.py:1`, `collectors/scrapy_collector.py:1`, `collectors/news_api_collector.py:1`, `collectors/policies.py:1` (`PolicyEnforcer`), `collectors/tasks.py:1` `poll_source`/`poll_all_sources`, Celery Beat schedule `config/celery.py:1` |
| 3 | **Ingestion queue** — *Redis / RabbitMQ / Kafka* | Decouples collectors from storage, absorbs bursts, retries | Primary: `redis:7` (`docker-compose.yml:17`), Celery broker `CELERY_BROKER_URL` (`backend/config/settings.py:104`). Pluggable via `QUEUE_BACKEND` — see `docker-compose.yml:17` profiles for `rabbitmq`/`kafka` and `docs/architecture.md:1` |
| 4 | **Storage layer** (3 sub-boxes) | Durable persistence by access pattern | **PostgreSQL** structured records (`backend/ingestion/models.py:1` `CollectedDocument`/`RawArtifact`), **Elasticsearch** full-text (`backend/processing/search.py:1` monthly `osint-documents-YYYY.MM`), **Object storage** raw HTML/media S3/MinIO (`backend/config/settings.py:109`, `minio` service `docker-compose.yml:39`) |
| 5 | **Processing and NLP layer** — *Entity extraction, sentiment, topic modeling, dedup, language ID* | Enrichment & dedup | `backend/processing/nlp.py:1` (`extract_entities`, `analyze_sentiment`, `detect_language`, `extract_topics`, dedup via `hash` in `backend/ingestion/models.py:1`), `backend/processing/tasks.py:1` `enrich_document`/`enrich_pending`, HF `transformers` + `spaCy` |
| 6 | **Backend API (Django + DRF)** — *REST + WebSocket (Django Channels) for real-time updates* | Business logic, auth, live push | Django + DRF (`backend/config/urls.py:1`), Channels `backend/config/asgi.py:1` + `backend/alerts/consumers.py:1` + `backend/alerts/routing.py:1`, OpenAPI `drf-spectacular` at `/api/docs/` |
| 7 | **Frontend (Vue.js)** — *Dashboards, geo maps, trend charts, alerts* | Analyst UX | Vue 3 + Pinia + Vue Router (`frontend/src/router.js:1`), ECharts `frontend/src/views/Dashboard.vue:1`, Leaflet `frontend/src/views/MapView.vue:1`, alerts/watchlists `frontend/src/views/AlertsView.vue:1` |

### Cross-cutting (bottom, two boxes side-by-side — not sequenced vertically)

| Box | Content (verbatim from diagram) | Repo mapping |
|-----|---------------------------------|--------------|
| **Security (cross-cutting)** | Auth (OAuth2/JWT), RBAC · Encryption in transit/at rest · Audit logging | JWT `rest_framework_simplejwt` (`backend/config/settings.py:90`), RBAC `backend/accounts/permissions.py:1` (`IsAdmin`/`IsAnalyst`), TLS `SECURE_*` (`backend/config/settings.py:127`), Vault/Secrets via env + `k8s/secret.example.yaml:1`, audit `backend/audit/middleware.py:1` + `backend/audit/models.py:1` |
| **DevOps (cross-cutting)** | Docker + Compose/Kubernetes · Git + CI/CD pipelines · Monitoring: Prometheus/Grafana | `docker-compose.yml:1`, `k8s/*.yaml`, `.github/workflows/ci.yml:1`, `devops/prometheus.yml:1` |

## 3. Data flow (arrows in diagram)

```
Public data sources
  ↓
Collection layer (Celery Beat triggers poll_all_sources every 15m; poll_source per Source)
  ↓  PolicyEnforcer checks robots.txt + rate_limit_rps + allowed_domains before fetch
Ingestion queue (Redis list / Celery task queue; RabbitMQ/Kafka interchangeable via config)
  ↓  Workers deduplicate (sha256 hash + URL), write raw HTML to S3 (RawArtifact), metadata to PostgreSQL
Storage layer (PostgreSQL + Elasticsearch + S3 are the durable sinks)
  ↓
Processing and NLP layer (enrich_pending picks status=raw, runs NER/sentiment/topic/lang, writes Enrichment, indexes to Elasticsearch)
  ↓
Backend API (serves search/filter/aggregation from ES+PG; pushes Alert via Channels group user_{id})
  ↓
Frontend (polls REST, subscribes to ws/alerts/ for live updates, renders dashboards)
```

Security & DevOps are **orthogonal**: they apply to every layer (auth at API, TLS at ingress, encryption for PG/S3, audit at middleware, CI scans container + deps, Prometheus scrapes `backend:8000`).

## 4. Compliance notes tied to HLD

- Only public data; `collectors/policies.py:1` enforces `respects_robots`, `rate_limit_rps`, `block_auth_required`, `block_paywall`.
- Every `CollectedDocument` retains `url` + `collected_at` + `content_html_s3_key` (`backend/ingestion/models.py:1`) for traceability to source.
- `CollectionPolicy.jurisdiction` allows per-source/per-jurisdiction tuning without code change.

## 5. File map to diagram

- Diagram SVG: `docs/diagrams/high-level-design.svg`
- Diagram Mermaid: `docs/diagrams/high-level-design.mmd`
- Detailed layer table & NFRs: `docs/architecture.md`
- Data model: `docs/data-model.md`
- Security checklist: `docs/security-checklist.md`
