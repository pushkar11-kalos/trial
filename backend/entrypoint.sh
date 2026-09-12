#!/bin/sh
set -e

echo "[metracheck] Running database migrations..."
python -m alembic upgrade head

echo "[metracheck] Seeding demo data (idempotent -- skips if already seeded)..."
python -m app.seed

echo "[metracheck] Starting MetraCheck API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
