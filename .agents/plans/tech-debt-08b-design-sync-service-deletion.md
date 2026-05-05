# Tech Debt 08b — Delete `DesignSyncService` facade

**Source:** Follow-up to `.agents/plans/tech-debt-08-converter-god-functions-followup.md` Part C (F012). The facade was deliberately kept in 08C to bound blast radius; this plan removes it.
**Branch off:** `main` once 08C lands.
**Estimated effort:** **1 session** — mostly mechanical search-and-replace driven by the carved sub-service boundaries.
**Prerequisite:** 08C merged. Carved sub-services live at `app/design_sync/services/{connection_service,assets_service,conversion_service,import_service,webhook_service,access_service}.py`. Facade still in `app/design_sync/service.py` delegating to them.

## Why this exists

The 08C carve kept `DesignSyncService` as a ≤300-LOC facade because direct migration of every caller would have inflated the diff with churn unrelated to the carve itself. The risk was bundling two refactors and getting a snapshot regression we couldn't bisect cleanly. With the carve verified green, removing the facade is now a contained, mechanical pass.

## Findings still open

- F012 partially resolved — sub-services exist, but the facade still acts as a single broad entry point that all callers depend on. While in place, its `__init__` instantiates every sub-service even when only one is used per request.

## Pre-flight

```bash
git checkout -b refactor/tech-debt-08b-delete-facade main
make check
make snapshot-test
make snapshot-visual
rg -n "DesignSyncService" app/ tests/ --type py | wc -l   # baseline blast count
```

## Migration phases

Each phase is an independent commit so reverts are surgical.

### Phase 1 — Routes

`app/design_sync/routes.py` currently has:
- 1 `from app.design_sync.service import DesignSyncService`
- 1 `def get_service(db) -> DesignSyncService` factory used by 30+ `Depends(get_service)` annotations
- 5 inline `service = DesignSyncService(db)` constructions (lines `530, 562, 591, 754, ...` — re-grep after rebase)
- 1 `DesignSyncService(db)._repo` private-attr reach at the Figma webhook handler

Migration: replace `Depends(get_service)` with per-resource `Depends(get_<carved>_service)` factories that return the matching carved service. Each handler should depend on the smallest sub-service it needs:

| Route group | Sub-service |
|---|---|
| `/connections` CRUD + sync + refresh + link | `ConnectionService` |
| `/connections/{id}/files`, `/components`, `/images`, `/assets`, `/structure` | `AssetsService` |
| `/connections/{id}/tokens`, `/diff`, `/diagnostic`, `/w3c-*`, `/layout`, `/brief` | `TokenConversionService` |
| `/imports/*`, `/extract-components` | `ImportRequestService` |
| `/webhooks/figma`, `/connections/{id}/webhook` | `WebhookService` |

Replace `DesignSyncService(db)._repo` at the Figma webhook handler with `DesignSyncRepository(db)` (already imported elsewhere).

### Phase 2 — Webhook background worker

`app/design_sync/webhook.py:64`:
```python
service = DesignSyncService(db)
msg = await service.handle_webhook_sync(connection_id)
```

Becomes:
```python
ctx = DesignSyncContext(db)
ws = WebhookService(ctx)  # facade=None — falls back to fresh sub-service instances
msg = await ws.handle_webhook_sync(connection_id)
```

### Phase 3 — Background import pipeline

`app/design_sync/import_service.py:80` accepts `design_service_factory: type[DesignSyncService]` and constructs `factory(db)` to call methods inside `run_conversion`. Audit which methods it calls; today (08C state) it reaches for `analyze_layout`, `download_assets`, etc. Replace with explicit sub-service injection:

```python
class DesignImportService:
    def __init__(self, *, ctx_factory: Callable[[AsyncSession], DesignSyncContext], user: User):
        self._ctx_factory = ctx_factory
        self._user = user

    async def run_conversion(self, ...):
        async with get_db_context() as db:
            ctx = self._ctx_factory(db)
            tokens = TokenConversionService(ctx)
            assets = AssetsService(ctx)
            ...
```

The carved-service `start_conversion` constructs this with `ctx_factory=DesignSyncContext`.

### Phase 4 — MCP / blueprint engine

```bash
rg -n "DesignSyncService" app/mcp/ app/ai/blueprints/ app/streaming/ --type py
```

Currently empty (08C verified) — this section is a tripwire: if anything appears post-08C, migrate it the same way (depend on the smallest carved service).

### Phase 5 — Tests

Test fixtures still construct `DesignSyncService(mock_db)` in:
- `app/design_sync/tests/test_import_service.py` (3 fixtures)
- `app/design_sync/tests/test_webhook.py` (TestHandleWebhookSync, TestFormatDiffSummary)
- `app/design_sync/tests/test_build_document.py` (TestSyncConnectionBuildDocument)
- `app/design_sync/tests/test_service.py` (multiple class-scoped fixtures)
- `app/design_sync/tests/test_routes.py` (~25 `patch.object(DesignSyncService, ...)` sites)

For each, swap to the carved service:
```python
@pytest.fixture
def service(mock_db: AsyncMock) -> ImportRequestService:
    ctx = DesignSyncContext(mock_db)
    return ImportRequestService(ctx)
```

`patch.object(DesignSyncService, "method")` → `patch.object(<CarvedService>, "method")`. Routes tests need to override `Depends(get_<carved>_service)` instead of patching the class directly.

The `_format_diff_summary` and `_compute_token_diff` static methods used directly in tests (`test_webhook.py:409`, `test_service.py:1466`) become module-level imports:
- `from app.design_sync.services.webhook_service import format_diff_summary`
- `from app.design_sync.services.conversion_service import compute_token_diff`

### Phase 6 — Delete facade

Delete the `DesignSyncService` class from `app/design_sync/service.py`. Module retains: `SUPPORTED_PROVIDERS`, `fetch_target_clients`, `_filter_structure`, `_layout_to_response`, training case helpers, `_DEBUG_DIR` / `_MANIFEST_PATH`. Remove crypto re-exports.

The two static helpers retained on the facade as compat shims (`_compute_token_diff`, `_format_diff_summary`) are deleted. Phase 5 already migrated their callers to the underlying free functions.

## Verify after each phase

```bash
make snapshot-visual          # zero pixel diff vs baseline
make snapshot-test
make converter-data-regression
make test app/design_sync/ -v
make check
```

## Risk notes

- **Routes Depends migration is the riskiest phase.** Each route gets a new `Depends`; getting the wrong sub-service causes 500s at request time, not import time. Mitigation: migrate one route group per commit; smoke-test the API surface after each (`make e2e-smoke`).
- **`DesignImportService` factory pattern** is currently reachable from production via `start_conversion`. Don't change the surface contract until Phase 3 is fully verified — bg tasks crashing on serialized state are hard to bisect.
- **Tests with deep `patch.object` chains** in `test_routes.py` may reveal behavior that was only working by accident through the facade. Treat any newly-failing test in Phase 5 as a real signal, not a migration cost.

## Done when

- [x] `app/design_sync/service.py` no longer defines `DesignSyncService`.
- [x] No production code path constructs `DesignSyncService(...)`.
- [x] All 2264 design_sync tests still green.
- [x] `rg -n "DesignSyncService" app/ --type py` returns only docstring mentions + provider-named classes (`FigmaDesignSyncService` etc.); no live references to a `DesignSyncService` symbol.
- [x] `TECH_DEBT_AUDIT.md` F012 entry updated from "facade in place" to "fully resolved".
- [ ] Single PR title: `refactor(design_sync): delete DesignSyncService facade (08b)`.
