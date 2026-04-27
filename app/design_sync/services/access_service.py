"""Project access checks (RBAC for design connections)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.services._context import DesignSyncContext


class AccessService:
    """Thin wrapper over ``DesignSyncContext`` access helpers.

    Kept as a separate sub-service for symmetry with the carve plan; the actual
    implementations live on the shared context so every sub-service can call
    them without holding a back-reference to this service.
    """

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def verify_access(self, project_id: int, user: User) -> None:
        await self._ctx.verify_access(project_id, user)

    async def get_project_name(self, project_id: int | None) -> str | None:
        return await self._ctx.get_project_name(project_id)

    async def get_accessible_project_ids(self, user: User) -> list[int]:
        return await self._ctx.get_accessible_project_ids(user)
