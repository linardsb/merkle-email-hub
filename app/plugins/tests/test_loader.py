"""Tests for plugin loader — dynamic import, error handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.plugins.exceptions import PluginLoadError
from app.plugins.loader import PluginLoader
from app.plugins.manifest import PluginManifest, PluginType


def _make_manifest(
    name: str = "test-plugin", entry_point: str = "test_plugin.main"
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        hub_api_version=">=1.0",
        plugin_type=PluginType.qa_check,
        entry_point=entry_point,
    )


class TestPluginLoader:
    def test_successful_import(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        pkg_dir = plugin_dir / "test_plugin"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "main.py").write_text("def setup(hub):\n    pass\n")

        loader = PluginLoader()
        manifest = _make_manifest()
        module = loader.load(manifest, tmp_path)
        assert hasattr(module, "setup")
        assert callable(module.setup)

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        loader = PluginLoader()
        manifest = _make_manifest(name="nonexistent")
        with pytest.raises(PluginLoadError, match="not found"):
            loader.load(manifest, tmp_path)

    def test_missing_setup_raises(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        pkg_dir = plugin_dir / "test_plugin"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "main.py").write_text("# no setup function\n")

        loader = PluginLoader()
        manifest = _make_manifest()
        with pytest.raises(PluginLoadError, match="setup"):
            loader.load(manifest, tmp_path)

    def test_non_callable_setup_raises(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        pkg_dir = plugin_dir / "test_plugin"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "main.py").write_text("setup = 42\n")

        loader = PluginLoader()
        manifest = _make_manifest()
        with pytest.raises(PluginLoadError, match="not callable"):
            loader.load(manifest, tmp_path)

    def test_import_error_raises(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        pkg_dir = plugin_dir / "test_plugin"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "main.py").write_text("raise ImportError('bad dependency')\n")

        loader = PluginLoader()
        manifest = _make_manifest()
        with pytest.raises(PluginLoadError, match="Failed to import"):
            loader.load(manifest, tmp_path)

    def test_single_segment_entry_point_rejected(self) -> None:
        loader = PluginLoader()
        manifest = _make_manifest(entry_point="os")
        with pytest.raises(PluginLoadError, match="dotted Python module path"):
            loader._validate_entry_point(manifest)

    def test_blocked_prefix_rejected(self, tmp_path: Path) -> None:
        loader = PluginLoader()
        manifest = _make_manifest(entry_point="subprocess.run")
        with pytest.raises(PluginLoadError, match="blocked module prefix"):
            loader._validate_entry_point(manifest)

    def test_valid_entry_point_accepted(self) -> None:
        loader = PluginLoader()
        manifest = _make_manifest(entry_point="my_plugin.main")
        loader._validate_entry_point(manifest)  # should not raise
