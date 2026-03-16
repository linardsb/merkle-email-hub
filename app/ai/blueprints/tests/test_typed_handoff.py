# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for typed handoff schemas (15.1)."""

from typing import cast

import pytest

from app.ai.blueprints.handoff import (
    AccessibilityHandoff,
    DarkModeHandoff,
    ScaffolderHandoff,
    format_upstream_constraints,
)
from app.ai.blueprints.protocols import AgentHandoff


class TestTypedPayloads:
    """Typed payload dataclasses."""

    def test_scaffolder_handoff_frozen(self) -> None:
        h = ScaffolderHandoff(template_name="promo_1col")
        with pytest.raises(AttributeError):
            h.template_name = "other"  # type: ignore[misc]

    def test_default_values(self) -> None:
        h = DarkModeHandoff()
        assert h.overrides_count == 0
        assert h.strategy == ""

    def test_colors_applied_dict(self) -> None:
        h = ScaffolderHandoff(colors_applied={"primary": "#FF0000"})
        assert h.colors_applied["primary"] == "#FF0000"


class TestAgentHandoffWithPayload:
    """AgentHandoff carries typed_payload."""

    def test_typed_payload_preserved_in_compact(self) -> None:
        payload = ScaffolderHandoff(template_name="promo")
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>big html</p>",
            typed_payload=payload,
        )
        compacted = handoff.compact()
        assert compacted.artifact == ""
        assert compacted.typed_payload is payload

    def test_uncertainties_in_summary(self) -> None:
        handoff = AgentHandoff(
            agent_name="scaffolder",
            confidence=0.85,
            uncertainties=("color_choice", "layout"),
        )
        assert "unc=2" in handoff.summary()

    def test_no_uncertainties_in_summary(self) -> None:
        handoff = AgentHandoff(agent_name="scaffolder", confidence=0.9)
        assert "unc=" not in handoff.summary()

    def test_backward_compat_no_payload(self) -> None:
        """Existing handoffs without typed_payload still work."""
        handoff = AgentHandoff(agent_name="scaffolder", artifact="<p>ok</p>")
        assert handoff.typed_payload is None
        assert handoff.uncertainties == ()
        compacted = handoff.compact()
        assert compacted.typed_payload is None


class TestFormatUpstreamConstraints:
    """format_upstream_constraints produces agent-specific context strings."""

    def test_scaffolder_constraints(self) -> None:
        payload = ScaffolderHandoff(
            template_name="promo_1col",
            slots_filled=("header", "body", "cta"),
            colors_applied={"primary": "#FF0000"},
            locked_roles=("footer_bg",),
        )
        handoff = AgentHandoff(agent_name="scaffolder", typed_payload=payload)
        result = format_upstream_constraints(handoff)
        assert "Template: promo_1col" in result
        assert "Locked roles (do not change): footer_bg" in result

    def test_no_payload_returns_empty(self) -> None:
        handoff = AgentHandoff(agent_name="scaffolder")
        assert format_upstream_constraints(handoff) == ""

    def test_non_handoff_returns_empty(self) -> None:
        assert format_upstream_constraints("not a handoff") == ""

    def test_uncertainties_included(self) -> None:
        payload = DarkModeHandoff(overrides_count=3, strategy="custom")
        handoff = AgentHandoff(
            agent_name="dark_mode",
            typed_payload=payload,
            uncertainties=("bg_color_dark",),
        )
        result = format_upstream_constraints(handoff)
        assert "Uncertainties: bg_color_dark" in result

    def test_dark_mode_constraints(self) -> None:
        payload = DarkModeHandoff(
            overrides_count=5,
            strategy="custom",
            prefers_color_scheme=True,
        )
        handoff = AgentHandoff(agent_name="dark_mode", typed_payload=payload)
        result = format_upstream_constraints(handoff)
        assert "Strategy: custom" in result
        assert "prefers-color-scheme" in result

    def test_accessibility_constraints(self) -> None:
        payload = AccessibilityHandoff(
            issues_fixed=3,
            alt_text_warnings=("img1 missing alt",),
        )
        handoff = AgentHandoff(agent_name="accessibility", typed_payload=payload)
        result = format_upstream_constraints(handoff)
        assert "Issues fixed: 3" in result
        assert "Alt text warnings: img1 missing alt" in result


class TestEngineTypedHandoffFlow:
    """Integration: typed payloads flow through engine execution."""

    @pytest.mark.asyncio()
    async def test_typed_payload_reaches_downstream_context(self) -> None:
        """Downstream node receives upstream_constraints in metadata."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        captured_contexts: list[NodeContext] = []

        class TypedScaffolder:
            @property
            def name(self) -> str:
                return "scaffolder"

            @property
            def node_type(self) -> str:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                payload = ScaffolderHandoff(template_name="promo", locked_roles=("footer_bg",))
                return NodeResult(
                    status="success",
                    html="<p>test</p>",
                    handoff=AgentHandoff(
                        agent_name="scaffolder",
                        artifact="<p>test</p>",
                        typed_payload=payload,
                    ),
                )

        class CapturingNode:
            @property
            def name(self) -> str:
                return "dark_mode"

            @property
            def node_type(self) -> str:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                captured_contexts.append(context)
                return NodeResult(status="success", html=context.html)

        from app.ai.blueprints.protocols import BlueprintNode

        defn = BlueprintDefinition(
            name="test",
            nodes=cast(
                "dict[str, BlueprintNode]",
                {"scaffolder": TypedScaffolder(), "dark_mode": CapturingNode()},
            ),
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )
        engine = BlueprintEngine(defn)
        await engine.run(brief="test")

        assert len(captured_contexts) == 1
        ctx = captured_contexts[0]
        assert "upstream_constraints" in ctx.metadata
        constraints_str = ctx.metadata["upstream_constraints"]
        assert "Template: promo" in str(constraints_str)
        assert "Locked roles (do not change): footer_bg" in str(constraints_str)

    @pytest.mark.asyncio()
    async def test_no_typed_payload_no_constraints(self) -> None:
        """Node without typed_payload doesn't inject upstream_constraints."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        captured: list[NodeContext] = []

        class PlainNode:
            @property
            def name(self) -> str:
                return "scaffolder"

            @property
            def node_type(self) -> str:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    status="success",
                    html="<p>ok</p>",
                    handoff=AgentHandoff(agent_name="scaffolder", artifact="<p>ok</p>"),
                )

        class Receiver:
            @property
            def name(self) -> str:
                return "dark_mode"

            @property
            def node_type(self) -> str:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                captured.append(context)
                return NodeResult(status="success", html=context.html)

        from app.ai.blueprints.protocols import BlueprintNode

        defn = BlueprintDefinition(
            name="test",
            nodes=cast(
                "dict[str, BlueprintNode]",
                {"scaffolder": PlainNode(), "dark_mode": Receiver()},
            ),
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )
        engine = BlueprintEngine(defn)
        await engine.run(brief="test")

        assert "upstream_constraints" not in captured[0].metadata
