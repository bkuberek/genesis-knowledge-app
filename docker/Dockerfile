# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

ARG VITE_KEYCLOAK_URL=http://localhost:8080

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS python-builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

# Stage 3: Runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# Copy Python environment from builder
COPY --from=python-builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source and config
COPY src/ ./src/
COPY settings.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create document storage directory
RUN mkdir -p data/documents

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
