"""Integration tests for executor + hooks."""

from __future__ import annotations

import pytest

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.ai.pipeline.artifacts import ArtifactStore
from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.ai.pipeline.executor import PipelineExecutor
from app.core.config import PipelineConfig
from app.core.exceptions import HookAbortError


class _StubResponse:
    html: str = "<html><body><table><tr><td>stub</td></tr></table></body></html>"
    tokens_used: int = 100


class _MockRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, agent_name: str, inputs: dict[str, object]) -> object:
        self.calls.append(agent_name)
        return _StubResponse()


def _simple_dag() -> PipelineDag:
    """A→B linear DAG."""
    return PipelineDag(
        name="test-hook-dag",
        description="Test DAG for hook integration",
        nodes={
            "a": PipelineNode("agent_a", "complex", inputs=(), outputs=("html",)),
            "b": PipelineNode("agent_b", "standard", inputs=("html",), outputs=("final",)),
        },
    )


class TestExecutorFiresHooks:
    @pytest.mark.asyncio
    async def test_executor_fires_hooks(self) -> None:
        """Verify hook events fire in correct order during executor run."""
        fired_events: list[str] = []

        async def tracking_hook(ctx: HookContext) -> None:
            label = str(ctx.event)
            if ctx.agent_name:
                label += f":{ctx.agent_name}"
            fired_events.append(label)

        registry = HookRegistry(active_profile="standard")
        for event in HookEvent:
            registry.register(event, tracking_hook, name=f"tracker_{event}", profile="minimal")

        executor = PipelineExecutor(
            dag=_simple_dag(),
            store=ArtifactStore(),
            settings=PipelineConfig(enabled=True, max_concurrent_agents=5),
            agent_runner=_MockRunner(),
            hook_registry=registry,
        )

        await executor.execute("run-1")

        assert "pre_pipeline" in fired_events
        assert "post_pipeline" in fired_events
        # Pre/post agent for both agents
        assert "pre_agent:agent_a" in fired_events
        assert "post_agent:agent_a" in fired_events
        assert "pre_agent:agent_b" in fired_events
        assert "post_agent:agent_b" in fired_events
        # Pipeline events come first/last
        assert fired_events[0] == "pre_pipeline"
        assert fired_events[-1] == "post_pipeline"

    @pytest.mark.asyncio
    async def test_minimal_profile_cost_only(self) -> None:
        """Minimal profile only fires cost_tracker (minimal) hooks, not standard ones."""
        fired_hooks: list[str] = []

        async def minimal_hook(ctx: HookContext) -> None:
            fired_hooks.append("minimal")

        async def standard_hook(ctx: HookContext) -> None:
            fired_hooks.append("standard")

        registry = HookRegistry(active_profile="minimal")
        registry.register(HookEvent.POST_AGENT, minimal_hook, name="min_hook", profile="minimal")
        registry.register(HookEvent.POST_AGENT, standard_hook, name="std_hook", profile="standard")

        executor = PipelineExecutor(
            dag=_simple_dag(),
            store=ArtifactStore(),
            settings=PipelineConfig(enabled=True, max_concurrent_agents=5),
            agent_runner=_MockRunner(),
            hook_registry=registry,
        )

        await executor.execute("run-2")

        assert "minimal" in fired_hooks
        assert "standard" not in fired_hooks

    @pytest.mark.asyncio
    async def test_strict_abort_stops_pipeline(self) -> None:
        """HookAbortError from a hook propagates and stops the pipeline."""

        async def aborting_hook(ctx: HookContext) -> None:
            if ctx.agent_name == "agent_a":
                raise HookAbortError("gate", "rejected agent_a")

        registry = HookRegistry(active_profile="strict")
        registry.register(
            HookEvent.POST_AGENT,
            aborting_hook,
            name="abort_hook",
            profile="strict",
        )

        runner = _MockRunner()
        executor = PipelineExecutor(
            dag=_simple_dag(),
            store=ArtifactStore(),
            settings=PipelineConfig(enabled=True, max_concurrent_agents=5),
            agent_runner=runner,
            hook_registry=registry,
        )

        with pytest.raises(HookAbortError, match="rejected agent_a"):
            await executor.execute("run-3")

        # agent_a ran but agent_b should not have (abort after agent_a's POST_AGENT)
        assert "agent_a" in runner.calls
