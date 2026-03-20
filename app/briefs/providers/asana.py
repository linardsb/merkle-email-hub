"""Asana REST API provider."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from app.briefs.exceptions import BriefValidationError
from app.briefs.protocol import RawAttachment, RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://app.asana.com/api/1.0"


def _extract_gid(project_url: str) -> str:
    """Extract project GID from Asana URL."""
    # https://app.asana.com/0/1234567890/list
    match = re.search(r"asana\.com/0/(\d+)", project_url)
    if not match:
        msg = f"Cannot extract Asana project GID from URL: {project_url}"
        raise BriefValidationError(msg)
    return match.group(1)


class AsanaBriefProvider:
    """Asana REST API provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        token = credentials["personal_access_token"]
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_gid(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        token = credentials["personal_access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/projects/{project_id}/tasks",
                params={
                    "opt_fields": "name,assignee.name,due_on,completed,tags.name,memberships.section.name",
                    "limit": str(settings.briefs.max_items_per_sync),
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        for task in data.get("data", []):
            assignee = task.get("assignee")
            assignee_name = assignee.get("name", "") if assignee else ""
            raw_tags: list[dict[str, Any]] = task.get("tags", []) or []
            tags: list[str] = [t.get("name", "") for t in raw_tags]
            due_str = task.get("due_on")
            due_date = datetime.fromisoformat(due_str) if due_str else None
            completed = task.get("completed", False)

            items.append(
                RawBriefItem(
                    external_id=task["gid"],
                    title=task.get("name", ""),
                    description="",
                    status="done" if completed else "open",
                    priority=None,
                    assignees=[assignee_name] if assignee_name else [],
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
        token = credentials["personal_access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/tasks/{item_id}",
                params={
                    "opt_fields": "name,notes,html_notes,assignee.name,due_on,completed,tags.name,attachments",
                },
                headers=headers,
            )
            resp.raise_for_status()
            task = resp.json().get("data", {})

        assignee = task.get("assignee")
        assignee_name = assignee.get("name", "") if assignee else ""
        raw_tags: list[dict[str, Any]] = task.get("tags", []) or []
        tags: list[str] = [t.get("name", "") for t in raw_tags]
        due_str = task.get("due_on")

        raw_atts: list[dict[str, Any]] = task.get("attachments", []) or []
        attachments = [
            RawAttachment(
                filename=att.get("name", ""),
                url=att.get("download_url", att.get("view_url", "")),
            )
            for att in raw_atts
        ]

        return RawBriefItem(
            external_id=task["gid"],
            title=task.get("name", ""),
            description=task.get("html_notes", task.get("notes", "")),
            status="done" if task.get("completed") else "open",
            priority=None,
            assignees=[assignee_name] if assignee_name else [],
            labels=tags,
            due_date=datetime.fromisoformat(due_str) if due_str else None,
            attachments=attachments,
        )
