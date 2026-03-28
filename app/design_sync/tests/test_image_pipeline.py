"""Tests for image asset pipeline in design sync converter (Phase 33.10, 38.8)."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

from dataclasses import replace

from app.design_sync.converter import _meaningful_alt, node_to_email_html
from app.design_sync.converter_service import ConversionResult
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    TextBlock,
)
from app.design_sync.import_service import DesignImportService
from app.design_sync.protocol import DesignNode, DesignNodeType


class TestImageNodeResponsiveStyles:
    """IMAGE node emits correct HTML attributes and responsive styles."""

    def test_image_has_max_width(self) -> None:
        node = DesignNode(id="img1", name="Hero", type=DesignNodeType.IMAGE, width=600, height=400)
        html = node_to_email_html(node)
        assert "max-width:600px" in html

    def test_image_has_display_block(self) -> None:
        node = DesignNode(id="img1", name="Hero", type=DesignNodeType.IMAGE, width=600, height=400)
        html = node_to_email_html(node)
        assert "display:block" in html

    def test_image_has_width_100_percent(self) -> None:
        node = DesignNode(id="img1", name="Hero", type=DesignNodeType.IMAGE, width=600, height=400)
        html = node_to_email_html(node)
        assert "width:100%" in html
        assert "height:auto" in html

    def test_image_has_html_dimension_attrs(self) -> None:
        node = DesignNode(id="img1", name="Hero", type=DesignNodeType.IMAGE, width=600, height=400)
        html = node_to_email_html(node)
        assert 'width="600"' in html
        assert 'height="400"' in html

    def test_image_has_data_node_id(self) -> None:
        node = DesignNode(id="1:23", name="Logo", type=DesignNodeType.IMAGE, width=200, height=50)
        html = node_to_email_html(node)
        assert 'data-node-id="1:23"' in html

    def test_image_has_alt_text(self) -> None:
        node = DesignNode(
            id="img1", name="Company Logo", type=DesignNodeType.IMAGE, width=200, height=50
        )
        html = node_to_email_html(node)
        assert 'alt="Company Logo"' in html

    def test_image_without_dimensions_no_max_width(self) -> None:
        node = DesignNode(id="img2", name="Icon", type=DesignNodeType.IMAGE)
        html = node_to_email_html(node)
        assert 'src=""' in html
        assert "max-width:" not in html

    def test_image_alt_text_escapes_html(self) -> None:
        node = DesignNode(
            id="img3",
            name='Hero "banner" <1>',
            type=DesignNodeType.IMAGE,
            width=300,
            height=200,
        )
        html = node_to_email_html(node)
        assert "<1>" not in html  # angle brackets escaped
        assert "img" in html

    def test_image_has_mso_bicubic(self) -> None:
        node = DesignNode(id="img1", name="Photo", type=DesignNodeType.IMAGE, width=600, height=300)
        html = node_to_email_html(node)
        assert "-ms-interpolation-mode:bicubic" in html


class TestMeaningfulAlt:
    """38.8: _meaningful_alt() produces accessible alt text with smart fallbacks."""

    def test_strips_mj_prefix(self) -> None:
        """'mj-image' → generic layer name after stripping → 'Email image'."""
        assert _meaningful_alt("mj-image") == "Email image"

    def test_strips_figma_prefix(self) -> None:
        """'figma-hero' → 'hero' is not generic → preserved."""
        assert _meaningful_alt("figma-hero") == "hero"

    def test_uses_clean_name(self) -> None:
        """Meaningful name preserved as-is."""
        assert _meaningful_alt("Hero Banner") == "Hero Banner"

    def test_falls_back_to_heading(self) -> None:
        """Generic name + section with heading → heading content as alt."""
        section = EmailSection(
            section_type=EmailSectionType.CONTENT,
            node_id="s1",
            node_name="Section",
            texts=[TextBlock(node_id="t1", content="Summer Sale Preview", is_heading=True)],
            images=[],
            buttons=[],
        )
        assert _meaningful_alt("image", section=section) == "Summer Sale Preview"

    def test_falls_back_to_section_type(self) -> None:
        """Generic name + section with no heading → section type label."""
        section = EmailSection(
            section_type=EmailSectionType.HERO,
            node_id="s1",
            node_name="Section",
            texts=[],
            images=[],
            buttons=[],
        )
        assert _meaningful_alt("image", section=section) == "Hero image"

    def test_escapes_html_in_name(self) -> None:
        """HTML characters in name → escaped in alt."""
        assert _meaningful_alt("Sale <50% off>") == "Sale &lt;50% off&gt;"

    def test_none_name_returns_fallback(self) -> None:
        """None name → 'Email image' default."""
        assert _meaningful_alt(None) == "Email image"


class TestFillImageUrls:
    """_fill_image_urls() rewrites src attributes correctly."""

    def test_fills_matching_node_ids(self) -> None:
        html = '<img src="" data-node-id="1:2" width="600" /><img src="" data-node-id="3:4" />'
        urls = {
            "1:2": "/api/v1/design-sync/assets/42/1_2.png",
            "3:4": "/api/v1/design-sync/assets/42/3_4.png",
        }
        result = DesignImportService._fill_image_urls(html, urls)
        assert 'src="/api/v1/design-sync/assets/42/1_2.png"' in result
        assert 'src="/api/v1/design-sync/assets/42/3_4.png"' in result
        assert 'src=""' not in result

    def test_leaves_unmatched_nodes_empty(self) -> None:
        html = '<img src="" data-node-id="1:2" /><img src="" data-node-id="5:6" />'
        urls = {"1:2": "/api/v1/design-sync/assets/42/1_2.png"}
        result = DesignImportService._fill_image_urls(html, urls)
        assert 'src="/api/v1/design-sync/assets/42/1_2.png"' in result
        assert 'src=""' in result  # 5:6 not filled

    def test_empty_mapping_returns_unchanged(self) -> None:
        html = '<img src="" data-node-id="1:2" />'
        result = DesignImportService._fill_image_urls(html, {})
        assert result == html

    def test_no_img_tags_returns_unchanged(self) -> None:
        html = "<table><tr><td>No images</td></tr></table>"
        result = DesignImportService._fill_image_urls(html, {"1:2": "/url"})
        assert result == html


class TestConversionResultImages:
    """ConversionResult carries image metadata."""

    def test_default_empty_images(self) -> None:
        result = ConversionResult(html="<table></table>", sections_count=1)
        assert result.images == []

    def test_images_via_replace(self) -> None:
        """Frozen dataclass requires replace() for mutation."""
        result = ConversionResult(html="<table></table>", sections_count=1)
        updated = replace(
            result,
            images=[{"node_id": "1:2", "filename": "1_2.png", "hub_url": "/assets/1/1_2.png"}],
        )
        assert len(updated.images) == 1
        assert updated.images[0]["node_id"] == "1:2"
        assert updated.images[0]["hub_url"] == "/assets/1/1_2.png"
        # Original unchanged
        assert result.images == []

    def test_images_in_constructor(self) -> None:
        result = ConversionResult(
            html="<table></table>",
            sections_count=1,
            images=[
                {"node_id": "1:2", "filename": "1_2.png", "hub_url": "/assets/1/1_2.png"},
                {"node_id": "3:4", "filename": "3_4.png", "hub_url": "/assets/1/3_4.png"},
            ],
        )
        assert len(result.images) == 2
