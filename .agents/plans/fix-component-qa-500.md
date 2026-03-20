# Plan: Fix Component QA Endpoint 500

## Context
`POST /api/v1/components/{id}/versions/{ver}/qa` returns 500. Root cause: `get_compatibility()` accesses `component.versions[0]` which triggers lazy loading on a `Component` fetched via `repository.get()` — async SQLAlchemy raises `MissingGreenlet`. Secondary: no error handling around QA engine `run_checks()` or `extract_compatibility()`, so any check failure also produces an unhandled 500.

## Files to Modify
- `app/components/repository.py` — eager-load `versions` in `get()` method
- `app/components/service.py` — add error handling in `run_qa_for_version()`
- `app/components/qa_bridge.py` — wrap `run_checks()` and `extract_compatibility()` with error handling, add transaction rollback safety

## Implementation Steps

### Step 1: Fix lazy loading in `repository.get()` (PRIMARY FIX)

In `app/components/repository.py`, add `selectinload` to the `get()` method so `component.versions` is available in async context:

```python
from sqlalchemy.orm import selectinload

async def get(self, component_id: int) -> Component | None:
    result = await self.db.execute(
        select(Component)
        .where(Component.id == component_id, Component.deleted_at.is_(None))
        .options(selectinload(Component.versions))
    )
    return result.scalar_one_or_none()
```

**Note:** This affects all callers of `get()`. Verify the relationship is used elsewhere — if not needed in list/get_by_slug, keep those methods unchanged. Only `get()` needs it because `get_compatibility()` and `get_component()` both call `_get_or_404()` → `get()` and then access `component.versions`.

### Step 2: Add error handling in `qa_bridge.run_component_qa()`

In `app/components/qa_bridge.py`, wrap the QA engine call and compatibility extraction:

```python
from app.core.exceptions import AppError

async def run_component_qa(
    db: AsyncSession,
    version: ComponentVersion,
) -> ComponentQAResult:
    logger.info(...)

    qa_service = QAEngineService(db)
    try:
        qa_response = await qa_service.run_checks(
            QARunRequest(html=version.html_source),
        )
    except Exception as exc:
        logger.error(
            "components.qa_engine_failed",
            component_id=version.component_id,
            version_number=version.version_number,
            error=str(exc),
        )
        raise AppError(f"QA engine failed for component version: {exc}") from exc

    try:
        compatibility = extract_compatibility(version.html_source)
    except Exception as exc:
        logger.error(
            "components.compatibility_extraction_failed",
            component_id=version.component_id,
            error=str(exc),
        )
        raise AppError(f"Compatibility extraction failed: {exc}") from exc

    # Store link + update version compatibility
    cqa = ComponentQAResult(
        component_version_id=version.id,
        qa_result_id=qa_response.id,
        compatibility=compatibility,
    )
    db.add(cqa)
    version.compatibility = compatibility
    await db.commit()
    await db.refresh(cqa)

    logger.info(...)
    return cqa
```

### Step 3: Add error handling in `service.run_qa_for_version()`

No changes needed — `AppError` from qa_bridge will propagate to FastAPI's exception handler and return a proper error response instead of 500.

### Step 4: Add import for `selectinload` in repository

Ensure `from sqlalchemy.orm import selectinload` is added to `app/components/repository.py` imports.

## Security Checklist (scoped to this feature's endpoints)
- [x] Auth dependency (`require_role("developer")`) — already present on route
- [x] Rate limiting (`@limiter.limit("10/minute")`) — already present on route
- [x] Input validation via Pydantic schemas — path params are typed `int`
- [x] Error responses use `AppError` hierarchy — new `AppError` raises added
- [x] No secrets/credentials in logs or error responses — only `str(exc)` logged
- [x] No new endpoints added

## Verification
- [ ] `make check` passes (includes lint, types, tests, security-check)
- [ ] `POST /components/{id}/versions/{ver}/qa` returns proper error response (not 500) when QA fails
- [ ] `GET /components/{id}/compatibility` works without `MissingGreenlet` error
- [ ] Existing component tests still pass
