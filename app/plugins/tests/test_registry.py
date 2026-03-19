"""Tests for plugin registry — lifecycle, conflict detection, QA wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.plugins.api import HubPluginAPI
from app.plugins.exceptions import PluginConflictError, PluginError, PluginNotFoundError
from app.plugins.manifest import PluginManifest, PluginType
from app.plugins.registry import PluginRegistry, reset_plugin_registry


def _make_manifest(name: str = "test-plugin") -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        hub_api_version=">=1.0",
        plugin_type=PluginType.qa_check,
        entry_point="test_plugin.main",
    )


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_plugin_registry()


@pytest.fixture
def registry() -> PluginRegistry:
    return PluginRegistry()


@pytest.fixture
def sample_plugin_dir(tmp_path: Path) -> Path:
    """Create a valid plugin on disk."""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()
    pkg_dir = plugin_dir / "test_plugin"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "main.py").write_text(
        "def setup(hub):\n    async def check(html, config=None):\n"
        "        from app.qa_engine.schemas import QACheckResult\n"
        "        return QACheckResult(check_name='test_check', passed=True, score=1.0, details='ok', severity='info')\n"
        "    hub.qa.register_check('test_check', check)\n"
    )
    return tmp_path


class TestPluginRegistry:
    def test_register_and_list(self, registry: PluginRegistry, sample_plugin_dir: Path) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)
        plugins = registry.list_plugins()
        assert len(plugins) == 1
        assert plugins[0].manifest.name == "test-plugin"
        assert plugins[0].status == "active"

    def test_get_plugin(self, registry: PluginRegistry, sample_plugin_dir: Path) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)
        instance = registry.get_plugin("test-plugin")
        assert instance.manifest.name == "test-plugin"

    def test_get_nonexistent_raises(self, registry: PluginRegistry) -> None:
        with pytest.raises(PluginNotFoundError):
            registry.get_plugin("does-not-exist")

    def test_unregister(self, registry: PluginRegistry, sample_plugin_dir: Path) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)
        registry.unregister("test-plugin")
        assert registry.list_plugins() == []

    def test_unregister_nonexistent_raises(self, registry: PluginRegistry) -> None:
        with pytest.raises(PluginNotFoundError):
            registry.unregister("nope")

    def test_disable_and_enable(self, registry: PluginRegistry, sample_plugin_dir: Path) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)

        registry.disable("test-plugin")
        assert registry.get_plugin("test-plugin").status == "disabled"
        assert registry.get_active_qa_checks() == {}

        registry.enable("test-plugin")
        assert registry.get_plugin("test-plugin").status == "active"
        assert "test_check" in registry.get_active_qa_checks()

    def test_duplicate_registration_raises(
        self, registry: PluginRegistry, sample_plugin_dir: Path
    ) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)
        with pytest.raises(PluginConflictError, match="already registered"):
            registry.load_and_register(manifest, sample_plugin_dir)

    def test_qa_check_conflict_detection(
        self, registry: PluginRegistry, sample_plugin_dir: Path, tmp_path: Path
    ) -> None:
        """Two plugins registering the same QA check name should conflict."""
        manifest1 = _make_manifest(name="plugin-aaa")
        # Create another plugin dir with same check name
        p2 = tmp_path / "plugin-bbb"
        p2.mkdir()
        pkg2 = p2 / "test_plugin"
        pkg2.mkdir()
        (pkg2 / "__init__.py").write_text("")
        (pkg2 / "main.py").write_text(
            "def setup(hub):\n    async def check(html, config=None):\n"
            "        from app.qa_engine.schemas import QACheckResult\n"
            "        return QACheckResult(check_name='test_check', passed=True, score=1.0, details='ok', severity='info')\n"
            "    hub.qa.register_check('test_check', check)\n"
        )
        # First plugin registers fine
        # Manually create dirs matching expected layout
        p1_dir = tmp_path / "plugin-aaa"
        p1_dir.mkdir(exist_ok=True)
        pkg1 = p1_dir / "test_plugin"
        pkg1.mkdir(exist_ok=True)
        (pkg1 / "__init__.py").write_text("")
        (pkg1 / "main.py").write_text(
            "def setup(hub):\n    async def check(html, config=None):\n"
            "        from app.qa_engine.schemas import QACheckResult\n"
            "        return QACheckResult(check_name='test_check', passed=True, score=1.0, details='ok', severity='info')\n"
            "    hub.qa.register_check('test_check', check)\n"
        )
        registry.load_and_register(manifest1, tmp_path)

        manifest2 = _make_manifest(name="plugin-bbb")
        with pytest.raises(PluginConflictError, match="test_check"):
            registry.load_and_register(manifest2, tmp_path)

    def test_get_active_qa_checks(self, registry: PluginRegistry, sample_plugin_dir: Path) -> None:
        manifest = _make_manifest()
        registry.load_and_register(manifest, sample_plugin_dir)
        checks = registry.get_active_qa_checks()
        assert "test_check" in checks
        assert callable(checks["test_check"])

    def test_enable_error_state_raises(self, registry: PluginRegistry) -> None:
        """Cannot enable a plugin in error state."""
        from app.plugins.registry import PluginInstance

        manifest = _make_manifest()
        registry._plugins["test-plugin"] = PluginInstance(
            manifest=manifest,
            module=MagicMock(),
            api=HubPluginAPI(manifest),
            status="error",
            error="some error",
        )
        with pytest.raises(PluginError, match="error state"):
            registry.enable("test-plugin")

    def test_discover_and_load_mixed(self, tmp_path: Path) -> None:
        """discover_and_load handles partial failures gracefully."""
        registry = PluginRegistry()

        # Valid plugin
        good_dir = tmp_path / "good-plugin"
        good_dir.mkdir()
        (good_dir / "plugin.yaml").write_text(
            "name: good-plugin\nversion: '1.0.0'\nhub_api_version: '>=1.0'\n"
            "plugin_type: qa_check\nentry_point: good_plugin.main\n"
        )
        pkg = good_dir / "good_plugin"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text("def setup(hub):\n    pass\n")

        # Bad plugin (missing entry point module)
        bad_dir = tmp_path / "bad-plugin"
        bad_dir.mkdir()
        (bad_dir / "plugin.yaml").write_text(
            "name: bad-plugin\nversion: '1.0.0'\nhub_api_version: '>=1.0'\n"
            "plugin_type: qa_check\nentry_point: bad_plugin.main\n"
        )

        loaded = registry.discover_and_load(tmp_path)
        assert "good-plugin" in loaded
        assert "bad-plugin" not in loaded

        # Both show up in list — bad one in error state
        all_plugins = registry.list_plugins()
        assert len(all_plugins) == 2
        bad = registry.get_plugin("bad-plugin")
        assert bad.status == "error"
        assert bad.error is not None
