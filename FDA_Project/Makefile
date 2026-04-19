.PHONY: dev test test-47-matrix frontend-lint frontend-build frontend-e2e seed migrate build clean shell logs smoke aws-preflight phase1-bootstrap phase1-verify phase2-verify phase3-verify phase4-verify phase5-verify phase6-verify phase7-verify

dev:
	docker compose -f docker-compose.dev.yml up --build

test:
	cd vehicle_assessment_backend && PYTHONPATH=. pytest tests/ -v --asyncio-mode=auto --cov=app --cov=ml

test-47-matrix:
	cd vehicle_assessment_backend && CASE_COUNT=$$(PYTHONPATH=. pytest tests/test_dsq_v2.py --collect-only -q | grep -c "test_dsq_v2_47_case_matrix_contract\\[case") && echo "Collected DSQ matrix cases: $$CASE_COUNT" && test "$$CASE_COUNT" -eq 47

frontend-lint:
	cd vahannetra_frontend && rm -rf .next && npm run lint

frontend-build:
	cd vahannetra_frontend && npm run build

frontend-e2e:
	cd vahannetra_frontend && npm run test:e2e

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

phase4-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase4

phase5-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase5

phase6-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase6

phase7-verify:
	cd .. && PYTHONPATH=. python -m vahannetra.scripts.verify_phase7
