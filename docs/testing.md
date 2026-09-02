# Testing — Quantsmind OSINT Platform

> Run all: `docker compose exec backend pytest -v --cov` · `cd frontend && npm run test` · `k6 run devops/loadtest/k6.js`
> CI runs all on every push to `develop`/`main` (`.github/workflows/ci.yml:1`)

## 1. Matrix (code → test file → type)

| Layer (HLD) | Code | Existing test | New test (this doc) | Type | Command |
|-------------|------|---------------|---------------------|------|---------|
| **Accounts / Auth** | `backend/accounts/models.py:1` `views.py:1` `permissions.py:1` | `backend/accounts/tests.py:1` (create_user, jwt_obtain) | `backend/accounts/tests_auth.py` `test_permissions.py` | Unit + API (pytest-django, DRF APIClient) | `pytest backend/accounts -v` |
| **Sources / Policies** | `backend/sources/models.py:1` `views.py:1` | — | `backend/sources/tests.py` | API + RBAC | `pytest backend/sources -v` |
| **Ingestion** | `backend/ingestion/models.py:1` `views.py:1` | `backend/ingestion/tests.py:1` (dedup hash) | `backend/ingestion/tests_api.py` `tests_s3.py` | Unit (hash/simhash) + API (stats/docs) + S3 mock (moto) | `pytest backend/ingestion -v` |
| **Processing / NLP** | `backend/processing/nlp.py:1` `search.py:1` `tasks.py:1` | — | `backend/processing/tests_nlp.py` `tests_search.py` `tests_tasks.py` | Unit (NER/sentiment/lang/topic/geo) + ES mock (responses) + Celery eager | `pytest backend/processing -v` |
| **Alerts / WS** | `backend/alerts/models.py:1` `views.py:1` `consumers.py:1` `tasks.py:1` | — | `backend/alerts/tests_api.py` `tests_ws.py` | API (watchlist CRUD) + Channels WebSocket (Communicator) | `pytest backend/alerts -v` |
| **Audit** | `backend/audit/middleware.py:1` `views.py:1` | — | `backend/audit/tests.py` | Integration (admin only, redaction) | `pytest backend/audit -v` |
| **Collectors** | `collectors/policies.py:1` `rss_collector.py:1` `scrapy_collector.py:1` `news_api_collector.py:1` `tasks.py:1` | — | `collectors/tests_policies.py` `tests_collectors.py` `tests_tasks.py` | Unit (robots/cache/throttle) + mocked requests/feedparser + Celery eager | `pytest collectors -v --import-mode=importlib` |
| **Frontend (Vue)** | `frontend/src/views/Dashboard.vue:1` `SearchView.vue:1` `MapView.vue:1` `AlertsView.vue:1` `SourcesView.vue:1` `stores/auth.js:1` | — | `frontend/src/__tests__/Dashboard.spec.js` `SearchView.spec.js` `MapView.spec.js` `AlertsView.spec.js` `stores/auth.spec.js` | Component (Vitest+jsdom+Vue Test Utils) | `npm run test --prefix frontend` |
| **E2E** | Full stack | — | `e2e/tests.spec.js` (Playwright) | E2E (login→seed→collect→search→alert WS) | `npx playwright test` |
| **Infra / K8s** | `docker-compose.yml:1` `k8s/*.yaml` | — | `tests/k8s/test_manifests.py` (kubeval) | Static (kubeval + compose config) | `kubeval k8s/*.yaml; docker compose config` |
| **Load** | `devops/loadtest/k6.js:1` | ✅ exists | — | Perf (k6: 20→50 users, p95<500ms) | `k6 run --env BASE_URL=http://localhost:8000 devops/loadtest/k6.js` |
| **Security** | `backend/config/settings.py:1` (TLS/HSTS/JWT) | Via CI bandit/pip-audit/trivy | `backend/tests_security.py` | SAST (bandit), SCA (pip-audit), container (trivy) | `bandit -r backend; pip-audit; trivy fs .` |

## 2. Backend — Test Cases (pytest)

