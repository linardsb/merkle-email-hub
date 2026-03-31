.PHONY: dev dev-be dev-fe dev-mock-esp dev-observe docker docker-down test test-fe lint types check check-fe db e2e install-hooks security-check sdk seed-knowledge ontology-sync ontology-sync-dry sync-ontology eval-verify eval-run eval-judge eval-labels eval-labeling-tool eval-analysis eval-blueprint eval-regression eval-check eval-calibrate eval-qa-calibrate eval-qa-coverage eval-dry-run eval-full eval-baseline eval-skill-test eval-golden eval-suggest cli-setup cli-list cli-search cli docker-logs test-properties e2e-ui sdk-local db-migrate db-revision db-squash eval-refresh seed-demo demo bench e2e-firefox e2e-webkit e2e-all-browsers e2e-smoke skill-versions skill-pin skill-unpin skill-rollback grafana help

# === Local Development ===

up: ## Bootstrap dev env after restart (Docker + DB + migrations + seed)
	@./scripts/startup.sh

dev: ## Start backend + frontend in parallel
	@echo "Syncing ontology to sidecar..."
	@cd services/maizzle-builder && npm run sync-ontology 2>/dev/null || echo "Ontology sync skipped (run npm install in services/maizzle-builder first)"
	@echo "Starting backend on :8891 and frontend on :3000..."
	@(uv run uvicorn app.main:app --reload --port 8891 &) && \
	(cd cms && pnpm --filter web dev)

dev-be: ## Start backend dev server
	uv run uvicorn app.main:app --reload --port 8891

dev-fe: ## Start frontend dev server
	cd cms && pnpm --filter web dev

dev-mock-esp: ## Start mock ESP server
	cd services/mock-esp && uvicorn main:app --reload --port 3002

seed-demo: ## Seed database with demo data (admin user, project, components)
	uv run python -m app.seed_demo

demo: db db-migrate seed-demo ## Full demo: start infra, migrate, seed, launch all services
	@echo "Starting mock ESP (:3002), backend (:8891), frontend (:3000)..."
	@(cd services/mock-esp && uvicorn main:app --port 3002 &) && \
	(uv run uvicorn app.main:app --reload --port 8891 &) && \
	(cd cms && pnpm --filter web dev)

# === Docker ===

docker: ## Build and start all services (local dev, port :80)
	@docker volume create email-hub_postgres_data 2>/dev/null || true
	AUTH_SECRET=$$(openssl rand -base64 32) docker-compose up -d --build

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Tail logs from all services
	docker-compose logs -f

dev-observe: ## Start all services + observability stack (Grafana :3333, Loki :3100)
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build

grafana: ## Open Grafana dashboard in browser
	open http://localhost:3333

# === Quality Checks ===

test: ## Run backend unit tests
	uv run pytest -v -m "not integration and not benchmark and not visual_regression and not collab"

bench: ## Run performance benchmark tests
	uv run pytest -v -m benchmark --no-header -rN

rendering-baselines: ## Regenerate visual regression baselines (manual, destructive)
	uv run python -c "import asyncio; from app.rendering.tests.visual_regression.baseline_generator import BaselineGenerator; asyncio.run(BaselineGenerator().generate_baselines())"

rendering-regression: ## Run visual regression tests against baselines
	uv run pytest app/rendering/tests/visual_regression/ -v -m visual_regression

test-collab: ## Run CRDT collaboration tests
	COLLAB_WS__ENABLED=true COLLAB_WS__CRDT_ENABLED=true uv run pytest -v -m collab

test-properties: ## Run property-based email invariant tests
	QA_PROPERTY_TESTING__ENABLED=true uv run pytest app/qa_engine/property_testing/tests/ -v

test-fe: ## Run frontend unit tests
	cd cms && pnpm --filter web test

lint: ## Format + lint
	uv run ruff format .
	uv run ruff check --fix .

types: ## Run mypy + pyright
	uv run mypy app/
	uv run pyright app/

check-fe: ## Run frontend checks (lint + format + type-check + tests)
	cd cms && pnpm --filter web lint 2>/dev/null || true
	cd cms && pnpm --filter web format:check 2>/dev/null || true
	cd cms && pnpm --filter web type-check
	cd cms && pnpm --filter web test

lint-fe: ## Format + lint frontend (ESLint + Prettier)
	cd cms && pnpm --filter web lint:fix 2>/dev/null || true
	cd cms && pnpm --filter web format 2>/dev/null || true

golden-conformance: ## Golden template conformance gate (design_sync)
	uv run pytest app/design_sync/tests/test_golden_conformance.py -x -q --tb=short

