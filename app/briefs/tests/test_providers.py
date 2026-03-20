"""Unit tests for brief providers (mock HTTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.briefs.exceptions import BriefValidationError
from app.briefs.providers.asana import AsanaBriefProvider, _extract_gid
from app.briefs.providers.basecamp import _extract_ids
from app.briefs.providers.clickup import _extract_list_id
from app.briefs.providers.jira import JiraBriefProvider, _extract_domain_and_key
from app.briefs.providers.monday import _extract_board_id
from app.briefs.providers.notion import _extract_database_id
from app.briefs.providers.trello import TrelloBriefProvider
from app.briefs.providers.trello import _extract_board_id as _extract_trello_id
from app.briefs.providers.wrike import _extract_folder_id

# ── URL Extraction Tests ──


class TestJiraUrlExtraction:
    def test_extracts_domain_and_key(self) -> None:
        url = "https://myteam.atlassian.net/jira/software/projects/EMAIL/board"
        domain, key = _extract_domain_and_key(url)
        assert domain == "myteam"
        assert key == "EMAIL"

    def test_extracts_from_browse_url(self) -> None:
        url = "https://myteam.atlassian.net/browse/PROJ"
        domain, key = _extract_domain_and_key(url)
        assert domain == "myteam"
        assert key == "PROJ"

    def test_raises_on_invalid_url(self) -> None:
        with pytest.raises(BriefValidationError, match="Cannot extract"):
            _extract_domain_and_key("https://example.com")


class TestAsanaUrlExtraction:
    def test_extracts_gid(self) -> None:
        url = "https://app.asana.com/0/1234567890/list"
        assert _extract_gid(url) == "1234567890"

    def test_raises_on_invalid_url(self) -> None:
        with pytest.raises(BriefValidationError, match="Cannot extract"):
            _extract_gid("https://example.com")


class TestMondayUrlExtraction:
    def test_extracts_board_id(self) -> None:
        url = "https://myteam.monday.com/boards/9876543210"
        assert _extract_board_id(url) == "9876543210"

    def test_raises_on_invalid_url(self) -> None:
        with pytest.raises(BriefValidationError, match="Cannot extract"):
            _extract_board_id("https://example.com")


class TestClickUpUrlExtraction:
    def test_extracts_list_id(self) -> None:
        url = "https://app.clickup.com/123/v/li/456"
        assert _extract_list_id(url) == "456"

    def test_extracts_folder_id(self) -> None:
        url = "https://app.clickup.com/123/v/f/789"
        assert _extract_list_id(url) == "789"


class TestTrelloUrlExtraction:
    def test_extracts_board_id(self) -> None:
        url = "https://trello.com/b/AbCdEfGh/my-board"
        assert _extract_trello_id(url) == "AbCdEfGh"


class TestNotionUrlExtraction:
    def test_extracts_database_id(self) -> None:
        url = "https://www.notion.so/workspace/abcdef1234567890abcdef1234567890?v=..."
        result = _extract_database_id(url)
        assert result == "abcdef12-3456-7890-abcd-ef1234567890"


class TestWrikeUrlExtraction:
    def test_extracts_folder_id(self) -> None:
        url = "https://www.wrike.com/open.htm?id=IEAAAAAQ123"
        assert _extract_folder_id(url) == "IEAAAAAQ123"


class TestBasecampUrlExtraction:
    def test_extracts_ids(self) -> None:
        url = "https://3.basecamp.com/12345/buckets/67890/todosets/111"
        account_id, project_id = _extract_ids(url)
        assert account_id == "12345"
        assert project_id == "67890"


# ── Provider Integration Tests (Mock HTTP) ──


def _mock_response(json_data: object, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://mock"),
    )
    return resp


class TestJiraProvider:
    @pytest.mark.asyncio
    async def test_list_items_parses_response(self) -> None:
        provider = JiraBriefProvider()
        mock_data = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "First task",
                        "status": {"name": "To Do"},
                        "priority": {"name": "High"},
                        "assignee": {"displayName": "Alice"},
                        "labels": ["email"],
                        "duedate": None,
                        "attachment": [],
                    },
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client_cls.return_value = mock_client

            items = await provider.list_items(
                {"email": "test@test.com", "api_token": "token"},
                "myteam/TEST",
            )

        assert len(items) == 1
        assert items[0].external_id == "TEST-1"
        assert items[0].title == "First task"
        assert items[0].status == "open"
        assert items[0].priority == "high"


class TestAsanaProvider:
    @pytest.mark.asyncio
    async def test_list_items_parses_response(self) -> None:
        provider = AsanaBriefProvider()
        mock_data = {
            "data": [
                {
                    "gid": "123",
                    "name": "Design review",
                    "assignee": {"name": "Bob"},
                    "due_on": None,
                    "completed": False,
                    "tags": [{"name": "email"}],
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client_cls.return_value = mock_client

            items = await provider.list_items(
                {"personal_access_token": "token"},
                "123456",
            )

        assert len(items) == 1
        assert items[0].external_id == "123"
        assert items[0].status == "open"
        assert items[0].assignees == ["Bob"]


class TestTrelloProvider:
    @pytest.mark.asyncio
    async def test_list_items_parses_response(self) -> None:
        provider = TrelloBriefProvider()
        mock_data = [
            {
                "id": "card1",
                "name": "Email template",
                "closed": False,
                "due": None,
                "labels": [{"name": "campaign"}],
            }
        ]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=_mock_response(mock_data))
            mock_client_cls.return_value = mock_client

            items = await provider.list_items(
                {"api_key": "key", "api_token": "token"},
                "boardId",
            )

        assert len(items) == 1
        assert items[0].external_id == "card1"
        assert items[0].status == "open"
        assert items[0].labels == ["campaign"]
