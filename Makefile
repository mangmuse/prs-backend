.PHONY: dev test lint format typecheck check migrate db

dev:
	uv run uvicorn src.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

typecheck:
	uv run mypy src/
	uv run basedpyright src/

check: lint format typecheck

migrate:
	uv run alembic upgrade head

db:
	docker-compose up -d
