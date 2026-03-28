"""Unit tests for MJML markup generation from layout analysis."""

from __future__ import annotations

from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnGroup,
    ColumnLayout,
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)
from app.design_sync.mjml_generator import (
    generate_mjml,
    inject_section_markers,
)
from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedTokens,
    ExtractedTypography,
)

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    node_id: str = "s1",
    node_name: str = "Section",
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
    column_layout: ColumnLayout = ColumnLayout.SINGLE,
    column_count: int = 1,
    bg_color: str | None = None,
    padding_top: float | None = None,
    padding_right: float | None = None,
    padding_bottom: float | None = None,
    padding_left: float | None = None,
    height: float | None = None,
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
        bg_color=bg_color,
        padding_top=padding_top,
        padding_right=padding_right,
        padding_bottom=padding_bottom,
        padding_left=padding_left,
        height=height,
        column_groups=column_groups or [],
    )


def _make_tokens(
    *,
    colors: list[ExtractedColor] | None = None,
    typography: list[ExtractedTypography] | None = None,
    dark_colors: list[ExtractedColor] | None = None,
) -> ExtractedTokens:
    return ExtractedTokens(
        colors=colors
        or [
            ExtractedColor(name="Primary", hex="#333333"),
            ExtractedColor(name="Background", hex="#ffffff"),
            ExtractedColor(name="Text", hex="#000000"),
        ],
        typography=typography
        or [
            ExtractedTypography(
                name="Heading", family="Inter", weight="700", size=24.0, line_height=32.0
            ),
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ],
        dark_colors=dark_colors or [],
    )


def _make_layout(sections: list[EmailSection]) -> DesignLayoutDescription:
    return DesignLayoutDescription(file_name="Test", sections=sections)


# ---------------------------------------------------------------------------
# Tests: basic MJML generation
# ---------------------------------------------------------------------------


class TestGenerateMjmlBasic:
    def test_generate_mjml_minimal(self) -> None:
        """Single CONTENT section produces valid MJML structure."""
        section = _make_section(texts=[TextBlock(node_id="t1", content="Hello world")])
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<mjml>" in result
        assert "</mjml>" in result
        assert "<mj-body" in result
        assert "<mj-section" in result
        assert "<mj-text" in result
        assert "Hello world" in result

    def test_generate_mjml_full_layout(self) -> None:
        """HEADER+HERO+CONTENT+CTA+FOOTER produces 5 mj-section blocks."""
        sections = [
            _make_section(EmailSectionType.HEADER, node_id="h1"),
            _make_section(EmailSectionType.HERO, node_id="h2"),
            _make_section(EmailSectionType.CONTENT, node_id="c1"),
            _make_section(EmailSectionType.CTA, node_id="cta1"),
            _make_section(EmailSectionType.FOOTER, node_id="f1"),
        ]
        layout = _make_layout(sections)
        result = generate_mjml(layout, _make_tokens())

        assert result.count("<mj-section") == 5

    def test_container_width(self) -> None:
        """Custom container_width appears in mj-body."""
        section = _make_section()
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens(), container_width=700)

        assert 'width="700px"' in result


# ---------------------------------------------------------------------------
# Tests: preheader
# ---------------------------------------------------------------------------


class TestPreheader:
    def test_preheader_in_head(self) -> None:
        """PREHEADER section generates mj-preview inside mj-head, not mj-body."""
        sections = [
            _make_section(
                EmailSectionType.PREHEADER,
                node_id="ph1",
                texts=[TextBlock(node_id="t1", content="Preview text here")],
            ),
            _make_section(EmailSectionType.CONTENT, node_id="c1"),
        ]
        layout = _make_layout(sections)
        result = generate_mjml(layout, _make_tokens())

        assert "<mj-preview>" in result
        assert "Preview text here" in result
        # Preheader should be in head, not as a section
        head_end = result.find("</mj-head>")
        body_start = result.find("<mj-body")
        preview_pos = result.find("<mj-preview>")
        assert preview_pos < head_end
        assert preview_pos < body_start


# ---------------------------------------------------------------------------
# Tests: column layouts
# ---------------------------------------------------------------------------


