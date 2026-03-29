"""Tests for component matcher — maps EmailSection to component slugs."""

from __future__ import annotations

from app.design_sync.component_matcher import (
    _build_column_fill_html,
    _is_placeholder,
    _safe_color,
    _safe_url,
    match_all,
    match_section,
)
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnGroup,
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    node_id: str = "frame_1",
    node_name: str = "Section",
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
    column_layout: ColumnLayout = ColumnLayout.SINGLE,
    column_count: int = 1,
    height: float | None = 200,
    bg_color: str | None = None,
    spacing_after: float | None = None,
    padding_top: float | None = None,
    padding_right: float | None = None,
    padding_bottom: float | None = None,
    padding_left: float | None = None,
    column_groups: list[ColumnGroup] | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=node_name,
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
        column_layout=column_layout,
        column_count=column_count,
        height=height,
        bg_color=bg_color,
        spacing_after=spacing_after,
        padding_top=padding_top,
        padding_right=padding_right,
        padding_bottom=padding_bottom,
        padding_left=padding_left,
        column_groups=column_groups or [],
    )


def _text(content: str, *, is_heading: bool = False, font_family: str | None = None) -> TextBlock:
    return TextBlock(node_id="t1", content=content, is_heading=is_heading, font_family=font_family)


def _image(
    node_id: str = "img_1", name: str = "photo", w: float = 600, h: float = 400
) -> ImagePlaceholder:
    return ImagePlaceholder(node_id=node_id, node_name=name, width=w, height=h)


def _button(text: str = "Click me") -> ButtonElement:
    return ButtonElement(node_id="btn_1", text=text)


