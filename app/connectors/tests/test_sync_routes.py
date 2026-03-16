# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Route tests for ESP sync API."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.connectors.exceptions import (
    ESPConnectionNotFoundError,
    ESPSyncFailedError,
    InvalidESPCredentialsError,
)
from app.connectors.sync_schemas import (
    ESPConnectionResponse,
    ESPTemplate,
    ESPTemplateList,
)
from app.connectors.sync_service import ConnectorSyncService
from app.core.rate_limit import limiter
from app.main import app

# ── Helpers ──

BASE = "/api/v1/connectors/sync"


def _make_user(role: str = "developer") -> User:
    """Create a mock user."""
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_connection_response(id: int = 1) -> ESPConnectionResponse:
    """Create a mock ESPConnectionResponse."""
    return ESPConnectionResponse(
        id=id,
        esp_type="braze",
        name="Test Connection",
        status="connected",
        credentials_hint="****1234",
        project_id=1,
        project_name="My Project",
        last_synced_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_esp_template(id: str = "tpl_1") -> ESPTemplate:
    """Create a mock ESPTemplate."""
    return ESPTemplate(
        id=id,
        name="Test Template",
        html="<div>Hello</div>",
        esp_type="braze",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    """Disable rate limiter for all tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    """Override auth to return a developer user."""
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    """Override auth to return a viewer user."""
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


# ── 1. POST /connections → 201 ──


@pytest.mark.usefixtures("_auth_developer")
def test_create_connection_201(client: TestClient) -> None:
    """POST /connections returns 201 with created connection."""
    mock_conn = _make_connection_response()

    with patch.object(
        ConnectorSyncService,
        "create_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.post(
            f"{BASE}/connections",
            json={
                "esp_type": "braze",
                "name": "Test Connection",
                "project_id": 1,
                "credentials": {"api_key": "test-key-1234"},
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["esp_type"] == "braze"
    assert body["credentials_hint"] == "****1234"


@pytest.mark.usefixtures("_auth_developer")
def test_create_connection_invalid_credentials_422(client: TestClient) -> None:
    """POST /connections with invalid credentials returns 422."""
    with patch.object(
        ConnectorSyncService,
        "create_connection",
        new_callable=AsyncMock,
        side_effect=InvalidESPCredentialsError("Invalid credentials for braze"),
    ):
        resp = client.post(
            f"{BASE}/connections",
            json={
                "esp_type": "braze",
                "name": "Test",
                "project_id": 1,
                "credentials": {"api_key": "bad"},
            },
        )

    assert resp.status_code == 422


@pytest.mark.usefixtures("_auth_developer")
def test_create_connection_invalid_esp_type_422(client: TestClient) -> None:
    """POST /connections with invalid esp_type returns 422 (Pydantic validation)."""
    resp = client.post(
        f"{BASE}/connections",
        json={
            "esp_type": "invalid_provider",
            "name": "Test",
            "project_id": 1,
            "credentials": {"api_key": "key"},
        },
    )
    assert resp.status_code == 422


# ── 2. GET /connections → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_list_connections_200(client: TestClient) -> None:
    """GET /connections returns 200 with connection list."""
    mock_conn = _make_connection_response()

    with patch.object(
        ConnectorSyncService,
        "list_connections",
        new_callable=AsyncMock,
        return_value=[mock_conn],
    ):
        resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == 1
    assert body[0]["esp_type"] == "braze"


@pytest.mark.usefixtures("_auth_viewer")
def test_list_connections_empty(client: TestClient) -> None:
    """GET /connections returns 200 with empty list."""
    with patch.object(
        ConnectorSyncService,
        "list_connections",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 200
    assert resp.json() == []


# ── 3. GET /connections/{id} → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_connection_200(client: TestClient) -> None:
    """GET /connections/{id} returns 200 with connection details."""
    mock_conn = _make_connection_response()

    with patch.object(
        ConnectorSyncService,
        "get_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.get(f"{BASE}/connections/1")

    assert resp.status_code == 200
    assert resp.json()["id"] == 1


@pytest.mark.usefixtures("_auth_viewer")
def test_get_connection_not_found_404(client: TestClient) -> None:
    """GET /connections/{id} returns 404 when not found."""
    with patch.object(
        ConnectorSyncService,
        "get_connection",
        new_callable=AsyncMock,
        side_effect=ESPConnectionNotFoundError("ESP connection 999 not found"),
    ):
        resp = client.get(f"{BASE}/connections/999")

    assert resp.status_code == 404


# ── 4. DELETE /connections/{id} → 204 ──


@pytest.mark.usefixtures("_auth_developer")
def test_delete_connection_204(client: TestClient) -> None:
    """DELETE /connections/{id} returns 204."""
    with patch.object(
        ConnectorSyncService,
        "delete_connection",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.delete(f"{BASE}/connections/1")

    assert resp.status_code == 204


@pytest.mark.usefixtures("_auth_developer")
def test_delete_connection_not_found_404(client: TestClient) -> None:
    """DELETE /connections/{id} returns 404 when not found."""
    with patch.object(
        ConnectorSyncService,
        "delete_connection",
        new_callable=AsyncMock,
        side_effect=ESPConnectionNotFoundError("not found"),
    ):
        resp = client.delete(f"{BASE}/connections/999")

    assert resp.status_code == 404


# ── 5. GET /connections/{id}/templates → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_list_remote_templates_200(client: TestClient) -> None:
    """GET /connections/{id}/templates returns 200 with template list."""
    tpl = _make_esp_template()
    mock_list = ESPTemplateList(templates=[tpl], count=1)

    with patch.object(
        ConnectorSyncService,
        "list_remote_templates",
        new_callable=AsyncMock,
        return_value=mock_list,
    ):
        resp = client.get(f"{BASE}/connections/1/templates")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["templates"][0]["id"] == "tpl_1"


@pytest.mark.usefixtures("_auth_developer")
def test_list_remote_templates_provider_error_500(client: TestClient) -> None:
    """GET /connections/{id}/templates returns 500 on provider error."""
    with patch.object(
        ConnectorSyncService,
        "list_remote_templates",
        new_callable=AsyncMock,
        side_effect=ESPSyncFailedError("Failed to list templates"),
    ):
        resp = client.get(f"{BASE}/connections/1/templates")

    assert resp.status_code == 500


# ── 6. GET /connections/{id}/templates/{tid} → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_get_remote_template_200(client: TestClient) -> None:
    """GET /connections/{id}/templates/{tid} returns 200 with template."""
    tpl = _make_esp_template()

    with patch.object(
        ConnectorSyncService,
        "get_remote_template",
        new_callable=AsyncMock,
        return_value=tpl,
    ):
        resp = client.get(f"{BASE}/connections/1/templates/tpl_1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "tpl_1"
    assert resp.json()["html"] == "<div>Hello</div>"


# ── 7. POST /connections/{id}/import → 201 ──


@pytest.mark.usefixtures("_auth_developer")
def test_import_template_201(client: TestClient) -> None:
    """POST /connections/{id}/import returns 201 with local template ID."""
    with patch.object(
        ConnectorSyncService,
        "import_template",
        new_callable=AsyncMock,
        return_value=42,
    ):
        resp = client.post(
            f"{BASE}/connections/1/import",
            json={"template_id": "remote_1"},
        )

    assert resp.status_code == 201
    assert resp.json() == {"template_id": 42}


@pytest.mark.usefixtures("_auth_developer")
def test_import_template_invalid_body_422(client: TestClient) -> None:
    """POST /connections/{id}/import with empty template_id returns 422."""
    resp = client.post(
        f"{BASE}/connections/1/import",
        json={"template_id": ""},
    )
    assert resp.status_code == 422


# ── 8. POST /connections/{id}/push → 201 ──


@pytest.mark.usefixtures("_auth_developer")
def test_push_template_201(client: TestClient) -> None:
    """POST /connections/{id}/push returns 201 with remote template."""
    tpl = _make_esp_template(id="remote_new")

    with patch.object(
        ConnectorSyncService,
        "push_template",
        new_callable=AsyncMock,
        return_value=tpl,
    ):
        resp = client.post(
            f"{BASE}/connections/1/push",
            json={"template_id": 10},
        )

    assert resp.status_code == 201
    assert resp.json()["id"] == "remote_new"


@pytest.mark.usefixtures("_auth_developer")
def test_push_template_provider_error_500(client: TestClient) -> None:
    """POST /connections/{id}/push returns 500 on provider error."""
    with patch.object(
        ConnectorSyncService,
        "push_template",
        new_callable=AsyncMock,
        side_effect=ESPSyncFailedError("Failed to push template"),
    ):
        resp = client.post(
            f"{BASE}/connections/1/push",
            json={"template_id": 10},
        )

    assert resp.status_code == 500


# ── 9. Unauthenticated requests → 401 ──


def test_unauthenticated_list_connections_401(client: TestClient) -> None:
    """GET /connections without auth returns 401."""
    app.dependency_overrides.clear()
    resp = client.get(f"{BASE}/connections")
    assert resp.status_code == 401


def test_unauthenticated_create_connection_401(client: TestClient) -> None:
    """POST /connections without auth returns 401."""
    app.dependency_overrides.clear()
    resp = client.post(
        f"{BASE}/connections",
        json={
            "esp_type": "braze",
            "name": "Test",
            "project_id": 1,
            "credentials": {"api_key": "k"},
        },
    )
    assert resp.status_code == 401


# ── 10. Viewer on developer-only endpoints → 403 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_create_connection(client: TestClient) -> None:
    """Viewer gets 403 on POST /connections (requires developer)."""
    resp = client.post(
        f"{BASE}/connections",
        json={
            "esp_type": "braze",
            "name": "Test",
            "project_id": 1,
            "credentials": {"api_key": "key"},
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_delete_connection(client: TestClient) -> None:
    """Viewer gets 403 on DELETE /connections/{id} (requires developer)."""
    resp = client.delete(f"{BASE}/connections/1")
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_list_remote_templates(client: TestClient) -> None:
    """Viewer gets 403 on GET /connections/{id}/templates (requires developer)."""
    resp = client.get(f"{BASE}/connections/1/templates")
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_get_remote_template(client: TestClient) -> None:
    """Viewer gets 403 on GET /connections/{id}/templates/{tid} (requires developer)."""
    resp = client.get(f"{BASE}/connections/1/templates/tpl_1")
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_import_template(client: TestClient) -> None:
    """Viewer gets 403 on POST /connections/{id}/import (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/1/import",
        json={"template_id": "remote_1"},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_push_template(client: TestClient) -> None:
    """Viewer gets 403 on POST /connections/{id}/push (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/1/push",
        json={"template_id": 10},
    )
    assert resp.status_code == 403


# ── 11. Viewer CAN access viewer-level endpoints ──


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_list_connections(client: TestClient) -> None:
    """Viewer can access GET /connections (viewer-level)."""
    with patch.object(
        ConnectorSyncService,
        "list_connections",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_get_connection(client: TestClient) -> None:
    """Viewer can access GET /connections/{id} (viewer-level)."""
    mock_conn = _make_connection_response()

    with patch.object(
        ConnectorSyncService,
        "get_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.get(f"{BASE}/connections/1")

    assert resp.status_code == 200