snapshot-test: ## Snapshot regression tests (real design inputs → expected HTML)
	uv run pytest app/design_sync/tests/test_snapshot_regression.py -v --tb=long

snapshot-capture: ## Capture current converter output for a snapshot case (CASE=5)
	uv run python scripts/snapshot-capture.py $(CASE) --overwrite

check: lint types test check-fe security-check validate-overlays lint-numeric golden-conformance flag-audit ## Run all checks (backend + frontend + security)

check-full: lint types test check-fe security-check migration-lint validate-overlays lint-numeric golden-conformance flag-audit ## Run all checks including migration lint

validate-overlays: ## Validate per-client skill overlay files
	uv run python scripts/validate-overlays.py

flag-audit: ## Audit feature flag lifecycle (warns >90d, errors >180d)
	uv run python scripts/flag-audit.py

list-overlays: ## List all client skill overlays
	@find data/clients -name "*.md" -path "*/agents/*/skills/*" 2>/dev/null | sort

e2e: ## Run all e2e tests
	cd cms && pnpm --filter web e2e

e2e-smoke: ## Run smoke E2E tests (Chromium, @smoke tagged)
	cd cms && pnpm --filter web e2e:smoke

e2e-ui: ## Open Playwright UI mode
	cd cms && pnpm --filter web e2e:ui

e2e-report: ## Open last Playwright HTML report
	cd cms && pnpm --filter web exec playwright show-report

e2e-firefox: ## Run e2e tests on Firefox
	cd cms && BROWSER=firefox pnpm --filter web e2e

e2e-webkit: ## Run e2e tests on WebKit (Safari)
	cd cms && BROWSER=webkit pnpm --filter web e2e

e2e-all-browsers: ## Run e2e tests on all browsers (Chromium + Firefox + WebKit)
	cd cms && BROWSER=all pnpm --filter web e2e

# === SDK ===

sdk: ## Generate TypeScript SDK from backend OpenAPI spec (backend must be running)
	cd cms && pnpm --filter @email-hub/sdk generate-sdk:fetch

sdk-local: ## Generate TypeScript SDK from local openapi.json snapshot
	cd cms && pnpm --filter @email-hub/sdk generate-sdk

sdk-snapshot: ## Export OpenAPI spec snapshot (no running backend needed)
	uv run python scripts/export-openapi.py

sdk-check: ## Verify SDK is up to date with OpenAPI spec (CI gate)
	uv run python scripts/export-openapi.py
	cd cms && pnpm --filter @email-hub/sdk generate-sdk
	@if ! git diff --quiet cms/packages/sdk/; then \
		echo "ERROR: SDK is out of date. Run 'make sdk-snapshot && make sdk-local' and commit."; \
		git diff --stat cms/packages/sdk/; \
		exit 1; \
	fi
	@echo "SDK is up to date."

# === Database ===

db: ## Start only PostgreSQL + Redis
	@docker volume create email-hub_postgres_data 2>/dev/null || true
	AUTH_SECRET=dev-placeholder docker-compose up -d db redis

db-migrate: ## Run database migrations
	uv run alembic upgrade head

db-revision: ## Create a new migration (usage: make db-revision m="description")
	uv run alembic revision --autogenerate -m "$(m)"

db-squash: ## Squash all migrations into a single baseline (destructive — requires confirmation)
	@bash scripts/squash-migrations.sh

# === Scaffolding ===

scaffold-feature: ## Scaffold a new vertical slice (usage: make scaffold-feature name=billing)
	@bash scripts/scaffold-feature.sh $(name)

# === Knowledge Base ===

seed-knowledge: ## Seed knowledge base with email dev content (requires DB + embedding provider)
	uv run python -m app.knowledge.seed

ontology-sync: ## Sync ontology from Can I Email
	uv run python -m app.knowledge.ontology.sync.cli

ontology-sync-dry: ## Sync ontology (dry run — show diff without writing)
	uv run python -m app.knowledge.ontology.sync.cli --dry-run

sync-ontology: ## Sync ontology data to sidecar (YAML → JSON) + check client matrix drift
	cd services/maizzle-builder && npm run sync-ontology
	uv run python scripts/sync-client-matrix.py --check

sync-caniemail: ## Sync caniemail.com CSS support data to data/caniemail-support.json
	uv run python scripts/sync-caniemail.py --verbose

# === Eval Pipeline ===

eval-verify: ## Verify LLM provider is configured and responding
	uv run python -m app.ai.agents.evals.verify_provider

