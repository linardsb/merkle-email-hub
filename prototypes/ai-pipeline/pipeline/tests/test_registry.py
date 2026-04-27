"""Tests for pipeline template registry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.ai.pipeline.registry import (
    PipelineRegistry,
    _parse_yaml,
    get_pipeline_registry,
    reset_pipeline_registry,
)
from app.core.exceptions import DomainValidationError, NotFoundError


class TestRegistryLifecycle:
    """Registry load, get, register, list."""

    def test_load_builtin_templates(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        names = registry.list_all()
        assert len(names) == 4
        assert "full-build" in names
        assert "quick-fix" in names
        assert "qa-only" in names
        assert "design-import" in names

    def test_get_existing(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        dag = registry.get("full-build")
        assert isinstance(dag, PipelineDag)
        assert dag.name == "full-build"

    def test_get_missing_raises(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        with pytest.raises(NotFoundError):
            registry.get("nonexistent")

    def test_register_runtime(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        dag = PipelineDag(
            name="custom",
            description="Custom pipeline",
            nodes={"x": PipelineNode("a", "standard", inputs=(), outputs=("o",))},
        )
        registry.register(dag)
        assert registry.get("custom") is dag

    def test_list_all(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        names = registry.list_all()
        assert names == sorted(names)

    def test_auto_load_on_get(self) -> None:
        registry = PipelineRegistry()
        # No explicit load() call — should auto-load
        dag = registry.get("full-build")
        assert dag.name == "full-build"

    def test_custom_dir(self, tmp_path: Path) -> None:
        custom_yaml = {
            "name": "custom-template",
            "description": "From custom dir",
            "nodes": {
                "x": {"agent": "a1", "tier": "standard", "inputs": [], "outputs": ["o"]},
            },
        }
        (tmp_path / "custom.yaml").write_text(yaml.dump(custom_yaml))

        registry = PipelineRegistry()
        registry._loaded = False
        registry._templates.clear()
        # Manually load built-in + custom
        from app.ai.pipeline.registry import _BUILTIN_DIR

        registry._load_directory(_BUILTIN_DIR)
        registry._load_directory(tmp_path)
        registry._loaded = True

        assert "custom-template" in registry.list_all()
        assert "full-build" in registry.list_all()

    def test_invalid_yaml_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "bad.yaml").write_text("not: [a valid pipeline")
        (tmp_path / "good.yaml").write_text(
            yaml.dump(
                {
                    "name": "good-one",
                    "description": "",
                    "nodes": {"x": {"agent": "a", "inputs": [], "outputs": []}},
                }
            )
        )
        registry = PipelineRegistry()
        registry._load_directory(tmp_path)
        assert "good-one" in registry._templates

    def test_duplicate_warns(self, tmp_path: Path) -> None:
        for i in range(2):
            (tmp_path / f"dup{i}.yaml").write_text(
                yaml.dump(
                    {
                        "name": "dup",
                        "description": f"v{i}",
                        "nodes": {"x": {"agent": "a", "inputs": [], "outputs": []}},
                    }
                )
            )
        registry = PipelineRegistry()
        registry._load_directory(tmp_path)
        # Last one wins
        assert registry._templates["dup"].description == "v1"

    def test_full_build_seven_nodes(self) -> None:
        registry = PipelineRegistry()
        registry.load()
        dag = registry.get("full-build")
        assert len(dag.nodes) == 7


class TestYamlParsing:
    """YAML parsing edge cases."""

    def test_parse_yaml_missing_name(self, tmp_path: Path) -> None:
        path = tmp_path / "noname.yaml"
        path.write_text(yaml.dump({"nodes": {"x": {"agent": "a"}}}))
        with pytest.raises(DomainValidationError, match="name"):
            _parse_yaml(path)

    def test_parse_yaml_missing_nodes(self, tmp_path: Path) -> None:
        path = tmp_path / "nonodes.yaml"
        path.write_text(yaml.dump({"name": "test"}))
        with pytest.raises(DomainValidationError, match="nodes"):
            _parse_yaml(path)


class TestSingleton:
    """Singleton lifecycle."""

    def test_singleton(self) -> None:
        a = get_pipeline_registry()
        b = get_pipeline_registry()
        assert a is b

    def test_reset_singleton(self) -> None:
        a = get_pipeline_registry()
        reset_pipeline_registry()
        b = get_pipeline_registry()
        assert a is not b
