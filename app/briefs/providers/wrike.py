"""Wrike REST API v4 provider."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from app.briefs.exceptions import BriefItemNotFoundError, BriefValidationError
from app.briefs.protocol import RawAttachment, RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://www.wrike.com/api/v4"

_STATUS_MAP: dict[str, str] = {
    "active": "open",
    "completed": "done",
    "deferred": "cancelled",
    "cancelled": "cancelled",
}

_PRIORITY_MAP: dict[str, str] = {
    "high": "high",
    "normal": "medium",
    "low": "low",
}


def _extract_folder_id(project_url: str) -> str:
    """Extract folder/project ID from Wrike URL."""
    # https://www.wrike.com/open.htm?id=IEAAAAAQ...
    match = re.search(r"[?&]id=([A-Za-z0-9]+)", project_url)
    if match:
        return match.group(1)
    # https://www.wrike.com/workspace.htm#path=folder&id=IEAAAAAQ...
    match = re.search(r"id=([A-Za-z0-9]+)", project_url)
    if match:
        return match.group(1)
    msg = f"Cannot extract Wrike folder ID from URL: {project_url}"
    raise BriefValidationError(msg)


class WrikeBriefProvider:
    """Wrike REST API v4 provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/contacts",
                params={"me": "true"},
                headers={"Authorization": f"Bearer {credentials['access_token']}"},
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_folder_id(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        headers = {"Authorization": f"Bearer {credentials['access_token']}"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/folders/{project_id}/tasks",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        for task in data.get("data", []):
            status_name = task.get("status", "Active")
            importance = task.get("importance", "Normal")
            responsibles: list[Any] = task.get("responsibleIds", []) or []
            dates: dict[str, Any] = task.get("dates", {}) or {}
            due_str: str | None = dates.get("due")
            due_date = datetime.fromisoformat(due_str) if due_str else None

            items.append(
                RawBriefItem(
                    external_id=task["id"],
                    title=task.get("title", ""),
                    description="",
                    status=_STATUS_MAP.get(status_name.lower(), "open"),
                    priority=_PRIORITY_MAP.get(importance.lower()),
                    assignees=[str(r) for r in responsibles],
                    labels=[],
                    due_date=due_date,
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
        headers = {"Authorization": f"Bearer {credentials['access_token']}"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/tasks/{item_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        tasks = data.get("data", [])
        if not tasks:
            msg = f"Wrike task {item_id} not found"
            raise BriefItemNotFoundError(msg)

        task = tasks[0]
        status_name = task.get("status", "Active")
        importance = task.get("importance", "Normal")
        dates: dict[str, Any] = task.get("dates", {}) or {}
        due_str: str | None = dates.get("due")

        raw_atts: list[dict[str, Any]] = task.get("attachments", []) or []
        attachments = [
            RawAttachment(
                filename=att.get("name", ""),
                url=att.get("url", ""),
                size_bytes=att.get("size"),
            )
            for att in raw_atts
        ]

        raw_responsibles: list[Any] = task.get("responsibleIds", []) or []
        return RawBriefItem(
            external_id=task["id"],
            title=task.get("title", ""),
            description=task.get("description", "") or "",
            status=_STATUS_MAP.get(status_name.lower(), "open"),
            priority=_PRIORITY_MAP.get(importance.lower()),
            assignees=[str(r) for r in raw_responsibles],
            labels=[],
            due_date=datetime.fromisoformat(due_str) if due_str else None,
            attachments=attachments,
        )
