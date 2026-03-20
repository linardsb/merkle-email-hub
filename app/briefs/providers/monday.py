"""Monday.com GraphQL API provider."""

from __future__ import annotations

import re

import httpx

from app.briefs.exceptions import BriefItemNotFoundError, BriefValidationError
from app.briefs.protocol import RawBriefItem
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_API_URL = "https://api.monday.com/v2"

_STATUS_MAP: dict[str, str] = {
    "done": "done",
    "stuck": "in_progress",
    "working on it": "in_progress",
    "": "open",
}


def _extract_board_id(project_url: str) -> str:
    """Extract board ID from Monday.com URL."""
    # https://myteam.monday.com/boards/1234567890
    match = re.search(r"/boards/(\d+)", project_url)
    if not match:
        msg = f"Cannot extract Monday.com board ID from URL: {project_url}"
        raise BriefValidationError(msg)
    return match.group(1)


class MondayBriefProvider:
    """Monday.com GraphQL API provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._api_url = base_url or _DEFAULT_API_URL

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.post(
                self._api_url,
                json={"query": "{ me { id name } }"},
                headers={"Authorization": credentials["api_key"]},
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                msg = f"Monday.com auth failed: {data['errors']}"
                raise BriefValidationError(msg)
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_board_id(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        query = """
        query ($boardId: [ID!]!) {
            boards(ids: $boardId) {
                items_page(limit: 500) {
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            type
                        }
                    }
                }
            }
        }
        """
        headers = {"Authorization": credentials["api_key"]}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.post(
                self._api_url,
                json={"query": query, "variables": {"boardId": [project_id]}},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items: list[RawBriefItem] = []
        boards = data.get("data", {}).get("boards", [])
        if not boards:
            return items

        for item in boards[0].get("items_page", {}).get("items", []):
            columns = {c["id"]: c for c in item.get("column_values", [])}

            # Extract status
            status_col = columns.get("status", {})
            status_text = (status_col.get("text", "") or "").lower()
            status = _STATUS_MAP.get(status_text, "open")

            # Extract person (assignee)
            person_col = columns.get("person", {})
            assignee = person_col.get("text", "") or ""

            items.append(
                RawBriefItem(
                    external_id=item["id"],
                    title=item.get("name", ""),
                    description="",
                    status=status,
                    priority=None,
                    assignees=[assignee] if assignee else [],
                    labels=[],
                    due_date=None,  # Monday date parsing is complex
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
        query = """
        query ($itemId: [ID!]!) {
            items(ids: $itemId) {
                id
                name
                column_values {
                    id
                    text
                    type
                }
                updates(limit: 1) {
                    text_body
                }
            }
        }
        """
        headers = {"Authorization": credentials["api_key"]}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.post(
                self._api_url,
                json={"query": query, "variables": {"itemId": [item_id]}},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items_data = data.get("data", {}).get("items", [])
        if not items_data:
            msg = f"Monday.com item {item_id} not found"
            raise BriefItemNotFoundError(msg)

        item = items_data[0]
        columns = {c["id"]: c for c in item.get("column_values", [])}
        status_text = (columns.get("status", {}).get("text", "") or "").lower()
        person_text = columns.get("person", {}).get("text", "") or ""

        # Get description from latest update
        updates = item.get("updates", [])
        description = updates[0].get("text_body", "") if updates else ""

        return RawBriefItem(
            external_id=item["id"],
            title=item.get("name", ""),
            description=description,
            status=_STATUS_MAP.get(status_text, "open"),
            priority=None,
            assignees=[person_text] if person_text else [],
            labels=[],
        )