### 2.1 Accounts (`backend/accounts/tests.py:1` + new `tests_auth.py`)

```python
# tests_auth.py — add to backend/accounts/
- test_create_user_role_defaults_to_analyst          # model default
- test_create_superuser_role_admin                   # is_admin()
- test_jwt_obtain_pair_success (username+password)  # POST /api/auth/token/ 200 + access+refresh
- test_jwt_obtain_wrong_password_401
- test_jwt_refresh_rotates_and_blacklists            # POST /api/auth/token/refresh/ + blacklist
- test_jwt_blacklist_blocks_reuse                    # POST /api/auth/token/blacklist/
- test_me_endpoint_requires_auth_401
- test_rbac_admin_can_list_users_admin_only          # GET /api/auth/users/ (IsAdmin)
- test_rbac_viewer_can_list_self_but_not_create
- test_analyst_cannot_promote_to_admin               # PATCH /api/auth/users/{id} role=admin → 403
```

### 2.2 Sources (`backend/sources/tests.py`)

```python
- test_source_crud_admin_only (create/update/delete 403 for viewer)
- test_source_list_authenticated
- test_policy_rate_limit_clamped_0_1_to_10
- test_trigger_requires_analyst (anon 401, viewer 403, analyst 200 queues poll_source)
- test_trigger_inactive_source_400
- test_policy_str_respects_robots
- test_collection_interval_default_15m
```

### 2.3 Ingestion (`backend/ingestion/tests.py:1` existing + `tests_api.py`)

```python
# existing: test_dedup_hash — sha256("same content") equal
# new:
- test_url_dedup_skips_duplicate (POST via poll_source)
- test_hash_unique_constraint (direct create duplicate hash → IntegrityError)
- test_list_documents_search_filter (GET /api/documents/?search=hello)
- test_filter_by_status_and_language
- test_stats_endpoint_aggregates_by_status_source_language (GET /api/documents/stats/)
- test_s3_artifact_created_on_ingest (moto mock s3.put_object + head)
- test_content_hash_auto_set_on_save
```

### 2.4 Processing (`backend/processing/tests_nlp.py`, `tests_search.py`, `tests_tasks.py`)

```python
# tests_nlp.py — no DB, no ES, no HF download needed (mocks where heavy)
- test_extract_entities_person_org_gpe (spaCy en_core_web_sm, "Barack Obama visited Paris")
- test_sentiment_lexicon_positive_negative_neutral ("great crisis" → negative, "excellent" → positive)
- test_sentiment_hf_mocked_positive (patch _get_hf_sentiment to return mock pipeline)
- test_detect_language_en_fr_de
- test_extract_topics_capitalized_phrases
- test_extract_geo_london_maps_to_lat_lon
- test_enrich_text_combines_all_keys
- test_simhash_near_dup_detects_close_hash (threshold)
# tests_search.py — mock requests via responses
- test_ensure_index_puts_template_and_alias
- test_index_document_writes_to_alias (mock POST _doc)
- test_bulk_index_ndjson_format
- test_search_es_multi_match_and_filters
- test_search_es_aggregations_by_source_sentiment
# tests_tasks.py — Celery eager (CELERY_TASK_ALWAYS_EAGER=True)
- test_enrich_document_creates_enrichment_and_indexes
- test_enrich_pending_queues_raw_only
- test_reindex_failed_retries_enriched
```

### 2.5 Alerts (`backend/alerts/tests_api.py`, `tests_ws.py`)

```python
# tests_api.py
- test_create_watchlist_owner_is_request_user
- test_watchlist_queryset_scoped_to_user (analyst sees own only, admin sees all)
- test_create_rule_keyword_entity_topic_sentiment
- test_alert_trigger_on_keyword_in_doc_text (enrich → check_alerts_for_document → Alert created)
- test_alert_ws_pushed_to_user_group (ChannelLayer group_send called)
- test_mark_read_and_read_all
- test_owner_or_admin_object_perm (other user cannot delete watchlist → 403)
# tests_ws.py (Channels Communicator)
- test_ws_connect_with_jwt_token_query_param_ok (ws/alerts/?token=<JWT> → connected)
- test_ws_connect_anon_rejected_4401
- test_ws_ping_pong
- test_ws_receives_alert_message (send group alert_message → client gets json)
```

