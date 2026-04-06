# Contributing Guide

This project uses **vertical slice architecture** — each feature lives under `app/{feature}/` with its own models, schemas, service, routes, and tests. This guide covers the three most common contribution workflows.

## Prerequisites

```bash
uv sync                    # Install Python dependencies
cd cms && pnpm install     # Install frontend dependencies
make install-hooks         # Install pre-commit hooks
make db && make db-migrate # Start PostgreSQL + Redis, run migrations
make dev                   # Backend (:8891) + frontend (:3000)
```

## Essential Commands

| Command | What it does |
|---------|-------------|
| `make dev` | Start backend + frontend dev servers |
| `make check` | All checks (lint + types + tests + security + golden conformance + flag audit) |
| `make test` | Backend unit tests (excludes integration, benchmark, visual) |
| `make lint` | Format + lint (ruff — 26 rule sets) |
| `make types` | mypy + pyright (both strict) |
| `make check-fe` | Frontend lint + format + type-check + tests |
| `make security-check` | Ruff Bandit security rules |
| `make db-revision m="..."` | Create a new Alembic migration |
| `make db-migrate` | Run pending migrations |
| `make eval-golden` | CI golden test (deterministic, no LLM) |

---

## Workflow 1: Adding a Feature Slice

### Step 1 — Scaffold

```bash
make scaffold-feature name=billing
```

This creates `app/billing/` with 10 files:

```
app/billing/
├── __init__.py
├── models.py          # SQLAlchemy model with TimestampMixin + SoftDeleteMixin
├── schemas.py         # Pydantic Create/Update/Response schemas
├── exceptions.py      # BillingNotFoundError, BillingAlreadyExistsError
├── repository.py      # Data access (get, list, count, create)
├── service.py         # Business logic with structured logging
├── routes.py          # FastAPI APIRouter with auth + rate limiting
└── tests/
    ├── __init__.py
    ├── conftest.py    # make_billing() factory, mock_db fixture
    └── test_service.py # 6 unit tests for service layer
```

### Step 2 — Customise the model

Edit `models.py` to add your domain columns:

```python
"""Billing database models."""

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class Billing(Base, TimestampMixin, SoftDeleteMixin):
    """Billing model."""

    __tablename__ = "billings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Then update `schemas.py` to match.

### Step 3 — Register routes

In `app/main.py`, add:

```python
# At the top, with other imports:
from app.billing.routes import router as billing_router

# With other router includes:
app.include_router(billing_router)
```

For feature-flagged modules, use conditional registration:

```python
if settings.billing.enabled:
    from app.billing.routes import router as billing_router
    app.include_router(billing_router)
```

### Step 4 — Create a migration

```bash
make db-revision m="add billing tables"
make db-migrate
```

### Step 5 — Write tests

The scaffold generates a `conftest.py` with a `make_billing()` factory and basic service tests. Extend them:

```python
# app/billing/tests/test_service.py
from app.billing.tests.conftest import make_billing

async def test_get_paid_billing(service):
    item = make_billing(id=1, is_paid=True)
    service.repository.get = AsyncMock(return_value=item)
    result = await service.get(1)
    assert result.is_paid is True
```

**Markers:**
- No marker needed for unit tests (default: `make test` runs them)
- `@pytest.mark.integration` for tests requiring a real database
- `@pytest.mark.benchmark` for performance tests

### Step 6 — Verify

```bash
make check   # lint + types + tests + security
```

---

## Workflow 2: Adding an AI Agent

### Step 1 — Create the agent directory

```
app/ai/agents/{agent_name}/
├── __init__.py
├── service.py           # Extends BaseAgentService
├── schemas.py           # {Agent}Request, {Agent}Response
├── routes.py            # POST /api/v1/agents/{name}/process
├── prompt.py            # build_system_prompt(), detect_relevant_skills()
├── SKILL.md             # Agent capability documentation (L1 + L2)
├── skill-versions.yaml  # Skill versioning config
└── skills/              # L3 skill files (loaded on-demand)
    └── __init__.py
```

### Step 2 — Implement the service

Extend `BaseAgentService` from `app/ai/agents/base.py`:

```python
"""My agent service."""

from __future__ import annotations

from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.routing import TaskTier
from app.core.logging import get_logger

logger = get_logger(__name__)


class MyAgentService(BaseAgentService):
    """My agent pipeline."""

    # Required class-level config
    agent_name: str = "my_agent"
    sanitization_profile: str = "default"   # nh3 allowlist profile from app/ai/shared.py
    model_tier: TaskTier = "standard"       # "standard", "fast", or "power"
    stream_prefix: str = "myagent"          # SSE event prefix

    def build_system_prompt(
        self, relevant_skills: list[str], **kwargs: Any
    ) -> str:
        """Build the LLM system prompt."""
        ...

    def detect_relevant_skills(self, request: Any) -> list[str]:
        """Determine which SKILL.md sections to load."""
        return []

    def _build_user_message(self, request: Any) -> str:
        """Build the LLM user message from the request."""
        ...

    def _post_process(self, raw_content: str) -> str:
        """Post-LLM processing (extraction, sanitization)."""
        ...
```

### Step 3 — Create the judge

Add `app/ai/agents/evals/judges/{agent_name}.py` with 5 evaluation criteria:

```python
from app.ai.agents.evals.judges.schemas import JudgeCriteria

