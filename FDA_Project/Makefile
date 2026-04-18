.PHONY: dev test seed migrate build clean shell logs smoke aws-preflight

dev:
docker compose -f docker-compose.dev.yml up --build

test:
cd vehicle_assessment_backend && PYTHONPATH=. pytest tests/ -v --asyncio-mode=auto --cov=app --cov=ml

seed:
docker compose exec api python scripts/seed_garages.py

migrate:
docker compose exec api alembic upgrade head

build:
docker compose build

clean:
docker compose down -v --remove-orphans

shell:
docker compose exec api bash

logs:
docker compose logs -f api worker

smoke:
bash scripts/test_api.sh http://localhost:8000

aws-preflight:
bash scripts/aws_deploy_preflight.sh
