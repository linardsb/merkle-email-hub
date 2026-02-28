.PHONY: dev dev-be dev-fe docker docker-down test lint types check db e2e e2e-all install-hooks security-check

# === Local Development ===

dev: ## Start backend + frontend in parallel
	@echo "Starting backend on :8891 and frontend on :3000..."
	@(uv run uvicorn app.main:app --reload --port 8891 &) && \
	(cd cms && pnpm --filter web dev)

dev-be: ## Start backend dev server
	uv run uvicorn app.main:app --reload --port 8891

dev-fe: ## Start frontend dev server
	cd cms && pnpm --filter web dev

# === Docker ===

docker: ## Build and start all services (local dev, port :80)
	@docker volume create merkle-email-hub_postgres_data 2>/dev/null || true
	AUTH_SECRET=$$(openssl rand -base64 32) docker-compose up -d --build

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Tail logs from all services
	docker-compose logs -f

# === Quality Checks ===

test: ## Run unit tests
	uv run pytest -v -m "not integration"

lint: ## Format + lint
	uv run ruff format .
	uv run ruff check --fix .

types: ## Run mypy + pyright
	uv run mypy app/
	uv run pyright app/

check: lint types test ## Run all checks (lint, types, tests)

e2e: ## Run all e2e tests
	cd cms && pnpm --filter web e2e

e2e-all: ## Run ALL e2e tests
	cd cms && pnpm --filter web e2e

e2e-ui: ## Open Playwright UI mode
	cd cms && pnpm --filter web e2e:ui

# === Database ===

db: ## Start only PostgreSQL + Redis
	@docker volume create merkle-email-hub_postgres_data 2>/dev/null || true
	AUTH_SECRET=dev-placeholder docker-compose up -d db redis

db-migrate: ## Run database migrations
	uv run alembic upgrade head

db-revision: ## Create a new migration (usage: make db-revision m="description")
	uv run alembic revision --autogenerate -m "$(m)"

# === Security ===

install-hooks: ## Install git pre-commit hook
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

security-check: ## Run security lint (Ruff Bandit rules)
	uv run ruff check app/ --select=S --no-fix

# === Help ===

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
