"""ClickUp REST API v2 provider."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.briefs.exceptions import BriefValidationError
from app.briefs.protocol import RawAttachment, RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://api.clickup.com/api/v2"

_STATUS_MAP: dict[str, str] = {
    "to do": "open",
    "open": "open",
    "in progress": "in_progress",
    "review": "in_progress",
    "complete": "done",
    "closed": "done",
    "done": "done",
    "cancelled": "cancelled",
}

_PRIORITY_MAP: dict[int, str] = {
    1: "high",
    2: "high",
    3: "medium",
    4: "low",
}


def _extract_list_id(project_url: str) -> str:
    """Extract list/folder/space ID from ClickUp URL."""
    # https://app.clickup.com/123/v/li/456
    # https://app.clickup.com/123/v/f/789/li/456
    match = re.search(r"/li/(\d+)", project_url)
    if match:
        return match.group(1)
    # Fallback: try folder
    match = re.search(r"/f/(\d+)", project_url)
    if match:
        return match.group(1)
    # Fallback: try space
    match = re.search(r"/(\d+)/v", project_url)
    if match:
        return match.group(1)
    msg = f"Cannot extract ClickUp list/folder ID from URL: {project_url}"
    raise BriefValidationError(msg)


class ClickUpBriefProvider:
    """ClickUp REST API v2 provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/user",
                headers={"Authorization": credentials["api_token"]},
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_list_id(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        headers = {"Authorization": credentials["api_token"]}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/list/{project_id}/task",
                params={"include_closed": "true"},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        for task in data.get("tasks", []):
            status_obj: dict[str, Any] = task.get("status") or {}
            status_name: str = status_obj.get("status", "open")
            priority_obj = task.get("priority")
            priority_id = int(priority_obj.get("id", 0)) if priority_obj else 0
            assignees = [
                a.get("username", a.get("email", "")) for a in task.get("assignees", []) if a
            ]
            raw_tags: list[dict[str, Any]] = task.get("tags", []) or []
            tags: list[str] = [t.get("name", "") for t in raw_tags]
            due_ts = task.get("due_date")
            due_date = datetime.fromtimestamp(int(due_ts) / 1000, tz=UTC) if due_ts else None

            items.append(
                RawBriefItem(
                    external_id=task["id"],
                    title=task.get("name", ""),
                    description="",
                    status=_STATUS_MAP.get(status_name.lower(), "open"),
                    priority=_PRIORITY_MAP.get(priority_id),
                    assignees=assignees,
                    labels=tags,
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
        headers = {"Authorization": credentials["api_token"]}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/task/{item_id}",
                headers=headers,
            )
            resp.raise_for_status()
            task = resp.json()

        status_obj_detail: dict[str, Any] = task.get("status") or {}
        status_name: str = status_obj_detail.get("status", "open")
        priority_obj = task.get("priority")
        priority_id = int(priority_obj.get("id", 0)) if priority_obj else 0
        assignees = [a.get("username", a.get("email", "")) for a in task.get("assignees", []) if a]
        raw_tags: list[dict[str, Any]] = task.get("tags", []) or []
        tags: list[str] = [t.get("name", "") for t in raw_tags]
        due_ts = task.get("due_date")

        raw_atts: list[dict[str, Any]] = task.get("attachments", []) or []
        attachments = [
            RawAttachment(
                filename=att.get("title", ""),
                url=att.get("url", ""),
                size_bytes=att.get("total_size"),
            )
            for att in raw_atts
        ]

        return RawBriefItem(
            external_id=task["id"],
            title=task.get("name", ""),
            description=task.get("description", "") or "",
            status=_STATUS_MAP.get(status_name.lower(), "open"),
            priority=_PRIORITY_MAP.get(priority_id),
            assignees=assignees,
            labels=tags,
            due_date=(
                datetime.fromtimestamp(int(due_ts) / 1000) if due_ts else None  # noqa: DTZ006
            ),
            attachments=attachments,
        )
