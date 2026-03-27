# pyright: reportPrivateUsage=false
"""Cross-module integration tests for Phase 35 components.

Verifies interactions between:
- Section cache + MJML conversion
- W3C token round-trip through pipeline
- Correction tracker diff extraction
- Section hash stability
- Visual fidelity scoring after conversion
"""

from __future__ import annotations

import io

from PIL import Image

from app.design_sync.correction_tracker import extract_correction_diffs
from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    TextBlock,
)
from app.design_sync.mjml_generator import generate_mjml
from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.section_cache import clear_section_cache, compute_section_hash
from app.design_sync.visual_scorer import FidelityScore, score_fidelity
from app.design_sync.w3c_export import export_w3c_tokens
from app.design_sync.w3c_tokens import parse_w3c_tokens

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    node_id: str = "s1",
    node_name: str = "Section",
    texts: list[TextBlock] | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=node_name,
        texts=texts or [],
        images=[],
        buttons=[],
        column_groups=[],
    )


def _make_tokens(
    *,
    colors: list[ExtractedColor] | None = None,
    dark_colors: list[ExtractedColor] | None = None,
) -> ExtractedTokens:
    return ExtractedTokens(
        colors=colors
        or [
            ExtractedColor(name="Primary", hex="#333333"),
            ExtractedColor(name="Background", hex="#ffffff"),
        ],
        dark_colors=dark_colors or [],
        typography=[
            ExtractedTypography(
                name="Body", family="Arial", weight="400", size=16.0, line_height=24.0
            ),
        ],
    )


def _make_layout(sections: list[EmailSection]) -> DesignLayoutDescription:
    return DesignLayoutDescription(file_name="Test", sections=sections)


def _make_png(width: int, height: int, *, color: int = 128) -> bytes:
    """Create a solid grayscale PNG."""
    img = Image.new("L", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Section hash stability
# ---------------------------------------------------------------------------


class TestSectionHashStability:
    def test_same_input_same_hash(self) -> None:
        """Same section + tokens + container_width → identical hash across calls."""
        section = _make_section(texts=[TextBlock(node_id="t1", content="Hello")])
        tokens = _make_tokens()

        hash1 = compute_section_hash(section, tokens, container_width=600)
        hash2 = compute_section_hash(section, tokens, container_width=600)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_tokens_different_hash(self) -> None:
        """Changed tokens → different hash."""
        section = _make_section(texts=[TextBlock(node_id="t1", content="Hello")])
        tokens_a = _make_tokens()
        tokens_b = _make_tokens(colors=[ExtractedColor(name="Primary", hex="#FF0000")])

        hash_a = compute_section_hash(section, tokens_a, container_width=600)
        hash_b = compute_section_hash(section, tokens_b, container_width=600)

        assert hash_a != hash_b

    def test_different_container_width_different_hash(self) -> None:
        """Changed container_width → different hash."""
        section = _make_section(texts=[TextBlock(node_id="t1", content="Hello")])
        tokens = _make_tokens()

        hash_600 = compute_section_hash(section, tokens, container_width=600)
        hash_700 = compute_section_hash(section, tokens, container_width=700)

        assert hash_600 != hash_700


# ---------------------------------------------------------------------------
# W3C token round-trip
# ---------------------------------------------------------------------------


class TestW3cRoundTrip:
    def test_w3c_round_trip_in_pipeline(self) -> None:
        """parse_w3c_tokens → ExtractedTokens → generate_mjml → valid output."""
        w3c_json = {
            "color": {
                "$type": "color",
                "primary": {"$value": "#0066CC"},
                "background": {"$value": "#FFFFFF"},
            },
            "typography": {
                "$type": "fontFamily",
                "body": {"$value": "Arial, sans-serif"},
            },
        }
        result = parse_w3c_tokens(w3c_json)
        tokens = result.tokens

        sections = [
            _make_section(texts=[TextBlock(node_id="t1", content="Test content")]),
        ]
        layout = _make_layout(sections)
        mjml = generate_mjml(layout, tokens)

        assert "<mjml>" in mjml
        assert "<mj-section" in mjml

    def test_w3c_export_preserves_colors(self) -> None:
        """export_w3c_tokens round-trip preserves color values."""
        tokens = _make_tokens(
            colors=[
                ExtractedColor(name="brand", hex="#FF6600"),
                ExtractedColor(name="text", hex="#222222"),
            ],
        )
        exported = export_w3c_tokens(tokens)

        assert "color" in exported
        assert "brand" in exported["color"]
        assert "#FF6600" in str(exported["color"]["brand"])


# ---------------------------------------------------------------------------
# Correction tracker integration
# ---------------------------------------------------------------------------


class TestCorrectionTrackerIntegration:
    def test_correction_tracker_records_diff(self) -> None:
        """Agent HTML change → extract_correction_diffs detects changes."""
        original = '<table><tr><td style="color: red;">Hello</td></tr></table>'
        corrected = '<table><tr><td style="color: blue;">Hello</td></tr></table>'

        diffs = extract_correction_diffs(original, corrected)
        assert len(diffs) > 0
        assert any(
            d.attribute == "style.color" and d.change_type == "property_changed" for d in diffs
        )

    def test_correction_tracker_no_diff_for_identical(self) -> None:
        """Identical HTML → no diffs extracted."""
        html = "<table><tr><td>Hello</td></tr></table>"
        diffs = extract_correction_diffs(html, html)
        assert len(diffs) == 0


# ---------------------------------------------------------------------------
# Cache clear between tests
# ---------------------------------------------------------------------------


class TestCacheClearWorks:
    def test_clear_section_cache_resets(self) -> None:
        """clear_section_cache() resets the singleton cache."""
        clear_section_cache()
        # After clearing, we should be able to get a fresh cache
        # This is a smoke test — detailed cache tests in test_section_cache.py
        section = _make_section(texts=[TextBlock(node_id="t1", content="Cache test")])
        tokens = _make_tokens()
        _hash = compute_section_hash(section, tokens, container_width=600)
        assert isinstance(_hash, str)


# ---------------------------------------------------------------------------
# Visual fidelity after conversion
# ---------------------------------------------------------------------------


class TestFidelityAfterConversion:
    def test_fidelity_scoring_with_identical_images(self) -> None:
        """score_fidelity with identical images → overall 1.0."""
        png = _make_png(100, 100, color=128)
        sections = [_make_section(node_id="s1")]
        result = score_fidelity(png, png, sections, blur_sigma=0)

        assert isinstance(result, FidelityScore)
        assert result.overall == 1.0
