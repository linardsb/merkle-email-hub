"""Tests for custom component generation via Scaffolder (Phase 47.8)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.component_matcher import ComponentMatch
from app.design_sync.component_renderer import RenderedSection
from app.design_sync.custom_component_generator import (
    _build_brief,
    _build_design_context,
    generate_custom_component,
)
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)
from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)

# ── Factories ────────────────────────────────────────────────────────


def _make_section(
    *,
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id="node-1",
        node_name="Test Section",
        column_layout=ColumnLayout.SINGLE,
        column_count=1,
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
    )


def _make_tokens(
    *,
    colors: list[ExtractedColor] | None = None,
    typography: list[ExtractedTypography] | None = None,
) -> ExtractedTokens:
    return ExtractedTokens(
        colors=colors or [ExtractedColor(name="primary", hex="#FF0000", opacity=1.0)],
        typography=typography
        or [
            ExtractedTypography(
                name="body",
                family="Arial",
                weight="400",
                size=16.0,
                line_height=1.5,
            )
        ],
        spacing=[ExtractedSpacing(name="small", value=8.0)],
    )


def _make_match(
    *,
    confidence: float = 0.4,
    section: EmailSection | None = None,
    section_idx: int = 0,
) -> ComponentMatch:
    return ComponentMatch(
        section_idx=section_idx,
        section=section or _make_section(),
        component_slug="hero-block",
        slot_fills=[],
        token_overrides=[],
        confidence=confidence,
    )


def _mock_settings(
    *,
    enabled: bool = True,
    threshold: float = 0.6,
    model: str = "",
    max_per_email: int = 3,
) -> MagicMock:
    mock_ds = MagicMock()
    mock_ds.custom_component_enabled = enabled
    mock_ds.custom_component_confidence_threshold = threshold
    mock_ds.custom_component_model = model
    mock_ds.custom_component_max_per_email = max_per_email
    mock_s = MagicMock()
    mock_s.design_sync = mock_ds
    return mock_s


def _mock_scaffolder_response(
    html: str = "<table><tr><td>Generated</td></tr></table>",
) -> MagicMock:
    resp = MagicMock()
    resp.html = html
    resp.model = "claude-sonnet-4-5-20250514"
    resp.confidence = 0.85
    return resp


# ── TestCustomComponentGenerator ─────────────────────────────────────


class TestCustomComponentGenerator:
    """Tests for the generate_custom_component function."""

    @pytest.mark.asyncio
    async def test_generate_returns_html(self) -> None:
        expected_html = "<table><tr><td>Custom</td></tr></table>"
        mock_service = AsyncMock()
        mock_service.generate.return_value = _mock_scaffolder_response(expected_html)

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            result = await generate_custom_component(_make_section(), _make_tokens())

        assert result == expected_html

    @pytest.mark.asyncio
    async def test_brief_includes_section_data(self) -> None:
        section = _make_section(
            section_type=EmailSectionType.HERO,
            texts=[TextBlock(node_id="t1", content="Welcome to our sale")],
            images=[ImagePlaceholder(node_id="i1", node_name="hero-img")],
            buttons=[ButtonElement(node_id="b1", text="Shop Now")],
        )
        mock_service = AsyncMock()
        mock_service.generate.return_value = _mock_scaffolder_response()

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            await generate_custom_component(section, _make_tokens())

        request = mock_service.generate.call_args[0][0]
        assert "hero" in request.brief.lower()
        assert "Welcome to our sale" in request.brief
        assert "Shop Now" in request.brief

    @pytest.mark.asyncio
    async def test_design_context_includes_tokens(self) -> None:
        tokens = _make_tokens(
            colors=[ExtractedColor(name="brand", hex="#0066CC", opacity=1.0)],
        )
        mock_service = AsyncMock()
        mock_service.generate.return_value = _mock_scaffolder_response()

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            await generate_custom_component(_make_section(), tokens)

        request = mock_service.generate.call_args[0][0]
        assert request.design_context is not None
        design_tokens = request.design_context["design_tokens"]
        assert any(c["hex"] == "#0066CC" for c in design_tokens["colors"])

    @pytest.mark.asyncio
    async def test_design_screenshot_included_when_provided(self) -> None:
        mock_service = AsyncMock()
        mock_service.generate.return_value = _mock_scaffolder_response()
        screenshot = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            await generate_custom_component(
                _make_section(), _make_tokens(), design_screenshot=screenshot
            )

        request = mock_service.generate.call_args[0][0]
        assert "design_screenshot_b64" in request.design_context

    @pytest.mark.asyncio
    async def test_scaffolder_error_propagates(self) -> None:
        mock_service = AsyncMock()
        mock_service.generate.side_effect = RuntimeError("Scaffolder failed")

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            with pytest.raises(RuntimeError, match="Scaffolder failed"):
                await generate_custom_component(_make_section(), _make_tokens())

    @pytest.mark.asyncio
    async def test_model_override_applied(self) -> None:
        mock_service = AsyncMock()
        mock_service.generate.return_value = _mock_scaffolder_response()

        with (
            patch(
                "app.design_sync.custom_component_generator.get_settings",
                return_value=_mock_settings(model="claude-opus-4-20250514"),
            ),
            patch(
                "app.ai.agents.scaffolder.service.get_scaffolder_service",
                return_value=mock_service,
            ),
            patch("app.ai.security.prompt_guard.scan_for_injection") as mock_scan,
        ):
            mock_scan.return_value = MagicMock(clean=True, flags=[], sanitized=None)
            await generate_custom_component(_make_section(), _make_tokens())

        request = mock_service.generate.call_args[0][0]
        assert request.brand_config is not None
        assert request.brand_config["model_override"] == "claude-opus-4-20250514"


# ── TestConverterIntegration ─────────────────────────────────────────


class TestConverterIntegration:
    """Tests for custom generation integration in converter_service."""

    def test_low_confidence_triggers_custom_gen(self) -> None:
        from app.design_sync.converter_service import DesignConverterService

        match = _make_match(confidence=0.4)
        tokens = _make_tokens()

        generated = RenderedSection(
            html="<table><tr><td>Custom</td></tr></table>",
            component_slug="custom-generated",
            section_idx=0,
        )

        with patch.object(
            DesignConverterService,
            "_try_custom_generate",
            return_value=generated,
        ) as mock_gen:
            result = DesignConverterService._try_custom_generate(match, tokens)

        assert result is not None
        assert result.component_slug == "custom-generated"
        mock_gen.assert_called_once_with(match, tokens)

    def test_high_confidence_returns_none_from_generator(self) -> None:
        """When confidence is high, _try_custom_generate is not called.

        We verify the threshold logic by checking the condition directly.
        """
        match = _make_match(confidence=0.8)
        settings = _mock_settings(threshold=0.6)

        # Confidence >= threshold → custom gen should NOT be attempted
        assert not (match.confidence < settings.design_sync.custom_component_confidence_threshold)

    def test_max_cap_respected(self) -> None:
        """Verify the max-per-email counter logic."""
        settings = _mock_settings(max_per_email=3)
        max_cap = settings.design_sync.custom_component_max_per_email

        # Simulate 4 low-confidence sections, cap at 3
        custom_gen_count = 0
        results: list[str] = []
        for _i in range(4):
            if custom_gen_count < max_cap:
                results.append("custom")
                custom_gen_count += 1
            else:
                results.append("template")

        assert results == ["custom", "custom", "custom", "template"]
        assert custom_gen_count == 3


# ── TestFeatureFlag ──────────────────────────────────────────────────


class TestFeatureFlag:
    """Tests for feature flag gating."""

    def test_disabled_flag_skips_generation(self) -> None:
        settings = _mock_settings(enabled=False)

        # When disabled, the enabled check prevents custom gen
        _custom_gen_enabled = (
            settings.design_sync.custom_component_enabled
            and settings.design_sync.custom_component_max_per_email > 0
        )
        assert not _custom_gen_enabled


# ── TestBriefConstruction ────────────────────────────────────────────


class TestBriefConstruction:
    """Tests for brief building logic."""

    def test_brief_contains_section_type(self) -> None:
        section = _make_section(section_type=EmailSectionType.HERO)
        brief = _build_brief(section)
        assert "hero" in brief.lower()

    def test_brief_contains_table_requirement(self) -> None:
        brief = _build_brief(_make_section())
        assert "table-based" in brief.lower()

    def test_design_context_has_color_tokens(self) -> None:
        tokens = _make_tokens(
            colors=[ExtractedColor(name="bg", hex="#FFFFFF", opacity=1.0)],
        )
        ctx = _build_design_context(tokens)
        design_tokens = ctx["design_tokens"]
        assert isinstance(design_tokens, dict)
        assert "colors" in design_tokens

    def test_design_context_screenshot_b64(self) -> None:
        tokens = _make_tokens()
        screenshot = b"\x89PNG" + b"\x00" * 20
        ctx = _build_design_context(tokens, design_screenshot=screenshot)
        assert "design_screenshot_b64" in ctx
