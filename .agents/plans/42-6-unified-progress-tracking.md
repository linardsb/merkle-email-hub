# Plan: 42.6 Unified Progress Tracking for Long-Running Operations

## Context

Each long-running operation (rendering, QA, design sync, connectors, blueprints) has its own polling pattern returning full entities just to check a `status` field. A dedicated `GET /api/v1/progress/{operation_id}` endpoint returns only status + progress + message (~200 bytes), is ETag-friendly (42.1), and provides consistent UX. This does NOT replace per-feature detail endpoints.

## Research Summary

| Area | Key File | Role |
|------|----------|------|
| Router registration | `app/main.py` | `app.include_router(router)` pattern, lifespan handler for cleanup |
| Config | `app/core/config.py:1-687` | Pydantic `BaseModel` config classes, add `ProgressConfig` |
| Exceptions | `app/core/exceptions.py` | `AppError` → `NotFoundError` → 404 mapping via `setup_exception_handlers` |
| ETag middleware | `app/core/etag.py` | MD5 hash of JSON body, 304 on `If-None-Match` match — works automatically on new routes |
| Schemas | `app/shared/schemas.py` | `PaginatedResponse[T]`, `ErrorResponse` patterns |
| Rendering svc | `app/rendering/service.py` | `submit_test()` → wire start/update/complete |
| Design sync svc | `app/design_sync/service.py` | `start_conversion()` → multi-stage progress (fetch→convert→save) |
| QA engine svc | `app/qa_engine/service.py` | `run_checks()` → per-check progress (1/N → N/N) |
| Connectors svc | `app/connectors/service.py` | `export()` → gate checks + per-ESP progress |
| Blueprint progress | `app/ai/blueprints/schemas.py` | Already has `BlueprintProgress` — wire to ProgressTracker |

**Existing pattern (blueprints):** `BlueprintProgress` dataclass in `app/ai/blueprints/schemas.py` — similar concept, node-level progress. Our ProgressTracker is operation-level, complementary.

**Router registration:** Import router in `app/main.py`, call `app.include_router(progress_router)`. ETag middleware applies automatically to all JSON GET responses.

## Test Landscape

| Category | Files | Patterns |
|----------|-------|----------|
| Core tests | `app/core/tests/test_etag.py` | TestClient, ETag 304 verification |
| Rendering route tests | `app/rendering/tests/test_routes.py` | `_make_user()`, `patch.object(Service, method, AsyncMock)` |
| QA test factories | `app/qa_engine/tests/conftest.py` | `make_qa_result()`, `make_qa_check()` |
| Design sync factories | `app/design_sync/tests/conftest.py` | `make_design_node()`, `make_file_structure()` |
| Frontend hook tests | `cms/.../hooks/__tests__/use-smart-polling.test.ts` | `renderHook`, `vi.spyOn(document, "hidden")` |
| SWR hook tests | `cms/.../hooks/__tests__/use-data-hooks.test.ts` | Mock `swr`, verify keys/fetcher |

**Route test pattern:**
```python
@pytest.fixture(autouse=True)
def _disable_rate_limiter(): limiter.enabled = False; yield; limiter.enabled = True

@pytest.fixture
def _auth_developer():
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield; app.dependency_overrides.clear()

# Tests use patch.object(Service, "method", new_callable=AsyncMock, return_value=...)
```

## Type Check Baseline

| Target | pyright errors | pyright warnings |
|--------|---------------|-----------------|
| `app/core/` | 0 | 4 (unused test fixtures) |
| `app/rendering/service.py` | 0 | 1 |
| `app/design_sync/service.py` | 64 | 2 (pre-existing Figma dict types) |
| `app/qa_engine/service.py` | 0 | 0 |
| `app/connectors/service.py` | 0 | 0 |

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `app/core/progress.py` | `ProgressTracker` class, `ProgressEntry` dataclass, `OperationStatus` enum |
| `app/core/progress_routes.py` | REST endpoints: `GET /{id}`, `GET /active` |
| `app/core/tests/test_progress.py` | 12 unit tests for tracker + routes |
| `cms/apps/web/src/hooks/use-progress.ts` | `useProgress(operationId)` SWR hook |
| `cms/apps/web/src/hooks/__tests__/use-progress.test.ts` | Frontend hook tests |

### Modified Files
| File | Change |
|------|--------|
| `app/core/config.py` | Add `ProgressConfig` class |
| `app/main.py` | Register `progress_router`, add cleanup to lifespan |

### Integration Files (wire one at a time, NOT all at once)
| File | Change |
|------|--------|
| `app/rendering/service.py` | `ProgressTracker.start/update` in `submit_test()` |
| `app/design_sync/service.py` | `ProgressTracker.start/update` in `start_conversion()` |
| `app/qa_engine/service.py` | `ProgressTracker.start/update` in `run_checks()` |
| `app/connectors/service.py` | `ProgressTracker.start/update` in `export()` |

## Implementation Steps

### Step 1: Core Module — `app/core/progress.py`

