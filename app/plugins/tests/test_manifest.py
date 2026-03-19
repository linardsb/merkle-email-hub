"""Tests for plugin manifest parsing and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.plugins.manifest import PluginManifest, PluginMetadata, PluginPermission, PluginType


class TestPluginManifest:
    def test_valid_manifest(self) -> None:
        m = PluginManifest(
            name="sample-qa-check",
            version="1.0.0",
            hub_api_version=">=1.0",
            plugin_type=PluginType.qa_check,
            entry_point="sample_qa_check.main",
        )
        assert m.name == "sample-qa-check"
        assert m.version == "1.0.0"
        assert m.plugin_type == PluginType.qa_check
        assert m.permissions == []
        assert m.metadata == PluginMetadata()

    def test_all_plugin_types_accepted(self) -> None:
        for pt in PluginType:
            m = PluginManifest(
                name="test-plugin",
                version="1.0.0",
                hub_api_version=">=1.0",
                plugin_type=pt,
                entry_point="test.main",
            )
            assert m.plugin_type == pt

    def test_permissions_list(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            hub_api_version=">=1.0",
            plugin_type=PluginType.qa_check,
            entry_point="test.main",
            permissions=[PluginPermission.read_templates, PluginPermission.call_llm],
        )
        assert len(m.permissions) == 2
        assert PluginPermission.call_llm in m.permissions

    def test_invalid_name_too_short(self) -> None:
        with pytest.raises(ValidationError, match="3-64 chars"):
            PluginManifest(
                name="ab",
                version="1.0.0",
                hub_api_version=">=1.0",
                plugin_type=PluginType.qa_check,
                entry_point="test.main",
            )

    def test_invalid_name_uppercase(self) -> None:
        with pytest.raises(ValidationError, match="lowercase"):
            PluginManifest(
                name="My-Plugin",
                version="1.0.0",
                hub_api_version=">=1.0",
                plugin_type=PluginType.qa_check,
                entry_point="test.main",
            )

    def test_invalid_name_starts_with_number(self) -> None:
        with pytest.raises(ValidationError, match="start with letter"):
            PluginManifest(
                name="1plugin",
                version="1.0.0",
                hub_api_version=">=1.0",
                plugin_type=PluginType.qa_check,
                entry_point="test.main",
            )

    def test_invalid_semver(self) -> None:
        with pytest.raises(ValidationError, match="semver"):
            PluginManifest(
                name="test-plugin",
                version="v1",
                hub_api_version=">=1.0",
                plugin_type=PluginType.qa_check,
                entry_point="test.main",
            )

    def test_valid_semver_with_prerelease(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0-beta.1",
            hub_api_version=">=1.0",
            plugin_type=PluginType.qa_check,
            entry_point="test.main",
        )
        assert m.version == "1.0.0-beta.1"

    def test_metadata_populated(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            hub_api_version=">=1.0",
            plugin_type=PluginType.qa_check,
            entry_point="test.main",
            metadata=PluginMetadata(
                author="Test Author",
                description="A test plugin",
                tags=["test", "qa"],
            ),
        )
        assert m.metadata.author == "Test Author"
        assert m.metadata.tags == ["test", "qa"]

    def test_config_schema_optional(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            hub_api_version=">=1.0",
            plugin_type=PluginType.qa_check,
            entry_point="test.main",
            config_schema={"type": "object", "properties": {"threshold": {"type": "number"}}},
        )
        assert m.config_schema is not None
        assert "threshold" in m.config_schema["properties"]
