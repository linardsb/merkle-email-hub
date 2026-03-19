"""Penpot REST API client."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

from app.connectors.http_resilience import resilient_request
from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.penpot.schemas import (
    PenpotFile,
    PenpotProject,
)

logger = get_logger(__name__)


class PenpotClient:
    """HTTP client for the Penpot REST API.

    Penpot v2 REST API uses RPC-style commands.
    Authentication via access token in Authorization header.

    Use as an async context manager to reuse a single httpx connection pool::

        async with PenpotClient(...) as client:
            await client.get_file(file_id)
    """

    def __init__(self, base_url: str, access_token: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Token {access_token}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._http = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _get_http(self) -> httpx.AsyncClient:
        """Return the managed client. Raises if used outside context manager."""
        if self._http is None:
            msg = "PenpotClient must be used as async context manager: async with PenpotClient(...) as client:"
            raise RuntimeError(msg)
        return self._http

    async def validate(self) -> bool:
        """Validate credentials by fetching user profile."""
        try:
            http = self._get_http()
            resp = await resilient_request(
                http,
                "GET",
                f"{self._base_url}/api/rpc/command/get-profile",
                headers=self._headers,
            )
            return resp.status_code == 200
        except (httpx.HTTPError, SyncFailedError):
            logger.warning("penpot.connection_validation_failed", exc_info=True)
            return False

    async def list_projects(self) -> list[PenpotProject]:
        """List all projects accessible to the authenticated user."""
        http = self._get_http()
        resp = await resilient_request(
            http,
            "GET",
            f"{self._base_url}/api/rpc/command/get-all-projects",
            headers=self._headers,
        )
        self._check_response(resp)
        return [PenpotProject(**p) for p in resp.json()]

    async def list_project_files(self, project_id: str) -> list[PenpotFile]:
        """List files within a project."""
        http = self._get_http()
        resp = await resilient_request(
            http,
            "GET",
            f"{self._base_url}/api/rpc/command/get-project-files",
            headers=self._headers,
            params={"project-id": project_id},
        )
        self._check_response(resp)
        return [PenpotFile(**f) for f in resp.json()]

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """Get full file data including pages, objects, colors, typographies."""
        http = self._get_http()
        resp = await resilient_request(
            http,
            "GET",
            f"{self._base_url}/api/rpc/command/get-file",
            headers=self._headers,
            params={"id": file_id, "components-v2": "true"},
        )
        self._check_response(resp)
        result: dict[str, Any] = resp.json()
        return result

    async def get_file_object_thumbnails(
        self,
        file_id: str,
        object_ids: list[str],
    ) -> dict[str, str]:
        """Get thumbnail URLs for specific objects (components)."""
        http = self._get_http()
        resp = await resilient_request(
            http,
            "POST",
            f"{self._base_url}/api/rpc/command/get-file-object-thumbnails",
            headers=self._headers,
            json={"file-id": file_id, "object-ids": object_ids},
        )
        self._check_response(resp)
        thumbnails: dict[str, str] = resp.json()
        return thumbnails

    async def export_shapes(
        self,
        file_id: str,
        page_id: str,
        object_ids: list[str],
        export_type: str = "png",
        scale: float = 2.0,
    ) -> list[bytes]:
        """Export shapes as images. Returns raw bytes per object."""
        results: list[bytes] = []
        http = self._get_http()
        for oid in object_ids:
            resp = await resilient_request(
                http,
                "POST",
                f"{self._base_url}/api/export",
                headers={**self._headers, "Accept": "application/octet-stream"},
                json={
                    "file-id": file_id,
                    "page-id": page_id,
                    "object-id": oid,
                    "type": export_type,
                    "scale": scale,
                },
            )
            self._check_response(resp)
            results.append(resp.content)
        return results

    def _check_response(self, resp: httpx.Response) -> None:
        """Raise SyncFailedError for non-2xx responses."""
        if resp.status_code == 401:
            raise SyncFailedError("Penpot authentication failed — check access token")
        if resp.status_code == 403:
            raise SyncFailedError("Penpot access denied — insufficient permissions")
        if resp.status_code == 404:
            raise SyncFailedError("Penpot resource not found")
        if not resp.is_success:
            raise SyncFailedError(
                f"Penpot API error: {resp.status_code}",
            )
