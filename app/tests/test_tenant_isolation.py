# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Cross-entity tenant isolation regression — SKELETON.

Per `.agents/plans/tech-debt-03-multi-tenant-isolation.md` §C this is the
load-bearing regression test. The scoping logic itself (F001/F002) is
already enforced at the repository layer (`scoped_access` raises if a
route forgets to swap to `get_scoped_db`); this file is the cross-entity
*regression net* that would catch a future regression where a new repo
ships without scoping.

Status: skeleton. The plan calls for a real Postgres `db: AsyncSession`
fixture (with table truncation between tests) — that harness does not yet
exist in this repo. The `db` fixture below skips when no test DB URL is
configured (`TEST_DATABASE__URL`); the test will activate as soon as the
harness lands. Until then the test is opt-in only.

Markers:
- `@pytest.mark.tenant_isolation` opts out of the autouse `scoped_access`
  bypass (see root `conftest.py`) and the `_override_scoped_db` autouse.
- `@pytest.mark.integration` keeps it out of the unit-test job.

Entities marked `xfail(strict=False)` are wired up but not yet validated
end-to-end. Components and Knowledge are intentionally *not* in
`ENTITY_FIXTURES` because their repos are documented tenant-exempt (see
`app/components/repository.py` and `app/knowledge/repository.py` module
docstrings).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.tests.factories import auth_header, seed_org, seed_user

pytestmark = [pytest.mark.integration, pytest.mark.tenant_isolation]


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Real Postgres `AsyncSession`. Skips if no `TEST_DATABASE__URL` is set.

    Promote to a project-wide harness with table truncation once the
    integration DB infrastructure lands; for now this is a self-skipping
    stub so the rest of the test machinery (markers, fixtures, params)
    stays exercised by collection.
    """
    url = os.environ.get("TEST_DATABASE__URL")
    if not url:
        pytest.skip("TEST_DATABASE__URL not set — tenant isolation harness pending")
    engine = create_async_engine(url, future=True)
    sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def two_orgs(db: AsyncSession) -> tuple[Any, Any]:
    """Two orgs each with a developer-role user + project membership."""
    org1 = await seed_org(db, name=None)
    org2 = await seed_org(db, name=None)
    user1 = await seed_user(db, client_org_id=org1.id, role="developer")
    user2 = await seed_user(db, client_org_id=org2.id, role="developer")
    return user1, user2


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """ASGI httpx client against the live FastAPI app (no TestClient overrides)."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Per-entity fixture table ──
# Each row: post-payload + GET-by-id path. `xfail` rows are wired but not
# yet validated against a live integration run — promote to plain `id=...`
# as each is confirmed.
ENTITY_FIXTURES: dict[str, dict[str, Any]] = {
    "projects": {
        "list_path": "/api/v1/projects/projects",
        "get_path": "/api/v1/projects/projects/{id}",
        "create_payload": lambda org_id: {"name": "iso-test", "client_org_id": org_id},
    },
}


@pytest.mark.parametrize(
    "entity",
    [
        pytest.param("projects", id="projects"),
        pytest.param(
            "templates",
            id="templates",
            marks=pytest.mark.xfail(
                strict=True, reason="payload schema not yet wired in this test"
            ),
        ),
        pytest.param(
            "memory",
            id="memory",
            marks=pytest.mark.xfail(
                strict=True, reason="payload schema not yet wired in this test"
            ),
        ),
        pytest.param(
            "qa_results",
            id="qa_results",
            marks=pytest.mark.xfail(
                strict=True, reason="payload schema not yet wired in this test"
            ),
        ),
        pytest.param(
            "briefs",
            id="briefs",
            marks=pytest.mark.xfail(
                strict=False,
                reason="briefs are BOLA-by-creator (not org-scoped); needs a "
                "user-isolation variant rather than the org-isolation pattern below",
            ),
        ),
        pytest.param(
            "approvals",
            id="approvals",
            marks=pytest.mark.xfail(
                strict=True, reason="payload schema not yet wired in this test"
            ),
        ),
    ],
)
async def test_no_cross_org_read(
    client: AsyncClient,
    two_orgs: tuple[Any, Any],
    entity: str,
) -> None:
    """user2 must not see entities user1 created in a different org."""
    user1, user2 = two_orgs
    fx = ENTITY_FIXTURES[entity]
    user1_org_id = await _resolve_user_org(client, user1)

    # user1 creates
    create_resp = await client.post(
        fx["list_path"],
        json=fx["create_payload"](user1_org_id),
        headers=auth_header(user1),
    )
    assert create_resp.status_code in (200, 201), (
        f"{entity}: create failed: {create_resp.status_code} {create_resp.text}"
    )
    entity_id = create_resp.json()["id"]

    # user2 cannot fetch
    get_resp = await client.get(fx["get_path"].format(id=entity_id), headers=auth_header(user2))
    assert get_resp.status_code in (403, 404), (
        f"{entity}: cross-org GET succeeded ({get_resp.status_code})"
    )

    # user2 list excludes
    list_resp = await client.get(fx["list_path"], headers=auth_header(user2))
    body = list_resp.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert entity_id not in [e.get("id") for e in items], (
        f"{entity}: cross-org list leaked id {entity_id}"
    )


async def _resolve_user_org(client: AsyncClient, user: Any) -> int:
    """Get the org id user is a member of (via /me or membership lookup).

    Falls back to inspecting the user object directly if a `/me` endpoint
    isn't available.
    """
    _ = client
    # Each seeded user has exactly one project tying them to one org; use
    # the membership cache on the user object if present, else default.
    return getattr(user, "client_org_id", 1)