eval-run: eval-verify ## Run agent evals (generate traces)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --skip-existing

eval-judge: ## Run judges on traces (generate verdicts)
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --skip-existing

eval-rejudge: ## Re-run judges WITHOUT skip-existing (overwrites verdicts)
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --mode hybrid

eval-compare: ## Compare pre/post golden-reference verdicts
	uv run python scripts/eval-compare-verdicts.py --pre-dir traces/pre_golden --post-dir traces --output traces/verdict_comparison.json

eval-labels: ## Scaffold human label templates from traces+verdicts (all 9 agents)
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/scaffolder_verdicts.jsonl --traces traces/scaffolder_traces.jsonl --output traces/scaffolder_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/dark_mode_verdicts.jsonl --traces traces/dark_mode_traces.jsonl --output traces/dark_mode_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/content_verdicts.jsonl --traces traces/content_traces.jsonl --output traces/content_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/outlook_fixer_verdicts.jsonl --traces traces/outlook_fixer_traces.jsonl --output traces/outlook_fixer_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/accessibility_verdicts.jsonl --traces traces/accessibility_traces.jsonl --output traces/accessibility_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/personalisation_verdicts.jsonl --traces traces/personalisation_traces.jsonl --output traces/personalisation_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/code_reviewer_verdicts.jsonl --traces traces/code_reviewer_traces.jsonl --output traces/code_reviewer_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/knowledge_verdicts.jsonl --traces traces/knowledge_traces.jsonl --output traces/knowledge_human_labels.jsonl
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/innovation_verdicts.jsonl --traces traces/innovation_traces.jsonl --output traces/innovation_human_labels.jsonl

eval-labeling-tool: eval-labels ## Regenerate labeling tool data from traces+labels
	uv run python scripts/generate-labeling-data.py --traces-dir traces/ --output docs/eval-labeling-data.json

eval-analysis: ## Analyze judge verdicts (failure taxonomy)
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json

eval-blueprint: ## Run blueprint pipeline evals
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl

eval-regression: ## Check for eval regressions vs baseline
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json

eval-check: eval-analysis eval-regression ## Full eval CI gate (analysis + regression check)

eval-calibrate: ## Calibrate judges against human labels (all 9 agents)
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/scaffolder_verdicts.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/scaffolder_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/dark_mode_verdicts.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/dark_mode_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/content_verdicts.jsonl --labels traces/content_human_labels.jsonl --output traces/content_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/outlook_fixer_verdicts.jsonl --labels traces/outlook_fixer_human_labels.jsonl --output traces/outlook_fixer_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/accessibility_verdicts.jsonl --labels traces/accessibility_human_labels.jsonl --output traces/accessibility_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/personalisation_verdicts.jsonl --labels traces/personalisation_human_labels.jsonl --output traces/personalisation_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/code_reviewer_verdicts.jsonl --labels traces/code_reviewer_human_labels.jsonl --output traces/code_reviewer_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/knowledge_verdicts.jsonl --labels traces/knowledge_human_labels.jsonl --output traces/knowledge_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/innovation_verdicts.jsonl --labels traces/innovation_human_labels.jsonl --output traces/innovation_calibration.json

eval-qa-calibrate: ## Calibrate QA gate against human labels (all 9 agents)
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/scaffolder_traces.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/qa_calibration_scaffolder.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/dark_mode_traces.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/qa_calibration_dark_mode.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/content_traces.jsonl --labels traces/content_human_labels.jsonl --output traces/qa_calibration_content.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/outlook_fixer_traces.jsonl --labels traces/outlook_fixer_human_labels.jsonl --output traces/qa_calibration_outlook_fixer.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/accessibility_traces.jsonl --labels traces/accessibility_human_labels.jsonl --output traces/qa_calibration_accessibility.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/personalisation_traces.jsonl --labels traces/personalisation_human_labels.jsonl --output traces/qa_calibration_personalisation.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/code_reviewer_traces.jsonl --labels traces/code_reviewer_human_labels.jsonl --output traces/qa_calibration_code_reviewer.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/knowledge_traces.jsonl --labels traces/knowledge_human_labels.jsonl --output traces/qa_calibration_knowledge.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/innovation_traces.jsonl --labels traces/innovation_human_labels.jsonl --output traces/qa_calibration_innovation.json

eval-qa-coverage: ## Report judge criteria → QA check coverage and agreement rates
	uv run python -m app.ai.agents.evals.judge_criteria_map --traces traces/ --output traces/qa_coverage.json

eval-dry-run: ## Full eval pipeline dry-run (no LLM needed)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --dry-run
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --dry-run
	$(MAKE) eval-labels
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl --dry-run
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json
	@echo "\n=== Dry-run pipeline complete ==="

