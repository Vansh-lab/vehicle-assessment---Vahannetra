.PHONY: dev test seed migrate build clean shell logs smoke aws-preflight

COMPOSE_FILE=docker-compose.dev.yml

dev:
	docker compose -f $(COMPOSE_FILE) up --build

test:
	cd vehicle_assessment_backend && PYTHONPATH=. pytest tests/ -v --asyncio-mode=auto --cov=app --cov=ml

seed:
	docker compose -f $(COMPOSE_FILE) exec api python scripts/seed_garages.py

migrate:
	docker compose -f $(COMPOSE_FILE) exec api alembic upgrade head

build:
	docker compose -f $(COMPOSE_FILE) build

clean:
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans

shell:
	docker compose -f $(COMPOSE_FILE) exec api bash

logs:
	docker compose -f $(COMPOSE_FILE) logs -f api worker

smoke:
	bash scripts/test_api.sh http://localhost:8000

aws-preflight:
	bash scripts/aws_deploy_preflight.sh
