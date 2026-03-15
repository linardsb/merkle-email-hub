# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Route tests for design sync API."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.design_sync.schemas import (
    ComponentListResponse,
    ConnectionResponse,
    DesignComponentResponse,
    DesignTokensResponse,
    DownloadAssetsResponse,
    ExtractComponentsResponse,
    FileStructureResponse,
    GenerateBriefResponse,
    ImageExportResponse,
    ImportResponse,
    LayoutAnalysisResponse,
    StoredAssetResponse,
)
from app.design_sync.service import DesignSyncService
from app.main import app

# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    """Create a mock user."""
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_connection_response(id: int = 1) -> ConnectionResponse:
    """Create a mock ConnectionResponse."""
    return ConnectionResponse(
        id=id,
        name="Test Design",
        provider="figma",
        file_key="abc123",
        file_url="https://figma.com/design/abc123/Test",
        access_token_last4="x7Kz",
        status="connected",
        last_synced_at=None,
        project_id=1,
        project_name="My Project",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_tokens_response(connection_id: int = 1) -> DesignTokensResponse:
    """Create a mock DesignTokensResponse."""
    return DesignTokensResponse(
        connection_id=connection_id,
        colors=[],
        typography=[],
        spacing=[],
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_file_structure_response(connection_id: int = 1) -> FileStructureResponse:
    """Create a mock FileStructureResponse."""
    return FileStructureResponse(
        connection_id=connection_id,
        file_name="Test File",
        pages=[],
    )


def _make_component_list_response(connection_id: int = 1) -> ComponentListResponse:
    """Create a mock ComponentListResponse."""
    return ComponentListResponse(
        connection_id=connection_id,
        components=[
            DesignComponentResponse(
                component_id="comp:1",
                name="Button",
                description="Primary button",
            ),
        ],
        total=1,
    )


def _make_image_export_response(connection_id: int = 1) -> ImageExportResponse:
    """Create a mock ImageExportResponse."""
    return ImageExportResponse(
        connection_id=connection_id,
        images=[],
        total=0,
    )


def _make_download_assets_response(connection_id: int = 1) -> DownloadAssetsResponse:
    """Create a mock DownloadAssetsResponse."""
    return DownloadAssetsResponse(
        connection_id=connection_id,
        assets=[StoredAssetResponse(node_id="1:2", filename="1_2.png")],
        total=1,
        skipped=0,
    )


def _make_layout_analysis_response(connection_id: int = 1) -> LayoutAnalysisResponse:
    """Create a mock LayoutAnalysisResponse."""
    return LayoutAnalysisResponse(
        connection_id=connection_id,
        file_name="Test File",
        overall_width=600.0,
        sections=[],
        total_text_blocks=0,
        total_images=0,
    )


def _make_brief_response(connection_id: int = 1) -> GenerateBriefResponse:
    """Create a mock GenerateBriefResponse."""
    return GenerateBriefResponse(
        connection_id=connection_id,
        brief="# Campaign Brief\n\nGenerated brief content.",
        sections_detected=3,
        layout_summary="header, hero, footer",
    )


def _make_extract_components_response(import_id: int = 10) -> ExtractComponentsResponse:
    """Create a mock ExtractComponentsResponse."""
    return ExtractComponentsResponse(
        import_id=import_id,
        status="extracting",
        total_components=5,
        message="Extracting 5 components in the background",
    )


def _make_import_response(
    id: int = 1,
    status: str = "pending",
    result_template_id: int | None = None,
) -> ImportResponse:
    """Create a mock ImportResponse."""
    return ImportResponse(
        id=id,
        connection_id=1,
        project_id=1,
        status=status,
        selected_node_ids=["1:2", "1:3"],
        generated_brief="# Brief",
        result_template_id=result_template_id,
        error_message=None,
        created_by_id=1,
        assets=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


# ── Fixtures ──

BASE = "/api/v1/design-sync"


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


# ── 1. GET /connections → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_list_connections_200(client: TestClient) -> None:
    """GET /connections returns 200 with connection list."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "list_connections",
        new_callable=AsyncMock,
        return_value=[mock_conn],
    ):
        resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == 1
    assert body[0]["provider"] == "figma"


# ── 2. GET /connections/{id} → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_connection_200(client: TestClient) -> None:
    """GET /connections/{id} returns 200 with connection details."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "get_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.get(f"{BASE}/connections/1")

    assert resp.status_code == 200
    assert resp.json()["id"] == 1
    assert resp.json()["file_key"] == "abc123"


# ── 3. GET /connections/{id}/tokens → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_tokens_200(client: TestClient) -> None:
    """GET /connections/{id}/tokens returns 200 with design tokens."""
    mock_tokens = _make_tokens_response()

    with patch.object(
        DesignSyncService,
        "get_tokens",
        new_callable=AsyncMock,
        return_value=mock_tokens,
    ):
        resp = client.get(f"{BASE}/connections/1/tokens")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == 1
    assert "colors" in body
    assert "typography" in body
    assert "spacing" in body


# ── 4. POST /connections → 201 ──


@pytest.mark.usefixtures("_auth_developer")
def test_create_connection_201(client: TestClient) -> None:
    """POST /connections returns 201 with created connection."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "create_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.post(
            f"{BASE}/connections",
            json={
                "name": "Test Design",
                "provider": "figma",
                "file_url": "https://figma.com/design/abc123/Test",
                "access_token": "figd_test_token_1234567890",
                "project_id": 1,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["id"] == 1
    assert resp.json()["provider"] == "figma"


# ── 5. POST /connections/delete → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_delete_connection_200(client: TestClient) -> None:
    """POST /connections/delete returns 200 with success flag."""
    with patch.object(
        DesignSyncService,
        "delete_connection",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = client.post(
            f"{BASE}/connections/delete",
            json={"id": 1},
        )

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


# ── 6. POST /connections/sync → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_sync_connection_200(client: TestClient) -> None:
    """POST /connections/sync returns 200 with synced connection."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "sync_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.post(
            f"{BASE}/connections/sync",
            json={"id": 1},
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == 1


# ── 7. GET /connections/{id}/file-structure → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_file_structure_200(client: TestClient) -> None:
    """GET /connections/{id}/file-structure returns 200 with file tree."""
    mock_fs = _make_file_structure_response()

    with patch.object(
        DesignSyncService,
        "get_file_structure",
        new_callable=AsyncMock,
        return_value=mock_fs,
    ):
        resp = client.get(f"{BASE}/connections/1/file-structure")

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == 1
    assert body["file_name"] == "Test File"
    assert isinstance(body["pages"], list)


# ── 8. GET /connections/{id}/components → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_list_components_200(client: TestClient) -> None:
    """GET /connections/{id}/components returns 200 with component list."""
    mock_cl = _make_component_list_response()

    with patch.object(
        DesignSyncService,
        "list_components",
        new_callable=AsyncMock,
        return_value=mock_cl,
    ):
        resp = client.get(f"{BASE}/connections/1/components")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["components"][0]["name"] == "Button"


# ── 9. POST /connections/export-images → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_export_images_200(client: TestClient) -> None:
    """POST /connections/export-images returns 200 with exported images."""
    mock_export = _make_image_export_response()

    with patch.object(
        DesignSyncService,
        "export_images",
        new_callable=AsyncMock,
        return_value=mock_export,
    ):
        resp = client.post(
            f"{BASE}/connections/export-images",
            json={
                "connection_id": 1,
                "node_ids": ["1:2", "1:3"],
                "format": "png",
                "scale": 2.0,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == 1
    assert body["total"] == 0


# ── 10. POST /connections/download-assets → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_download_assets_200(client: TestClient) -> None:
    """POST /connections/download-assets returns 200 with stored assets."""
    mock_dl = _make_download_assets_response()

    with patch.object(
        DesignSyncService,
        "download_assets",
        new_callable=AsyncMock,
        return_value=mock_dl,
    ):
        resp = client.post(
            f"{BASE}/connections/download-assets",
            json={
                "connection_id": 1,
                "node_ids": ["1:2"],
                "format": "png",
                "scale": 2.0,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["assets"][0]["filename"] == "1_2.png"


# ── 11. GET /assets/{conn_id}/{filename} → 200 (FileResponse) ──


@pytest.mark.usefixtures("_auth_viewer")
def test_serve_asset_200(client: TestClient, tmp_path: Path) -> None:
    """GET /assets/{conn_id}/{filename} serves a stored file."""
    # Create a real temp file so FileResponse works
    asset_file = tmp_path / "test_asset.png"
    asset_file.write_bytes(b"\x89PNG fake image data")

    mock_conn = _make_connection_response()

    with (
        patch.object(
            DesignSyncService,
            "get_connection",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch.object(
            DesignSyncService,
            "get_asset_path",
            return_value=asset_file,
        ),
    ):
        resp = client.get(f"{BASE}/assets/1/test_asset.png")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["content-security-policy"] == "default-src 'none'"
    assert b"PNG" in resp.content


# ── 12. POST /connections/analyze-layout → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_analyze_layout_200(client: TestClient) -> None:
    """POST /connections/analyze-layout returns 200 with layout analysis."""
    mock_layout = _make_layout_analysis_response()

    with patch.object(
        DesignSyncService,
        "analyze_layout",
        new_callable=AsyncMock,
        return_value=mock_layout,
    ):
        resp = client.post(
            f"{BASE}/connections/analyze-layout",
            json={"connection_id": 1, "selected_node_ids": []},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == 1
    assert body["file_name"] == "Test File"
    assert isinstance(body["sections"], list)


# ── 13. POST /connections/generate-brief → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_generate_brief_200(client: TestClient) -> None:
    """POST /connections/generate-brief returns 200 with generated brief."""
    mock_brief = _make_brief_response()

    with patch.object(
        DesignSyncService,
        "generate_brief",
        new_callable=AsyncMock,
        return_value=mock_brief,
    ):
        resp = client.post(
            f"{BASE}/connections/generate-brief",
            json={
                "connection_id": 1,
                "selected_node_ids": [],
                "include_tokens": True,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == 1
    assert body["sections_detected"] == 3
    assert "Campaign Brief" in body["brief"]


# ── 14. POST /connections/{id}/extract-components → 202 ──


@pytest.mark.usefixtures("_auth_developer")
def test_extract_components_202(client: TestClient) -> None:
    """POST /connections/{id}/extract-components returns 202 Accepted."""
    mock_extract = _make_extract_components_response()

    with patch.object(
        DesignSyncService,
        "extract_components",
        new_callable=AsyncMock,
        return_value=mock_extract,
    ):
        resp = client.post(
            f"{BASE}/connections/1/extract-components",
            json={"component_ids": None, "generate_html": True},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "extracting"
    assert body["total_components"] == 5


# ── 15. POST /imports → 201 ──


@pytest.mark.usefixtures("_auth_developer")
def test_create_import_201(client: TestClient) -> None:
    """POST /imports returns 201 with created import."""
    mock_import = _make_import_response()

    with patch.object(
        DesignSyncService,
        "create_design_import",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.post(
            f"{BASE}/imports",
            json={
                "connection_id": 1,
                "brief": "A promotional email campaign for spring sale with hero image and CTA.",
                "selected_node_ids": ["1:2", "1:3"],
                "template_name": "Spring Sale",
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["status"] == "pending"


# ── 16. GET /imports/{id} → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_import_200(client: TestClient) -> None:
    """GET /imports/{id} returns 200 with import details."""
    mock_import = _make_import_response()

    with patch.object(
        DesignSyncService,
        "get_design_import",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.get(f"{BASE}/imports/1")

    assert resp.status_code == 200
    assert resp.json()["id"] == 1
    assert resp.json()["selected_node_ids"] == ["1:2", "1:3"]


# ── 17. GET /imports/by-template/{template_id} → 200 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_get_import_by_template_200(client: TestClient) -> None:
    """GET /imports/by-template/{template_id} returns 200 with import."""
    mock_import = _make_import_response(status="completed", result_template_id=42)

    with patch.object(
        DesignSyncService,
        "get_import_by_template",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.get(f"{BASE}/imports/by-template/42?project_id=1")

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.usefixtures("_auth_viewer")
def test_get_import_by_template_null(client: TestClient) -> None:
    """GET /imports/by-template/{template_id} returns 200 null when no import exists."""
    with patch.object(
        DesignSyncService,
        "get_import_by_template",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.get(f"{BASE}/imports/by-template/999?project_id=1")

    assert resp.status_code == 200
    assert resp.json() is None


# ── 18. PATCH /imports/{id}/brief → 200 ──


@pytest.mark.usefixtures("_auth_developer")
def test_update_import_brief_200(client: TestClient) -> None:
    """PATCH /imports/{id}/brief returns 200 with updated import."""
    mock_import = _make_import_response()

    with patch.object(
        DesignSyncService,
        "update_import_brief",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.patch(
            f"{BASE}/imports/1/brief",
            json={"generated_brief": "Updated campaign brief with more detail."},
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == 1


# ── 19. POST /imports/{id}/convert → 202 ──


@pytest.mark.usefixtures("_auth_developer")
def test_convert_import_202(client: TestClient) -> None:
    """POST /imports/{id}/convert returns 202 Accepted."""
    mock_import = _make_import_response(status="converting")

    with patch.object(
        DesignSyncService,
        "start_conversion",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.post(
            f"{BASE}/imports/1/convert",
            json={"run_qa": True, "output_mode": "structured"},
        )

    assert resp.status_code == 202
    assert resp.json()["status"] == "converting"


# ── 20. Unauthenticated request → 401 ──


def test_unauthenticated_returns_401(client: TestClient) -> None:
    """Requests without auth credentials return 401."""
    # No auth override — dependency_overrides is empty
    app.dependency_overrides.clear()

    resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 401


# ── 21. Viewer on developer-only endpoint → 403 ──


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_create_connection(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections (requires developer)."""
    resp = client.post(
        f"{BASE}/connections",
        json={
            "name": "Test",
            "provider": "figma",
            "file_url": "https://figma.com/design/abc/Test",
            "access_token": "figd_test_token_1234567890",
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_delete_connection(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/delete (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/delete",
        json={"id": 1},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_sync_connection(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/sync (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/sync",
        json={"id": 1},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_export_images(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/export-images (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/export-images",
        json={"connection_id": 1, "node_ids": ["1:2"]},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_download_assets(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/download-assets (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/download-assets",
        json={"connection_id": 1, "node_ids": ["1:2"]},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_generate_brief(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/generate-brief (requires developer)."""
    resp = client.post(
        f"{BASE}/connections/generate-brief",
        json={"connection_id": 1},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_extract_components(client: TestClient) -> None:
    """Viewer role gets 403 on POST /connections/{id}/extract-components."""
    resp = client.post(
        f"{BASE}/connections/1/extract-components",
        json={},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_create_import(client: TestClient) -> None:
    """Viewer role gets 403 on POST /imports (requires developer)."""
    resp = client.post(
        f"{BASE}/imports",
        json={
            "connection_id": 1,
            "brief": "A promotional email campaign for spring sale.",
            "selected_node_ids": ["1:2"],
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_update_brief(client: TestClient) -> None:
    """Viewer role gets 403 on PATCH /imports/{id}/brief (requires developer)."""
    resp = client.patch(
        f"{BASE}/imports/1/brief",
        json={"generated_brief": "Updated brief."},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_forbidden_on_convert(client: TestClient) -> None:
    """Viewer role gets 403 on POST /imports/{id}/convert (requires developer)."""
    resp = client.post(
        f"{BASE}/imports/1/convert",
        json={"run_qa": True, "output_mode": "structured"},
    )
    assert resp.status_code == 403


# ── Viewer CAN access viewer-level endpoints ──


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_on_list_connections(client: TestClient) -> None:
    """Viewer role can access GET /connections (viewer-level)."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "list_connections",
        new_callable=AsyncMock,
        return_value=[mock_conn],
    ):
        resp = client.get(f"{BASE}/connections")

    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_on_get_connection(client: TestClient) -> None:
    """Viewer role can access GET /connections/{id} (viewer-level)."""
    mock_conn = _make_connection_response()

    with patch.object(
        DesignSyncService,
        "get_connection",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        resp = client.get(f"{BASE}/connections/1")

    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_on_get_tokens(client: TestClient) -> None:
    """Viewer role can access GET /connections/{id}/tokens (viewer-level)."""
    mock_tokens = _make_tokens_response()

    with patch.object(
        DesignSyncService,
        "get_tokens",
        new_callable=AsyncMock,
        return_value=mock_tokens,
    ):
        resp = client.get(f"{BASE}/connections/1/tokens")

    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_on_get_import(client: TestClient) -> None:
    """Viewer role can access GET /imports/{id} (viewer-level)."""
    mock_import = _make_import_response()

    with patch.object(
        DesignSyncService,
        "get_design_import",
        new_callable=AsyncMock,
        return_value=mock_import,
    ):
        resp = client.get(f"{BASE}/imports/1")

    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_allowed_on_analyze_layout(client: TestClient) -> None:
    """Viewer role can access POST /connections/analyze-layout (viewer-level)."""
    mock_layout = _make_layout_analysis_response()

    with patch.object(
        DesignSyncService,
        "analyze_layout",
        new_callable=AsyncMock,
        return_value=mock_layout,
    ):
        resp = client.post(
            f"{BASE}/connections/analyze-layout",
            json={"connection_id": 1},
        )

    assert resp.status_code == 200
