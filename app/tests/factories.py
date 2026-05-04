"""Shared test factories for cross-feature integration tests.

Used by `app/tests/test_tenant_isolation.py` and any future cross-entity
regression test that needs to spin up isolated `(org, project, user)`
tuples in a real database.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import AuthService
from app.auth.token import create_access_token
from app.projects.models import ClientOrg, Project, ProjectMember


async def seed_org(db: AsyncSession, *, name: str | None = None) -> ClientOrg:
    """Create a `ClientOrg` with a unique name/slug."""
    suffix = uuid.uuid4().hex[:8]
    label = name or f"iso-org-{suffix}"
    org = ClientOrg(name=label, slug=label, is_active=True)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def seed_user(
    db: AsyncSession,
    *,
    client_org_id: int,
    role: str = "developer",
    email: str | None = None,
) -> User:
    """Create a `User` and a `Project` membership tying them to `client_org_id`.

    The project + ProjectMember row is what `_resolve_access` reads to
    populate `TenantAccess.project_ids` / `org_ids`. Without it, every
    seeded user resolves to empty scope and isolation tests would pass
    trivially.
    """
    suffix = uuid.uuid4().hex[:8]
    user_email = email or f"iso-{suffix}@email-hub.test"
    user = User(
        email=user_email,
        hashed_password=AuthService.hash_password("test-password-12345"),
        name=f"iso-{suffix}",
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    project = Project(
        name=f"iso-project-{suffix}",
        client_org_id=client_org_id,
        created_by_id=user.id,
        is_active=True,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    member = ProjectMember(project_id=project.id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()
    return user


def auth_header(user: User) -> dict[str, str]:
    """Bearer header carrying a valid access token for `user`."""
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}
