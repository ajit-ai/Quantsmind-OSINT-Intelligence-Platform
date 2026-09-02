.PHONY: up down migrate seed collect test
up: ; docker compose up --build
down: ; docker compose down -v
migrate: ; docker compose exec backend python manage.py migrate
seed: ; docker compose exec backend python manage.py seed_sources
collect: ; docker compose exec backend python manage.py collect
test: ; docker compose exec backend pytest -v --cov
logs: ; docker compose logs -f