```python
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.core.logging import get_logger

logger = get_logger(__name__)


class OperationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEntry:
    operation_id: str
    operation_type: str  # "rendering", "qa_scan", "design_sync", "export", "blueprint"
    status: OperationStatus = OperationStatus.PENDING
    progress: int = 0  # 0-100
    message: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


class ProgressTracker:
    """In-memory progress store for long-running operations.

    Thread-safe via lock. Entries auto-expire after configurable max_age.
    """

    _store: dict[str, ProgressEntry] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def start(cls, operation_id: str, operation_type: str) -> ProgressEntry:
        entry = ProgressEntry(operation_id=operation_id, operation_type=operation_type)
        with cls._lock:
            cls._store[operation_id] = entry
        logger.info("progress.started", operation_id=operation_id, operation_type=operation_type)
        return entry

    @classmethod
    def update(
        cls,
        operation_id: str,
        *,
        progress: int | None = None,
        status: OperationStatus | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> ProgressEntry | None:
        with cls._lock:
            entry = cls._store.get(operation_id)
            if not entry:
                return None
            if progress is not None:
                entry.progress = min(max(progress, 0), 100)
            if status is not None:
                entry.status = status
            if message is not None:
                entry.message = message
            if error is not None:
                entry.error = error
            entry.updated_at = datetime.now(UTC)
        return entry

    @classmethod
    def get(cls, operation_id: str) -> ProgressEntry | None:
        with cls._lock:
            return cls._store.get(operation_id)

    @classmethod
    def get_active(cls) -> list[ProgressEntry]:
        with cls._lock:
            return [
                e for e in cls._store.values()
                if e.status in (OperationStatus.PENDING, OperationStatus.PROCESSING)
            ]

    @classmethod
    def cleanup_completed(cls, max_age_seconds: int = 300) -> int:
        now = datetime.now(UTC)
        with cls._lock:
            to_remove = [
                k for k, v in cls._store.items()
                if v.status in (OperationStatus.COMPLETED, OperationStatus.FAILED)
                and (now - v.updated_at).total_seconds() > max_age_seconds
            ]
            for k in to_remove:
                del cls._store[k]
        if to_remove:
            logger.debug("progress.cleanup", removed=len(to_remove))
        return len(to_remove)

    @classmethod
    def clear(cls) -> None:
        """Clear all entries. For testing only."""
        with cls._lock:
            cls._store.clear()
```

### Step 2: Config — Add `ProgressConfig` to `app/core/config.py`

```python
class ProgressConfig(BaseModel):
    """Progress tracking settings."""
    max_retention_seconds: int = 300
    cleanup_interval_seconds: int = 60
```

Add field to `Settings`: `progress: ProgressConfig = ProgressConfig()`

### Step 3: Routes — `app/core/progress_routes.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.routes import get_current_user
from app.core.exceptions import NotFoundError
from app.core.progress import OperationStatus, ProgressTracker

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


class ProgressResponse(BaseModel):
    operation_id: str
    operation_type: str
    status: OperationStatus
    progress: int
    message: str
    error: str | None = None


@router.get("/{operation_id}", response_model=ProgressResponse)
async def get_progress(
    operation_id: str,
    _current_user: object = Depends(get_current_user),
) -> ProgressResponse:
    entry = ProgressTracker.get(operation_id)
    if not entry:
        raise NotFoundError(f"Operation {operation_id} not found")
    return ProgressResponse(
        operation_id=entry.operation_id,
        operation_type=entry.operation_type,
        status=entry.status,
        progress=entry.progress,
        message=entry.message,
        error=entry.error,
    )


@router.get("/active/list", response_model=list[ProgressResponse])
async def get_active_operations(
    _current_user: object = Depends(get_current_user),
) -> list[ProgressResponse]:
    entries = ProgressTracker.get_active()
    return [
        ProgressResponse(
            operation_id=e.operation_id,
            operation_type=e.operation_type,
            status=e.status,
            progress=e.progress,
            message=e.message,
            error=e.error,
        )
        for e in entries
    ]
```

**Note:** Active list at `/active/list` (not `/active`) to avoid path conflict with `/{operation_id}` matching "active".

### Step 4: Register in `app/main.py`

1. Import: `from app.core.progress_routes import router as progress_router`
2. Register: `app.include_router(progress_router)`
3. Add cleanup task in lifespan:
```python
async def _progress_cleanup_loop(settings: Settings) -> None:
    """Periodic cleanup of expired progress entries."""
    import asyncio
    from app.core.progress import ProgressTracker
    while True:
        await asyncio.sleep(settings.progress.cleanup_interval_seconds)
        ProgressTracker.cleanup_completed(settings.progress.max_retention_seconds)
```
Start in lifespan `startup`, cancel in `shutdown`.

### Step 5: Frontend Hook — `cms/apps/web/src/hooks/use-progress.ts`

```typescript
import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

export interface ProgressEntry {
  operation_id: string;
  operation_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  error: string | null;
}

