.PHONY: dev test seed migrate build clean shell logs smoke

dev:
	docker compose -f docker-compose.yml up --build

test:
	cd vehicle_assessment_backend && PYTHONPATH=. pytest -q

seed:
	docker compose exec api python -c "from app.main import init_seed_data; init_seed_data()"

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
