# Quantsmind OSINT Intelligence Platform

Secure, scalable Open-Source Intelligence (OSINT) platform — collects, processes, and visualizes **publicly available data only** for real-time monitoring, trend analysis, and decision support. Built exactly to the approved high-level design (7 sequential layers + 2 cross-cutting concerns).

> **Stack:** Python · Scrapy/Playwright · Celery Beat · Redis/RabbitMQ/Kafka · PostgreSQL · Elasticsearch · MinIO (S3) · spaCy / Transformers · Django + DRF + Channels · Vue 3 + Pinia + ECharts + Leaflet · Docker/Compose/K8s · GitHub Actions · Prometheus/Grafana

## 1. Architecture — High-Level Design (authoritative)

![High-Level Design](docs/diagrams/high-level-design.svg)

> Source: `docs/diagrams/high-level-design.svg` (pixel-faithful to approved image, dark background) and `docs/diagrams/high-level-design.mmd` (Mermaid, version-controlled). Short link: `docs/high-level-design.md:1` | Detailed table: `docs/architecture.md:1`

**Mermaid (renders on GitHub, copy to https://mermaid.live):**

```mermaid
flowchart TD
    A[Public data sources<br/><sub>Websites, news, social media, forums, public APIs, RSS</sub>]
    B[Collection layer (Python)<br/><sub>Scrapy, Playwright, API connectors — scheduled by Celery beat</sub>]
    C[Ingestion queue<br/><sub>Redis / RabbitMQ / Kafka</sub>]
    D{{Storage layer}} --> D1[(PostgreSQL<br/><sub>Structured records</sub>)] & D2[(Elasticsearch<br/><sub>Full-text search</sub>)] & D3[(Object storage<br/><sub>Raw HTML, media, S3/MinIO</sub>)]
    E[Processing and NLP layer<br/><sub>Entity extraction, sentiment, topic modeling, dedup, language ID</sub>]
    F[Backend API (Django + DRF)<br/><sub>REST + WebSocket (Django Channels) for real-time updates</sub>]
    G[Frontend (Vue.js)<br/><sub>Dashboards, geo maps, trend charts, alerts</sub>]
    A --> B --> C --> D --> E --> F --> G
```

### 1.1 Layers — verbatim from diagram, top → bottom

| # | Diagram box | Purpose | Where in repo |
|---|-------------|---------|---------------|
| 1 | **Public data sources** — *Websites, news, social media, forums, public APIs, RSS* | Public-only inputs | `backend/sources/models.py:1` `Source` (seeded via `seed_sources`) |
| 2 | **Collection layer (Python)** — *Scrapy, Playwright, API connectors — scheduled by Celery beat* | Scheduled/on-demand scraping & API polling | `collectors/rss_collector.py:1`, `collectors/scrapy_collector.py:1`, `collectors/news_api_collector.py:1`, `collectors/policies.py:1` `PolicyEnforcer`, `collectors/tasks.py:1` `poll_source`/`poll_all_sources`, `backend/config/celery.py:1` |
| 3 | **Ingestion queue** — *Redis / RabbitMQ / Kafka* | Decouple collectors from storage, bursts, retries | `docker-compose.yml:17` `redis:7` (primary); pluggable `rabbitmq`/`kafka` profiles — swap `CELERY_BROKER_URL` (`backend/config/settings.py:104`) |
| 4 | **Storage layer** — 3 sub-boxes | Durable persistence | **PostgreSQL** structured (`backend/ingestion/models.py:1`), **Elasticsearch** full-text (`backend/processing/search.py:1` `osint-documents-YYYY.MM`), **Object storage** raw HTML/media S3/MinIO (`backend/config/settings.py:109`, `docker-compose.yml:39`) |
| 5 | **Processing and NLP layer** — *Entity extraction, sentiment, topic modeling, dedup, language ID* | Enrichment | `backend/processing/nlp.py:1`, `backend/processing/tasks.py:1` (spaCy/HF Transformers, langdetect, dedup sha256) |
| 6 | **Backend API (Django + DRF)** — *REST + WebSocket (Django Channels) for real-time updates* | Business logic, auth, live push, OpenAPI | `backend/config/urls.py:1`, `backend/config/asgi.py:1`, `backend/alerts/consumers.py:1` `ws/alerts/`, Swagger `/api/docs/` |
| 7 | **Frontend (Vue.js)** — *Dashboards, geo maps, trend charts, alerts* | Analyst UX | `frontend/src/router.js:1`, `frontend/src/views/Dashboard.vue:1` (ECharts), `frontend/src/views/MapView.vue:1` (Leaflet), `frontend/src/views/SearchView.vue:1`, `frontend/src/views/AlertsView.vue:1` |

### 1.2 Cross-cutting (diagram bottom — side-by-side, orthogonal to every layer)

| Box (verbatim) | What it covers | Implementation |
|----------------|----------------|----------------|
| **Security (cross-cutting)** — *Auth (OAuth2/JWT), RBAC · Encryption in transit/at rest · Audit logging* | Auth, RBAC, crypto, audit | SimpleJWT (`backend/config/settings.py:90`), RBAC `backend/accounts/permissions.py:1` (admin/analyst/viewer), TLS `SECURE_*`, Vault/AWS Secrets Manager + `k8s/secret.example.yaml:1`, audit `backend/audit/middleware.py:1`→`backend/audit/models.py:1` |
| **DevOps (cross-cutting)** — *Docker + Compose/Kubernetes · Git + CI/CD pipelines · Monitoring: Prometheus/Grafana* | Build, deploy, observe | `docker-compose.yml:1` (dev), `k8s/*.yaml` (prod), `.github/workflows/ci.yml:1` (lint/test/build/Trivy), `devops/prometheus.yml:1` + Grafana |

### 1.3 Data flow (arrows in diagram)

```
Public data sources
  ↓  Cron/Beat every 15m (+ on-demand POST /api/sources/{id}/trigger/)
Collection layer — PolicyEnforcer checks respects_robots + rate_limit_rps + allowed_domains + block_auth/paywall
  ↓
Ingestion queue — Redis (Celery task queue); RabbitMQ/Kafka via QUEUE_BACKEND env swap
  ↓  dedup (sha256 + canonical_url) → raw HTML → S3 (RawArtifact), metadata → PostgreSQL (status=raw)
Storage layer
  ↓  enrich_pending (every 2m) picks status=raw → NER/sentiment/topic/lang + geo → Enrichment → index ES (status→indexed) → check_alerts_for_document
Processing and NLP layer
  ↓
Backend API — serves search/filter/aggregation (ES+PG), pushes Alert via Channels group user_{id}
  ↓  REST + WebSocket
Frontend — polls REST, subscribes ws/alerts/, renders dashboards
```

Full NFRs, scalability, and tech mapping: `docs/architecture.md:1`. Data model: `docs/data-model.md:1`. Security gates: `docs/security-checklist.md:1`.

## 2. Quick Start

```bash
cp .env.example .env
docker compose up --build
# backend:  http://localhost:8000/api/        Swagger: http://localhost:8000/api/docs/
# frontend: http://localhost:5173  (prod nginx :3000)
# minio:    http://localhost:9001  (minioadmin/minioadmin, bucket: osint-raw)
# elasticsearch: http://localhost:9200
# grafana:  http://localhost:3001  (admin/admin)  prometheus: http://localhost:9090
```

Create admin & seed:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_sources
docker compose exec backend python manage.py collect --source bbc_rss   # or reuters_rss / gdelt_api / quotes_scrape
# trigger from API:
curl -X POST http://localhost:8000/api/sources/<id>/trigger/ -H "Authorization: Bearer <JWT>"
```

## 3. Services

| Service | Port | Description | Image / Build |
|---------|------|-------------|---------------|
| backend | 8000 | Django + DRF + Channels (Daphne) | `backend/Dockerfile:1` |
| celery_worker | — | Collection + enrichment workers | `backend/Dockerfile:1` `celery -A config worker` |
| celery_beat | — | Scheduler (poll every 15m, enrich every 2m) | `backend/Dockerfile:1` `celery -A config beat` |
| frontend | 5173/3000 | Vue 3 SPA (Vite dev:5173, nginx prod:80→3000) | `frontend/Dockerfile:1` |
| postgres | 5432 | Structured records | `postgres:16-alpine` |
| elasticsearch | 9200 | Full-text search (`osint-documents-YYYY.MM`) | `elasticsearch:8.12.0` |
| minio | 9000/9001 | S3-compatible raw HTML/media | `minio/minio` |
| redis | 6379 | Queue & cache (primary broker) | `redis:7-alpine` |
| prometheus | 9090 | Metrics | `prom/prometheus` |
| grafana | 3001 | Dashboards | `grafana/grafana` |

Swap queue: `docker-compose.yml:17` comment explains `rabbitmq:3` / `kafka` profiles — set `CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//` or `kafka://kafka:9092`.

## 4. API

- Auth: `POST /api/auth/token/` (SimpleJWT obtain), `POST /api/auth/token/refresh/`, `GET /api/auth/users/` (RBAC)
- Sources: `GET /api/sources/`, `POST /api/sources/{id}/trigger/` (IsAnalyst)
- Documents: `GET /api/documents/?search=&status=&language=&ordering=-collected_at` (SearchFilter, DjangoFilter)
- Processing: `GET /api/processing/search/?q=&source=` (ES proxy), `GET /api/processing/trends/`, `GET /api/processing/geo/`
- Alerts: `GET|POST /api/alerts/watchlists/`, `GET /api/alerts/` (user-scoped)
- Audit (admin): `GET /api/audit/`
- WebSocket: `ws/alerts/` (AuthMiddlewareStack → group `user_{id}` → `alert_message`)
- OpenAPI: `GET /api/schema/` + `GET /api/docs/` (Spectacular Swagger)

## 5. Security (cross-cutting)

- JWT short-lived access (15m) + refresh rotation (`backend/config/settings.py:90`), OAuth2-ready.
- RBAC: `admin` (full), `analyst` (collect + manage own watchlists), `viewer` (read-only) — enforced in `backend/accounts/permissions.py:1` + queryset scoping.
- TLS everywhere (`SECURE_SSL_REDIRECT`/`HSTS` when `DEBUG=0`), encryption at rest (PG volume/S3 SSE), secrets via Vault/AWS Secrets Manager (never in repo — `k8s/secret.example.yaml:1`).
- Audit: every `POST/PUT/PATCH/DELETE` + sensitive `GET /export` logged to `AuditLog` (`backend/audit/middleware.py:1`).
- Scraping compliance: `collectors/policies.py:1` respects `robots.txt`, rate limits, blocks auth/paywall, configurable per `sources.CollectionPolicy` + `jurisdiction`.

See `docs/security-checklist.md:1` for the full gate before release.

## 6. DevOps (cross-cutting)

- **Local:** `docker compose up --build` (`docker-compose.yml:1`), `Makefile` (`make up/down/migrate/seed/test/logs`)
- **Prod:** `k8s/*.yaml` (namespace, backend Deployment×2, postgres StatefulSet, Ingress TLS `osint.example.com`)
- **CI/CD:** `.github/workflows/ci.yml:1` — backend flake8+pytest, frontend `npm ci && build`, `docker compose config` + image builds, Trivy FS scan. Branch protection on `main` (this repo: `develop` → PR → `main`).
- **Monitoring:** `devops/prometheus.yml:1` scrapes `backend:8000`, Grafana at `:3001`; centralized logs via ELK/Loki (forward from backend).

## 7. Repository Layout

```
backend/        # Django 5 + DRF + Channels + Celery (accounts/sources/ingestion/processing/alerts/audit)
collectors/     # RSS/Scrapy/News-API collectors + PolicyEnforcer + Celery tasks (poll_source/poll_all_sources)
frontend/       # Vue 3 + Pinia + Router + ECharts + Leaflet (Dashboard/Search/Map/Alerts/Sources/Login)
k8s/            # Kubernetes manifests (prod) + secret.example.yaml
devops/         # prometheus.yml + grafana provisioning
docs/           # high-level-design.md (HLD), architecture.md, data-model.md, security-checklist.md, diagrams/
.github/        # workflows/ci.yml
docker-compose.yml  # 9-service local stack
.env.example    # all env vars with safe defaults
```

## 8. Testing

```bash
docker compose exec backend pytest -v --cov          # backend unit (accounts/tests.py, ingestion/tests.py)
cd frontend && npm run test                          # frontend vitest (jsdom)
docker compose exec backend flake8 backend --max-line-length=120
```

## 9. Compliance & Auditability

Only publicly available data. Every `CollectedDocument` retains `source.url` + `collected_at` + `content_html_s3_key` (S3) for source attribution. Scrapers honor `robots.txt`/ToS/rate limits; `CollectionPolicy` is configurable per source/jurisdiction without code change.

## 10. References

- HLD: `docs/high-level-design.md:1` (diagram SVG `docs/diagrams/high-level-design.svg:1`)
- Architecture deep-dive: `docs/architecture.md:1`
- Data model: `docs/data-model.md:1`
- Security review: `docs/security-checklist.md:1`

## License

Proprietary — Quantsmind.
