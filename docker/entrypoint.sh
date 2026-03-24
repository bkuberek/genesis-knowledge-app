#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head 2>&1 || echo "Warning: migrations may have failed"

echo "Starting Knowledge API..."
exec uvicorn knowledge_api.app:create_app --factory --host 0.0.0.0 --port 8000
