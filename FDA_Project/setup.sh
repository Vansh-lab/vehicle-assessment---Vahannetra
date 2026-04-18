#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

echo "[1/5] starting docker stack"
docker compose -f docker-compose.yml up -d --build

echo "[2/5] waiting for api container"
until docker compose exec -T api python -c "print('ready')" >/dev/null 2>&1; do
  sleep 2
done

echo "[3/5] applying migrations"
docker compose exec -T api alembic upgrade head

echo "[4/5] seeding data"
docker compose exec -T api python scripts/seed_garages.py

echo "[5/5] services status"
docker compose ps

echo "Setup complete. Frontend: http://localhost:3000 API: http://localhost:8000"
