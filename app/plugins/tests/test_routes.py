"""Tests for plugin admin endpoints."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.plugins.manifest import PluginManifest, PluginType
from app.plugins.registry import PluginInstance, PluginRegistry, reset_plugin_registry


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_plugin_registry()


def _make_instance(
    name: str = "test-plugin", status: str = "active", error: str | None = None
) -> PluginInstance:
    manifest = PluginManifest(
        name=name,
        version="1.0.0",
        hub_api_version=">=1.0",
        plugin_type=PluginType.qa_check,
        entry_point="test.main",
    )
    from app.plugins.api import HubPluginAPI

    return PluginInstance(
        manifest=manifest,
        module=MagicMock(),
        api=HubPluginAPI(manifest),
        status=status,
        error=error,
    )


@pytest.fixture
def mock_registry() -> PluginRegistry:
    registry = PluginRegistry()
    instance = _make_instance()
    registry._plugins["test-plugin"] = instance
    return registry


@pytest.fixture
def client(mock_registry: PluginRegistry) -> Generator[TestClient]:
    from fastapi import FastAPI

    from app.auth.dependencies import get_current_user
    from app.core.rate_limit import limiter
    from app.plugins.routes import router

    app = FastAPI()
    app.include_router(router)

    limiter.enabled = False

    # Override the core auth dependency to return a fake admin user
    mock_user = MagicMock()
    mock_user.role = "admin"
    mock_user.id = 1
    mock_user.is_active = True

    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("app.plugins.routes.get_plugin_registry", return_value=mock_registry):
        yield TestClient(app)

    limiter.enabled = True
    app.dependency_overrides.clear()


class TestPluginRoutes:
    def test_list_plugins(self, client: TestClient) -> None:
        resp = client.get("/api/v1/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["plugins"][0]["name"] == "test-plugin"

    def test_get_plugin(self, client: TestClient) -> None:
        resp = client.get("/api/v1/plugins/test-plugin")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-plugin"

    def test_disable_plugin(self, client: TestClient) -> None:
        resp = client.post("/api/v1/plugins/test-plugin/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_enable_plugin(self, client: TestClient, mock_registry: PluginRegistry) -> None:
        mock_registry.disable("test-plugin")
        resp = client.post("/api/v1/plugins/test-plugin/enable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_delete_plugin(self, client: TestClient) -> None:
        resp = client.delete("/api/v1/plugins/test-plugin")
        assert resp.status_code == 204


class TestPluginRoutesAuth:
    def test_non_admin_rejected(self, mock_registry: PluginRegistry) -> None:
        """Non-admin users get 403 on all plugin endpoints."""
        from fastapi import FastAPI

        from app.auth.dependencies import get_current_user
        from app.core.rate_limit import limiter
        from app.plugins.routes import router

        app = FastAPI()
        app.include_router(router)
        limiter.enabled = False

        # Override auth to return a viewer (non-admin) user
        viewer = MagicMock()
        viewer.role = "viewer"
        viewer.id = 2
        viewer.is_active = True
        app.dependency_overrides[get_current_user] = lambda: viewer

        with patch("app.plugins.routes.get_plugin_registry", return_value=mock_registry):
            client = TestClient(app, raise_server_exceptions=False)
            assert client.get("/api/v1/plugins").status_code == 403
            assert client.get("/api/v1/plugins/test-plugin").status_code == 403
            assert client.post("/api/v1/plugins/test-plugin/enable").status_code == 403
            assert client.post("/api/v1/plugins/test-plugin/disable").status_code == 403
            assert client.delete("/api/v1/plugins/test-plugin").status_code == 403

        limiter.enabled = True
        app.dependency_overrides.clear()

    def test_unauthenticated_rejected(self, mock_registry: PluginRegistry) -> None:
        """Unauthenticated requests get 401."""
        from fastapi import FastAPI

        from app.core.rate_limit import limiter
        from app.plugins.routes import router

        app = FastAPI()
        app.include_router(router)
        limiter.enabled = False

        # No dependency override — auth will fail
        with patch("app.plugins.routes.get_plugin_registry", return_value=mock_registry):
            client = TestClient(app, raise_server_exceptions=False)
            assert client.get("/api/v1/plugins").status_code == 401

        limiter.enabled = True
