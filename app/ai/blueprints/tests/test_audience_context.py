"""Tests for audience context: persona → ontology → agent constraints."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.ai.blueprints.audience_context import (
    AudienceProfile,
    build_audience_profile,
    format_audience_context,
    resolve_audience_clients,
)
from app.knowledge.ontology.types import (
    ClientEngine,
    CSSCategory,
    CSSProperty,
    EmailClient,
    SupportEntry,
    SupportLevel,
)
from app.personas.schemas import PersonaResponse

_NOW = datetime.fromisoformat("2026-01-01T00:00:00")


def _make_persona(
    *,
    name: str = "Test",
    email_client: str = "gmail",
    dark_mode: bool = False,
    viewport_width: int = 600,
    device_type: str = "desktop",
) -> PersonaResponse:
    return PersonaResponse(
        id=1,
        name=name,
        slug=name.lower(),
        email_client=email_client,
        device_type=device_type,
        dark_mode=dark_mode,
        viewport_width=viewport_width,
        os_name="macOS",
        is_preset=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


class TestResolveAudienceClients:
    def test_single_persona_gmail(self) -> None:
        personas = [_make_persona(email_client="gmail")]
        result = resolve_audience_clients(personas)
        assert result == ["gmail_web", "gmail_ios", "gmail_android"]

    def test_multiple_personas_deduplicates(self) -> None:
        personas = [
            _make_persona(email_client="gmail"),
            _make_persona(email_client="gmail"),  # duplicate
        ]
        result = resolve_audience_clients(personas)
        assert result == ["gmail_web", "gmail_ios", "gmail_android"]

    def test_multiple_different_personas(self) -> None:
        personas = [
            _make_persona(email_client="gmail"),
            _make_persona(email_client="outlook-365"),
        ]
        result = resolve_audience_clients(personas)
        assert "gmail_web" in result
        assert "outlook_365_win" in result

    def test_unknown_slug_returns_empty(self) -> None:
        personas = [_make_persona(email_client="unknown-client")]
        result = resolve_audience_clients(personas)
        assert result == []


class TestBuildAudienceProfile:
    def test_empty_personas_returns_none(self) -> None:
        assert build_audience_profile([]) is None

    def test_unknown_client_returns_none(self) -> None:
        personas = [_make_persona(email_client="unknown-client")]
        assert build_audience_profile(personas) is None

    @patch("app.ai.blueprints.audience_context.load_ontology")
    def test_outlook_has_constraints(self, mock_ontology: MagicMock) -> None:
        """Outlook personas should produce constraints for unsupported CSS."""
        flexbox_prop = CSSProperty(
            id="flexbox",
            property_name="display: flex",
            value="flex",
            category=CSSCategory.LAYOUT,
            description="Flexbox layout",
            mdn_url="",
            tags=(),
        )
        outlook_client = EmailClient(
            id="outlook_365_win",
            name="Outlook 365 (Windows)",
            family="outlook",
            platform="windows",
            engine=ClientEngine.WORD,
            market_share=10.0,
            notes="",
            tags=(),
        )
        support_entry = SupportEntry(
            property_id="flexbox",
            client_id="outlook_365_win",
            level=SupportLevel.NONE,
            notes="Word rendering engine",
            fallback_ids=(),
            workaround="Use table layout",
        )

        registry = mock_ontology.return_value
        registry.get_client.return_value = outlook_client
        registry.properties_unsupported_by.return_value = [flexbox_prop]
        registry.get_support_entry.return_value = support_entry

        personas = [_make_persona(email_client="outlook-365")]
        profile = build_audience_profile(personas)

        assert profile is not None
        assert len(profile.constraints) == 1
        assert profile.constraints[0].property_name == "display: flex"
        assert profile.constraints[0].client_name == "Outlook 365 (Windows)"
        assert profile.constraints[0].workaround == "Use table layout"

    @patch("app.ai.blueprints.audience_context.load_ontology")
    def test_dark_mode_required(self, mock_ontology: MagicMock) -> None:
        registry = mock_ontology.return_value
        registry.get_client.return_value = EmailClient(
            id="gmail_web",
            name="Gmail (Web)",
            family="gmail",
            platform="web",
            engine=ClientEngine.BLINK,
            market_share=30.0,
            notes="",
            tags=(),
        )
        registry.properties_unsupported_by.return_value = []

        personas = [_make_persona(email_client="gmail", dark_mode=True)]
        profile = build_audience_profile(personas)

        assert profile is not None
        assert profile.dark_mode_required is True

    @patch("app.ai.blueprints.audience_context.load_ontology")
    def test_mobile_viewports(self, mock_ontology: MagicMock) -> None:
        registry = mock_ontology.return_value
        registry.get_client.return_value = EmailClient(
            id="gmail_web",
            name="Gmail (Web)",
            family="gmail",
            platform="web",
            engine=ClientEngine.BLINK,
            market_share=30.0,
            notes="",
            tags=(),
        )
        registry.properties_unsupported_by.return_value = []

        personas = [
            _make_persona(email_client="gmail", viewport_width=375),
            _make_persona(email_client="gmail", viewport_width=600),
        ]
        profile = build_audience_profile(personas)

        assert profile is not None
        assert profile.mobile_viewports == (375,)


class TestFormatAudienceContext:
    def test_includes_client_names(self) -> None:
        profile = AudienceProfile(
            persona_names=("Gmail User",),
            client_ids=("gmail_web",),
            clients=(
                EmailClient(
                    id="gmail_web",
                    name="Gmail (Web)",
                    family="gmail",
                    platform="web",
                    engine=ClientEngine.BLINK,
                    market_share=30.0,
                    notes="",
                    tags=(),
                ),
            ),
            constraints=(),
            dark_mode_required=False,
            mobile_viewports=(),
        )
        output = format_audience_context(profile)
        assert "Gmail (Web)" in output
        assert "Gmail User" in output

    def test_includes_constraints(self) -> None:
        from app.ai.blueprints.audience_context import AudienceConstraint

        profile = AudienceProfile(
            persona_names=("Outlook User",),
            client_ids=("outlook_365_win",),
            clients=(
                EmailClient(
                    id="outlook_365_win",
                    name="Outlook 365",
                    family="outlook",
                    platform="windows",
                    engine=ClientEngine.WORD,
                    market_share=10.0,
                    notes="",
                    tags=(),
                ),
            ),
            constraints=(
                AudienceConstraint(
                    property_id="flexbox",
                    property_name="display: flex",
                    category="layout",
                    level=SupportLevel.NONE,
                    client_name="Outlook 365",
                    client_id="outlook_365_win",
                    fallback_ids=(),
                    workaround="Use table layout",
                ),
            ),
            dark_mode_required=False,
            mobile_viewports=(),
        )
        output = format_audience_context(profile)
        assert "display: flex" in output
        assert "Outlook 365" in output
        assert "Use table layout" in output
        assert "CSS PROPERTIES TO AVOID" in output

    def test_dark_mode_requirement(self) -> None:
        profile = AudienceProfile(
            persona_names=("DM User",),
            client_ids=("gmail_web",),
            clients=(
                EmailClient(
                    id="gmail_web",
                    name="Gmail (Web)",
                    family="gmail",
                    platform="web",
                    engine=ClientEngine.BLINK,
                    market_share=30.0,
                    notes="",
                    tags=(),
                ),
            ),
            constraints=(),
            dark_mode_required=True,
            mobile_viewports=(),
        )
        output = format_audience_context(profile)
        assert "Dark mode support is required" in output

    def test_no_constraints_message(self) -> None:
        profile = AudienceProfile(
            persona_names=("Simple User",),
            client_ids=("gmail_web",),
            clients=(
                EmailClient(
                    id="gmail_web",
                    name="Gmail (Web)",
                    family="gmail",
                    platform="web",
                    engine=ClientEngine.BLINK,
                    market_share=30.0,
                    notes="",
                    tags=(),
                ),
            ),
            constraints=(),
            dark_mode_required=False,
            mobile_viewports=(),
        )
        output = format_audience_context(profile)
        assert "No CSS restrictions" in output


class TestEngineAudienceIntegration:
    """Verify engine injects audience_context into agentic node metadata."""

    @pytest.mark.asyncio
    async def test_audience_context_injected_for_agentic_nodes(self) -> None:
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        captured_context: list[NodeContext] = []

        class _CaptureNode:
            name = "capture"
            node_type = "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                captured_context.append(context)
                return NodeResult(status="success", html="<div>ok</div>")

        definition = BlueprintDefinition(
            name="test",
            nodes={"capture": _CaptureNode()},  # type: ignore[dict-item]
            edges=[],
            entry_node="capture",
        )

        profile = AudienceProfile(
            persona_names=("Test User",),
            client_ids=("gmail_web",),
            clients=(
                EmailClient(
                    id="gmail_web",
                    name="Gmail (Web)",
                    family="gmail",
                    platform="web",
                    engine=ClientEngine.BLINK,
                    market_share=30.0,
                    notes="",
                    tags=(),
                ),
            ),
            constraints=(),
            dark_mode_required=False,
            mobile_viewports=(),
        )

        engine = BlueprintEngine(definition, audience_profile=profile)
        await engine.run(brief="test brief")

        assert len(captured_context) == 1
        ctx = captured_context[0]
        assert "audience_context" in ctx.metadata
        audience_context = str(ctx.metadata["audience_context"])
        assert "Gmail (Web)" in audience_context
        assert "TARGET AUDIENCE CONSTRAINTS" in audience_context

    @pytest.mark.asyncio
    async def test_no_audience_context_when_profile_is_none(self) -> None:
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        captured_context: list[NodeContext] = []

        class _CaptureNode:
            name = "capture"
            node_type = "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                captured_context.append(context)
                return NodeResult(status="success", html="<div>ok</div>")

        definition = BlueprintDefinition(
            name="test",
            nodes={"capture": _CaptureNode()},  # type: ignore[dict-item]
            edges=[],
            entry_node="capture",
        )

        engine = BlueprintEngine(definition)  # No audience_profile
        await engine.run(brief="test brief")

        assert len(captured_context) == 1
        assert "audience_context" not in captured_context[0].metadata
