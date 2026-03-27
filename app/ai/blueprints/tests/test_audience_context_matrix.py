"""Regression matrix tests for audience context formatting (Phase 32.8).

Tests that format_audience_context() produces expected output for key client
profiles — gmail (clipping), apple_mail (no restrictions), outlook (VML),
and multi-client worst-case aggregation.
"""

from __future__ import annotations

from app.ai.blueprints.audience_context import (
    AudienceConstraint,
    AudienceProfile,
    format_audience_context,
)
from app.knowledge.ontology.types import (
    ClientEngine,
    EmailClient,
    SupportLevel,
)


def _make_client(
    *,
    id: str,
    name: str,
    engine: ClientEngine = ClientEngine.BLINK,
    family: str = "test",
    platform: str = "test",
) -> EmailClient:
    return EmailClient(id=id, name=name, family=family, platform=platform, engine=engine)


def _make_constraint(
    *,
    prop_name: str,
    client_name: str,
    client_id: str,
    category: str = "layout",
    workaround: str = "",
) -> AudienceConstraint:
    return AudienceConstraint(
        property_id=prop_name.lower().replace(" ", "_"),
        property_name=prop_name,
        category=category,
        level=SupportLevel.NONE,
        client_name=client_name,
        client_id=client_id,
        fallback_ids=(),
        workaround=workaround,
    )


class TestAudienceContextMatrix:
    """Regression tests for audience context formatting per client profile."""

    def test_gmail_mentions_clipping(self) -> None:
        """Gmail audience context includes clipping warning."""
        profile = AudienceProfile(
            persona_names=("Gmail User",),
            client_ids=("gmail_web",),
            clients=(_make_client(id="gmail_web", name="Gmail (Web)"),),
            constraints=(),
            dark_mode_required=False,
            mobile_viewports=(),
            rendering_engines=("blink",),
            dark_mode_types=("forced_inversion",),
            vml_required=False,
            clip_threshold_kb=102,
        )
        output = format_audience_context(profile)

        assert "Gmail" in output
        assert "102" in output
        assert "clip" in output.lower()

    def test_apple_mail_no_layout_restrictions(self) -> None:
        """Apple Mail supports all CSS — no 'unsupported' warnings."""
        profile = AudienceProfile(
            persona_names=("Apple User",),
            client_ids=("apple_mail_macos",),
            clients=(
                _make_client(
                    id="apple_mail_macos",
                    name="Apple Mail (macOS)",
                    engine=ClientEngine.WEBKIT,
                ),
            ),
            constraints=(),  # Apple Mail supports everything
            dark_mode_required=False,
            mobile_viewports=(),
            rendering_engines=("webkit",),
            dark_mode_types=("developer_controlled",),
            vml_required=False,
            clip_threshold_kb=None,
        )
        output = format_audience_context(profile)

        assert "Apple Mail" in output
        assert "No CSS restrictions" in output
        assert "unsupported" not in output.lower()

    def test_outlook_mentions_vml(self) -> None:
        """Outlook audience context mentions VML requirement."""
        profile = AudienceProfile(
            persona_names=("Outlook User",),
            client_ids=("outlook_365_win",),
            clients=(
                _make_client(
                    id="outlook_365_win",
                    name="Outlook 365 (Windows)",
                    engine=ClientEngine.WORD,
                ),
            ),
            constraints=(
                _make_constraint(
                    prop_name="border-radius",
                    category="box_model",
                    client_name="Outlook 365 (Windows)",
                    client_id="outlook_365_win",
                    workaround="Use VML <v:roundrect>",
                ),
            ),
            dark_mode_required=False,
            mobile_viewports=(),
            rendering_engines=("word",),
            dark_mode_types=(),
            vml_required=True,
            clip_threshold_kb=None,
        )
        output = format_audience_context(profile)

        assert "Outlook" in output
        assert "VML" in output

    def test_multi_client_aggregates_worst_case(self) -> None:
        """Multi-client profile includes both client names + worst-case constraints."""
        profile = AudienceProfile(
            persona_names=("Gmail User", "Outlook User"),
            client_ids=("gmail_web", "outlook_365_win"),
            clients=(
                _make_client(id="gmail_web", name="Gmail (Web)"),
                _make_client(
                    id="outlook_365_win",
                    name="Outlook 365 (Windows)",
                    engine=ClientEngine.WORD,
                ),
            ),
            constraints=(
                _make_constraint(
                    prop_name="flexbox",
                    category="layout",
                    client_name="Outlook 365 (Windows)",
                    client_id="outlook_365_win",
                    workaround="Use nested tables",
                ),
                _make_constraint(
                    prop_name="border-radius",
                    category="box_model",
                    client_name="Outlook 365 (Windows)",
                    client_id="outlook_365_win",
                    workaround="Use VML <v:roundrect>",
                ),
            ),
            dark_mode_required=False,
            mobile_viewports=(),
            rendering_engines=("blink", "word"),
            dark_mode_types=("forced_inversion",),
            vml_required=True,
            clip_threshold_kb=102,
        )
        output = format_audience_context(profile)

        # Both clients mentioned
        assert "Gmail" in output
        assert "Outlook" in output
        # Worst-case constraints present
        assert "flexbox" in output.lower()
        assert "unsupported" in output.lower()
        # VML required from Outlook
        assert "VML" in output
        # Clipping from Gmail
        assert "102" in output
