"""Async HTTP client for the Kestra REST API."""

from __future__ import annotations

from typing import Any, cast

import httpx
import yaml

from app.core.config import get_settings
from app.core.logging import get_logger
from app.workflows.exceptions import (
    KestraUnavailableError,
    WorkflowNotFoundError,
    WorkflowTriggerError,
)
from app.workflows.schemas import Execution, Flow, LogEntry, TaskRun

logger = get_logger(__name__)


class KestraClient:
    """HTTP client for Kestra workflow orchestration API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.kestra.api_url.rstrip("/")
        self._namespace = settings.kestra.namespace
        self._timeout = settings.kestra.request_timeout_s
        self._headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if settings.kestra.api_token:
            self._headers["Authorization"] = f"Bearer {settings.kestra.api_token}"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _url(self, path: str) -> str:
        return f"{self._base_url}/api/v1{path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:  # noqa: ANN401
        """Execute HTTP request with error handling."""
        try:
            client = await self._get_client()
            resp = await client.request(method, self._url(path), **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.ConnectError as exc:
            raise KestraUnavailableError("Cannot connect to Kestra service") from exc
        except httpx.TimeoutException as exc:
            raise KestraUnavailableError("Kestra request timed out") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise WorkflowNotFoundError(f"Kestra resource not found: {path}") from exc
            logger.error(
                "kestra.http_error",
                status_code=exc.response.status_code,
                path=path,
            )
            raise WorkflowTriggerError(f"Kestra API error: {exc.response.status_code}") from exc

    # --- Flow management ---

    async def create_flow(
        self, flow_id: str, definition: dict[str, Any], *, namespace: str | None = None
    ) -> Flow:
        """Register or update a workflow definition."""
        ns = namespace or self._namespace
        definition["id"] = flow_id
        definition["namespace"] = ns
        yaml_source = yaml.dump(definition, default_flow_style=False)

        resp = await self._request(
            "POST",
            "/flows",
            content=yaml_source,
            headers={"Content-Type": "application/x-yaml", "Accept": "application/json"},
        )
        data = resp.json()
        logger.info("kestra.flow.created", flow_id=flow_id, namespace=ns)
        return Flow(
            id=data["id"],
            namespace=data["namespace"],
            revision=data.get("revision", 1),
            description=data.get("description"),
            inputs=data.get("inputs", []),
            triggers=data.get("triggers", []),
        )

    async def get_flow(self, flow_id: str, *, namespace: str | None = None) -> Flow:
        """Get a flow definition."""
        ns = namespace or self._namespace
        resp = await self._request("GET", f"/flows/{ns}/{flow_id}")
        data = resp.json()
        return Flow(
            id=data["id"],
            namespace=data["namespace"],
            revision=data.get("revision", 1),
            description=data.get("description"),
            inputs=data.get("inputs", []),
            triggers=data.get("triggers", []),
        )

    async def list_flows(self, *, namespace: str | None = None) -> list[Flow]:
        """List all flows in a namespace."""
        ns = namespace or self._namespace
        resp = await self._request("GET", f"/flows/{ns}")
        results: list[Flow] = []
        for item in resp.json():
            results.append(
                Flow(
                    id=item["id"],
                    namespace=item["namespace"],
                    revision=item.get("revision", 1),
                    description=item.get("description"),
                    inputs=item.get("inputs", []),
                    triggers=item.get("triggers", []),
                )
            )
        return results

    # --- Execution management ---

    async def trigger_execution(
        self, flow_id: str, inputs: dict[str, Any], *, namespace: str | None = None
    ) -> Execution:
        """Start a workflow execution with given inputs."""
        ns = namespace or self._namespace
        resp = await self._request(
            "POST",
            f"/executions/{ns}/{flow_id}",
            json=inputs,
        )
        data = resp.json()
        logger.info(
            "kestra.execution.triggered",
            execution_id=data["id"],
            flow_id=flow_id,
        )
        return self._parse_execution(data)

    async def get_execution(self, execution_id: str) -> Execution:
        """Get execution status and details."""
        resp = await self._request("GET", f"/executions/{execution_id}")
        return self._parse_execution(resp.json())

    async def list_executions(
        self, flow_id: str, *, namespace: str | None = None, limit: int = 25
    ) -> list[Execution]:
        """List recent executions for a flow."""
        ns = namespace or self._namespace
        resp = await self._request(
            "GET",
            "/executions",
            params={"namespace": ns, "flowId": flow_id, "size": limit},
        )
        raw: Any = resp.json()
        items: list[dict[str, Any]] = cast(
            list[dict[str, Any]],
            raw.get("results", raw) if isinstance(raw, dict) else raw,
        )
        return [self._parse_execution(item) for item in items]

    async def get_logs(self, execution_id: str) -> list[LogEntry]:
        """Get execution log entries."""
        resp = await self._request("GET", f"/logs/{execution_id}")
        return [
            LogEntry(
                timestamp=entry["timestamp"],
                level=entry.get("level", "INFO"),
                message=entry.get("message", ""),
                task_id=entry.get("taskId"),
            )
            for entry in resp.json()
        ]

    # --- Helpers ---

    @staticmethod
    def _parse_execution(data: dict[str, Any]) -> Execution:
        """Parse Kestra execution JSON into typed schema."""
        task_runs = [
            TaskRun(
                task_id=tr["taskId"],
                status=tr["state"]["current"],
                started=tr["state"].get("startDate"),
                ended=tr["state"].get("endDate"),
                outputs=tr.get("outputs", {}),
            )
            for tr in data.get("taskRunList", [])
        ]
        return Execution(
            id=data["id"],
            namespace=data["namespace"],
            flow_id=data["flowId"],
            status=data["state"]["current"],
            started=data["state"]["startDate"],
            ended=data["state"].get("endDate"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            task_runs=task_runs,
        )

    async def health_check(self) -> bool:
        """Check Kestra API availability."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self._base_url}/api/v1/plugins")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