class TestColumnLayouts:
    def test_two_column_layout(self) -> None:
        """TWO_COLUMN section produces 2 mj-column with 50% width."""
        section = _make_section(
            column_layout=ColumnLayout.TWO_COLUMN,
            column_count=2,
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert result.count('width="50%"') == 2

    def test_three_column_layout(self) -> None:
        """THREE_COLUMN section produces 3 mj-column with 33.33% width."""
        section = _make_section(
            column_layout=ColumnLayout.THREE_COLUMN,
            column_count=3,
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert result.count('width="33.33%"') == 3

    def test_multi_column_proportional(self) -> None:
        """MULTI_COLUMN with column_groups uses proportional widths."""
        groups = [
            ColumnGroup(column_idx=0, node_id="g1", node_name="Col1", width=200.0),
            ColumnGroup(column_idx=1, node_id="g2", node_name="Col2", width=400.0),
        ]
        section = _make_section(
            column_layout=ColumnLayout.MULTI_COLUMN,
            column_count=2,
            column_groups=groups,
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens(), container_width=600)

        assert 'width="33.33%"' in result
        assert 'width="66.67%"' in result


# ---------------------------------------------------------------------------
# Tests: element rendering
# ---------------------------------------------------------------------------


class TestElementRendering:
    def test_button_element(self) -> None:
        """ButtonElement produces mj-button with href and text."""
        section = _make_section(buttons=[ButtonElement(node_id="b1", text="Click Me", width=200.0)])
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<mj-button" in result
        assert "Click Me" in result
        assert 'href="#"' in result
        assert 'width="200px"' in result

    def test_image_element(self) -> None:
        """ImagePlaceholder produces mj-image with src, alt, width."""
        section = _make_section(
            images=[
                ImagePlaceholder(node_id="i1", node_name="Hero Image", width=600.0, height=300.0)
            ]
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<mj-image" in result
        assert 'alt="Hero Image"' in result
        assert 'width="600px"' in result

    def test_heading_detection(self) -> None:
        """TextBlock with is_heading=True produces heading tag with larger font."""
        section = _make_section(
            texts=[
                TextBlock(
                    node_id="t1",
                    content="Big Title",
                    font_size=36.0,
                    is_heading=True,
                    font_weight=700,
                )
            ]
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<h1>" in result
        assert "Big Title" in result
        assert 'font-size="36px"' in result
        assert 'font-weight="700"' in result

    def test_small_heading_uses_h2(self) -> None:
        """Headings with font_size < 28 use h2 tag."""
        section = _make_section(
            texts=[TextBlock(node_id="t1", content="Subheading", font_size=20.0, is_heading=True)]
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<h2>" in result


# ---------------------------------------------------------------------------
# Tests: special sections
# ---------------------------------------------------------------------------


class TestSpecialSections:
    def test_spacer_section(self) -> None:
        """SPACER section produces mj-spacer with correct height."""
        section = _make_section(EmailSectionType.SPACER, height=40.0)
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<mj-spacer" in result
        assert 'height="40px"' in result

    def test_divider_section(self) -> None:
        """DIVIDER section produces mj-divider."""
        section = _make_section(EmailSectionType.DIVIDER)
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<mj-divider" in result

    def test_footer_muted_style(self) -> None:
        """FOOTER section uses smaller font and muted color."""
        section = _make_section(
            EmailSectionType.FOOTER,
            texts=[TextBlock(node_id="t1", content="Unsubscribe")],
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert 'font-size="12px"' in result
        assert "Unsubscribe" in result

    def test_hero_background(self) -> None:
        """HERO section with background image uses background-url."""
        section = _make_section(
            EmailSectionType.HERO,
            images=[ImagePlaceholder(node_id="bg1", node_name="Hero BG", is_background=True)],
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "background-url" in result


# ---------------------------------------------------------------------------
# Tests: token injection
# ---------------------------------------------------------------------------


class TestTokenInjection:
    def test_token_injection_colors(self) -> None:
        """Palette colors appear in mj-attributes defaults."""
        tokens = _make_tokens(
            colors=[
                ExtractedColor(name="Primary", hex="#ff0000"),
                ExtractedColor(name="Background", hex="#f5f5f5"),
                ExtractedColor(name="Text", hex="#111111"),
            ]
        )
        section = _make_section()
        layout = _make_layout([section])
        result = generate_mjml(layout, tokens)

        # Button default uses primary
        assert "#ff0000" in result
        # Body background
        assert "#f5f5f5" in result

    def test_token_injection_typography(self) -> None:
        """Font family from tokens appears in mj-all defaults."""
        tokens = _make_tokens(
            typography=[
                ExtractedTypography(
                    name="Heading", family="Georgia", weight="700", size=28.0, line_height=36.0
                ),
                ExtractedTypography(
                    name="Body", family="Verdana", weight="400", size=14.0, line_height=22.0
                ),
            ]
        )
        section = _make_section()
        layout = _make_layout([section])
        result = generate_mjml(layout, tokens)

        assert "Verdana" in result

    def test_dark_mode_css(self) -> None:
        """Dark mode tokens generate prefers-color-scheme CSS in mj-style."""
        tokens = _make_tokens(
            colors=[
                ExtractedColor(name="Background", hex="#ffffff"),
                ExtractedColor(name="Text", hex="#000000"),
            ],
            dark_colors=[
                ExtractedColor(name="Background", hex="#1a1a1a"),
                ExtractedColor(name="Text", hex="#eeeeee"),
            ],
        )
        section = _make_section()
        layout = _make_layout([section])
        result = generate_mjml(layout, tokens)

        assert "prefers-color-scheme: dark" in result
        assert "#1a1a1a" in result


# ---------------------------------------------------------------------------
# Tests: security
# ---------------------------------------------------------------------------


class TestSecurity:
    def test_text_html_escaping(self) -> None:
        """Text with HTML tags is escaped in MJML output."""
        section = _make_section(
            texts=[TextBlock(node_id="t1", content="<script>alert('xss')</script>")]
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_section_padding(self) -> None:
        """Section padding fields are converted to padding attribute."""
        section = _make_section(
            padding_top=20.0, padding_right=30.0, padding_bottom=20.0, padding_left=30.0
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert 'padding="20px 30px 20px 30px"' in result


# ---------------------------------------------------------------------------
# Tests: post-processing (section markers)
# ---------------------------------------------------------------------------


class TestSectionMarkers:
    def test_inject_section_markers(self) -> None:
        """Comment markers are replaced with data-* wrapper divs."""
        compiled_html = (
            "<!-- section:s1:content -->\n"
            "<table><tr><td>Hello</td></tr></table>\n"
            "<!-- section:s2:footer -->\n"
            "<table><tr><td>Footer</td></tr></table>"
        )
        layout = _make_layout(
            [
                _make_section(EmailSectionType.CONTENT, node_id="s1"),
                _make_section(EmailSectionType.FOOTER, node_id="s2"),
            ]
        )
        result = inject_section_markers(compiled_html, layout)

        assert 'data-section-type="content"' in result
        assert 'data-node-id="s1"' in result
        assert 'data-section-type="footer"' in result
        assert 'data-node-id="s2"' in result


# -- Phase 39.1: Enriched field tests --


class TestButtonEnrichedMjml:
    """39.1: ButtonElement with url/border_radius -> correct mj-button attrs."""

    def test_button_uses_enriched_fields(self) -> None:
        btn = ButtonElement(
            node_id="b1",
            text="Shop Now",
            width=200.0,
            url="https://shop.example.com",
            border_radius=8.0,
            fill_color="#FF6600",
        )
        section = _make_section(buttons=[btn])
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())

        assert 'href="https://shop.example.com"' in result
        assert 'border-radius="8px"' in result
        assert 'background-color="#FF6600"' in result
        assert 'href="#"' not in result

    def test_button_default_href_when_no_url(self) -> None:
        """Backward compat: no url -> still gets href='#'."""
        btn = ButtonElement(node_id="b1", text="Click", width=200.0)
        section = _make_section(buttons=[btn])
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())
        assert 'href="#"' in result


class TestMjmlMeaningfulAlt:
    """38.8: MJML image alt text uses _meaningful_alt()."""

    def test_mjml_image_meaningful_alt(self) -> None:
        """ImagePlaceholder with generic name → meaningful alt, not raw name."""
        section = _make_section(
            images=[ImagePlaceholder(node_id="i1", node_name="mj-image", width=600.0, height=300.0)]
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())
        assert "<mj-image" in result
        assert 'alt="mj-image"' not in result
        assert 'alt="Email image"' in result

    def test_mjml_hero_section_background_url(self) -> None:
        """Hero section with is_background image → background-url on mj-section."""
        section = _make_section(
            section_type=EmailSectionType.HERO,
            images=[
                ImagePlaceholder(
                    node_id="bg1",
                    node_name="Hero BG",
                    width=600.0,
                    height=400.0,
                    is_background=True,
                )
            ],
            texts=[TextBlock(node_id="t1", content="Welcome", is_heading=True, font_size=32.0)],
        )
        layout = _make_layout([section])
        result = generate_mjml(layout, _make_tokens())
        assert "background-url" in result
        assert "bg1" in result