class TestMatchSectionType:
    """Test that each EmailSectionType maps to the expected component slug."""

    def test_preheader(self) -> None:
        s = _make_section(EmailSectionType.PREHEADER, texts=[_text("Preview")])
        m = match_section(s, 0)
        assert m.component_slug == "preheader"
        assert m.confidence == 1.0

    def test_header_with_image(self) -> None:
        s = _make_section(EmailSectionType.HEADER, images=[_image()])
        m = match_section(s, 0)
        assert m.component_slug == "logo-header"

    def test_header_with_nav_text(self) -> None:
        s = _make_section(
            EmailSectionType.HEADER,
            texts=[_text("Home"), _text("About"), _text("Contact")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "email-header"

    def test_hero_with_image_and_text(self) -> None:
        s = _make_section(
            EmailSectionType.HERO,
            texts=[_text("Big Title", is_heading=True)],
            images=[_image()],
            buttons=[_button("Shop")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "hero-block"

    def test_hero_image_only(self) -> None:
        s = _make_section(EmailSectionType.HERO, images=[_image()])
        m = match_section(s, 0)
        assert m.component_slug == "full-width-image"

    def test_content_text_only(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Heading", is_heading=True), _text("Body text")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "text-block"

    def test_content_image_and_text(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True)],
            images=[_image()],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"

    def test_content_image_only(self) -> None:
        s = _make_section(EmailSectionType.CONTENT, images=[_image()])
        m = match_section(s, 0)
        assert m.component_slug == "image-block"

    def test_content_multiple_images(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            images=[_image("i1", "p1"), _image("i2", "p2")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "image-grid"

    def test_cta(self) -> None:
        s = _make_section(EmailSectionType.CTA, buttons=[_button("Buy")])
        m = match_section(s, 0)
        assert m.component_slug == "cta-button"

    def test_footer(self) -> None:
        s = _make_section(EmailSectionType.FOOTER, texts=[_text("Legal")])
        m = match_section(s, 0)
        assert m.component_slug == "email-footer"

    def test_social(self) -> None:
        s = _make_section(EmailSectionType.SOCIAL)
        m = match_section(s, 0)
        assert m.component_slug == "social-icons"

    def test_divider(self) -> None:
        s = _make_section(EmailSectionType.DIVIDER)
        m = match_section(s, 0)
        assert m.component_slug == "divider"

    def test_spacer(self) -> None:
        s = _make_section(EmailSectionType.SPACER, height=24)
        m = match_section(s, 0)
        assert m.component_slug == "spacer"

    def test_nav(self) -> None:
        s = _make_section(EmailSectionType.NAV)
        m = match_section(s, 0)
        assert m.component_slug == "navigation-bar"

    def test_unknown_with_text(self) -> None:
        s = _make_section(EmailSectionType.UNKNOWN, texts=[_text("Something")])
        m = match_section(s, 0)
        assert m.component_slug == "text-block"
        assert m.confidence < 1.0

    def test_unknown_with_image_and_text(self) -> None:
        s = _make_section(
            EmailSectionType.UNKNOWN,
            texts=[_text("Title")],
            images=[_image()],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"
        assert m.confidence < 1.0


class TestColumnLayout:
    """Test that column layouts override section type."""

    def test_two_column(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
            texts=[_text("Col 1"), _text("Col 2")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "column-layout-2"

    def test_three_column(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.THREE_COLUMN,
            column_count=3,
        )
        m = match_section(s, 0)
        assert m.component_slug == "column-layout-3"

    def test_multi_column(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.MULTI_COLUMN,
            column_count=4,
        )
        m = match_section(s, 0)
        assert m.component_slug == "column-layout-4"


class TestSlotFills:
    """Test that slot fills are extracted correctly from section content."""

    def test_hero_slot_fills(self) -> None:
        s = _make_section(
            EmailSectionType.HERO,
            texts=[_text("Big Title", is_heading=True), _text("Description")],
            images=[_image("hero_img", "Banner")],
            buttons=[_button("Shop Now")],
        )
        m = match_section(s, 0)
        fill_ids = {f.slot_id for f in m.slot_fills}
        assert "headline" in fill_ids
        assert "subtext" in fill_ids
        assert "hero_image" in fill_ids
        assert "cta_text" in fill_ids

    def test_text_block_heading_and_body(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True), _text("Body content")],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert fills_by_id["heading"].value == "Title"
        assert "Body content" in fills_by_id["body"].value

    def test_cta_button_fills(self) -> None:
        s = _make_section(EmailSectionType.CTA, buttons=[_button("Buy Now")])
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert fills_by_id["cta_text"].value == "Buy Now"
        assert fills_by_id["cta_url"].value == "#"

    def test_spacer_height_fill(self) -> None:
        s = _make_section(EmailSectionType.SPACER, height=48)
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert fills_by_id["spacer_height"].value == "48"

    def test_logo_header_image_fill(self) -> None:
        s = _make_section(EmailSectionType.HEADER, images=[_image("logo_1", "Logo", 180, 48)])
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "logo_url" in fills_by_id
        assert fills_by_id["logo_url"].attr_overrides["width"] == "180"

    def test_column_fills_distribute_texts(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
            texts=[_text("Left"), _text("Right")],
        )
        m = match_section(s, 0)
        fill_ids = {f.slot_id for f in m.slot_fills}
        assert "col_1" in fill_ids
        assert "col_2" in fill_ids


class TestTokenOverrides:
    """Test token override extraction from section properties."""

    def test_bg_color_override(self) -> None:
        s = _make_section(EmailSectionType.CONTENT, bg_color="#f5f0e8")
        m = match_section(s, 0)
        bg_overrides = [o for o in m.token_overrides if o.css_property == "background-color"]
        assert len(bg_overrides) == 1
        assert bg_overrides[0].value == "#f5f0e8"

    def test_font_family_override(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True, font_family="Georgia, serif")],
        )
        m = match_section(s, 0)
        font_overrides = [o for o in m.token_overrides if o.css_property == "font-family"]
        assert len(font_overrides) >= 1

    def test_padding_override(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            padding_top=16,
            padding_right=24,
            padding_bottom=16,
            padding_left=24,
        )
        m = match_section(s, 0)
        pad_overrides = [o for o in m.token_overrides if o.css_property == "padding"]
        assert len(pad_overrides) == 1
        assert pad_overrides[0].value == "16px 24px 16px 24px"


class TestMatchAll:
    """Test batch matching."""

    def test_matches_multiple_sections(self) -> None:
        sections = [
            _make_section(EmailSectionType.HEADER, images=[_image()]),
            _make_section(
                EmailSectionType.HERO, images=[_image()], texts=[_text("H", is_heading=True)]
            ),
            _make_section(EmailSectionType.CONTENT, texts=[_text("Body")]),
            _make_section(EmailSectionType.FOOTER),
        ]
        matches = match_all(sections)
        assert len(matches) == 4
        assert matches[0].component_slug == "logo-header"
        assert matches[1].component_slug == "hero-block"
        assert matches[2].component_slug == "text-block"
        assert matches[3].component_slug == "email-footer"

    def test_section_idx_sequential(self) -> None:
        sections = [
            _make_section(EmailSectionType.SPACER),
            _make_section(EmailSectionType.DIVIDER),
        ]
        matches = match_all(sections)
        assert matches[0].section_idx == 0
        assert matches[1].section_idx == 1

    def test_spacing_after_preserved(self) -> None:
        s = _make_section(EmailSectionType.CONTENT, texts=[_text("X")], spacing_after=24.0)
        m = match_section(s, 0)
        assert m.spacing_after == 24.0


class TestEdgeCases:
    """Test edge cases and fallbacks."""

    def test_empty_content_section_becomes_spacer(self) -> None:
        s = _make_section(EmailSectionType.CONTENT, height=50)
        m = match_section(s, 0)
        assert m.component_slug == "spacer"
        assert m.confidence < 1.0

    def test_html_escape_in_slot_fills(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("<script>alert(1)</script>", is_heading=True)],
        )
        m = match_section(s, 0)
        heading_fill = next(f for f in m.slot_fills if f.slot_id == "heading")
        assert "<script>" not in heading_fill.value
        assert "&lt;script&gt;" in heading_fill.value


class TestNavSlotFills:
    """Test navigation-bar slot fill generation."""

    def test_nav_with_buttons(self) -> None:
        """Buttons become nav links."""
        s = _make_section(
            EmailSectionType.NAV,
            buttons=[_button("Melbourne"), _button("Amsterdam"), _button("Seoul")],
            texts=[_text("Stores (LaB)", is_heading=True)],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "nav_links" in fills_by_id
        assert "Melbourne" in fills_by_id["nav_links"].value
        assert "Amsterdam" in fills_by_id["nav_links"].value
        assert "Seoul" in fills_by_id["nav_links"].value

    def test_nav_with_texts_fallback(self) -> None:
        """When no buttons, body texts become nav links."""
        s = _make_section(
            EmailSectionType.NAV,
            texts=[_text("Home"), _text("About"), _text("Contact")],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "nav_links" in fills_by_id
        assert "Home" in fills_by_id["nav_links"].value

    def test_nav_with_all_headings_fallback(self) -> None:
        """When all texts are headings, they still become nav links."""
        s = _make_section(
            EmailSectionType.NAV,
            texts=[
                _text("Man", is_heading=True),
                _text("Woman", is_heading=True),
                _text("Accessories", is_heading=True),
            ],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "nav_links" in fills_by_id
        assert "Man" in fills_by_id["nav_links"].value
        assert "Accessories" in fills_by_id["nav_links"].value

    def test_nav_empty_section(self) -> None:
        """Empty NAV section produces no fills."""
        s = _make_section(EmailSectionType.NAV)
        m = match_section(s, 0)
        assert m.slot_fills == []

    def test_nav_links_are_anchor_tags(self) -> None:
        """Nav links are rendered as <a> tags with navbar-link class."""
        s = _make_section(
            EmailSectionType.NAV,
            buttons=[_button("Products")],
        )
        m = match_section(s, 0)
        nav_fill = next(f for f in m.slot_fills if f.slot_id == "nav_links")
        assert '<a class="navbar-link"' in nav_fill.value
        assert "Products" in nav_fill.value

    def test_nav_html_escape(self) -> None:
        """Nav link text is HTML-escaped."""
        s = _make_section(
            EmailSectionType.NAV,
            buttons=[_button("A&B <Co>")],
        )
        m = match_section(s, 0)
        nav_fill = next(f for f in m.slot_fills if f.slot_id == "nav_links")
        assert "A&amp;B &lt;Co&gt;" in nav_fill.value


class TestFooterSlotFills:
    """Test email-footer slot fill generation."""

    def test_footer_with_texts(self) -> None:
        """Footer texts become footer_content with <p> tags."""
        s = _make_section(
            EmailSectionType.FOOTER,
            texts=[
                _text("Contact Us  Instagram  Facebook"),
                _text("You can unsubscribe here"),
            ],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "footer_content" in fills_by_id
        assert "<p " in fills_by_id["footer_content"].value
        assert "Contact Us" in fills_by_id["footer_content"].value
        assert "unsubscribe" in fills_by_id["footer_content"].value

    def test_footer_empty_section(self) -> None:
        """Empty FOOTER section produces no fills."""
        s = _make_section(EmailSectionType.FOOTER)
        m = match_section(s, 0)
        assert m.slot_fills == []

    def test_footer_html_escape(self) -> None:
        """Footer text is HTML-escaped."""
        s = _make_section(
            EmailSectionType.FOOTER,
            texts=[_text("© 2026 A&B Corp")],
        )
        m = match_section(s, 0)
        footer_fill = next(f for f in m.slot_fills if f.slot_id == "footer_content")
        assert "A&amp;B Corp" in footer_fill.value


class TestTinyIconHeuristic:
    """Test that content sections with only tiny icons → navigation-bar."""

    def test_tiny_icons_with_text_becomes_nav(self) -> None:
        """6 category texts + 6 tiny 20x20 icons → navigation-bar, not article-card."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                _text("Man", is_heading=True),
                _text("Woman", is_heading=True),
                _text("Accessories", is_heading=True),
            ],
            images=[
                _image("i1", "arrow", 20, 20),
                _image("i2", "arrow", 20, 20),
                _image("i3", "arrow", 20, 20),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "navigation-bar"
        assert m.confidence == 0.9

    def test_large_images_with_text_remains_article_card(self) -> None:
        """Normal-sized images + text still → article-card."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True)],
            images=[_image("i1", "photo", 300, 200)],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"

    def test_mixed_icon_sizes_two_images_becomes_image_grid(self) -> None:
        """Two images (mixed sizes) with text → image-grid (multi-candidate scoring)."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True)],
            images=[
                _image("i1", "arrow", 20, 20),
                _image("i2", "photo", 300, 200),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "image-grid"

    def test_icon_threshold_boundary(self) -> None:
        """Images exactly at 30px threshold are still icons."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Link")],
            images=[_image("i1", "icon", 30, 30)],
        )
        m = match_section(s, 0)
        assert m.component_slug == "navigation-bar"

    def test_icon_just_above_threshold(self) -> None:
        """Images at 31px are no longer icons."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title")],
            images=[_image("i1", "img", 31, 31)],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"


# ── Phase 38.6 Bug Fix Tests ──


class TestSemanticColumnHTML:
    """Bug 51: Column fills should produce structured HTML, not raw text."""

    def test_column_fill_html_has_paragraph_tags(self) -> None:
        group = ColumnGroup(
            column_idx=1,
            node_id="c1",
            node_name="Col 1",
            texts=[
                TextBlock(node_id="t1", content="Product title", is_heading=True, font_size=18.0)
            ],
        )
        result = _build_column_fill_html(group)
        assert "<h3" in result
        assert "Product title" in result
        assert "font-size:18px" in result

    def test_column_fill_html_body_text_in_p_tag(self) -> None:
        group = ColumnGroup(
            column_idx=1,
            node_id="c1",
            node_name="Col 1",
            texts=[TextBlock(node_id="t1", content="Description text")],
        )
        result = _build_column_fill_html(group)
        assert "<p " in result
        assert "Description text" in result

    def test_column_fill_html_button_as_anchor(self) -> None:
        """Bug 49: Buttons must render as <a> elements, not plain text."""
        group = ColumnGroup(
            column_idx=1,
            node_id="c1",
            node_name="Col 1",
            buttons=[ButtonElement(node_id="b1", text="SHOP NOW", fill_color="#FF5500")],
        )
        result = _build_column_fill_html(group)
        assert "<a " in result
        assert "SHOP NOW" in result
        assert "background-color:#FF5500" in result

    def test_column_fill_html_preserves_text_color(self) -> None:
        """Bug 50: Text color from design should be applied."""
        group = ColumnGroup(
            column_idx=1,
            node_id="c1",
            node_name="Col 1",
            texts=[TextBlock(node_id="t1", content="White text", text_color="#FFFFFF")],
        )
        result = _build_column_fill_html(group)
        assert "color:#FFFFFF" in result

    def test_column_fill_strips_placeholder_text(self) -> None:
        """Bug 54: Placeholder text must not appear in output."""
        group = ColumnGroup(
            column_idx=1,
            node_id="c1",
            node_name="Col 1",
            texts=[
                TextBlock(node_id="t1", content="Image caption — describe the image"),
                TextBlock(node_id="t2", content="Real content"),
            ],
        )
        result = _build_column_fill_html(group)
        assert "describe the image" not in result
        assert "Real content" in result


class TestTextColorOverrides:
    """Bug 50: Text color should propagate through token overrides."""

    def test_heading_color_override(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                TextBlock(node_id="t1", content="Title", is_heading=True, text_color="#FFFFFF"),
            ],
        )
        m = match_section(s, 0)
        color_overrides = [o for o in m.token_overrides if o.css_property == "color"]
        assert len(color_overrides) >= 1
        assert color_overrides[0].value == "#FFFFFF"

    def test_body_color_override(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                TextBlock(node_id="t1", content="Body", text_color="#AABBCC"),
            ],
        )
        m = match_section(s, 0)
        color_overrides = [o for o in m.token_overrides if o.css_property == "color"]
        assert any(o.value == "#AABBCC" for o in color_overrides)


class TestArticleCardGuard:
    """Bug 52: Sections with >2 images or column groups should NOT match article-card."""

    def test_many_images_becomes_image_gallery(self) -> None:
        """3+ images → image-gallery (not article-card or image-grid)."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title")],
            images=[_image("i1", "p1"), _image("i2", "p2"), _image("i3", "p3")],
        )
        m = match_section(s, 0)
        assert m.component_slug != "article-card"
        assert m.component_slug == "image-gallery"

    def test_column_groups_not_article_card(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title")],
            images=[_image()],
            column_groups=[
                ColumnGroup(column_idx=1, node_id="c1", node_name="Col 1"),
                ColumnGroup(column_idx=2, node_id="c2", node_name="Col 2"),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug != "article-card"


class TestMultiParagraphBody:
    """Bug 53: Multiple body texts must each get their own <p> element."""

    def test_multiple_body_paragraphs(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                _text("Heading", is_heading=True),
                _text("First paragraph"),
                _text("Second paragraph"),
            ],
        )
        m = match_section(s, 0)
        body = next(f for f in m.slot_fills if f.slot_id == "body")
        assert body.value.count("<p ") == 2
        assert "First paragraph" in body.value
        assert "Second paragraph" in body.value

    def test_article_card_multi_paragraph(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                _text("Title", is_heading=True),
                _text("Para 1"),
                _text("Para 2"),
            ],
            images=[_image()],
        )
        m = match_section(s, 0)
        body = next(f for f in m.slot_fills if f.slot_id == "body_text")
        assert body.value.count("<p ") == 2


class TestPlaceholderSuppression:
    """Bug 54: Placeholder text must be filtered out."""

    def test_placeholder_filtered_from_body(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[
                _text("Heading", is_heading=True),
                _text("Your text here"),
                _text("Real content"),
            ],
        )
        m = match_section(s, 0)
        body = next(f for f in m.slot_fills if f.slot_id == "body")
        assert "Your text here" not in body.value
        assert "Real content" in body.value

    def test_is_placeholder_detection(self) -> None:
        assert _is_placeholder("Image caption — describe the image")
        assert _is_placeholder("Lorem ipsum dolor sit amet")
        assert _is_placeholder("Add your text here")
        assert not _is_placeholder("SHOP THE COLLECTION")
        assert not _is_placeholder("Eiger Nordwand Jacket")


class TestButtonInTextBlock:
    """Bug 49: Buttons in text-block sections should render as CTA HTML."""

    def test_text_block_with_button(self) -> None:
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Heading", is_heading=True), _text("Body text")],
            buttons=[ButtonElement(node_id="b1", text="Shop Now", fill_color="#0066cc")],
        )
        m = match_section(s, 0)
        body = next(f for f in m.slot_fills if f.slot_id == "body")
        assert "<a " in body.value
        assert "Shop Now" in body.value
        assert "background-color:#0066cc" in body.value


class TestURLValidation:
    """Bug 59: Button URLs must be validated."""

    def test_safe_url_allows_http(self) -> None:
        assert _safe_url("https://example.com") == "https://example.com"

    def test_safe_url_blocks_javascript(self) -> None:
        assert _safe_url("javascript:alert(1)") == "#"

    def test_safe_url_allows_relative(self) -> None:
        assert _safe_url("/path/to/page") == "/path/to/page"

    def test_safe_url_none_returns_hash(self) -> None:
        assert _safe_url(None) == "#"


class TestColorValidation:
    """Security: Color values must be validated hex."""

    def test_safe_color_valid_hex(self) -> None:
        assert _safe_color("#FF5500") == "#FF5500"
        assert _safe_color("#abc") == "#abc"

    def test_safe_color_rejects_injection(self) -> None:
        assert _safe_color("#333;position:fixed") == "#333333"

    def test_safe_color_none_returns_fallback(self) -> None:
        assert _safe_color(None) == "#333333"
        assert _safe_color(None, "#0066cc") == "#0066cc"


# ── Phase 39.6: Multi-Candidate Scoring Tests ──


class TestMultiCandidateScoring:
    """Verify multi-candidate scoring selects the correct component."""

    def test_product_grid_detection(self) -> None:
        """2+ column groups with image + text → product-grid."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title A"), _text("Title B")],
            images=[_image("i1", "p1"), _image("i2", "p2")],
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Col 1",
                    texts=[TextBlock(node_id="t1", content="Title A", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i1", node_name="p1")],
                ),
                ColumnGroup(
                    column_idx=2,
                    node_id="c2",
                    node_name="Col 2",
                    texts=[TextBlock(node_id="t2", content="Title B", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i2", node_name="p2")],
                ),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "product-grid"
        assert m.confidence == 0.95

    def test_product_grid_over_article_card(self) -> None:
        """Product grid (0.95) beats article-card (0.9) for mixed column content."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Prod A", is_heading=True), _text("Prod B", is_heading=True)],
            images=[_image("i1", "p1"), _image("i2", "p2")],
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Col 1",
                    texts=[TextBlock(node_id="t1", content="Prod A", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i1", node_name="p1")],
                ),
                ColumnGroup(
                    column_idx=2,
                    node_id="c2",
                    node_name="Col 2",
                    texts=[TextBlock(node_id="t2", content="Prod B", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i2", node_name="p2")],
                ),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "product-grid"
        assert m.component_slug != "article-card"

    def test_image_grid_two_images(self) -> None:
        """Exactly 2 images with ≤1 text → image-grid."""
        s = _make_section(
            EmailSectionType.CONTENT,
            images=[_image("i1", "p1"), _image("i2", "p2")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "image-grid"
        assert m.confidence == 0.85

    def test_image_gallery_three_plus(self) -> None:
        """3+ images with no text → image-gallery."""
        s = _make_section(
            EmailSectionType.CONTENT,
            images=[_image("i1", "a"), _image("i2", "b"), _image("i3", "c")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "image-gallery"
        assert m.confidence == 0.88

    def test_article_card_single_image_text(self) -> None:
        """1 image + text, single column → article-card at 0.9."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Heading", is_heading=True), _text("Body text")],
            images=[_image()],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"
        assert m.confidence == 0.9

    def test_category_nav_short_texts(self) -> None:
        """3+ short texts (<20 chars) → category-nav."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Shoes"), _text("Bags"), _text("Watches"), _text("Hats")],
        )
        m = match_section(s, 0)
        assert m.component_slug == "category-nav"
        assert m.confidence == 0.7

    def test_fallback_to_text_block(self) -> None:
        """Empty content section falls back to spacer at 0.5."""
        s = _make_section(EmailSectionType.CONTENT)
        m = match_section(s, 0)
        assert m.component_slug == "spacer"
        assert m.confidence == 0.5

    def test_icon_nav_still_works(self) -> None:
        """Tiny icons + text → navigation-bar at 0.9."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Home"), _text("About")],
            images=[
                _image("i1", "icon1", 20, 20),
                _image("i2", "icon2", 20, 20),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "navigation-bar"
        assert m.confidence == 0.9


class TestSpatialColumnAssignment:
    """Column groups are used for column assignment when present."""

    def test_column_groups_fill_by_index(self) -> None:
        """Column groups fill col_1, col_2 by column_idx."""
        s = _make_section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Left",
                    texts=[TextBlock(node_id="t1", content="Left content")],
                ),
                ColumnGroup(
                    column_idx=2,
                    node_id="c2",
                    node_name="Right",
                    texts=[TextBlock(node_id="t2", content="Right content")],
                ),
            ],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "col_1" in fills_by_id
        assert "col_2" in fills_by_id
        assert "Left content" in fills_by_id["col_1"].value
        assert "Right content" in fills_by_id["col_2"].value

    def test_column_groups_preferred_over_roundrobin(self) -> None:
        """When column_groups exist, they are used instead of round-robin."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("A"), _text("B"), _text("C")],
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Left",
                    texts=[
                        TextBlock(node_id="t1", content="A"),
                        TextBlock(node_id="t2", content="B"),
                    ],
                ),
                ColumnGroup(
                    column_idx=2,
                    node_id="c2",
                    node_name="Right",
                    texts=[TextBlock(node_id="t3", content="C")],
                ),
            ],
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        # Both A and B in col_1 (not round-robin A→1, B→2, C→1)
        assert "A" in fills_by_id["col_1"].value
        assert "B" in fills_by_id["col_1"].value
        assert "C" in fills_by_id["col_2"].value

    def test_roundrobin_fallback_without_groups(self) -> None:
        """Without column_groups, round-robin distributes texts."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("A"), _text("B")],
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
        )
        m = match_section(s, 0)
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "col_1" in fills_by_id
        assert "col_2" in fills_by_id

    def test_single_group_no_column_fills(self) -> None:
        """Single column_group with mixed content still gets article-card."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True)],
            images=[_image()],
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Col 1",
                    texts=[TextBlock(node_id="t1", content="Title", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i1", node_name="img")],
                ),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "article-card"


class TestSlotValidation:
    """Slot fill rate validation."""

    def test_full_fill_rate(self) -> None:
        from app.design_sync.component_matcher import SlotFill
        from app.design_sync.component_renderer import _validate_slot_fill_rate

        html = '<td data-slot="a">X</td><td data-slot="b">Y</td>'
        fills = [SlotFill("a", "val1"), SlotFill("b", "val2")]
        rate, warnings = _validate_slot_fill_rate(html, fills)
        assert rate == 1.0
        assert not warnings

    def test_low_fill_rate_warning(self) -> None:
        from app.design_sync.component_matcher import SlotFill
        from app.design_sync.component_renderer import _validate_slot_fill_rate

        html = '<td data-slot="a">X</td><td data-slot="b">Y</td><td data-slot="c">Z</td>'
        fills = [SlotFill("a", "val1")]
        rate, warnings = _validate_slot_fill_rate(html, fills)
        assert rate < 0.5
        assert len(warnings) == 1
        assert "Low slot fill rate" in warnings[0]

    def test_no_slots_template(self) -> None:
        from app.design_sync.component_renderer import _validate_slot_fill_rate

        html = "<table><tr><td>No slots here</td></tr></table>"
        rate, warnings = _validate_slot_fill_rate(html, [])
        assert rate == 1.0
        assert not warnings


class TestConfidenceInResult:
    """Confidence scores propagated through the pipeline."""

    def test_confidence_in_component_match(self) -> None:
        """Match carries the correct confidence from scoring."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Heading", is_heading=True)],
            images=[_image()],
        )
        m = match_section(s, 0)
        assert isinstance(m.confidence, float)
        assert 0.0 < m.confidence <= 1.0

    def test_confidence_varies_by_type(self) -> None:
        """Different component types get different confidence scores."""
        s_article = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("Title", is_heading=True)],
            images=[_image()],
        )
        s_grid = _make_section(
            EmailSectionType.CONTENT,
            images=[_image("i1", "a"), _image("i2", "b")],
        )
        m_article = match_section(s_article, 0)
        m_grid = match_section(s_grid, 1)
        # Article-card and image-grid have different confidence values
        assert m_article.confidence != m_grid.confidence


class TestNewComponentSlotFills:
    """Slot fills for new component types."""

    def test_product_grid_slot_fills(self) -> None:
        """Product grid fills per-group slots: product_1_title, product_2_title, etc."""
        s = _make_section(
            EmailSectionType.CONTENT,
            texts=[_text("A"), _text("B")],
            images=[_image("i1", "p1"), _image("i2", "p2")],
            column_groups=[
                ColumnGroup(
                    column_idx=1,
                    node_id="c1",
                    node_name="Col 1",
                    texts=[TextBlock(node_id="t1", content="Product A", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i1", node_name="p1")],
                ),
                ColumnGroup(
                    column_idx=2,
                    node_id="c2",
                    node_name="Col 2",
                    texts=[TextBlock(node_id="t2", content="Product B", is_heading=True)],
                    images=[ImagePlaceholder(node_id="i2", node_name="p2")],
                ),
            ],
        )
        m = match_section(s, 0)
        assert m.component_slug == "product-grid"
        fills_by_id = {f.slot_id: f for f in m.slot_fills}
        assert "product_1_title" in fills_by_id
        assert "product_2_title" in fills_by_id
        assert fills_by_id["product_1_title"].value == "Product A"
        assert fills_by_id["product_2_title"].value == "Product B"
