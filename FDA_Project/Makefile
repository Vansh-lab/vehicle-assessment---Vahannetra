.PHONY: dev test seed migrate build clean shell logs smoke aws-preflight phase1-bootstrap phase1-verify phase2-verify phase3-verify

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

phase1-bootstrap:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.bootstrap_target_tree

phase1-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_scope_lock

phase2-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase2_backend

phase3-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase3_backend