### 2.6 Audit (`backend/audit/tests.py`)

```python
- test_audit_logged_on_post_create (POST /api/sources/ → AuditLog exists, status recorded)
- test_audit_not_logged_on_health_or_docs (GET /health/ and /api/docs/ → no log)
- test_audit_ip_and_user_agent_captured (X-Forwarded-For)
- test_audit_admin_can_list_logs (GET /api/audit/ 200 for admin, 403 for viewer)
- test_password_redacted_in_payload (body_keys redacted, not raw password)
```

## 3. Collectors (`collectors/tests_*.py`)

```python
# tests_policies.py
- test_can_fetch_blocks_login_and_paywall_when_policy_true
- test_can_fetch_allows_when_policy_none
- test_allowed_domains_allowlist (allowed contains host → allow, not in list → block)
- test_respects_robots_cached (mock RobotFileParser.can_fetch false → block, second call uses cache)
- test_throttle_sleeps_for_rate_limit (policy rps=2 → second throttle sleeps ~0.5s)
# tests_collectors.py (mock requests/feedparser)
- test_collect_rss_parses_feed_and_respects_policy (mock feedparser.parse)
- test_collect_rss_fetch_full_text_when_flag (source.config fetch_full_text true → requests.get called)
- test_collect_scrape_requests_fallback_parses_quote (mock html with .quote → 1 item)
- test_collect_scrape_playwright_path_when_use_playwright_true (patch _fetch_playwright)
- test_collect_news_api_parses_gdelt_articles (mock requests.get json with articles)
# tests_tasks.py (pytest + celery eager, moto s3, responses ES)
- test_poll_source_saves_docs_and_s3 (mock collect_rss→[item], mock boto3 s3, moto bucket)
- test_poll_source_skips_dup_url_and_hash
- test_poll_source_retry_on_collector_exception (side_effect Exception → retry)
- test_poll_all_sources_queues_each_active
- test_dlq_push_on_max_retries (mock redis.lpush)
```

## 4. Frontend (Vitest + Vue Test Utils, jsdom) — `frontend/src/__tests__/`

```
frontend/src/__tests__/
  Dashboard.spec.js — mounts Dashboard.vue, mocks axios GET /api/documents/ + trends/facets, checks trend xAxis, table rows, polling not required (vitest timers)
  SearchView.spec.js — sets q+filters, clicks Search, mocks /api/processing/search/ → hits, checks highlight <mark>, agg chips
  MapView.spec.js — mocks leaflet import, axios /api/processing/geo/ → markers, checks L.marker called, fitAll called
  AlertsView.spec.js — mocks watchlists/alerts GET, tests createWatchlist POST + rule, markAllRead, WS not required (mock WebSocket)
  SourcesView.spec.js — mocks /api/sources/ → table rows, triggers POST /trigger/ success+error
  stores/auth.spec.js — pinia test: login → localStorage access set + header, refreshToken success, logout blacklists, interceptor 401→refresh
```

Example run:

```bash
npm install --prefix frontend
npm run test --prefix frontend  # vitest run (jsdom) — see frontend/vite.config.js:6
```

Set `frontend/vite.config.js:6` already has `test:{environment:'jsdom'}`; add to `package.json:10` script `"test":"vitest run"` existing.

## 5. E2E (Playwright) — `e2e/tests.spec.js`

```js
// e2e/tests.spec.js — requires running stack: `docker compose up`
- test('full flow: login as admin → seed → trigger BBC RSS → search → watchlist → alert', async ({page})=>{
    await page.goto('/login'); await page.fill('input[placeholder="Username"]','admin'); ...
    await page.goto('/sources'); await page.click('text=Collect now');
    await page.goto('/search'); await page.fill('input[placeholder="Search"]','election'); await page.click('text=Search');
    await expect(page.locator('text=open source')).toBeVisible();
    await page.goto('/alerts'); await page.fill('input[placeholder="Watchlist name"]','E2E'); ...
  })
```

