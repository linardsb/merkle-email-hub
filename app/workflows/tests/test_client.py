"""Unit tests for KestraClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.workflows.exceptions import (
    KestraUnavailableError,
    WorkflowNotFoundError,
    WorkflowTriggerError,
)
from app.workflows.kestra_client import KestraClient


def _mock_settings() -> Any:
    """Create mock settings for KestraClient."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.kestra.api_url = "http://kestra-test:8080"
    settings.kestra.namespace = "test-ns"
    settings.kestra.request_timeout_s = 5.0
    settings.kestra.api_token = "test-token"
    return settings


def _make_client() -> KestraClient:
    with patch("app.workflows.kestra_client.get_settings", return_value=_mock_settings()):
        return KestraClient()


def _execution_json(
    exec_id: str = "exec-1",
    flow_id: str = "test-flow",
    status: str = "RUNNING",
) -> dict[str, Any]:
    return {
        "id": exec_id,
        "namespace": "test-ns",
        "flowId": flow_id,
        "state": {
            "current": status,
            "startDate": "2026-03-18T10:00:00Z",
        },
        "inputs": {"brief": "test"},
        "outputs": {},
        "taskRunList": [
            {
                "taskId": "build",
                "state": {
                    "current": "SUCCESS",
                    "startDate": "2026-03-18T10:00:01Z",
                    "endDate": "2026-03-18T10:00:05Z",
                },
                "outputs": {"html": "<p>test</p>"},
            }
        ],
    }


def _mock_http_client(
    handler: Any,
) -> AsyncMock:
    """Create a mock httpx.AsyncClient that uses handler for request/get."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    mock.is_closed = False

    async def _request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request(method, url)
        resp: httpx.Response = handler(req)
        resp._request = req
        return resp

    async def _get(url: str, **kwargs: Any) -> httpx.Response:
        return await _request("GET", url, **kwargs)

    mock.request = _request
    mock.get = _get
    return mock


class TestKestraClientInit:
    def test_auth_header_set_when_token_configured(self) -> None:
        client = _make_client()
        assert client._headers["Authorization"] == "Bearer test-token"

    def test_base_url_stripped(self) -> None:
        client = _make_client()
        assert client._base_url == "http://kestra-test:8080"


class TestHealthCheck:
    @pytest.mark.anyio
    async def test_health_check_returns_true(self) -> None:
        client = _make_client()
        mock = _mock_http_client(lambda _req: httpx.Response(200, json=[]))
        client._client = mock
        result = await client.health_check()
        assert result is True

    @pytest.mark.anyio
    async def test_health_check_returns_false_on_error(self) -> None:
        client = _make_client()
        mock = _mock_http_client(lambda _req: httpx.Response(500))
        client._client = mock
        result = await client.health_check()
        assert result is False


class TestTriggerExecution:
    @pytest.mark.anyio
    async def test_trigger_parses_response(self) -> None:
        client = _make_client()
        exec_data = _execution_json()

        def _handler(_req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=exec_data)

        mock = _mock_http_client(_handler)
        client._client = mock
        execution = await client.trigger_execution("test-flow", {"brief": "test"})

        assert execution.id == "exec-1"
        assert execution.flow_id == "test-flow"
        assert execution.status == "RUNNING"
        assert len(execution.task_runs) == 1
        assert execution.task_runs[0].task_id == "build"


class TestGetExecution:
    @pytest.mark.anyio
    async def test_404_raises_not_found(self) -> None:
        client = _make_client()

        def _handler(_req: httpx.Request) -> httpx.Response:
            resp = httpx.Response(404, json={"message": "not found"})
            raise httpx.HTTPStatusError("Not found", request=_req, response=resp)

        mock = _mock_http_client(_handler)
        client._client = mock
        with pytest.raises(WorkflowNotFoundError):
            await client.get_execution("nonexistent")

    @pytest.mark.anyio
    async def test_500_raises_trigger_error(self) -> None:
        client = _make_client()

        def _handler(_req: httpx.Request) -> httpx.Response:
            resp = httpx.Response(500, json={"message": "error"})
            raise httpx.HTTPStatusError("Server error", request=_req, response=resp)

        mock = _mock_http_client(_handler)
        client._client = mock
        with pytest.raises(WorkflowTriggerError):
            await client.get_execution("exec-1")

    @pytest.mark.anyio
    async def test_connect_error_raises_unavailable(self) -> None:
        client = _make_client()

        def _handler(_req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        mock = _mock_http_client(_handler)
        client._client = mock
        with pytest.raises(KestraUnavailableError):
            await client.get_execution("exec-1")

    @pytest.mark.anyio
    async def test_timeout_raises_unavailable(self) -> None:
        client = _make_client()

        def _handler(_req: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Timed out")

        mock = _mock_http_client(_handler)
        client._client = mock
        with pytest.raises(KestraUnavailableError, match="timed out"):
            await client.get_execution("exec-1")
