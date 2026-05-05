"""Shared context wiring used by all carved design sync sub-services.

Holds the per-request DB session, repository, and provider cache shared across
sub-services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.auth.models import User
from app.design_sync.exceptions import UnsupportedProviderError
from app.design_sync.figma.service import extract_file_key
from app.design_sync.penpot.service import extract_file_id as extract_penpot_id
from app.design_sync.protocol import DesignSyncProvider
from app.design_sync.repository import DesignSyncRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DesignSyncContext:
    """Per-request shared deps for carved sub-services."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo_default = DesignSyncRepository(db)
        self._providers: dict[str, DesignSyncProvider] = {}

    @property
    def repo(self) -> DesignSyncRepository:
        return self._repo_default

    def get_provider(self, provider_name: str) -> DesignSyncProvider:
        if provider_name not in self._providers:
            from app.design_sync.service import SUPPORTED_PROVIDERS

            provider_cls = SUPPORTED_PROVIDERS.get(provider_name)
            if provider_cls is None:
                raise UnsupportedProviderError(
                    f"Provider '{provider_name}' is not supported. "
                    f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
                )
            self._providers[provider_name] = provider_cls()
        return self._providers[provider_name]

    @staticmethod
    def extract_file_ref(provider: str, file_url: str) -> str:
        """Extract provider-specific file reference from URL."""
        if provider == "figma":
            return extract_file_key(file_url)
        if provider == "penpot":
            return extract_penpot_id(file_url)
        return file_url

    async def verify_access(self, project_id: int, user: User) -> None:
        from app.projects.service import ProjectService

        project_service = ProjectService(self.db)
        await project_service.verify_project_access(project_id, user)

    async def get_project_name(self, project_id: int | None) -> str | None:
        return await self.repo.get_project_name(project_id)

    async def get_accessible_project_ids(self, user: User) -> list[int]:
        return await self.repo.get_accessible_project_ids(user.id, user.role)
