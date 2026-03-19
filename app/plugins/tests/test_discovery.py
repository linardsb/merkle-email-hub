"""Tests for plugin discovery — directory scanning, conflict detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.plugins.discovery import PluginDiscovery


@pytest.fixture
def plugin_dir(tmp_path: Path) -> Path:
    return tmp_path / "plugins"


@pytest.fixture
def discovery() -> PluginDiscovery:
    return PluginDiscovery()


VALID_MANIFEST_YAML = """\
name: test-plugin
version: "1.0.0"
hub_api_version: ">=1.0"
plugin_type: qa_check
entry_point: test_plugin.main
permissions: []
metadata:
  author: "Test"
  description: "A test plugin"
  tags: ["test"]
"""

VALID_MANIFEST_JSON = {
    "name": "json-plugin",
    "version": "2.0.0",
    "hub_api_version": ">=1.0",
    "plugin_type": "qa_check",
    "entry_point": "json_plugin.main",
}


class TestPluginDiscovery:
    def test_empty_directory(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        result = discovery.discover(plugin_dir)
        assert result == []

    def test_nonexistent_directory(self, discovery: PluginDiscovery, tmp_path: Path) -> None:
        result = discovery.discover(tmp_path / "nonexistent")
        assert result == []

    def test_valid_yaml_manifest(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "test-plugin"
        plugin_path.mkdir()
        (plugin_path / "plugin.yaml").write_text(VALID_MANIFEST_YAML)

        result = discovery.discover(plugin_dir)
        assert len(result) == 1
        assert result[0].name == "test-plugin"
        assert result[0].version == "1.0.0"

    def test_valid_json_manifest(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "json-plugin"
        plugin_path.mkdir()
        (plugin_path / "plugin.json").write_text(json.dumps(VALID_MANIFEST_JSON))

        result = discovery.discover(plugin_dir)
        assert len(result) == 1
        assert result[0].name == "json-plugin"

    def test_invalid_manifest_skipped(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "bad-plugin"
        plugin_path.mkdir()
        (plugin_path / "plugin.yaml").write_text("name: AB\nversion: bad\n")

        result = discovery.discover(plugin_dir)
        assert result == []

    def test_no_manifest_file_skipped(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "no-manifest"
        plugin_path.mkdir()
        (plugin_path / "README.md").write_text("hello")

        result = discovery.discover(plugin_dir)
        assert result == []

    def test_yaml_preferred_over_json(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()
        plugin_path = plugin_dir / "dual-plugin"
        plugin_path.mkdir()
        (plugin_path / "plugin.yaml").write_text(VALID_MANIFEST_YAML)
        (plugin_path / "plugin.json").write_text(json.dumps(VALID_MANIFEST_JSON))

        result = discovery.discover(plugin_dir)
        assert len(result) == 1
        assert result[0].name == "test-plugin"  # from YAML

    def test_multiple_plugins(self, plugin_dir: Path, discovery: PluginDiscovery) -> None:
        plugin_dir.mkdir()

        p1 = plugin_dir / "aaa-plugin"
        p1.mkdir()
        (p1 / "plugin.yaml").write_text(VALID_MANIFEST_YAML)

        p2 = plugin_dir / "zzz-plugin"
        p2.mkdir()
        (p2 / "plugin.json").write_text(json.dumps(VALID_MANIFEST_JSON))

        result = discovery.discover(plugin_dir)
        assert len(result) == 2

    def test_non_directory_children_ignored(
        self, plugin_dir: Path, discovery: PluginDiscovery
    ) -> None:
        plugin_dir.mkdir()
        (plugin_dir / "readme.txt").write_text("not a plugin")

        result = discovery.discover(plugin_dir)
        assert result == []