MY_AGENT_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(name="criterion_1", description="What to check..."),
    JudgeCriteria(name="criterion_2", description="..."),
    JudgeCriteria(name="criterion_3", description="..."),
    JudgeCriteria(name="criterion_4", description="..."),
    JudgeCriteria(name="criterion_5", description="..."),
]

class MyAgentJudge:
    """Binary judge for my_agent outputs."""

    agent_name: str = "my_agent"
    criteria: list[JudgeCriteria] = MY_AGENT_CRITERIA

    def build_prompt(self, judge_input: "JudgeInput") -> str:
        ...

    def parse_response(self, raw: str, judge_input: "JudgeInput") -> "JudgeVerdict":
        ...
```

### Step 4 — Register the judge

In `app/ai/agents/evals/judges/__init__.py`:

```python
from app.ai.agents.evals.judges.my_agent import MyAgentJudge

# Add to JUDGE_REGISTRY dict:
JUDGE_REGISTRY = {
    ...
    "my_agent": MyAgentJudge,
}
```

### Step 5 — Add synthetic test data

Create `app/ai/agents/evals/synthetic_data_{agent_name}.py` with at least 10 test cases covering your agent's failure-prone dimensions.

### Step 6 — Register the router

In `app/main.py`:

```python
from app.ai.agents.my_agent.routes import router as my_agent_router
app.include_router(my_agent_router)
```

### Step 7 — Verify

```bash
make eval-golden  # Validate judge configuration
make check        # Full quality gate
```

---

## Workflow 3: Adding an ESP Connector

### Step 1 — Implement the provider

Create `app/connectors/{esp_name}/` implementing the `ConnectorProvider` protocol from `app/connectors/protocol.py`:

```python
"""My ESP connector service."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class MyESPConnectorService:
    """ESP connector for MyESP.

    Implements the ConnectorProvider protocol:
        async def export(html, name, credentials=None) -> str
    """

    async def export(
        self,
        html: str,
        name: str,
        credentials: dict[str, str] | None = None,
    ) -> str:
        """Export compiled HTML to MyESP.

        Args:
            html: Compiled email HTML from Maizzle build.
            name: User-provided name for the template.
            credentials: Optional decrypted ESP credentials.

        Returns:
            External ID string from the ESP.
        """
        if credentials:
            # Real API call
            ...
        # Mock response for development
        return f"myesp_mock_{name}"
```

### Step 2 — Register the connector

In `app/connectors/service.py`, add to the `SUPPORTED_CONNECTORS` dict:

```python
from app.connectors.my_esp.service import MyESPConnectorService

SUPPORTED_CONNECTORS: dict[str, type[ConnectorProvider]] = {
    ...
    "my_esp": MyESPConnectorService,
}
```

### Step 3 — Add mock endpoint

Create `services/mock-esp/{esp_name}/routes.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/my-esp", tags=["my-esp"])

@router.post("/content")
async def create_content(data: dict) -> dict:
    """Mock MyESP content creation endpoint."""
    return {"id": f"mock_{data.get('name', 'unnamed')}", "status": "created"}
```

Register in `services/mock-esp/main.py`:

```python
from my_esp.routes import router as my_esp_router
app.include_router(my_esp_router)
```

### Step 4 — Add integration tests

```python
# app/connectors/my_esp/tests/test_export.py
from app.connectors.my_esp.service import MyESPConnectorService

async def test_export_mock():
    service = MyESPConnectorService()
    result = await service.export("<html>test</html>", "test-template")
    assert "myesp_mock_" in result

async def test_export_with_credentials():
    service = MyESPConnectorService()
    creds = {"api_key": "test-key", "endpoint": "https://mock.esp"}
    result = await service.export("<html>test</html>", "test-template", credentials=creds)
    assert result  # Returns external ID
```

### Step 5 — Verify

```bash
make check
```

---

## Code Style Quick Reference

| Rule | Details |
|------|---------|
| Type annotations | All functions must have complete type annotations (mypy + pyright strict) |
| Logging | `from app.core.logging import get_logger` — events: `domain.action_state` |
| Exceptions | Inherit from `AppError` hierarchy in `app.core.exceptions` |
| Config | Nested Pydantic: `settings.database.url`, `settings.auth.jwt_secret_key` |
| SQL safety | Always use `escape_like()` for LIKE/ILIKE patterns |
| Auth | `get_current_user` (any user) or `require_role("admin")` (RBAC) |
| Rate limiting | `@limiter.limit("30/minute")` on all public endpoints |
| Repository | Database operations ONLY (no business logic) |
| Service | Business logic, validation, logging |
| Routes | Thin — delegate to service, handle HTTP concerns only |

## Common Gotchas

- **TCH auto-fix danger:** Never run `ruff --fix` with TCH rules enabled — it breaks runtime imports for SQLAlchemy, Pydantic, and datetime. Use `--no-fix` for TCH or exclude them.
- **Auth cache in tests:** The root `conftest.py` auto-clears auth cache between tests via `_clear_auth_cache`. If you see stale user data, check this fixture.
- **Async test mode:** `asyncio_mode = "auto"` is configured in `pyproject.toml` — no need for explicit `@pytest.mark.asyncio` markers.
- **Test linting:** Test files have relaxed rules (S101, ANN, ARG, D, FBT, SIM, PERF, RET are ignored).
