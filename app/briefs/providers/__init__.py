"""Brief provider registry — maps platform names to provider implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.briefs.protocol import BriefProvider

_providers: dict[str, type[BriefProvider]] | None = None


def get_provider_registry() -> dict[str, type[BriefProvider]]:
    """Lazily build and return the provider registry."""
    global _providers
    if _providers is not None:
        return _providers

    from app.briefs.providers.asana import AsanaBriefProvider
    from app.briefs.providers.basecamp import BasecampBriefProvider
    from app.briefs.providers.clickup import ClickUpBriefProvider
    from app.briefs.providers.jira import JiraBriefProvider
    from app.briefs.providers.monday import MondayBriefProvider
    from app.briefs.providers.notion import NotionBriefProvider
    from app.briefs.providers.trello import TrelloBriefProvider
    from app.briefs.providers.wrike import WrikeBriefProvider

    _providers = {
        "jira": JiraBriefProvider,
        "asana": AsanaBriefProvider,
        "monday": MondayBriefProvider,
        "clickup": ClickUpBriefProvider,
        "trello": TrelloBriefProvider,
        "notion": NotionBriefProvider,
        "wrike": WrikeBriefProvider,
        "basecamp": BasecampBriefProvider,
    }
    return _providers
