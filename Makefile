.PHONY: up down restart logs build clean test lint format

# Always build before starting
up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up --build -d

logs:
	docker compose logs -f

build:
	docker compose build

clean:
	docker compose down -v

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
