"""Tests for adjacent-section background color propagation (Phase 41.2)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from app.design_sync.bgcolor_propagator import (
    _build_part_index,
    _inject_bgcolor,
    propagate_adjacent_bgcolor,
)
from app.design_sync.component_matcher import ComponentMatch
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_solid_png(w: int, h: int, rgb: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (w, h), rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_noisy_png(w: int, h: int, seed: int = 42) -> bytes:
    import numpy as np

    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    node_id: str = "1:1",
    images: list[ImagePlaceholder] | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=f"Section-{node_id}",
        images=images or [],
    )


def _make_match(
    idx: int,
    slug: str,
    section: EmailSection | None = None,
) -> ComponentMatch:
    sec = section or _make_section()
    return ComponentMatch(
        section_idx=idx,
        section=sec,
        component_slug=slug,
        slot_fills=[],
        token_overrides=[],
    )


def _image(node_id: str = "img:1") -> ImagePlaceholder:
    return ImagePlaceholder(node_id=node_id, node_name="image")


# Minimal section HTML with a <table> wrapper
_SECTION_HTML = '<table role="presentation" width="600"><tr><td>Content</td></tr></table>'
_SECTION_HTML_WITH_BGCOLOR = (
    '<table bgcolor="#FFFFFF" role="presentation"><tr><td>X</td></tr></table>'
)

# MSO spacer (same format as converter_service.py)
_SPACER_HTML = (
    '<!--[if mso]>\n<table role="presentation" width="600" align="center" '
    'cellpadding="0" cellspacing="0" border="0"><tr>'
    '<td height="20" style="font-size:0;line-height:0;'
    'mso-line-height-rule:exactly;">&nbsp;</td></tr></table>\n'
    "<![endif]-->\n"
    "<!--[if !mso]><!-->\n"
    '<div style="height:20px;line-height:20px;font-size:1px;'
    'mso-line-height-rule:exactly;">&nbsp;</div>\n'
    "<!--<![endif]-->"
)


# ---------------------------------------------------------------------------
# Tests: propagate_adjacent_bgcolor
# ---------------------------------------------------------------------------


class TestPropagateAdjacentBgcolor:
    def test_image_above_text_propagates_bottom_edge(self, tmp_path: Path) -> None:
        """Full-width-image followed by text-block → bgcolor from bottom edge."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (2, 82, 181)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        text_match = _make_match(1, "text-block")

        parts = [_SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        assert result[0] == _SECTION_HTML  # image section unchanged
        assert 'bgcolor="#0252B5"' in result[1]  # text section got bgcolor

    def test_text_above_image_propagates_top_edge(self, tmp_path: Path) -> None:
        """Text-block followed by full-width-image → bgcolor from top edge."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (232, 93, 38)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        text_match = _make_match(0, "text-block")
        img_match = _make_match(1, "full-width-image", img_section)

        parts = [_SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [text_match, img_match],
            parts,
            image_dir=tmp_path,
        )

        assert 'bgcolor="#E85D26"' in result[0]  # text section got bgcolor
        assert result[1] == _SECTION_HTML  # image section unchanged

    def test_noisy_image_no_propagation(self, tmp_path: Path) -> None:
        """Photographic/noisy edge → no bgcolor propagated."""
        (tmp_path / "img_1.png").write_bytes(_make_noisy_png(200, 200))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        text_match = _make_match(1, "heading-block")

        parts = [_SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        assert result == parts  # no changes

    def test_non_adjacent_no_propagation(self, tmp_path: Path) -> None:
        """Image with a divider between text → no propagation."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (255, 0, 0)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        divider_match = _make_match(1, "divider")
        text_match = _make_match(2, "text-block")

        parts = [_SECTION_HTML, _SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, divider_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        # Divider is not text-like, text is not adjacent to image
        assert result == parts

    def test_existing_bgcolor_preserved(self, tmp_path: Path) -> None:
        """Section with existing bgcolor attribute is not overwritten."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (255, 0, 0)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        text_match = _make_match(1, "text-block")

        parts = [_SECTION_HTML, _SECTION_HTML_WITH_BGCOLOR]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        assert 'bgcolor="#FFFFFF"' in result[1]  # original preserved
        assert 'bgcolor="#FF0000"' not in result[1]

    def test_no_connection_id_no_image_dir(self) -> None:
        """Without connection_id or image_dir, returns parts unchanged."""
        img_match = _make_match(0, "full-width-image")
        text_match = _make_match(1, "text-block")

        parts = [_SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
        )

        assert result == parts

    def test_single_section_no_propagation(self) -> None:
        """Single section → no pairs to check."""
        match = _make_match(0, "full-width-image")
        parts = [_SECTION_HTML]
        result = propagate_adjacent_bgcolor([match], parts, image_dir=Path("/tmp"))
        assert result == parts

    def test_multiple_adjacent_pairs(self, tmp_path: Path) -> None:
        """Two independent image→text pairs both get propagated."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (0, 0, 255)))
        (tmp_path / "img_2.png").write_bytes(_make_solid_png(100, 50, (255, 128, 0)))

        img1 = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img2 = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:2",
            images=[_image("img:2")],
        )
        matches = [
            _make_match(0, "full-width-image", img1),
            _make_match(1, "text-block"),
            _make_match(2, "full-width-image", img2),
            _make_match(3, "cta-button"),
        ]

        parts = [_SECTION_HTML, _SECTION_HTML, _SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(matches, parts, image_dir=tmp_path)

        assert 'bgcolor="#0000FF"' in result[1]
        assert 'bgcolor="#FF8000"' in result[3]
        assert result[0] == _SECTION_HTML  # image sections unchanged
        assert result[2] == _SECTION_HTML

    def test_spacer_interleaving(self, tmp_path: Path) -> None:
        """Spacers between sections don't confuse part index mapping."""
        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (0, 255, 0)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        text_match = _make_match(1, "text-block")

        # Parts with spacer interleaved: [img_html, spacer, text_html]
        parts = [_SECTION_HTML, _SPACER_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        assert result[0] == _SECTION_HTML  # image unchanged
        assert result[1] == _SPACER_HTML  # spacer unchanged
        assert 'bgcolor="#00FF00"' in result[2]  # text got bgcolor

    def test_all_text_like_slugs_accepted(self, tmp_path: Path) -> None:
        """All text-like slugs receive propagation."""
        from app.design_sync.bgcolor_propagator import _TEXT_LIKE_SLUGS

        (tmp_path / "img_1.png").write_bytes(_make_solid_png(100, 50, (128, 0, 128)))

        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )

        for slug in _TEXT_LIKE_SLUGS:
            img_match = _make_match(0, "full-width-image", img_section)
            text_match = _make_match(1, slug)
            parts = [_SECTION_HTML, _SECTION_HTML]
            result = propagate_adjacent_bgcolor(
                [img_match, text_match],
                parts,
                image_dir=tmp_path,
            )
            assert 'bgcolor="#800080"' in result[1], f"Slug {slug!r} not propagated"

    def test_missing_image_file_no_propagation(self, tmp_path: Path) -> None:
        """Image section with no local file → no propagation."""
        # Don't write any image file
        img_section = _make_section(
            section_type=EmailSectionType.HERO,
            node_id="img:1",
            images=[_image("img:1")],
        )
        img_match = _make_match(0, "full-width-image", img_section)
        text_match = _make_match(1, "text-block")

        parts = [_SECTION_HTML, _SECTION_HTML]
        result = propagate_adjacent_bgcolor(
            [img_match, text_match],
            parts,
            image_dir=tmp_path,
        )

        assert result == parts


# ---------------------------------------------------------------------------
# Tests: _inject_bgcolor (unit)
# ---------------------------------------------------------------------------


class TestInjectBgcolor:
    def test_injects_on_first_table(self) -> None:
        html = '<table role="presentation"><tr><td>X</td></tr></table>'
        result = _inject_bgcolor(html, "#FF0000")
        assert result.startswith('<table bgcolor="#FF0000"')

    def test_skips_existing_bgcolor(self) -> None:
        html = '<table bgcolor="#FFFFFF"><tr><td>X</td></tr></table>'
        result = _inject_bgcolor(html, "#FF0000")
        assert 'bgcolor="#FFFFFF"' in result
        assert 'bgcolor="#FF0000"' not in result

    def test_only_first_table(self) -> None:
        html = "<table><tr><td><table><tr><td>inner</td></tr></table></td></tr></table>"
        result = _inject_bgcolor(html, "#00FF00")
        assert result.count('bgcolor="#00FF00"') == 1

    def test_no_table(self) -> None:
        html = "<div>no table here</div>"
        result = _inject_bgcolor(html, "#FF0000")
        assert result == html


# ---------------------------------------------------------------------------
# Tests: _build_part_index (unit)
# ---------------------------------------------------------------------------


class TestBuildPartIndex:
    def test_no_spacers(self) -> None:
        matches = [_make_match(0, "a"), _make_match(1, "b")]
        parts = ["<table>section0</table>", "<table>section1</table>"]
        index = _build_part_index(matches, parts)
        assert index == {0: 0, 1: 1}

    def test_with_spacers(self) -> None:
        matches = [_make_match(0, "a"), _make_match(1, "b")]
        parts = ["<table>s0</table>", _SPACER_HTML, "<table>s1</table>"]
        index = _build_part_index(matches, parts)
        assert index == {0: 0, 1: 2}

    def test_multiple_spacers(self) -> None:
        matches = [_make_match(0, "a"), _make_match(1, "b"), _make_match(2, "c")]
        parts = [
            "<table>s0</table>",
            _SPACER_HTML,
            "<table>s1</table>",
            _SPACER_HTML,
            "<table>s2</table>",
        ]
        index = _build_part_index(matches, parts)
        assert index == {0: 0, 1: 2, 2: 4}
