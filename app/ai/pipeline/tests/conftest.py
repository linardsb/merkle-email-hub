"""Shared fixtures for pipeline tests."""

from __future__ import annotations

import asyncio

import pytest

from app.ai.pipeline.artifacts import ArtifactStore
from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.ai.pipeline.registry import reset_pipeline_registry
from app.core.config import PipelineConfig


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset singleton before each test."""
    reset_pipeline_registry()
    yield  # type: ignore[misc]
    reset_pipeline_registry()


@pytest.fixture
def three_level_nodes() -> dict[str, PipelineNode]:
    """3-level DAG: A → [B, C] → D."""
    return {
        "a": PipelineNode("agent_a", "complex", inputs=(), outputs=("html",)),
        "b": PipelineNode("agent_b", "standard", inputs=("html",), outputs=("styled_html",)),
        "c": PipelineNode("agent_c", "standard", inputs=("html",), outputs=("qa_results",)),
        "d": PipelineNode(
            "agent_d", "lightweight", inputs=("styled_html", "qa_results"), outputs=("final",)
        ),
    }


@pytest.fixture
def three_level_dag(three_level_nodes: dict[str, PipelineNode]) -> PipelineDag:
    return PipelineDag(name="test-3level", description="Test DAG", nodes=three_level_nodes)


# ── Executor Fixtures ──


class _StubResponse:
    """Stub agent response with default values."""

    html: str = "<html><body><table><tr><td>stub</td></tr></table></body></html>"
    tokens_used: int = 100


class MockAgentRunner:
    """Configurable mock agent runner for executor tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.responses: dict[str, object] = {}
        self.delays: dict[str, float] = {}
        self.errors: dict[str, Exception] = {}

    async def __call__(self, agent_name: str, inputs: dict[str, object]) -> object:
        self.calls.append((agent_name, inputs))
        if agent_name in self.errors:
            raise self.errors[agent_name]
        if agent_name in self.delays:
            await asyncio.sleep(self.delays[agent_name])
        return self.responses.get(agent_name, _StubResponse())


@pytest.fixture
def mock_runner() -> MockAgentRunner:
    return MockAgentRunner()


@pytest.fixture
def pipeline_config() -> PipelineConfig:
    return PipelineConfig(enabled=True, max_concurrent_agents=5)


@pytest.fixture
def artifact_store() -> ArtifactStore:
    return ArtifactStore()
