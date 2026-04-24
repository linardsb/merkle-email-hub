# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Tests for export orchestration endpoints and service."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.connectors.exceptions import (
    ESPConnectionNotFoundError,
    ESPSyncFailedError,
)
from app.connectors.sync_schemas import (
    BulkExportResponse,
    ExportResponse,
)
from app.connectors.sync_service import ConnectorSyncService
from app.core.rate_limit import limiter
from app.main import app

BASE = "/api/v1/connectors/sync"


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_export_response(**overrides: object) -> ExportResponse:
    defaults: dict[str, Any] = {
        "esp_template_id": "remote_42",
        "template_name": "My Email",
        "target_esp": "braze",
        "tokens_rewritten": 3,
        "warnings": [],
    }
    defaults.update(overrides)
    return ExportResponse(**defaults)


def _make_bulk_response(succeeded: int = 2, failed: int = 0) -> BulkExportResponse:
    from app.connectors.sync_schemas import BulkExportItemResult

    results: list[BulkExportItemResult] = []
    for i in range(succeeded):
        results.append(
            BulkExportItemResult(
                template_id=i + 1,
                success=True,
                esp_template_id=f"remote_{i + 1}",
                tokens_rewritten=0,
            )
        )
    for i in range(failed):
        results.append(
            BulkExportItemResult(
                template_id=succeeded + i + 1,
                success=False,
                error="Push failed",
            )
        )
    return BulkExportResponse(
        results=results,
        total=succeeded + failed,
        succeeded=succeeded,
        failed=failed,
    )


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── 1. Export Single ──


@pytest.mark.usefixtures("_auth_developer")
def test_export_with_html_201(client: TestClient) -> None:
    """POST /export with inline HTML returns 201."""
    mock_resp = _make_export_response()

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table><tr><td>Hello</td></tr></table>",
                "target_esp": "braze",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["esp_template_id"] == "remote_42"
    assert body["tokens_rewritten"] == 3


@pytest.mark.usefixtures("_auth_developer")
def test_export_with_token_rewrite_201(client: TestClient) -> None:
    """POST /export with source_esp triggers rewrite."""
    mock_resp = _make_export_response(tokens_rewritten=5)

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_export:
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>{{first_name}}</table>",
                "target_esp": "sfmc",
                "connection_id": 1,
                "source_esp": "braze",
                "rewrite_tokens": True,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["tokens_rewritten"] == 5
    call_kwargs = mock_export.call_args
    assert call_kwargs.kwargs["source_esp"] == "braze"
    assert call_kwargs.kwargs["rewrite_tokens"] is True


@pytest.mark.usefixtures("_auth_developer")
def test_export_no_rewrite_needed_201(client: TestClient) -> None:
    """POST /export with rewrite_tokens=false skips rewriting."""
    mock_resp = _make_export_response(tokens_rewritten=0)

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_export:
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>plain</table>",
                "target_esp": "braze",
                "connection_id": 1,
                "rewrite_tokens": False,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["tokens_rewritten"] == 0
    assert mock_export.call_args.kwargs["rewrite_tokens"] is False


@pytest.mark.usefixtures("_auth_developer")
def test_export_with_template_id_201(client: TestClient) -> None:
    """POST /export with template_id fetches HTML from DB."""
    mock_resp = _make_export_response(template_name="From DB")

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_export:
        resp = client.post(
            f"{BASE}/export",
            json={
                "template_id": 10,
                "target_esp": "braze",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["template_name"] == "From DB"
    assert mock_export.call_args.kwargs["template_id"] == 10


@pytest.mark.usefixtures("_auth_developer")
def test_export_connection_not_found_404(client: TestClient) -> None:
    """POST /export with invalid connection returns 404."""
    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        side_effect=ESPConnectionNotFoundError("ESP connection 999 not found"),
    ):
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>x</table>",
                "target_esp": "braze",
                "connection_id": 999,
            },
        )

    assert resp.status_code == 404


# ── 2. Export Bulk ──