Run: `npx playwright test --project=chromium`

## 6. Infra / K8s / Compose

```bash
# backend/tests_security.py (optional) — already via CI
pytest backend/tests_security.py -v  # asserts SECURE_* headers when DEBUG=0, JWT lifetimes

# Manifest lint (CI already does)
kubeval k8s/*.yaml          # fails on invalid k8s spec
docker compose config       # validates compose (no port clash, healthcheck syntax)
docker compose config --profile queue-rabbitmq | grep rabbitmq  # queue pluggability
```

## 7. Load / Performance

Already implemented `devops/loadtest/k6.js:1` (20→50 VUs, thresholds `http_req_failed<0.05`, `p95<500ms`):

```bash
k6 run --env BASE_URL=http://localhost:8000 devops/loadtest/k6.js
# or make loadtest (Makefile:11) → `k6 run --env BASE_URL=http://localhost:8000 devops/loadtest/k6.js`
```

CI does not run k6 (needs live stack); run locally before release or in nightly workflow.

## 8. How to Run (copy-paste)

```bash
# 1. Backend unit+API (needs postgres+redis; use docker stack or sqlite fallback)
docker compose up -d postgres redis elasticsearch minio
cp .env.example .env
docker compose exec backend pytest -v --cov --cov-report=term-missing

# To run only a layer:
docker compose exec backend pytest backend/accounts -v
docker compose exec backend pytest backend/processing/tests_nlp.py -v
docker compose exec backend pytest collectors/tests_policies.py --import-mode=importlib -v

# 2. Frontend
npm ci --prefix frontend && npm run test --prefix frontend
# watch: npx vitest --prefix frontend

# 3. E2E (needs stack up + frontend built)
docker compose up --build -d
npx playwright install --with-deps
npx playwright test

# 4. Security / lint (CI mirrors)
pip install bandit pip-audit
bandit -r backend -ll
pip-audit
trivy fs .

# 5. Load
k6 run devops/loadtest/k6.js
```

## 9. Coverage Expectations

| Area | Current in repo | After this plan | CI gate |
|------|-----------------|-----------------|---------|
| accounts/auth | 2 tests | 10 tests (RBAC+JWT lifecycle) | CI pytest --cov fails if <60% (add `--cov-fail-under=60`) |
| ingestion | 1 test | 7 tests (dedup+S3+stats) | — |
| processing/NLP | 0 | 14 tests (NER/sentiment/topics/geo/search/enrich) | — |
| collectors | 0 | 15 tests (policies+scrape/rss/news_api+tasks) | — |
| alerts/WS | 0 | 10 tests (CRUD+WS auth) | — |
| frontend | 0 | 6 spec files (~30 assertions) | CI: `npm run test` must pass |
| e2e | 0 | 1 flow (5 steps) | nightly |
| load | k6 | k6 | manual/nightly |

## 10. Files to Create Next (if you want me to scaffold them now)

```
backend/accounts/tests_auth.py
backend/accounts/tests_permissions.py
backend/sources/tests.py
backend/ingestion/tests_api.py
backend/processing/tests_nlp.py
backend/processing/tests_search.py
backend/processing/tests_tasks.py
backend/alerts/tests_api.py
backend/alerts/tests_ws.py
backend/audit/tests.py
collectors/tests_policies.py
collectors/tests_collectors.py
collectors/tests_tasks.py
frontend/src/__tests__/Dashboard.spec.js
frontend/src/__tests__/SearchView.spec.js
frontend/src/__tests__/MapView.spec.js
frontend/src/__tests__/AlertsView.spec.js
frontend/src/__tests__/SourcesView.spec.js
frontend/src/stores/__tests__/auth.spec.js
e2e/tests.spec.js
backend/tests_security.py
```

Say `scaffold tests` and I'll generate all files above (wired to the actual code, mocked ES/S3/Redis where needed) and push to `develop` → `main`.
