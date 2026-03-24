#!/bin/sh
set -e

# Wait for PostgreSQL to accept connections before running migrations.
# This is needed because depends_on: service_started doesn't guarantee
# the database is actually ready to accept connections.
echo "Waiting for PostgreSQL..."
DB_HOST="${KNOWLEDGE_DATABASE__HOST:-postgres}"
DB_PORT="${KNOWLEDGE_DATABASE__PORT:-5432}"
MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
    if python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "PostgreSQL is ready."
        break
    fi
    if [ "$i" = "$MAX_RETRIES" ]; then
        echo "Warning: PostgreSQL not reachable after ${MAX_RETRIES} attempts, proceeding anyway..."
    else
        echo "Waiting for PostgreSQL... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    fi
done

echo "Running database migrations..."
alembic upgrade head 2>&1 || echo "Warning: migrations may have failed, will retry on next restart"

echo "Starting Knowledge API..."
exec uvicorn knowledge_api.app:create_app --factory --host 0.0.0.0 --port 8000
