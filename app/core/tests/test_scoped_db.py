# pyright: reportPrivateUsage=false, reportUnusedFunction=false, reportArgumentType=false
"""Contract tests for `app.core.scoped_db`.

These tests verify the *helper* — the runtime check that flags missing
tenant scope, the admin sentinel that disables filtering, the
membership-cache-driven access resolution, and the system context for
background jobs. Repo-level filter behaviour is exercised in each
feature's own tests with the autouse bypass disabled (see the
``tenant_isolation`` marker in ``conftest.py``).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.models import User
from app.core.scoped_db import (
    _SYSTEM_ACCESS,
    TenantAccess,
    _resolve_access,
    clear_membership_cache,
    get_system_db_context,
    invalidate_membership_cache,
    scoped_access,
)

pytestmark = pytest.mark.tenant_isolation


def _make_user(user_id: int = 1, role: str = "developer") -> User:
    return cast(User, SimpleNamespace(id=user_id, role=role))


@pytest.fixture(autouse=True)
def _isolate_cache():
    clear_membership_cache()
    yield
    clear_membership_cache()


def test_scoped_access_raises_when_session_unstamped() -> None:
    """A bare session (no `tenant_access`) must fail loud — silent fallback would leak."""
    session = MagicMock()
    session.info = {}
    with pytest.raises(RuntimeError, match="Did a route forget"):
        scoped_access(session)


def test_scoped_access_returns_stamped_value() -> None:
    access = TenantAccess(project_ids=frozenset({1, 2}), org_ids=frozenset({10}), role="developer")
    session = MagicMock()
    session.info = {"tenant_access": access}
    assert scoped_access(session) is access


def test_admin_sentinel_disables_filter() -> None:
    """The admin path is `None`, not an empty frozenset."""
    access = TenantAccess(project_ids=None, org_ids=None, role="admin")
    assert access.project_ids is None
    assert access.org_ids is None


@pytest.mark.asyncio
async def test_resolve_access_admin_returns_sentinel() -> None:
    db = AsyncMock()
    user = _make_user(user_id=1, role="admin")
    access = await _resolve_access(db, user)
    assert access.project_ids is None
    assert access.org_ids is None
    assert access.role == "admin"
    # Admin path skips the DB query — no execute.
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_access_developer_resolves_membership() -> None:
    db = AsyncMock()
    rows_result = MagicMock()
    rows_result.all.return_value = [(7, 100), (8, 100), (9, 200)]
    db.execute = AsyncMock(return_value=rows_result)

    user = _make_user(user_id=42, role="developer")
    access = await _resolve_access(db, user)
    assert access.project_ids == frozenset({7, 8, 9})
    assert access.org_ids == frozenset({100, 200})
    assert access.role == "developer"


@pytest.mark.asyncio
async def test_resolve_access_uses_membership_cache() -> None:
    db = AsyncMock()
    rows_result = MagicMock()
    rows_result.all.return_value = [(1, 10)]
    db.execute = AsyncMock(return_value=rows_result)
    user = _make_user(user_id=99, role="developer")

    first = await _resolve_access(db, user)
    second = await _resolve_access(db, user)

    assert first is second
    assert db.execute.await_count == 1  # cached on second call


@pytest.mark.asyncio
async def test_invalidate_membership_cache_forces_refetch() -> None:
    db = AsyncMock()
    rows_result = MagicMock()
    rows_result.all.return_value = [(1, 10)]
    db.execute = AsyncMock(return_value=rows_result)
    user = _make_user(user_id=99, role="developer")

    await _resolve_access(db, user)
    invalidate_membership_cache(user.id)
    await _resolve_access(db, user)

    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_system_db_context_stamps_system_access() -> None:
    """Background jobs get the all-`None` sentinel so repos skip filtering."""
    async with get_system_db_context() as session:
        access = scoped_access(session)
    assert access is _SYSTEM_ACCESS
    assert access.role == "system"
