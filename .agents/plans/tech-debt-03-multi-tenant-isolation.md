# Tech Debt 03 — Multi-Tenant Isolation (revised 2026-05-04)

**Source:** `TECH_DEBT_AUDIT.md` — F001 (RLS inert), F002 (8 repos don't filter by `client_org_id`), F003 (`/projects?client_org_id=` accepts any value).

**Goal:** Every list/get/update/delete query is scoped by tenant access, enforced uniformly, with a regression test that proves no cross-org leakage. F001/F002/F003 marked **RESOLVED** when the regression test is green.

**Approach:** **B (app-layer scoping)** was chosen and shipped. RLS removed in `sec03_disable_rls_for_app_layer_scoping.py`. Defense-in-depth comes from `scoped_access(session)` raising `RuntimeError` when the session lacks tenant scope — fail-loud instead of silent leak.

## Status snapshot

The original plan is partially landed. This revision reflects the actual codebase and lists only remaining work.

**Shipped (commit `db953681` + follow-ups `c2061ed2`, `9f15c209`, `6988c349`):**
- `app/core/scoped_db.py` — `TenantAccess` dataclass (`project_ids` / `org_ids` frozensets, admin sentinel `None`), 30s `TTLCache`, three entry points (`get_scoped_db`, `get_scoped_db_context`, `get_system_db_context`), `scoped_access(session)` accessor.
- 5 of 8 repos use `scoped_access`: `projects`, `templates`, `memory`, `approval`, `qa_engine`.
- 9 routes on `get_scoped_db`: `qa_engine`, `approval`, `templates`, `memory`, `projects`, `design_sync`, `connectors{,/sync,/tolgee}`.
- F003 closed in `app/projects/routes.py:88-91` (admin-only cross-org query param now access-checked against `scoped_access`).
- RLS revert migration `sec03_disable_rls_for_app_layer_scoping.py`.
- `conftest.py` `tenant_isolation` pytest marker — autouse bypass keeps existing tests green; opt-in with `@pytest.mark.tenant_isolation`.
- Contract tests for the helper itself: `app/core/tests/test_scoped_db.py`.
- BOLA tests for projects: `app/projects/tests/test_bola.py`.

**Remaining (this revision covers):**
1. Tenant-scope **4 repos**: `auth`, `components` (verify global-vs-tenant first), `knowledge`, `briefs`.
2. Swap **14 routes** still on `get_db` to `get_scoped_db`, with documented allowlist for the 3 legitimate exceptions.
3. Write **`app/tests/test_tenant_isolation.py`** — the parametrized cross-entity regression. Without this, F001/F002/F003 cannot be marked resolved.

## The canonical pattern (do not invent a parallel one)

The implementation reads tenant scope from `session.info["tenant_access"]`, not a method kwarg. Repos look like:

```python
from app.core.scoped_db import scoped_access

class FooRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, ...) -> Sequence[Foo]:
        access = scoped_access(self.db)            # raises if session is unscoped
        stmt = select(Foo)
        if access.org_ids is not None:             # None = admin/system → no filter
            stmt = stmt.where(Foo.client_org_id.in_(access.org_ids))
        return (await self.db.execute(stmt)).scalars().all()
```

For project-scoped tables (rows tied to a `project_id` rather than `client_org_id` directly), filter on `access.project_ids` instead and join through `Project` if needed.

**Why this beats the original plan's required-kwarg shape:** routes don't need to know about `client_org_id`; service signatures don't change; background jobs share the pattern via `get_scoped_db_context`; missing scope fails loudly via `scoped_access` rather than silently when a kwarg defaults to `None`. The static-typing safety the kwarg form would have given is replaced by the universal `scoped_access` runtime check, which has the additional virtue of catching the case where a route forgot to swap `get_db` → `get_scoped_db`.

## Part A — Repo sweep (4 remaining)

For each repo, every read/mutate of a tenant-owned table calls `scoped_access(self.db)` and applies the corresponding filter. Per-repo notes below capture the special cases.

### A1. `app/auth/repository.py`

| Method | Action | Notes |
|---|---|---|
| `find_by_email(email)` | **EXEMPT — leave unscoped** | Pre-auth login resolver. Document with `# pragma: tenant-exempt — pre-auth login` so the audit grep can ignore it. |
| `find_by_id(user_id)` | Scope: filter `User.client_org_id.in_(access.org_ids)` when not admin. | Raise `NotFoundError` for cross-org reads (don't 403 — leaks existence). |
| `create(user)` | Validate caller's role can create in target org (handled at service); repo unchanged. | — |
| `update(user)` / `delete(user)` | Repo accepts a User instance — caller-owned. Add an assertion: caller's `access.org_ids` must contain `user.client_org_id`. | Mutating another org's user is the leak path. |
| `list(...)` / `count_filtered(...)` / `count()` | Scope on `client_org_id`. Admin (`access.org_ids is None`) sees all. | `count()` becomes per-org count for non-admins. |
| Audit-log queries | Scope on actor's `client_org_id` (or target's, depending on schema). | Verify schema before applying. |

### A2. `app/components/repository.py`

⚠️ **Investigate first.** The `Component` model may be a **global library entity** shared across all tenants (the architecture doc references "89 → 150 components" as a system-wide library). If `Component` has no `client_org_id` column and components are intentionally global, **mark the repo exempt** with a docstring at the top:

```python
"""Components are a global library — intentionally cross-tenant.
Tenant scoping is enforced on Project↔Component associations, not on the
Component table itself."""
```

If components are tenant-scoped (some tenants have private components), apply the canonical pattern to `get`, `get_by_slug`, `list`, `count`, `update`, `delete`, `get_versions`, `get_version`, `search_with_compatibility`, `search_by_embedding`. Cross-version JOINs filter on the parent component's org.

**Decision needed before code touches this file.** Capture the answer at the top of the repo and in this plan's PR description.

### A3. `app/knowledge/repository.py`

Largest repo (30+ methods). Tenant entities: `Document`, `DocumentChunk`. Likely-global: `Tag`, `domains` listing. Verify each.

| Method | Action |
|---|---|
| `create_document` | Caller-supplied `client_org_id` → assert it's in `access.org_ids` (or admin). |
| `get_document`, `update_document*`, `delete_document` | Filter via `Document.client_org_id`. |
| `list_documents`, `count_documents` | Scope. |
| `get_chunks_by_document`, `bulk_create_chunks` | Join → `Document.client_org_id`. |
| `search_vector`, `search_fulltext` | **Critical.** Filter MUST be in SQL `WHERE` clause (post-fetch filtering on pgvector results is pathological — `LIMIT k` returns the wrong rows). F054 (query-text clamp) is independent and already done. |
| `list_tags`, `get_tag_by_name`, `create_tag`, `delete_tag`, `get_or_create_tag` | Tags appear global. Confirm and document. If per-org, scope. |
| `add_tags_to_document`, `remove_tag_from_document`, `get_tags_for_document(s)` | Document filter applies via the join. |

### A4. `app/briefs/repository.py`

Currently passes `user_id, role` explicitly to `list_connections`, `get_accessible_project_ids`. **Migrate to `scoped_access`** for consistency — keeps tenant logic in one place. The current `(user_id, role)` API is a parallel scoping mechanism that future maintainers will get wrong.

| Method | Action |
|---|---|
| `create_connection` | Service-layer asserts caller's project access; repo unchanged. |
| `get_connection(id)` | Scope: filter `BriefConnection.client_org_id`. |
| `list_connections(user_id, role)` | **Refactor signature** → `list_connections()`. Read scope from session. |
| `delete_connection`, `update_connection_status` | Scope. |
| `upsert_item`, `list_items`, `list_items_for_connection`, `get_item*`, `get_items_by_ids`, `replace_resources`, `replace_attachments` | Filter via `BriefConnection.client_org_id` join. **Watch for `brief_connections` metadata leaks** — even with encrypted creds, listing connection names cross-org is a leak. |
| `get_accessible_project_ids(user_id, role)` | Becomes redundant (use `access.project_ids`). Remove or deprecate. |

Sweep service callsites in the same commit: `rg "(briefs_repo|brief_repo)\.(list_connections|get_accessible_project_ids)" app/`.

### A5. Repo test sweep (per-repo)

The `tenant_isolation` autouse bypass means existing AsyncMock-based tests stay green without changes. Two cases need attention:

- Tests in the changed repo that previously asserted `repo.list()` returned the synthetic seed list — if they relied on no filtering happening, they'll still pass under the bypass. Mark new isolation behaviour with `@pytest.mark.tenant_isolation` rather than retrofitting old tests.
- Service-layer tests that mocked the repo with a positional `(user_id, role)` arg (`briefs` only) need their mocks updated when A4 changes the signature. `rg "list_connections\(" app/briefs/tests app/briefs/service.py` to find them.

## Part B — Route sweep (14 routes)

For every router still on `Depends(get_db)`, swap to `Depends(get_scoped_db)` unless the route is on the **explicit allowlist**. Background-task code spawned from a request uses `get_scoped_db_context(user)`.

### Routes to swap

| File | Callsites |
|---|---|
| `app/components/routes.py:27` | 1 (service factory) |
| `app/briefs/routes.py:27` | 1 (service factory) |
| `app/knowledge/routes.py:50, 388` | 2 |
| `app/rendering/routes.py:50` | 1 |
| `app/personas/routes.py:18` | 1 |
| `app/email_engine/routes.py:31` | 1 |
| `app/templates/upload/routes.py:28` | 1 |
| `app/reporting/routes.py:26` | 1 |
| `app/ai/skills/routes.py:30` | 1 |
| `app/ai/blueprints/routes.py:49,69,117,195,262,348,410` | **7 — all in one diff** |
| `app/ai/voice/routes.py` | scan + swap |
| `app/ai/prompt_store_routes.py` | scan + swap |
| `app/ai/routes.py` | scan + swap |

After the sweep:

```bash
rg "Depends\(get_db\)" app/ --type py
```

Result must match the allowlist exactly.

### Allowlist (verified — these MUST keep `get_db`)

| File:line | Reason |
|---|---|
| `app/auth/routes.py:41` (`get_service`) | Pre-auth (login, refresh, password reset). No user yet → no scope to apply. |
| `app/auth/dependencies.py:47` (`get_current_user`) | The resolver itself must run pre-auth to produce the user that scope depends on. Circular otherwise. |
| `app/core/health.py:41, 94` | `/health` endpoints — no caller identity, intentional. |

Document each with an inline `# tenant-exempt: <reason>` comment so future sweeps don't false-flag them.

### Background work spawned from routes

Anywhere a route returns 202 and continues work in an `asyncio` task that opens its own `AsyncSessionLocal()`, swap to `async with get_scoped_db_context(user):`. Audit candidates:

```bash
rg "AsyncSessionLocal\(\)" app/ --type py
```

Anything in cron / blueprint workers / MCP tools / webhook handlers that has no originating user uses `get_system_db_context()` (admin-equivalent scope, intentional cross-tenant).

## Part C — Regression test (load-bearing)

**New file:** `app/tests/test_tenant_isolation.py`. This is the test that closes F001/F002/F003.

Constraints:
- **Real DB** — the test asserts SQL-level isolation, not mock behaviour. Use the existing integration test fixtures (`@pytest.mark.integration`, real `db` session per `conftest.py`).
- **Mark `@pytest.mark.tenant_isolation`** so the autouse bypass does NOT kick in. Without this marker, every assertion silently passes.
- **Per-test fixture, not module-scoped** — transaction rollback per test or each test creates its own orgs. Module-scoped state masks cross-test bleed.

Skeleton:

```python
# pyright: reportUnknownMemberType=false
"""Cross-entity tenant isolation regression. Closes F001/F002/F003."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.tests.factories import seed_org, seed_user, auth_header

pytestmark = [pytest.mark.integration, pytest.mark.tenant_isolation]


@pytest_asyncio.fixture
async def two_orgs(db: AsyncSession):
    org1 = await seed_org(db, name="iso-org-1")
    org2 = await seed_org(db, name="iso-org-2")
    user1 = await seed_user(db, client_org_id=org1.id, role="developer")
    user2 = await seed_user(db, client_org_id=org2.id, role="developer")
    return user1, user2


# Per-entity create payloads. Keep minimal — schema validation lives elsewhere.
ENTITY_FIXTURES: dict[str, dict] = {
    "projects":    {"path": "/api/v1/projects/",            "create": {"name": "p"}},
    "components":  {"path": "/api/v1/components/",          "create": {"slug": "c", "name": "c"}},  # only if A2 finds components are tenant-scoped
    "templates":   {"path": "/api/v1/templates/",           "create": {"name": "t"}},
    "qa_results":  {"path": "/api/v1/qa/results/",          "create": {...}},
    "knowledge":   {"path": "/api/v1/knowledge/documents/", "create": {...}},
    "memory":      {"path": "/memory/",                     "create": {...}},
    "briefs":      {"path": "/api/v1/briefs/",              "create": {...}},
    "approvals":   {"path": "/api/v1/approvals/",           "create": {...}},
}


@pytest.mark.parametrize("entity", list(ENTITY_FIXTURES))
async def test_no_cross_org_read(client: AsyncClient, two_orgs, entity: str):
    user1, user2 = two_orgs
    fx = ENTITY_FIXTURES[entity]
    # user1 creates
    res = await client.post(fx["path"], json=fx["create"], headers=auth_header(user1))
    assert res.status_code == 201, res.text
    entity_id = res.json()["id"]
    # user2 cannot get
    res = await client.get(f"{fx['path']}{entity_id}", headers=auth_header(user2))
    assert res.status_code in (403, 404), f"{entity}: cross-org GET succeeded"
    # user2 list excludes
    res = await client.get(fx["path"], headers=auth_header(user2))
    body = res.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert entity_id not in [e["id"] for e in items], f"{entity}: cross-org list leaked"


@pytest.mark.parametrize("entity", list(ENTITY_FIXTURES))
async def test_no_cross_org_mutate(client: AsyncClient, two_orgs, entity: str):
    """Cross-org PATCH/DELETE must not succeed and must not modify the row."""
    # symmetric structure: create as user1, attempt PATCH/DELETE as user2,
    # assert status in (403, 404) AND verify row unchanged via user1 GET.
    ...
```

If `seed_org` / `seed_user` / `auth_header` don't exist in `app/tests/factories.py`, add them. Match the conventions of `app/projects/tests/test_bola.py`.

**Stretch — defense-in-depth:** add a unit test that opens a session via plain `get_db`, calls each scoped repo's `list()`, asserts `RuntimeError` is raised. This proves `scoped_access` fails loudly when a future route forgets to swap.

## Part D — RLS cleanup

✅ Shipped as `alembic/versions/sec03_disable_rls_for_app_layer_scoping.py`. No further work.

## Verification

```bash
make check
make test app/tests/test_tenant_isolation.py -v        # MUST pass — non-negotiable
make e2e-smoke

# Audit: every authenticated route on get_scoped_db
rg "Depends\(get_db\)" app/ --type py
# Result must match the §B allowlist (auth/routes.py:41, auth/dependencies.py:47, core/health.py:41+94).

# Pyright regression gate — preflight baseline = 0 errors across the 10 target files
uv run pyright \
  app/projects/repository.py app/projects/routes.py \
  app/auth/repository.py app/components/repository.py \
  app/memory/repository.py app/templates/repository.py \
  app/qa_engine/repository.py app/knowledge/repository.py \
  app/briefs/repository.py app/approval/repository.py
# Any error count > 0 is a regression introduced by this work.
```

## Sequencing

Recommended order to keep diffs reviewable:

1. **Part C skeleton + factories** first, marked `xfail` for entities whose repos aren't yet scoped. Lets every subsequent commit flip an `xfail` → `pass` and proves progress.
2. **Part A1 (auth)** — smallest. Removes one xfail.
3. **Part A2 (components)** — investigation step; either documents exempt status or scopes the repo.
4. **Part A4 (briefs)** — signature refactor; keep in its own commit.
5. **Part A3 (knowledge)** — largest; pgvector filter is the highest-risk change, review carefully.
6. **Part B route sweep** — mechanical; one commit per router file is fine. `ai/blueprints` (7 callsites) in one commit.
7. **Final commit:** remove all `xfail` markers, all parametrize entries pass.

## Risk notes

- **Knowledge pgvector / fulltext** — filter must be in SQL `WHERE`, not Python post-filter. Vector search with `LIMIT k` followed by Python filtering returns the wrong top-k.
- **`auth.find_by_email`** — pre-auth login. MUST stay unscoped. Mark with `# pragma: tenant-exempt — pre-auth login`.
- **Components** — verify global-vs-tenant before scoping. Wrong call here either leaks (under-scoping) or breaks the entire library (over-scoping).
- **Memory model** — project-scoped, filter via `access.project_ids` (Memory rows have a `project_id`, not a `client_org_id`).
- **Admin role** — `access.org_ids is None` disables filtering. This is a feature for admin tooling, not a bug. Audit-log every admin cross-org read at the route layer.
- **Test fixture leakage** — `two_orgs` MUST be per-test (function-scoped) or wrapped in transaction rollback. Module-scoped fixtures will mask intermittent leaks.
- **`tenant_isolation` marker** — without it, the autouse bypass disables the filters being tested. Every isolation test MUST set `pytestmark = pytest.mark.tenant_isolation` (or the per-test marker).
- **Background-task sessions** — `AsyncSessionLocal()` opened directly in a request-spawned task drops scope. Use `get_scoped_db_context(user)` for user-bound work, `get_system_db_context()` for genuinely system-level work.

## Done when

- [ ] `auth`, `components` (or documented exempt), `knowledge`, `briefs` repos scoped via `scoped_access`.
- [ ] `briefs` repo signatures no longer take `(user_id, role)` positionally; service callsites updated.
- [ ] All 14 listed routes on `get_scoped_db`. `rg "Depends\(get_db\)" app/` matches the allowlist exactly.
- [ ] Background-task sessions audited; user-bound work uses `get_scoped_db_context`.
- [ ] `app/tests/test_tenant_isolation.py` green for every entity in `ENTITY_FIXTURES` (no `xfail`).
- [ ] Defense-in-depth unit test: scoped repos raise `RuntimeError` under plain `get_db`.
- [ ] Pyright on 10 target files: 0 errors (matches preflight baseline).
- [ ] PR titled `sec(multi-tenant): close remaining repos and add cross-entity regression (F001 F002 F003)`.
- [ ] PR description records the components global-vs-tenant decision.
- [ ] F001, F002, F003 marked **RESOLVED** in `TECH_DEBT_AUDIT.md`.

## Rollback

Each part is independent. The route sweep (Part B) is reversible by reverting the swap commit — `get_scoped_db` and `get_db` are interface-compatible. Repo changes (Part A) are additive — `scoped_access` calls can be removed without restoring the old shape. The regression test (Part C) is pure-additive.
