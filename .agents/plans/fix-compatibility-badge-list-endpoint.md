# Plan: Fix Compatibility Badge — Unblock via List Endpoint

## Context

The `compatibility_badge` field on `ComponentResponse` is always `None` when fetched via the **list** endpoint (`GET /api/v1/components/`). Only the **detail** endpoint (`GET /api/v1/components/{id}`) populates it. This is because `list_components` in `service.py` does a raw `model_validate` without querying QA compatibility data.

The frontend component browser (`component-card.tsx`) and builder palette (`component-palette.tsx`) both use the list endpoint via `useComponents()`, so badges never render in practice.

**Root cause:** `service.py:list_components()` skips the `get_latest_compatibility()` call that `get_component()` makes, and there's no batch equivalent in the repository.

## Files to Modify

- `app/components/repository.py` — Add `get_latest_compatibility_batch()` method
- `app/components/service.py` — Update `list_components()` to populate badges
- `app/components/tests/test_compatibility.py` — Add test for list-with-badges
- `cms/apps/web/src/components/builder/component-palette.tsx` — Show badge in palette card

## Implementation Steps

### Step 1: Add batch compatibility query to repository

In `app/components/repository.py`, add a new method that fetches the latest compatibility for multiple components in a single query:

```python
async def get_latest_compatibility_batch(
    self, component_ids: list[int]
) -> dict[int, dict[str, str]]:
    """Get latest QA compatibility for multiple components in one query.

    Returns dict mapping component_id → compatibility dict.
    Components without QA data are omitted from the result.
    """
    if not component_ids:
        return {}

    # Subquery: latest QA result per component (by version_number desc)
    latest_qa = (
        select(
            ComponentVersion.component_id,
            ComponentQAResult.compatibility,
            func.row_number()
            .over(
                partition_by=ComponentVersion.component_id,
                order_by=ComponentVersion.version_number.desc(),
            )
            .label("rn"),
        )
        .join(ComponentQAResult, ComponentQAResult.component_version_id == ComponentVersion.id)
        .where(ComponentVersion.component_id.in_(component_ids))
        .subquery()
    )

    query = select(latest_qa.c.component_id, latest_qa.c.compatibility).where(
        latest_qa.c.rn == 1
    )
    result = await self.db.execute(query)
    return {row.component_id: row.compatibility for row in result.all()}
```

**Note:** Uses `row_number() OVER (PARTITION BY ... ORDER BY ...)` window function to pick the latest QA result per component in one round trip. No N+1.

### Step 2: Update `list_components` in service to populate badges

In `app/components/service.py`, modify `list_components()`:

```python
async def list_components(
    self,
    pagination: PaginationParams,
    *,
    category: str | None = None,
    search: str | None = None,
) -> PaginatedResponse[ComponentResponse]:
    items = await self.repository.list(
        offset=pagination.offset, limit=pagination.page_size, category=category, search=search
    )
    total = await self.repository.count(category=category, search=search)

    # Batch-fetch compatibility badges (single query for all returned components)
    component_ids = [c.id for c in items]
    compat_map = await self.repository.get_latest_compatibility_batch(component_ids)

    responses: list[ComponentResponse] = []
    for c in items:
        resp = ComponentResponse.model_validate(c)
        resp.compatibility_badge = self._compute_badge(compat_map.get(c.id))
        responses.append(resp)

    return PaginatedResponse[ComponentResponse](
        items=responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
```

### Step 3: Add test for list-with-badges

In `app/components/tests/test_compatibility.py`, add:

```python
async def test_list_components_includes_badges(service):
    """list_components populates compatibility_badge from batch QA data."""
    comp1 = make_component(id=1, name="Header")
    comp2 = make_component(id=2, name="Footer")

    service.repository.list = AsyncMock(return_value=[comp1, comp2])
    service.repository.count = AsyncMock(return_value=2)
    service.repository.get_latest_compatibility_batch = AsyncMock(
        return_value={
            1: {"gmail_web": "full", "outlook_2019": "full"},
            2: {"gmail_web": "full", "outlook_2019": "none"},
        }
    )

    from app.shared.schemas import PaginationParams
    result = await service.list_components(PaginationParams(page=1, page_size=20))

    assert result.items[0].compatibility_badge == "full"
    assert result.items[1].compatibility_badge == "issues"


async def test_list_components_no_qa_data(service):
    """list_components without QA data has no badge."""
    comp1 = make_component(id=1, name="Header")
    service.repository.list = AsyncMock(return_value=[comp1])
    service.repository.count = AsyncMock(return_value=1)
    service.repository.get_latest_compatibility_batch = AsyncMock(return_value={})

    from app.shared.schemas import PaginationParams
    result = await service.list_components(PaginationParams(page=1, page_size=20))

    assert result.items[0].compatibility_badge is None
```

### Step 4: Add badge to builder palette card (frontend)

In `cms/apps/web/src/components/builder/component-palette.tsx`, add a small badge indicator to `PaletteCard`:

```tsx
// At top of file, add import:
import { CompatibilityBadge } from "@/components/components/compatibility-badge";

// In PaletteCard, after the category text div, add badge:
function PaletteCard({ component }: { component: ComponentResponse }) {
  // ... existing draggable setup ...

  return (
    <div /* ... existing props ... */ >
      <Icon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium text-foreground">
          {component.name}
        </div>
        <div className="flex items-center gap-1">
          <span className="truncate text-[10px] text-muted-foreground">
            {category}
          </span>
          <CompatibilityBadge badge={component.compatibility_badge} size="xs" />
        </div>
      </div>
    </div>
  );
}
```

**Note:** The `CompatibilityBadge` component already exists at `cms/apps/web/src/components/components/compatibility-badge.tsx`. If it doesn't support a `size="xs"` prop, either add one or use inline styling to keep it compact for the palette layout. Check the component first — if it already renders small enough, just use it as-is without the `size` prop.

## Security Checklist (scoped to this feature's endpoints)

No new endpoints are added. Changes are to existing `GET /api/v1/components/` which already has:
- [x] Auth dependency (`get_current_user`) on every route
- [x] Rate limiting (`@limiter.limit("30/minute")`) with `Request` parameter
- [x] Input validation via Pydantic schemas
- [x] Error responses use `AppError` hierarchy
- [x] No secrets/credentials in logs or error responses

The new repository method uses parameterized SQLAlchemy queries (`.in_(component_ids)`) — no SQL injection risk.

## Verification

- [ ] `make check` passes (includes lint, types, tests, frontend, security-check)
- [ ] `GET /api/v1/components/` returns populated `compatibility_badge` for components with QA data
- [ ] `GET /api/v1/components/` returns `null` badge for components without QA data
- [ ] Builder palette shows compatibility indicator on cards
- [ ] No N+1 queries — single batch query for all badges in a list page