eval-suggest: ## Generate SKILL.md amendment suggestions from eval failures
	uv run python -m app.ai.agents.evals.amendment_suggester --analysis traces/analysis.json --output traces/suggestions

eval-full: ## Full eval pipeline (requires LLM provider)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	$(MAKE) eval-regression
	$(MAKE) eval-suggest
	@echo "\n=== Full eval pipeline complete ==="

eval-skill-test: eval-verify ## A/B test a SKILL.md change (AGENT=scaffolder PROPOSED=path/to/SKILL.md)
	uv run python -m app.ai.agents.evals.skill_ab --agent $(AGENT) --proposed $(PROPOSED) --output traces/

eval-baseline: ## Run full eval pipeline and establish baseline (first time)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	cp traces/analysis.json traces/baseline.json
	@echo "\n=== Baseline established at traces/baseline.json ==="
	@echo "Commit traces/baseline.json to version control."

eval-golden: ## CI golden test — deterministic assembly regression (no LLM)
	uv run python -m app.ai.agents.evals.golden_cases --verbose

eval-refresh: ## Refresh analysis.json from production + synthetic verdicts
	uv run python -c "from app.ai.agents.evals.production_sampler import refresh_analysis; refresh_analysis()"

eval-skill-update: ## Detect skill file update candidates (dry-run)
	uv run python scripts/eval-skill-update.py --dry-run

eval-skill-update-apply: ## Generate skill file patches and create git branch
	uv run python scripts/eval-skill-update.py

# === Skill Versioning ===

skill-versions: ## List all agents' skill versions and pin status
	@uv run python -c "from app.ai.agents.skill_version import print_all_versions; print_all_versions()"

skill-pin: ## Pin a skill to a version (AGENT=dark_mode SKILL=client_behavior VERSION=1.0.0)
	@uv run python -c "from app.ai.agents.skill_version import pin_skill; pin_skill('$(AGENT)', '$(SKILL)', '$(VERSION)')"

skill-unpin: ## Unpin a skill (AGENT=dark_mode SKILL=client_behavior)
	@uv run python -c "from app.ai.agents.skill_version import unpin_skill; unpin_skill('$(AGENT)', '$(SKILL)')"

skill-rollback: ## Rollback a skill to a prior version (AGENT=dark_mode SKILL=client_behavior VERSION=1.0.0)
	uv run python scripts/eval-skill-update.py rollback $(AGENT) $(SKILL) $(VERSION)

# === CLI (mcp2cli) ===

.cli-ensure: ## (internal) auto-bake mcp2cli config if missing
	@bash scripts/setup-mcp2cli.sh --check || bash scripts/setup-mcp2cli.sh

cli-setup: ## Bake mcp2cli config for the Email Hub API (re-run to refresh)
	bash scripts/setup-mcp2cli.sh

cli-list: .cli-ensure ## List all API endpoints as CLI commands
	mcp2cli @emailhub --list

cli-search: .cli-ensure ## Search API endpoints (usage: make cli-search s="project")
	mcp2cli @emailhub --search "$(s)"

cli: .cli-ensure ## Call an API endpoint via CLI (usage: make cli c="health")
	mcp2cli @emailhub $(c)

# === Security ===

install-hooks: ## Install pre-commit hooks (format, lint, security, secrets, commit msg)
	pip install pre-commit 2>/dev/null || pipx install pre-commit
	pre-commit install --install-hooks
	pre-commit install --hook-type commit-msg
	@echo "Pre-commit hooks installed (pre-commit + commit-msg)."

security-check: ## Run security lint (Ruff Bandit rules)
	uv run ruff check app/ --select=S --ignore=S311 --no-fix

lint-numeric: ## Check for falsy-numeric or-default anti-pattern in design_sync
	@echo "Checking for falsy-numeric traps in design_sync..."
	@! grep -rn '\bor -\?[0-9]' app/design_sync/ --include='*.py' | grep -v '# noqa: falsy-or' | grep -v '/tests/' | grep -v '^\s*#'

migration-lint: ## Lint Alembic migrations for unsafe DDL (requires squawk)
	@command -v squawk >/dev/null 2>&1 || { echo "Install squawk: brew install sbdchd/squawk/squawk"; exit 1; }
	@find alembic/versions -name '*.py' -newer alembic/versions/.lint-marker 2>/dev/null | xargs -I{} squawk --reporter=compact {} || squawk --reporter=compact alembic/versions/*.py

# === Help ===

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
