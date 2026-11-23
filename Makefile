.PHONY: install lint format test up down migrate run

install:
	pip install -e ".[dev]"

lint:
	ruff check . && ruff format --check .

format:
	ruff check . --fix && ruff format .

test:
	pytest --cov=flowforge --cov-report=term-missing

up:
	docker compose up --build

down:
	docker compose down

migrate:
	alembic upgrade head

run:
	uvicorn flowforge.main:app --reload --app-dir src
