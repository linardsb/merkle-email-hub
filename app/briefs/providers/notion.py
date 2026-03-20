"""Notion API v1 provider."""

from __future__ import annotations

import re
from typing import Any, cast

import httpx

from app.briefs.exceptions import BriefValidationError
from app.briefs.protocol import RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"

_STATUS_MAP: dict[str, str] = {
    "not started": "open",
    "to do": "open",
    "in progress": "in_progress",
    "done": "done",
    "complete": "done",
    "cancelled": "cancelled",
    "archived": "cancelled",
}


def _extract_database_id(project_url: str) -> str:
    """Extract database ID from Notion URL (remove hyphens)."""
    # https://www.notion.so/workspace/abcdef1234567890abcdef1234567890?v=...
    # https://www.notion.so/abcdef1234567890abcdef1234567890
    match = re.search(r"([a-f0-9]{32})", project_url.replace("-", ""))
    if not match:
        msg = f"Cannot extract Notion database ID from URL: {project_url}"
        raise BriefValidationError(msg)
    raw = match.group(1)
    # Format as UUID: 8-4-4-4-12
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def _get_title(page: dict[str, Any]) -> str:
    """Extract title from a Notion page's properties."""
    props: dict[str, Any] = page.get("properties") or {}
    for raw_prop in props.values():
        prop = cast(dict[str, Any], raw_prop)
        if not isinstance(raw_prop, dict):
            continue
        if prop.get("type") == "title":
            title_parts: list[dict[str, Any]] = prop.get("title", [])
            return "".join(str(p.get("plain_text", "")) for p in title_parts)
    return ""


def _get_status(page: dict[str, Any]) -> str:
    """Extract status from a Notion page's properties."""
    props: dict[str, Any] = page.get("properties") or {}
    for raw_prop in props.values():
        prop = cast(dict[str, Any], raw_prop)
        if not isinstance(raw_prop, dict):
            continue
        if prop.get("type") == "status":
            status_obj: dict[str, Any] = prop.get("status") or {}
            name = str(status_obj.get("name", "")).lower()
            return _STATUS_MAP.get(name, "open")
    return "open"


def _get_assignees(page: dict[str, Any]) -> list[str]:
    """Extract assignees from people-type properties."""
    props: dict[str, Any] = page.get("properties") or {}
    for raw_prop in props.values():
        prop = cast(dict[str, Any], raw_prop)
        if not isinstance(raw_prop, dict):
            continue
        if prop.get("type") == "people":
            people: list[dict[str, Any]] = prop.get("people", [])
            return [str(p.get("name", "")) for p in people if p.get("name")]
    return []


class NotionBriefProvider:
    """Notion API v1 provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials['integration_token']}",
            "Notion-Version": _NOTION_VERSION,
        }

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/users/me",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_database_id(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        headers = self._headers(credentials)

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.post(
                f"{self._base_url}/databases/{project_id}/query",
                headers=headers,
                json={"page_size": min(100, settings.briefs.max_items_per_sync)},
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        for page in data.get("results", []):
            items.append(
                RawBriefItem(
                    external_id=page["id"],
                    title=_get_title(page),
                    description="",
                    status=_get_status(page),
                    priority=None,
                    assignees=_get_assignees(page),
                    labels=[],
                )
            )

        return items

    async def get_item(
        self,
        credentials: dict[str, str],
        project_id: str,  # noqa: ARG002
        item_id: str,
    ) -> RawBriefItem:
        settings = get_settings()
        headers = self._headers(credentials)

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            # Get page properties
            resp = await client.get(
                f"{self._base_url}/pages/{item_id}",
                headers=headers,
            )
            resp.raise_for_status()
            page = resp.json()

            # Get page content (blocks)
            blocks_resp = await client.get(
                f"{self._base_url}/blocks/{item_id}/children",
                headers=headers,
            )
            blocks_resp.raise_for_status()
            blocks = blocks_resp.json()

        # Build description from blocks
        desc_parts: list[str] = []
        for block in blocks.get("results", []):
            block_type = block.get("type", "")
            block_data = block.get(block_type, {})
            if isinstance(block_data, dict):
                typed_block = cast(dict[str, Any], block_data)
                rich_text: list[dict[str, Any]] = typed_block.get("rich_text", [])
                text = "".join(str(rt.get("plain_text", "")) for rt in rich_text)
                if text:
                    desc_parts.append(text)

        return RawBriefItem(
            external_id=page["id"],
            title=_get_title(page),
            description="\n".join(desc_parts),
            status=_get_status(page),
            priority=None,
            assignees=_get_assignees(page),
            labels=[],
        )