@pytest.mark.usefixtures("_auth_developer")
def test_bulk_export_all_succeed_201(client: TestClient) -> None:
    """POST /export-bulk with all items succeeding returns 201."""
    mock_resp = _make_bulk_response(succeeded=2, failed=0)

    with patch.object(
        ConnectorSyncService,
        "export_templates_bulk",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = client.post(
            f"{BASE}/export-bulk",
            json={
                "template_ids": [1, 2],
                "target_esp": "braze",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 2
    assert body["succeeded"] == 2
    assert body["failed"] == 0
    assert all(r["success"] for r in body["results"])


@pytest.mark.usefixtures("_auth_developer")
def test_bulk_export_partial_failure_201(client: TestClient) -> None:
    """POST /export-bulk with partial failure still returns 201."""
    mock_resp = _make_bulk_response(succeeded=1, failed=1)

    with patch.object(
        ConnectorSyncService,
        "export_templates_bulk",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = client.post(
            f"{BASE}/export-bulk",
            json={
                "template_ids": [1, 2],
                "target_esp": "sfmc",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    failed_items = [r for r in body["results"] if not r["success"]]
    assert len(failed_items) == 1
    assert failed_items[0]["error"] == "Push failed"


@pytest.mark.usefixtures("_auth_developer")
def test_bulk_export_empty_list_422(client: TestClient) -> None:
    """POST /export-bulk with empty template_ids returns 422."""
    resp = client.post(
        f"{BASE}/export-bulk",
        json={
            "template_ids": [],
            "target_esp": "braze",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 422


@pytest.mark.usefixtures("_auth_developer")
def test_bulk_export_max_50_limit_422(client: TestClient) -> None:
    """POST /export-bulk with >50 items returns 422."""
    resp = client.post(
        f"{BASE}/export-bulk",
        json={
            "template_ids": list(range(1, 52)),
            "target_esp": "braze",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 422


# ── 3. Token Rewrite in Export ──


@pytest.mark.usefixtures("_auth_developer")
def test_export_auto_detect_rewrite(client: TestClient) -> None:
    """Export auto-detects source ESP and rewrites tokens."""
    mock_resp = _make_export_response(tokens_rewritten=2, warnings=["truncated loop"])

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>{{first_name}}</table>",
                "target_esp": "sfmc",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["tokens_rewritten"] == 2
    assert "truncated loop" in body["warnings"]


@pytest.mark.usefixtures("_auth_developer")
def test_export_explicit_source_esp(client: TestClient) -> None:
    """Export with explicit source_esp passes it to service."""
    mock_resp = _make_export_response()

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_export:
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>%%emailaddr%%</table>",
                "target_esp": "braze",
                "connection_id": 1,
                "source_esp": "sfmc",
            },
        )

    assert resp.status_code == 201
    assert mock_export.call_args.kwargs["source_esp"] == "sfmc"


@pytest.mark.usefixtures("_auth_developer")
def test_export_rewrite_false_skips(client: TestClient) -> None:
    """Export with rewrite_tokens=false skips token rewriting."""
    mock_resp = _make_export_response(tokens_rewritten=0)

    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_export:
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>{{name}}</table>",
                "target_esp": "sfmc",
                "connection_id": 1,
                "rewrite_tokens": False,
            },
        )

    assert resp.status_code == 201
    assert mock_export.call_args.kwargs["rewrite_tokens"] is False


# ── 4. Auth + Validation ──


@pytest.mark.usefixtures("_auth_viewer")
def test_export_viewer_forbidden_403(client: TestClient) -> None:
    """Viewer gets 403 on POST /export (requires developer)."""
    resp = client.post(
        f"{BASE}/export",
        json={
            "html": "<table>x</table>",
            "target_esp": "braze",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_bulk_export_viewer_forbidden_403(client: TestClient) -> None:
    """Viewer gets 403 on POST /export-bulk (requires developer)."""
    resp = client.post(
        f"{BASE}/export-bulk",
        json={
            "template_ids": [1],
            "target_esp": "braze",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_developer")
def test_export_missing_html_and_template_422(client: TestClient) -> None:
    """POST /export without html or template_id returns 422."""
    resp = client.post(
        f"{BASE}/export",
        json={
            "target_esp": "braze",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 422


@pytest.mark.usefixtures("_auth_developer")
def test_export_invalid_esp_type_422(client: TestClient) -> None:
    """POST /export with invalid target_esp returns 422."""
    resp = client.post(
        f"{BASE}/export",
        json={
            "html": "<table>x</table>",
            "target_esp": "invalid_provider",
            "connection_id": 1,
        },
    )
    assert resp.status_code == 422


@pytest.mark.usefixtures("_auth_developer")
def test_export_provider_error_500(client: TestClient) -> None:
    """POST /export with provider failure returns 500."""
    with patch.object(
        ConnectorSyncService,
        "export_template",
        new_callable=AsyncMock,
        side_effect=ESPSyncFailedError("Failed to export template"),
    ):
        resp = client.post(
            f"{BASE}/export",
            json={
                "html": "<table>x</table>",
                "target_esp": "braze",
                "connection_id": 1,
            },
        )

    assert resp.status_code == 500
