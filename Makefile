# Recipes must work identically under cmd.exe (Windows) and sh (Linux/macOS/CI):
# only call cross-platform tools, no shell-specific syntax. See AGENTS.md.

BACKEND := --directory backend
FRONTEND := --dir frontend

.PHONY: install dev-db dev-backend dev-frontend migrate test test-backend test-frontend lint format up down

install:
	uv sync $(BACKEND)
	pnpm $(FRONTEND) install

dev-db:
	docker compose up -d db

dev-backend:
	uv run $(BACKEND) uvicorn app.main:app --reload --port 8000

dev-frontend:
	pnpm $(FRONTEND) dev

migrate:
	uv run $(BACKEND) alembic upgrade head

test: test-backend test-frontend

test-backend:
	uv run $(BACKEND) pytest

test-frontend:
	pnpm $(FRONTEND) test

lint:
	uv run $(BACKEND) ruff check .
	uv run $(BACKEND) ruff format --check .
	uv run $(BACKEND) mypy
	pnpm $(FRONTEND) typecheck
	pnpm $(FRONTEND) lint

format:
	uv run $(BACKEND) ruff check --fix .
	uv run $(BACKEND) ruff format .

up:
	docker compose up --build

down:
	docker compose down
