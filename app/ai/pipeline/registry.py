"""Pipeline template registry — loads DAG definitions from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.core.config import get_settings
from app.core.exceptions import DomainValidationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "templates"


class PipelineRegistry:
    """Singleton registry of pipeline DAG templates."""

    def __init__(self) -> None:
        self._templates: dict[str, PipelineDag] = {}
        self._loaded = False

    def load(self) -> None:
        """Load all YAML templates from built-in + custom directories."""
        self._templates.clear()
        self._load_directory(_BUILTIN_DIR)

        settings = get_settings()
        custom = settings.pipeline.custom_dir
        if custom:
            custom_path = Path(custom)
            if custom_path.is_dir():
                self._load_directory(custom_path)

        self._loaded = True
        logger.info(
            "pipeline.registry_loaded",
            template_count=len(self._templates),
        )

    def _load_directory(self, directory: Path) -> None:
        """Load all .yaml files from a directory."""
        for yaml_path in sorted(directory.glob("*.yaml")):
            try:
                dag = _parse_yaml(yaml_path)
                if dag.name in self._templates:
                    logger.warning(
                        "pipeline.duplicate_template",
                        name=dag.name,
                        path=str(yaml_path),
                    )
                self._templates[dag.name] = dag
            except Exception:
                logger.exception(
                    "pipeline.template_load_failed",
                    path=str(yaml_path),
                )

    def get(self, name: str) -> PipelineDag:
        """Retrieve a pipeline by name. Raises NotFoundError if missing."""
        self._ensure_loaded()
        dag = self._templates.get(name)
        if dag is None:
            raise NotFoundError(f"Pipeline template '{name}' not found")
        return dag

    def register(self, dag: PipelineDag) -> None:
        """Register a pipeline at runtime (e.g., from plugins)."""
        self._templates[dag.name] = dag
        logger.info("pipeline.template_registered", name=dag.name)

    def list_all(self) -> list[str]:
        """Return all available pipeline template names."""
        self._ensure_loaded()
        return sorted(self._templates)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


def _parse_yaml(path: Path) -> PipelineDag:
    """Parse a YAML pipeline definition into a PipelineDag."""
    raw: dict[str, object] = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        msg = f"Pipeline YAML must be a mapping, got {type(raw).__name__}"
        raise DomainValidationError(msg)

    name = raw.get("name")
    if not name or not isinstance(name, str):
        msg = f"Pipeline YAML missing 'name' field in {path.name}"
        raise DomainValidationError(msg)

    description = str(raw.get("description", ""))
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, dict):
        msg = f"Pipeline YAML missing 'nodes' mapping in {path.name}"
        raise DomainValidationError(msg)

    nodes: dict[str, PipelineNode] = {}
    raw_nodes_dict = cast(dict[str, Any], raw_nodes)
    for raw_id, node_data_raw in raw_nodes_dict.items():
        node_id = str(raw_id)
        if not isinstance(node_data_raw, dict):
            msg = f"Node '{node_id}' must be a mapping in {path.name}"
            raise DomainValidationError(msg)
        node_data = cast(dict[str, Any], node_data_raw)
        agent = str(node_data.get("agent", node_id))
        tier = str(node_data.get("tier", "standard"))
        raw_inputs: list[Any] = node_data.get("inputs", [])
        raw_outputs: list[Any] = node_data.get("outputs", [])
        raw_contract = node_data.get("contract")
        contract: str | None = str(raw_contract) if raw_contract is not None else None
        nodes[node_id] = PipelineNode(
            agent_name=agent,
            tier=tier,
            inputs=tuple(str(i) for i in raw_inputs),
            outputs=tuple(str(o) for o in raw_outputs),
            contract=contract,
        )

    return PipelineDag(name=name, description=description, nodes=nodes)


# ── Singleton ──

_registry: PipelineRegistry | None = None


def get_pipeline_registry() -> PipelineRegistry:
    """Get or create the singleton PipelineRegistry."""
    global _registry
    if _registry is None:
        _registry = PipelineRegistry()
    return _registry


def reset_pipeline_registry() -> None:
    """Reset singleton (for tests)."""
    global _registry
    _registry = None
