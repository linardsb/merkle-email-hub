"""Unit tests for the Accessibility Auditor agent — alt text validator + service integration."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.accessibility.alt_text_validator import (
    AltTextAnalysis,
    format_alt_text_warnings,
    validate_alt_text,
)
from app.ai.agents.accessibility.schemas import AccessibilityRequest
from app.ai.agents.accessibility.service import (
    AccessibilityService,
    _alt_text_warnings_var,
)
from app.ai.protocols import CompletionResponse

# ── HTML Fixtures ──

_GOOD_HTML = (
    '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body>'
    '<table role="presentation"><tr><td>'
    '<img src="hero.jpg" alt="Blue cotton t-shirt, front view" width="600">'
    '<img src="spacer.gif" alt="" width="1" height="20">'
    "</td></tr></table></body></html>"
)

_MISSING_ALT_HTML = (
    '<html><body><img src="hero.jpg" width="600"><img src="product.jpg" width="200"></body></html>'
)

_GENERIC_ALT_HTML = '<html><body><img src="hero.jpg" alt="image" width="600"></body></html>'

_FILENAME_ALT_HTML = (
    '<html><body><img src="hero.jpg" alt="hero-banner.jpg" width="600"></body></html>'
)

_BAD_PREFIX_HTML = (
    '<html><body><img src="hero.jpg" alt="Image of a product on display" width="600"></body></html>'
)

_SINGLE_WORD_HTML = '<html><body><img src="hero.jpg" alt="Product" width="600"></body></html>'

_LONG_ALT_HTML = (
    "<html><body>"
    '<img src="hero.jpg" alt="' + " ".join(["word"] * 30) + '" width="600">'
    "</body></html>"
)

_DECORATIVE_SPACER_WITH_TEXT = (
    '<html><body><img src="spacer.gif" alt="spacer image" width="600" height="20"></body></html>'
)

_DECORATIVE_SPACER_EMPTY = (
    '<html><body><img src="spacer.gif" alt="" width="600" height="20"></body></html>'
)

_TRACKING_PIXEL_WITH_ALT = (
    '<html><body><img src="track.gif" width="1" height="1" alt="tracker"></body></html>'
)

_TRACKING_PIXEL_EMPTY = (
    '<html><body><img src="track.gif" width="1" height="1" alt=""></body></html>'
)

_NO_IMAGES_HTML = "<html><body><p>No images here.</p></body></html>"

_EMPTY_ALT_CONTENT = '<html><body><img src="hero.jpg" alt="" width="600"></body></html>'


# ── AltTextValidator Tests ──


class TestValidateAltText:
    """Tests for the alt text quality validator."""

    def test_missing_alt_detected(self) -> None:
        result = validate_alt_text(_MISSING_ALT_HTML)
        assert result.total_images == 2
        assert result.images_with_alt == 0
        assert len(result.warnings) == 2
        assert all(w.severity == "error" for w in result.warnings)
        assert "missing alt attribute" in result.warnings[0].issue

    def test_generic_alt_detected(self) -> None:
        result = validate_alt_text(_GENERIC_ALT_HTML)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "error"
        assert "generic alt text" in result.warnings[0].issue

    def test_generic_alt_case_insensitive(self) -> None:
        html = '<html><body><img src="x.jpg" alt="IMAGE" width="600"></body></html>'
        result = validate_alt_text(html)
        assert len(result.warnings) == 1
        assert "generic alt text" in result.warnings[0].issue

    def test_filename_as_alt(self) -> None:
        result = validate_alt_text(_FILENAME_ALT_HTML)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "error"
        assert "filename" in result.warnings[0].issue

    def test_bad_prefix_detected(self) -> None:
        result = validate_alt_text(_BAD_PREFIX_HTML)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert "screen readers already announce" in result.warnings[0].issue

    def test_single_word_alt(self) -> None:
        result = validate_alt_text(_SINGLE_WORD_HTML)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert "single-word" in result.warnings[0].issue

    def test_long_alt_detected(self) -> None:
        result = validate_alt_text(_LONG_ALT_HTML)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert "too long" in result.warnings[0].issue

    def test_valid_content_alt_passes(self) -> None:
        result = validate_alt_text(_GOOD_HTML)
        assert len(result.warnings) == 0
        assert result.total_images == 2
        assert result.content_images == 1
        assert result.decorative_images == 1

    def test_decorative_spacer_with_text(self) -> None:
        result = validate_alt_text(_DECORATIVE_SPACER_WITH_TEXT)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert 'decorative image should have alt=""' in result.warnings[0].issue

    def test_decorative_spacer_empty_alt(self) -> None:
        result = validate_alt_text(_DECORATIVE_SPACER_EMPTY)
        assert len(result.warnings) == 0
        assert result.decorative_images == 1

    def test_tracking_pixel_1x1_with_alt(self) -> None:
        result = validate_alt_text(_TRACKING_PIXEL_WITH_ALT)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert "decorative" in result.warnings[0].issue

    def test_tracking_pixel_empty_alt(self) -> None:
        result = validate_alt_text(_TRACKING_PIXEL_EMPTY)
        assert len(result.warnings) == 0
        assert result.decorative_images == 1

    def test_no_images_returns_empty(self) -> None:
        result = validate_alt_text(_NO_IMAGES_HTML)
        assert result == AltTextAnalysis(
            warnings=(),
            total_images=0,
            images_with_alt=0,
            decorative_images=0,
            content_images=0,
        )

    def test_invalid_html_returns_empty(self) -> None:
        result = validate_alt_text("")
        assert result.total_images == 0
        assert len(result.warnings) == 0

    def test_content_image_empty_alt_error(self) -> None:
        result = validate_alt_text(_EMPTY_ALT_CONTENT)
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "error"
        assert "needs descriptive text" in result.warnings[0].issue

    def test_display_none_is_decorative(self) -> None:
        html = '<html><body><img src="x.jpg" alt="hidden" style="display:none;"></body></html>'
        result = validate_alt_text(html)
        assert result.decorative_images == 1
        assert len(result.warnings) == 1
        assert "decorative" in result.warnings[0].issue

    def test_decorative_keyword_not_false_positive_on_compound_words(self) -> None:
        """Compound filenames like 'cross-border-shopping.jpg' should NOT be decorative."""
        html = '<html><body><img src="cross-border-shopping.jpg" alt="International shopping" width="600"></body></html>'
        result = validate_alt_text(html)
        assert result.decorative_images == 0
        assert result.content_images == 1
        assert len(result.warnings) == 0

    def test_decorative_keyword_in_first_segment(self) -> None:
        html = '<html><body><img src="border-line.png" alt="decorative" width="600"></body></html>'
        result = validate_alt_text(html)
        assert result.decorative_images == 1

    def test_decorative_keyword_in_last_segment(self) -> None:
        html = '<html><body><img src="email-divider.png" alt="line" width="600"></body></html>'
        result = validate_alt_text(html)
        assert result.decorative_images == 1

    def test_multiple_issues_collected(self) -> None:
        html = (
            "<html><body>"
            '<img src="a.jpg">'  # missing alt
            '<img src="b.jpg" alt="image">'  # generic
            '<img src="spacer.gif" alt="spacer thing">'  # decorative with text
            "</body></html>"
        )
        result = validate_alt_text(html)
        assert len(result.warnings) == 3
        assert result.total_images == 3


class TestFormatAltTextWarnings:
    """Tests for the formatted warning output."""

    def test_format_includes_severity_and_src(self) -> None:
        warnings = format_alt_text_warnings(_GENERIC_ALT_HTML)
        assert len(warnings) == 1
        assert "[error]" in warnings[0]
        assert "hero.jpg" in warnings[0]

    def test_format_missing_alt_summary(self) -> None:
        warnings = format_alt_text_warnings(_MISSING_ALT_HTML)
        # First line should be the missing alt summary
        assert warnings[0].startswith("[error] 2/2 images missing alt attribute")

    def test_format_clean_html_empty(self) -> None:
        warnings = format_alt_text_warnings(_GOOD_HTML)
        assert warnings == []


# ── Service Integration Tests ──


class TestAccessibilityServicePostProcess:
    """Tests for AccessibilityService._post_process()."""

    def test_post_process_detects_generic_alt(self) -> None:
        svc = AccessibilityService()
        # _post_process calls super() which extracts HTML + sanitizes,
        # then runs alt text validation. We pass raw HTML (no code fence).
        html = svc._post_process(_GENERIC_ALT_HTML)
        warnings = _alt_text_warnings_var.get(None)
        assert warnings is not None
        assert len(warnings) >= 1
        assert "generic alt text" in warnings[0]
        # HTML should still be returned
        assert "img" in html

    def test_post_process_clean_html_no_warnings(self) -> None:
        svc = AccessibilityService()
        svc._post_process(_GOOD_HTML)
        warnings = _alt_text_warnings_var.get(None)
        assert warnings == []

    def test_response_includes_alt_text_warnings(self) -> None:
        svc = AccessibilityService()
        # Set up contextvar as _post_process would
        _alt_text_warnings_var.set(["[error] test warning"])
        req = AccessibilityRequest(html="x" * 50)
        response = svc._build_response(
            request=req,
            html="<html></html>",
            qa_results=None,
            qa_passed=None,
            model_id="test-model",
            confidence=0.8,
            skills_loaded=["wcag_email_mapping"],
            raw_content="",
        )
        assert response.alt_text_warnings == ["[error] test warning"]

    def test_response_empty_warnings_when_none(self) -> None:
        svc = AccessibilityService()
        _alt_text_warnings_var.set(None)
        req = AccessibilityRequest(html="x" * 50)
        response = svc._build_response(
            request=req,
            html="<html></html>",
            qa_results=None,
            qa_passed=None,
            model_id="test-model",
            confidence=0.8,
            skills_loaded=[],
            raw_content="",
        )
        assert response.alt_text_warnings == []


# ── Blueprint Node Tests ──


class TestAccessibilityNodeHandoff:
    """Tests for alt text warnings in blueprint node AgentHandoff."""

    @pytest.mark.asyncio
    async def test_handoff_emits_alt_warnings(self) -> None:
        from app.ai.blueprints.nodes.accessibility_node import AccessibilityNode
        from app.ai.blueprints.protocols import NodeContext

        node = AccessibilityNode()

        # HTML with generic alt text → should produce warnings
        bad_html = (
            '<!DOCTYPE html><html lang="en"><head><title>Test</title></head>'
            '<body><img src="hero.jpg" alt="image" width="600"></body></html>'
        )
        llm_response_content = f"```html\n{bad_html}\n```"

        mock_response = CompletionResponse(
            content=llm_response_content,
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 200},
        )

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(return_value=mock_response)

        context = NodeContext(
            html=bad_html,
            brief="Fix accessibility",
            iteration=0,
            qa_failures=[],
            metadata={},
        )

        with (
            patch("app.ai.blueprints.nodes.accessibility_node.get_registry") as mock_reg,
            patch("app.ai.blueprints.nodes.accessibility_node.get_settings"),
            patch("app.ai.blueprints.nodes.accessibility_node.resolve_model", return_value="test"),
        ):
            mock_reg.return_value.get_llm.return_value = mock_provider
            result = await node.execute(context)

        assert result.status == "success"
        assert result.handoff is not None
        assert len(result.handoff.warnings) > 0
        assert any("generic alt text" in w for w in result.handoff.warnings)

    @pytest.mark.asyncio
    async def test_handoff_empty_warnings_clean_html(self) -> None:
        from app.ai.blueprints.nodes.accessibility_node import AccessibilityNode
        from app.ai.blueprints.protocols import NodeContext

        node = AccessibilityNode()

        clean_html = (
            '<!DOCTYPE html><html lang="en"><head><title>Test</title></head>'
            '<body><img src="hero.jpg" alt="Blue cotton t-shirt, front view" width="600">'
            '<img src="spacer.gif" alt="" width="1" height="20">'
            "</body></html>"
        )
        llm_response_content = f"```html\n{clean_html}\n```"

        mock_response = CompletionResponse(
            content=llm_response_content,
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 200},
        )

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(return_value=mock_response)

        context = NodeContext(
            html=clean_html,
            brief="Fix accessibility",
            iteration=0,
            qa_failures=[],
            metadata={},
        )

        with (
            patch("app.ai.blueprints.nodes.accessibility_node.get_registry") as mock_reg,
            patch("app.ai.blueprints.nodes.accessibility_node.get_settings"),
            patch("app.ai.blueprints.nodes.accessibility_node.resolve_model", return_value="test"),
        ):
            mock_reg.return_value.get_llm.return_value = mock_provider
            result = await node.execute(context)

        assert result.status == "success"
        assert result.handoff is not None
        assert len(result.handoff.warnings) == 0
