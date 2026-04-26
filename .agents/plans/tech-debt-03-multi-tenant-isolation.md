# Tech Debt 03 — Multi-Tenant Isolation

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** Close the cross-tenant data leak across 8 repositories. **Largest single piece of remediation work in the audit.**
**Goal:** Every list/get/update/delete query is scoped by `client_org_id`, enforced uniformly, with a regression test that proves no cross-org leakage.
**Estimated effort:** 1–2 full sessions. Don't bundle with refactors.
**Prerequisite:** Plans 01–02 landed (they reduce surface area; F006/F007 deletions remove repo-shaped code that would otherwise need the filter).

## Findings addressed

F001 (RLS inert) — Critical
F002 (8 repos don't filter by `client_org_id`) — Critical
F003 (`/projects?client_org_id=` accepts any value) — Critical

## Decision gate (do this first)

Pick one approach. **Do not attempt both half-built.**

| Approach | Pros | Cons |
|---|---|---|
| **A. RLS + non-superuser DB role** | DB enforces; impossible to bypass via app bug. | DB role migration; needs `set_config` middleware; harder to debug. Postgres-only. |
| **B. Repo-layer filter only; revert RLS migrations** | Easier to debug, faster to land. | App-only enforcement; one missed repo call leaks. |

**Recommended default: B.** RLS as defense-in-depth is valuable but only if it's actually live; in this repo it's a comment. Pick B unless you have a strong reason for A. The plan below assumes B; deviations for A are noted in `### Approach A delta` blocks.

## Pre-flight

```bash
git checkout -b sec/tech-debt-03-tenant-isolation
make check
# Identify every repository:
find app -name "repository.py" | xargs grep -l "class.*Repository"
```

Expected list: `auth`, `projects`, `components`, `templates`, `qa_engine`, `knowledge`, `memory`, `briefs`, `approval`. (Plus any sub-repos.)

## Part A — Plumb `client_org_id` through the stack

### A1. Auth dependency exposes the org

Already exposed via `current_user.client_org_id`. Verify at `app/auth/dependencies.py`. No change.

### A2. Add a scoped session helper

**New file:** `app/core/scoped_db.py`:
```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.core.database import AsyncSessionLocal

async def get_scoped_db(
    user: Annotated[User, Depends(get_current_user)],
) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        # admin role gets cross-org reads (audit log via list_projects route)
        session.info["client_org_id"] = user.client_org_id
        session.info["role"] = user.role
        yield session
```

### Approach A delta
Add inside the `async with` block:
```python
await session.execute(text("SELECT set_config('app.current_client_id', :id, true)"),
                      {"id": str(user.client_org_id)})
await session.execute(text("SELECT set_config('app.current_role', :r, true)"),
                      {"r": user.role})
```
Plus DB role migration (see Part D).

### A3. Update each route to use `get_scoped_db`

For every router that currently uses `get_db`:
```bash
rg "Depends\(get_db\)" app/ --type py -l
```
Replace with `Depends(get_scoped_db)`. Routes that genuinely need cross-tenant access (admin tools) keep `get_db` — verified pre-auth allowlist (preflight scan):
- `app/auth/routes.py:38` — `get_service` for login/refresh (pre-auth, no user yet)
- `app/auth/dependencies.py:47` — `get_current_user` itself resolves the session (pre-auth)
- `app/core/health.py` — `/health` endpoint
- (audit remaining 22 callers in `rg "Depends\\(get_db\\)"`; default to `get_scoped_db`)

## Part B — Add the filter to every repository

For each repository in the list, every method that lists/gets/updates/deletes rows for tenant-owned tables adds the filter.

### B0. Signature decision (do this first)

Pick one. Affects every repo callsite (services + ~62 method definitions across 8 repos).

| Option | Shape | Trade-off |
|---|---|---|
| **Required kwarg** | `*, client_org_id: int` | Strict — pyright catches every missed callsite. Breaks all existing service callsites and AsyncMock tests at once (large diff, single PR). |
| **Optional with boundary check** | `*, client_org_id: int \| None = None` + `raise if None` in body | Smaller diff, incremental migration possible. Loses static guarantee — a missed kwarg fails at runtime, not type-check. |

**Recommended: required kwarg.** The whole point of this plan is to make leakage impossible. Defaulting `None` reintroduces the F002 footgun.

Existing `app/projects/repository.py:69-98` uses the optional form (`client_org_id: int | None = None`) — tighten to required as part of this work, or document why projects stays optional.

### B1. Pattern for `list`

```python
async def list(self, *, client_org_id: int, ...) -> list[T]:
    stmt = select(T).where(T.client_org_id == client_org_id)
    return (await self.session.execute(stmt)).scalars().all()
```

### B2. Pattern for `get_by_id`

```python
async def get_by_id(self, id: int, *, client_org_id: int) -> T | None:
    stmt = select(T).where(T.id == id, T.client_org_id == client_org_id)
    return (await self.session.execute(stmt)).scalar_one_or_none()
```

Service layer reads `client_org_id` from `session.info["client_org_id"]` and passes through. Routes do not pass `client_org_id` directly — it comes from auth via the session.

### B2a. Existing AsyncMock unit tests must be updated

Required-kwarg signature breaks every direct `repo.method(id)` callsite in unit tests. Known hits (preflight scan):

- `app/memory/tests/test_repository.py:63,74,97,110` — `repo.get_by_id(1)` / `repo.delete(1)` → add `client_org_id=1` (synthetic fixture value is fine; mocks don't enforce).

Sweep the rest with: `rg "\\b(repo|repository)\\.(list|get_by_id|update|delete)\\(" app/*/tests/` once Part B starts touching a repo, fix in the same commit.

### B3. Repository-by-repository walk

Tracker:

| Repo | Tables | Methods to update |
|---|---|---|
| `app/auth/repository.py` | `users`, `refresh_tokens`, `audit_log` | `list_users`, `get_user_by_email` (admin-only — keep cross-org), `get_user_by_id` (require org match). Audit log queries: filter by org. |
| `app/components/repository.py` | `components`, `component_versions` | All list/get/update/delete. Cross-version queries: ensure `JOIN component ON …` is org-filtered. |
| `app/templates/repository.py` | `templates`, `template_versions`, `golden_templates` | All. Note: `golden_templates` may be global (not tenant) — verify and exempt. |
| `app/qa_engine/repository.py` | `qa_results`, `qa_runs` | All. |
| `app/knowledge/repository.py` | `knowledge_chunks`, `knowledge_documents` | All. **Caution:** `search_fulltext` and pgvector search queries — add `WHERE client_org_id = :org` to every vector search. |
| `app/memory/repository.py` | `agent_memory_*` | All. Memory is project-scoped → filter via `Project.client_org_id`. |
| `app/briefs/repository.py` | `briefs`, `brief_connections` | All. Decrypted creds in `brief_connections` — already encrypted but cross-org access still leaks metadata. |
| `app/approval/repository.py` | `approvals`, `approval_requests`, `approval_decisions` | All. |

### B4. Route layer cleanup

For F003 specifically: `app/projects/routes.py:73-83`:
```python
async def list_projects(
    client_org_id: int | None = Query(None),
    db: AsyncSession = Depends(get_scoped_db),
    user: User = Depends(get_current_user),
) -> list[ProjectRead]:
    if user.role != "admin":
        client_org_id = user.client_org_id
    elif client_org_id is None:
        client_org_id = user.client_org_id  # default for admin too
    return await ProjectService(db).list(client_org_id=client_org_id)
```

## Part C — The regression test

**New file:** `app/tests/test_tenant_isolation.py` — single test parametrized over every entity type:

```python
@pytest_asyncio.fixture
async def two_orgs(db: AsyncSession) -> tuple[User, User]:
    org1 = await seed_org(db, name="org1")
    org2 = await seed_org(db, name="org2")
    user1 = await seed_user(db, client_org_id=org1.id, role="developer")
    user2 = await seed_user(db, client_org_id=org2.id, role="developer")
    return user1, user2

@pytest.mark.parametrize("entity", [
    "projects", "components", "templates", "qa_results",
    "knowledge_chunks", "memory_entries", "briefs", "approvals"
])
async def test_no_cross_org_read(client, two_orgs, entity):
    user1, user2 = two_orgs
    # user1 creates entity
    res = await client.post(f"/api/v1/{entity}/", json={...},
                            headers=auth_header(user1))
    entity_id = res.json()["id"]
    # user2 tries to read
    res = await client.get(f"/api/v1/{entity}/{entity_id}",
                           headers=auth_header(user2))
    assert res.status_code in (403, 404)
    # user2 list does NOT include
    res = await client.get(f"/api/v1/{entity}/", headers=auth_header(user2))
    assert entity_id not in [e["id"] for e in res.json()]
```

This test is non-negotiable. If it doesn't pass, the fix is incomplete.

## Part D — RLS cleanup (Approach B only)

Revert the RLS migrations. **New migration:**
```python
def upgrade():
    op.execute("DROP POLICY IF EXISTS rls_projects_org ON projects")
    op.execute("DROP POLICY IF EXISTS rls_projects_admin ON projects")
    # ... for every table covered by fdd89fceac29 + e5f2a9b73d14
    op.execute("ALTER TABLE projects DISABLE ROW LEVEL SECURITY")
    # ...
```

### Approach A delta
Skip Part D. Instead:
1. New DB user `appuser` with `LOGIN`, no `BYPASSRLS`.
2. New migration creates the role and grants schema/table privileges.
3. Update `DATABASE__URL` to use `appuser`.
4. Test cross-tenant queries fail at the DB level.

## Verification

```bash
make check
make test app/tests/test_tenant_isolation.py -v  # MUST pass
make e2e-smoke

# Sanity check: every authenticated route uses scoped_db
rg "Depends\(get_db\)" app/ --type py
# Result should match the allowlist in §A3 (auth/login, dependencies, /health).

# Pyright regression gate — preflight baseline = 0 errors across the 10 target files:
uv run pyright \
  app/projects/repository.py app/projects/routes.py \
  app/auth/repository.py app/components/repository.py \
  app/memory/repository.py app/templates/repository.py \
  app/qa_engine/repository.py app/knowledge/repository.py \
  app/briefs/repository.py app/approval/repository.py
# Any error count > 0 is a regression introduced by this work.
```

**Suggestion:** re-run `/preflight-check` after Part A lands but before Part B — Part B's diff against the post-A tree is more tractable than scanning everything up-front.

## Rollback

Single revert via PR-level `git revert`. The new `get_scoped_db` is additive; reverting restores pre-fix state. Test data introduced by `seed_org` is in pytest fixtures only.

## Risk notes

- **Knowledge pgvector search**: filter must be in the SQL `WHERE`, not post-fetch. Embedding search without an org filter is *very* slow when filtered after the fact.
- **`get_user_by_email` for login**: pre-auth, must NOT scope. Mark explicitly.
- **Memory model**: project-scoped (not directly tenant-scoped) — filter via `Project.client_org_id` join.
- **Admin role**: cross-org read is a feature for admins. Keep but log.
- **Test fixture leakage**: ensure `two_orgs` fixture is per-test (not module-scoped) or wrap in transaction rollback.

## Done when

- [ ] Decision gate documented in PR description (Approach A or B).
- [ ] All 8 repositories updated.
- [ ] Every route uses `get_scoped_db` or is on the explicit allowlist.
- [ ] `test_tenant_isolation.py` green for every entity.
- [ ] Approach B: RLS migrations reverted. Approach A: DB role migrated, `set_config` proven via direct psql test.
- [ ] PR titled `sec(multi-tenant): enforce client_org_id across repos (F001 F002 F003)`.
- [ ] Mark F001, F002, F003 as **RESOLVED**.
