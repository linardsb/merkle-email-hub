"""Jira Cloud REST API v3 provider."""

from __future__ import annotations

import base64
import re
from datetime import datetime
from typing import Any

import httpx

from app.briefs.exceptions import BriefValidationError
from app.briefs.protocol import RawAttachment, RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_STATUS_MAP: dict[str, str] = {
    "to do": "open",
    "open": "open",
    "new": "open",
    "backlog": "open",
    "in progress": "in_progress",
    "in review": "in_progress",
    "done": "done",
    "closed": "done",
    "resolved": "done",
    "cancelled": "cancelled",
    "won't do": "cancelled",
}

_PRIORITY_MAP: dict[str, str] = {
    "highest": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "lowest": "low",
}


def _extract_domain_and_key(project_url: str) -> tuple[str, str]:
    """Extract Atlassian domain and project key from URL."""
    # https://domain.atlassian.net/jira/software/projects/KEY/...
    # https://domain.atlassian.net/browse/KEY-123
    match = re.search(r"([\w-]+)\.atlassian\.net", project_url)
    if not match:
        msg = f"Cannot extract Atlassian domain from URL: {project_url}"
        raise BriefValidationError(msg)
    domain = match.group(1)

    key_match = re.search(r"/projects/([A-Z0-9]+)", project_url)
    if key_match:
        return domain, key_match.group(1)

    browse_match = re.search(r"/browse/([A-Z0-9]+)", project_url)
    if browse_match:
        return domain, browse_match.group(1)

    msg = f"Cannot extract project key from URL: {project_url}"
    raise BriefValidationError(msg)


class JiraBriefProvider:
    """Jira Cloud REST API v3 provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url_override = base_url

    def _resolve_base_url(self, domain: str) -> str:
        """Return override URL or build the real Atlassian URL from domain."""
        if self._base_url_override:
            return self._base_url_override
        return f"https://{domain}.atlassian.net/rest/api/3"

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:
        domain, _ = _extract_domain_and_key(project_url)
        base_url = self._resolve_base_url(domain)
        auth = base64.b64encode(
            f"{credentials['email']}:{credentials['api_token']}".encode()
        ).decode()
        settings = get_settings()

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{base_url}/myself",
                headers={"Authorization": f"Basic {auth}"},
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        domain, key = _extract_domain_and_key(project_url)
        return f"{domain}/{key}"

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        # We need the domain from stored context — extract from email domain won't work.
        # Use credentials email to build auth, and we need to store domain.
        # For simplicity, we'll search for the project across the user's accessible instance.
        email = credentials["email"]
        api_token = credentials["api_token"]
        auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

        # Discover domain from the Jira API — use serverInfo
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            # Try the standard Atlassian Cloud approach
            # The project_id here is the project key, and we need the base URL.
            # Since we validated credentials with a URL, the external_project_id
            # format is "KEY" and we stored the domain. But we don't have the domain
            # in credentials. So we encode it as "domain/KEY" in extract_project_id.
            parts = project_id.split("/", 1)
            if len(parts) == 2:
                domain, key = parts
            else:
                # Fallback: try using the key directly with serverInfo
                key = project_id
                # Try to get server info to discover base URL
                # This won't work without domain, so raise
                msg = "Jira project_id must be in 'domain/KEY' format"
                raise BriefValidationError(msg)

            base_url = self._resolve_base_url(domain)
            headers = {"Authorization": f"Basic {auth}"}

            resp = await client.get(
                f"{base_url}/search",
                params={
                    "jql": f'project="{key}"',
                    "maxResults": str(settings.briefs.max_items_per_sync),
                    "fields": "summary,status,priority,assignee,labels,duedate,attachment",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        for issue in data.get("issues", []):
            fields: dict[str, Any] = issue.get("fields", {})
            status_obj: dict[str, Any] = fields.get("status", {}) or {}
            status_name: str = status_obj.get("name", "Open")
            priority_obj: dict[str, Any] = fields.get("priority", {}) or {}
            priority_name: str = priority_obj.get("name", "")
            assignee = fields.get("assignee")
            assignee_name = assignee.get("displayName", "") if assignee else ""
            labels: list[str] = fields.get("labels", []) or []
            due_date_str = fields.get("duedate")
            due_date = datetime.fromisoformat(due_date_str) if due_date_str else None

            attachments: list[RawAttachment] = []
            raw_atts: list[dict[str, Any]] = fields.get("attachment", []) or []
            for att in raw_atts:
                attachments.append(
                    RawAttachment(
                        filename=att.get("filename", ""),
                        url=att.get("content", ""),
                        size_bytes=att.get("size"),
                    )
                )

            items.append(
                RawBriefItem(
                    external_id=issue["key"],
                    title=fields.get("summary", ""),
                    description="",  # Skip description in list (expensive)
                    status=_STATUS_MAP.get(status_name.lower(), "open"),
                    priority=_PRIORITY_MAP.get(priority_name.lower()),
                    assignees=[assignee_name] if assignee_name else [],
                    labels=labels,
                    due_date=due_date,
                    attachments=attachments,
                )
            )

        return items

    async def get_item(
        self, credentials: dict[str, str], project_id: str, item_id: str
    ) -> RawBriefItem:
        settings = get_settings()
        email = credentials["email"]
        api_token = credentials["api_token"]
        auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

        parts = project_id.split("/", 1)
        domain = parts[0] if len(parts) == 2 else project_id
        base_url = self._resolve_base_url(domain)

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{base_url}/issue/{item_id}",
                params={"expand": "renderedFields"},
                headers={"Authorization": f"Basic {auth}"},
            )
            resp.raise_for_status()
            issue = resp.json()

        fields: dict[str, Any] = issue.get("fields", {})
        rendered: dict[str, Any] = issue.get("renderedFields", {})
        status_obj: dict[str, Any] = fields.get("status", {}) or {}
        status_name: str = status_obj.get("name", "Open")
        priority_obj: dict[str, Any] = fields.get("priority", {}) or {}
        priority_name: str = priority_obj.get("name", "")
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName", "") if assignee else ""

        raw_atts: list[dict[str, Any]] = fields.get("attachment", []) or []
        attachments = [
            RawAttachment(
                filename=att.get("filename", ""),
                url=att.get("content", ""),
                size_bytes=att.get("size"),
            )
            for att in raw_atts
        ]

        return RawBriefItem(
            external_id=issue["key"],
            title=fields.get("summary", ""),
            description=rendered.get("description", fields.get("description", "") or ""),
            status=_STATUS_MAP.get(status_name.lower(), "open"),
            priority=_PRIORITY_MAP.get(priority_name.lower()),
            assignees=[assignee_name] if assignee_name else [],
            labels=fields.get("labels", []) or [],
            due_date=(datetime.fromisoformat(fields["duedate"]) if fields.get("duedate") else None),
            attachments=attachments,
        )
