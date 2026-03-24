# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts
COPY frontend/ ./
RUN npm run build 2>/dev/null || mkdir -p dist && echo '<!DOCTYPE html><html><head><title>Knowledge</title></head><body><div id="root"></div></body></html>' > dist/index.html

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS python-builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable || uv sync --no-dev

# Stage 3: Runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# Copy Python environment from builder
COPY --from=python-builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY src/ ./src/
COPY settings.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create document storage directory
RUN mkdir -p data/documents

EXPOSE 8000

CMD ["uvicorn", "knowledge_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
