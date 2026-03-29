"""Trello REST API provider."""

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

_DEFAULT_BASE_URL = "https://api.trello.com/1"


def _extract_board_id(project_url: str) -> str:
    """Extract board ID or short link from Trello URL."""
    # https://trello.com/b/AbCdEfGh/board-name
    match = re.search(r"trello\.com/b/([a-zA-Z0-9]+)", project_url)
    if not match:
        msg = f"Cannot extract Trello board ID from URL: {project_url}"
        raise BriefValidationError(msg)
    return match.group(1)


class TrelloBriefProvider:
    """Trello REST API provider."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL

    def _auth_params(self, credentials: dict[str, str]) -> dict[str, str]:
        return {"key": credentials["api_key"], "token": credentials["api_token"]}

    async def validate_credentials(self, credentials: dict[str, str], project_url: str) -> bool:  # noqa: ARG002
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/members/me",
                params=self._auth_params(credentials),
            )
            resp.raise_for_status()
        return True

    async def extract_project_id(self, project_url: str) -> str:
        return _extract_board_id(project_url)

    async def list_items(self, credentials: dict[str, str], project_id: str) -> list[RawBriefItem]:
        settings = get_settings()
        params = {**self._auth_params(credentials), "fields": "name,closed,due,labels,idMembers"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/boards/{project_id}/cards",
                params=params,
            )
            resp.raise_for_status()
            cards = resp.json()

        items: list[RawBriefItem] = []
        for card in cards:
            raw_labels: list[dict[str, Any]] = card.get("labels", []) or []
            labels: list[str] = [lbl.get("name", "") for lbl in raw_labels]
            due_str = card.get("due")
            due_date = datetime.fromisoformat(due_str) if due_str else None
            is_closed = card.get("closed", False)

            items.append(
                RawBriefItem(
                    external_id=card["id"],
                    title=card.get("name", ""),
                    description="",
                    status="done" if is_closed else "open",
                    priority=None,
                    assignees=[],
                    labels=labels,
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
        params = {**self._auth_params(credentials), "attachments": "true"}

        async with httpx.AsyncClient(timeout=settings.briefs.sync_timeout) as client:
            resp = await client.get(
                f"{self._base_url}/cards/{item_id}",
                params=params,
            )
            resp.raise_for_status()
            card = resp.json()

        raw_labels: list[dict[str, Any]] = card.get("labels", []) or []
        labels: list[str] = [lbl.get("name", "") for lbl in raw_labels]
        due_str = card.get("due")
        due_date = datetime.fromisoformat(due_str) if due_str else None

        raw_atts: list[dict[str, Any]] = card.get("attachments", []) or []
        attachments = [
            RawAttachment(
                filename=att.get("name", ""),
                url=att.get("url", ""),
                size_bytes=att.get("bytes"),
            )
            for att in raw_atts
        ]

        return RawBriefItem(
            external_id=card["id"],
            title=card.get("name", ""),
            description=card.get("desc", ""),
            status="done" if card.get("closed") else "open",
            priority=None,
            assignees=[],
            labels=labels,
            due_date=due_date,
            attachments=attachments,
        )
