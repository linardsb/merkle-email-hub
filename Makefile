.PHONY: dev dev-be dev-fe docker docker-down test test-fe lint types check check-fe db e2e e2e-all install-hooks security-check sdk seed-knowledge eval-verify eval-run eval-judge eval-labels eval-analysis eval-blueprint eval-regression eval-check eval-calibrate eval-qa-calibrate eval-dry-run eval-full eval-baseline

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

test: ## Run backend unit tests
	uv run pytest -v -m "not integration"

test-fe: ## Run frontend unit tests
	cd cms && pnpm --filter web test

lint: ## Format + lint
	uv run ruff format .
	uv run ruff check --fix .

types: ## Run mypy + pyright
	uv run mypy app/
	uv run pyright app/

check-fe: ## Run frontend checks (type-check + tests)
	cd cms && pnpm --filter web type-check
	cd cms && pnpm --filter web test

check: lint types test check-fe ## Run all checks (backend + frontend)

e2e: ## Run all e2e tests
	cd cms && pnpm --filter web e2e

e2e-all: ## Run ALL e2e tests
	cd cms && pnpm --filter web e2e

e2e-ui: ## Open Playwright UI mode
	cd cms && pnpm --filter web e2e:ui

# === SDK ===

sdk: ## Generate TypeScript SDK from backend OpenAPI spec (backend must be running)
	cd cms && pnpm --filter @merkle-email-hub/sdk generate-sdk:fetch

sdk-local: ## Generate TypeScript SDK from local openapi.json snapshot
	cd cms && pnpm --filter @merkle-email-hub/sdk generate-sdk

# === Database ===

db: ## Start only PostgreSQL + Redis
	@docker volume create merkle-email-hub_postgres_data 2>/dev/null || true
	AUTH_SECRET=dev-placeholder docker-compose up -d db redis

db-migrate: ## Run database migrations
	uv run alembic upgrade head

db-revision: ## Create a new migration (usage: make db-revision m="description")
	uv run alembic revision --autogenerate -m "$(m)"

# === Knowledge Base ===

seed-knowledge: ## Seed knowledge base with email dev content (requires DB + embedding provider)
	uv run python -m app.knowledge.seed

# === Eval Pipeline ===

eval-verify: ## Verify LLM provider is configured and responding
	uv run python -m app.ai.agents.evals.verify_provider

eval-run: eval-verify ## Run agent evals (generate traces)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --skip-existing

eval-judge: ## Run judges on traces (generate verdicts)
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --skip-existing

eval-labels: ## Scaffold human label templates from traces+verdicts
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/scaffolder_verdicts.jsonl --traces traces/scaffolder_traces.jsonl --output traces/scaffolder_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/dark_mode_verdicts.jsonl --traces traces/dark_mode_traces.jsonl --output traces/dark_mode_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/content_verdicts.jsonl --traces traces/content_traces.jsonl --output traces/content_human_labels.jsonl

eval-analysis: ## Analyze judge verdicts (failure taxonomy)
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json

eval-blueprint: ## Run blueprint pipeline evals
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl

eval-regression: ## Check for eval regressions vs baseline
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json

eval-check: eval-analysis eval-regression ## Full eval CI gate (analysis + regression check)

eval-calibrate: ## Calibrate judges against human labels (all 3 agents)
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/scaffolder_verdicts.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/scaffolder_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/dark_mode_verdicts.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/dark_mode_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/content_verdicts.jsonl --labels traces/content_human_labels.jsonl --output traces/content_calibration.json

eval-qa-calibrate: ## Calibrate QA gate against human labels (all 3 agents)
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/scaffolder_traces.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/qa_calibration_scaffolder.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/dark_mode_traces.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/qa_calibration_dark_mode.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/content_traces.jsonl --labels traces/content_human_labels.jsonl --output traces/qa_calibration_content.json

eval-dry-run: ## Full eval pipeline dry-run (no LLM needed)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --dry-run
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --dry-run
	$(MAKE) eval-labels
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl --dry-run
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json
	@echo "\n=== Dry-run pipeline complete ==="

eval-full: ## Full eval pipeline (requires LLM provider)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	$(MAKE) eval-regression
	@echo "\n=== Full eval pipeline complete ==="

eval-baseline: ## Run full eval pipeline and establish baseline (first time)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	cp traces/analysis.json traces/baseline.json
	@echo "\n=== Baseline established at traces/baseline.json ==="
	@echo "Commit traces/baseline.json to version control."

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
