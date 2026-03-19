"""Tests for HubPluginAPI — permission enforcement."""

from __future__ import annotations

import pytest

from app.plugins.api import HubPluginAPI
from app.plugins.exceptions import PluginPermissionError
from app.plugins.manifest import PluginManifest, PluginPermission, PluginType


def _make_manifest(permissions: list[PluginPermission] | None = None) -> PluginManifest:
    return PluginManifest(
        name="test-plugin",
        version="1.0.0",
        hub_api_version=">=1.0",
        plugin_type=PluginType.qa_check,
        entry_point="test.main",
        permissions=permissions or [],
    )


class TestHubPluginAPI:
    def test_require_permission_granted(self) -> None:
        manifest = _make_manifest(permissions=[PluginPermission.call_llm])
        api = HubPluginAPI(manifest)
        api._require_permission(PluginPermission.call_llm)  # should not raise

    def test_require_permission_denied(self) -> None:
        manifest = _make_manifest(permissions=[])
        api = HubPluginAPI(manifest)
        with pytest.raises(PluginPermissionError, match="call_llm"):
            api._require_permission(PluginPermission.call_llm)

    def test_qa_register_check(self) -> None:
        manifest = _make_manifest()
        api = HubPluginAPI(manifest)

        async def my_check(html: str, config: object = None) -> object:
            pass

        api.qa.register_check("my_check", my_check)  # type: ignore[arg-type]
        assert "my_check" in api.qa.registered_checks

    def test_config_api(self) -> None:
        manifest = _make_manifest()
        api = HubPluginAPI(manifest, config={"threshold": 0.5})
        assert api.config.get("threshold") == 0.5
        assert api.config.get("missing", "default") == "default"

    def test_manifest_property(self) -> None:
        manifest = _make_manifest()
        api = HubPluginAPI(manifest)
        assert api.manifest.name == "test-plugin"
