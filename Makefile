.PHONY: up down migrate seed collect test loadtest fmt
up: ; docker compose up --build
down: ; docker compose down -v
migrate: ; docker compose exec backend python manage.py migrate
seed: ; docker compose exec backend python manage.py seed_sources
collect: ; docker compose exec backend python manage.py collect
test: ; docker compose exec backend pytest -v --cov --cov-report=term
fmt: ; docker compose exec backend black backend || true
logs: ; docker compose logs -f
health: ; curl -sf http://localhost:8000/health/ | jq .
loadtest: ; k6 run --env BASE_URL=http://localhost:8000 devops/loadtest/k6.js
ps: ; docker compose ps