export function useProgress(operationId: string | null) {
  const smartInterval = useSmartPolling(POLL.realtime);

  return useSWR<ProgressEntry>(
    operationId ? `/api/v1/progress/${operationId}` : null,
    fetcher,
    {
      refreshInterval: (data) =>
        data && (data.status === "pending" || data.status === "processing")
          ? smartInterval
          : 0,
      ...SWR_PRESETS.polling,
    },
  );
}
```

### Step 6: Service Integration (one at a time)

**Pattern for all services — add import:**
```python
from app.core.progress import ProgressTracker, OperationStatus
```

**Rendering** (`app/rendering/service.py` — `submit_test()`):
- `ProgressTracker.start(test_id, "rendering")` at start
- `ProgressTracker.update(test_id, progress=pct, message=f"Rendering {client}")` per client
- `ProgressTracker.update(test_id, status=COMPLETED, progress=100)` on success
- `ProgressTracker.update(test_id, status=FAILED, error=str(e))` on exception

**Design Sync** (`app/design_sync/service.py` — `start_conversion()`):
- Start with `ProgressTracker.start(import_id, "design_sync")`
- Stage 1 (0-30%): Fetching — `update(progress=10, message="Fetching design...")`
- Stage 2 (30-70%): Converting — `update(progress=50, message="Converting sections...")`
- Stage 3 (70-100%): Saving — `update(progress=90, message="Saving components...")`
- Done: `update(status=COMPLETED, progress=100)`

**QA Engine** (`app/qa_engine/service.py` — `run_checks()`):
- Start with `ProgressTracker.start(scan_id, "qa_scan")`
- Per check: `update(progress=int(i/total*100), message=f"Running {check.name} ({i}/{total})")`
- Done: `update(status=COMPLETED, progress=100)`

**Connectors** (`app/connectors/service.py` — `export()`):
- Start with `ProgressTracker.start(export_id, "export")`
- Gate checks (0-20%): `update(progress=10, message="Checking gates...")`
- Per ESP (20-100%): `update(progress=pct, message=f"Exporting to {esp}...")`
- Done: `update(status=COMPLETED, progress=100)`

### Step 7: Tests — `app/core/tests/test_progress.py` (12 tests)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_start_creates_entry` | Entry in store, status=PENDING, progress=0 |
| 2 | `test_update_progress` | progress/status/message fields updated, updated_at changed |
| 3 | `test_get_existing` | Returns entry by operation_id |
| 4 | `test_get_nonexistent_returns_none` | Returns None |
| 5 | `test_cleanup_removes_expired` | Completed entries >max_age removed |
| 6 | `test_cleanup_preserves_active` | Active entries not removed |
| 7 | `test_get_active_filters` | Only PENDING/PROCESSING returned |
| 8 | `test_concurrent_operations` | Multiple entries coexist |
| 9 | `test_status_transitions` | PENDING→PROCESSING→COMPLETED valid |
| 10 | `test_error_capture` | error field set on FAILED |
| 11 | `test_route_get_progress_200` | Route returns JSON with correct fields |
| 12 | `test_route_get_progress_404` | Route returns 404 for unknown operation_id |

**Route tests follow existing pattern:** `TestClient`, `_disable_rate_limiter`, `_auth_developer` fixtures, `patch.object` for ProgressTracker.

### Step 8: Frontend Tests — `use-progress.test.ts`

| # | Test | Asserts |
|---|------|---------|
| 1 | `passes correct SWR key` | `/api/v1/progress/{id}` when operationId set |
| 2 | `passes null key when no operationId` | SWR receives null |
| 3 | `uses smart polling interval` | refreshInterval uses smartInterval for active ops |
| 4 | `stops polling when completed` | refreshInterval returns 0 for completed status |
| 5 | `stops polling when failed` | refreshInterval returns 0 for failed status |

## Preflight Warnings

- `app/design_sync/service.py` has 64 pre-existing pyright errors (Figma dict types) — do not increase count
- `ProgressTracker._store` is a **class variable** (shared mutable dict) — must clear in test fixtures to avoid cross-test contamination
- The `/active` path would conflict with `/{operation_id}` — use `/active/list` instead
- ETag middleware works automatically on all JSON GET responses — no special wiring needed
- Progress cleanup background task must be cancelled on shutdown to avoid `asyncio` warnings

## Security Checklist

| Check | Status |
|-------|--------|
| Auth required on both endpoints | `Depends(get_current_user)` |
| Rate limiting | Inherits from global rate limiter |
| No PII in progress messages | Enforce in code review — messages are operation status only |
| Operation IDs are UUIDs | Services generate UUIDs, not sequential ints |
| No SQL injection surface | In-memory store, no database queries |
| Error responses don't leak internals | `NotFoundError` returns generic 404 |
| No XSS surface | JSON-only responses, no HTML |

## Verification

- [ ] `make check` passes
- [ ] `GET /api/v1/progress/{id}` returns 200 with progress JSON
- [ ] Unknown operation_id returns 404
- [ ] `GET /api/v1/progress/active/list` returns active operations
- [ ] ETag → 304 when progress unchanged
- [ ] Completed entries cleaned up after 5 minutes
- [ ] Auth required (401 without token)
- [ ] Pyright errors ≤ baseline (core: 0, rendering: 0, design_sync: 64, qa: 0, connectors: 0)
- [ ] Frontend hook polls when active, stops when completed/failed
- [ ] 12 backend tests + 5 frontend tests pass
