"""Tests for MJML Jinja2 section template engine (Phase 35.4)."""

from __future__ import annotations

import pytest

from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnGroup,
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)
from app.design_sync.mjml_template_engine import (
    MjmlTemplateContext,
    MjmlTemplateEngine,
    build_template_context,
)
from app.design_sync.protocol import ExtractedColor, ExtractedTokens, ExtractedTypography
from app.projects.design_system import BrandPalette, Typography

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _palette() -> BrandPalette:
    return BrandPalette(
        primary="#333333",
        secondary="#666666",
        accent="#0066cc",
        background="#ffffff",
        text="#000000",
        link="#0000ee",
    )


def _typo() -> Typography:
    return Typography(
        heading_font="Georgia, serif",
        body_font="Arial, Helvetica, sans-serif",
        base_size="16px",
        heading_line_height="32px",
        body_line_height="24px",
    )


def _ctx(**overrides: object) -> MjmlTemplateContext:
    defaults: dict[str, object] = {
        "palette": _palette(),
        "typography": _typo(),
        "container_width": 600,
    }
    defaults.update(overrides)
    return MjmlTemplateContext(**defaults)  # type: ignore[arg-type]


def _section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    node_id: str = "f1",
    node_name: str = "Section",
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
    column_layout: ColumnLayout = ColumnLayout.SINGLE,
    column_count: int = 1,
    bg_color: str | None = None,
    height: float | None = 200,
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
        height=height,
        column_groups=column_groups or [],
    )


def _text(content: str = "Hello world", *, is_heading: bool = False) -> TextBlock:
    return TextBlock(node_id="t1", content=content, font_size=16.0, is_heading=is_heading)


def _image(
    node_id: str = "img1",
    name: str = "Hero Image",
    w: float = 560,
    h: float = 300,
    *,
    is_background: bool = False,
) -> ImagePlaceholder:
    return ImagePlaceholder(
        node_id=node_id, node_name=name, width=w, height=h, is_background=is_background
    )


def _button(text: str = "Click here") -> ButtonElement:
    return ButtonElement(node_id="btn1", text=text, width=200, height=44)


def _tokens() -> ExtractedTokens:
    return ExtractedTokens(
        colors=[
            ExtractedColor(name="Primary", hex="#333333"),
            ExtractedColor(name="Background", hex="#ffffff"),
            ExtractedColor(name="Text", hex="#000000"),
        ],
        typography=[
            ExtractedTypography(
                name="Heading", family="Georgia", weight="700", size=24.0, line_height=32.0
            ),
            ExtractedTypography(
                name="Body", family="Arial", weight="400", size=16.0, line_height=24.0
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


class TestResolveTemplateName:
    def test_hero(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.HERO, texts=[_text()])
        assert engine.resolve_template_name(s) == "hero.mjml.j2"

    def test_header(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.HEADER, images=[_image()])
        assert engine.resolve_template_name(s) == "header.mjml.j2"

    def test_cta(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.CTA, buttons=[_button()])
        assert engine.resolve_template_name(s) == "cta.mjml.j2"

    def test_footer(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.FOOTER, texts=[_text()])
        assert engine.resolve_template_name(s) == "footer.mjml.j2"

    def test_social_uses_footer_template(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.SOCIAL, texts=[_text()])
        assert engine.resolve_template_name(s) == "footer.mjml.j2"

    def test_spacer(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.SPACER)
        assert engine.resolve_template_name(s) == "spacer.mjml.j2"

    def test_divider_uses_spacer_template(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.DIVIDER)
        assert engine.resolve_template_name(s) == "spacer.mjml.j2"

    def test_content_single(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.CONTENT, texts=[_text()])
        assert engine.resolve_template_name(s) == "content_single.mjml.j2"

    def test_content_two_col(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.TWO_COLUMN,
            texts=[_text()],
        )
        assert engine.resolve_template_name(s) == "content_two_col.mjml.j2"

    def test_content_three_col(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.THREE_COLUMN,
            texts=[_text()],
        )
        assert engine.resolve_template_name(s) == "content_three_col.mjml.j2"

    def test_content_multi_col(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.MULTI_COLUMN,
            texts=[_text()],
        )
        assert engine.resolve_template_name(s) == "content_multi_col.mjml.j2"

    def test_image_only_section(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.CONTENT, images=[_image()])
        assert engine.resolve_template_name(s) == "image_full.mjml.j2"

    def test_unknown_with_text_uses_content_single(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.UNKNOWN, texts=[_text()])
        assert engine.resolve_template_name(s) == "content_single.mjml.j2"

    def test_nav_uses_header_template(self) -> None:
        engine = MjmlTemplateEngine()
        s = _section(EmailSectionType.NAV, texts=[_text()])
        assert engine.resolve_template_name(s) == "header.mjml.j2"


# ---------------------------------------------------------------------------
# Section rendering
# ---------------------------------------------------------------------------


class TestRenderSection:
    def test_hero_basic(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.HERO,
            texts=[_text("Welcome!", is_heading=True), _text("Subtext")],
            buttons=[_button("Get Started")],
            bg_color="#112233",
        )
        result = engine.render_section(s, ctx)
        assert "<mj-section" in result
        assert 'background-color="#112233"' in result
        assert "Welcome!" in result
        assert "<h1" in result
        assert "Subtext" in result
        assert "Get Started" in result
        assert "<mj-button" in result
        assert 'height="44px"' in result

    def test_hero_background_image(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.HERO,
            images=[_image("bg1", "BG", 600, 400, is_background=True)],
            texts=[_text("Over image", is_heading=True)],
        )
        result = engine.render_section(s, ctx)
        assert "background-url=" in result
        assert "background-size" in result

    def test_content_single(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.CONTENT,
            texts=[_text("Heading", is_heading=True), _text("Body copy")],
            images=[_image()],
        )
        result = engine.render_section(s, ctx)
        assert "<mj-section" in result
        assert "<h2" in result
        assert "Heading" in result
        assert "Body copy" in result
        assert "<mj-image" in result

    def test_content_two_col_with_groups(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        groups = [
            ColumnGroup(
                column_idx=0,
                node_id="g1",
                node_name="Left",
                texts=[_text("Left col")],
                images=[_image("img_l", "Left img", 270, 200)],
            ),
            ColumnGroup(
                column_idx=1,
                node_id="g2",
                node_name="Right",
                texts=[_text("Right col")],
            ),
        ]
        s = _section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.TWO_COLUMN,
            column_groups=groups,
            texts=[_text("Left col"), _text("Right col")],
        )
        result = engine.render_section(s, ctx)
        assert result.count('width="50%"') == 2
        assert "Left col" in result
        assert "Right col" in result

    def test_content_three_col_with_groups(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        groups = [
            ColumnGroup(column_idx=i, node_id=f"g{i}", node_name=f"Col {i}") for i in range(3)
        ]
        s = _section(
            EmailSectionType.CONTENT,
            column_layout=ColumnLayout.THREE_COLUMN,
            column_groups=groups,
            texts=[_text()],
        )
        result = engine.render_section(s, ctx)
        assert result.count('width="33.33%"') == 3

    def test_cta_button(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.CTA,
            texts=[_text("Ready?")],
            buttons=[_button("Buy Now")],
        )
        result = engine.render_section(s, ctx)
        assert "<mj-button" in result
        assert "Buy Now" in result
        assert 'height="44px"' in result
        assert 'align="center"' in result

    def test_header_logo(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.HEADER,
            images=[_image("logo", "Company Logo", 150, 50)],
        )
        result = engine.render_section(s, ctx)
        assert "<mj-image" in result
        assert "Company Logo" in result
        assert 'align="center"' in result

    def test_footer_text_and_links(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.FOOTER,
            texts=[_text("© 2026 Corp")],
            buttons=[_button("Unsubscribe")],
        )
        result = engine.render_section(s, ctx)
        assert "© 2026 Corp" in result
        assert "Unsubscribe" in result
        assert "<a " in result
        assert 'font-size="12px"' in result

    def test_image_full(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.CONTENT,
            images=[_image("img1", "Banner", 600, 300)],
        )
        result = engine.render_section(s, ctx)
        assert "<mj-image" in result
        assert 'fluid-on-mobile="true"' in result
        assert 'width="600px"' in result

    def test_spacer(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(EmailSectionType.SPACER, height=40)
        result = engine.render_section(s, ctx)
        assert "<mj-spacer" in result
        assert 'height="40px"' in result

    def test_divider(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(EmailSectionType.DIVIDER)
        result = engine.render_section(s, ctx)
        assert "<mj-divider" in result
        assert 'border-width="1px"' in result


# ---------------------------------------------------------------------------
# Full email rendering
# ---------------------------------------------------------------------------


class TestRenderEmail:
    def test_complete_document(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        sections = [
            _section(EmailSectionType.HEADER, images=[_image("logo", "Logo", 150, 50)]),
            _section(
                EmailSectionType.HERO,
                texts=[_text("Welcome", is_heading=True)],
                buttons=[_button("CTA")],
            ),
            _section(EmailSectionType.CONTENT, texts=[_text("Body content")]),
            _section(EmailSectionType.FOOTER, texts=[_text("© 2026")]),
        ]
        result = engine.render_email(sections, ctx)
        assert result.startswith("<mjml>")
        assert "</mjml>" in result
        assert "<mj-head>" in result
        assert "<mj-body" in result
        assert 'width="600px"' in result
        # All sections present
        assert result.count("<mj-section") == 4

    def test_preheader_in_head(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        result = engine.render_email(
            [_section(EmailSectionType.CONTENT, texts=[_text("Hi")])],
            ctx,
            preheader="Check out our deals",
        )
        assert "<mj-preview>Check out our deals</mj-preview>" in result

    def test_dark_mode_css(self) -> None:
        dark = (
            ExtractedColor(name="Background", hex="#1a1a1a"),
            ExtractedColor(name="Text", hex="#eeeeee"),
        )
        ctx = _ctx(dark_colors=dark)
        engine = MjmlTemplateEngine()
        result = engine.render_email(
            [_section(EmailSectionType.CONTENT, texts=[_text("Hi")])],
            ctx,
        )
        assert "prefers-color-scheme: dark" in result
        assert ".dark-background" in result
        assert "#1a1a1a" in result

    def test_no_dark_mode_when_empty(self) -> None:
        ctx = _ctx(dark_colors=())
        engine = MjmlTemplateEngine()
        result = engine.render_email(
            [_section(EmailSectionType.CONTENT, texts=[_text("Hi")])],
            ctx,
        )
        assert "prefers-color-scheme" not in result

    def test_section_markers_present(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(EmailSectionType.HERO, node_id="frame_42", texts=[_text("Hi")])
        result = engine.render_section(s, ctx)
        assert "<!-- section:frame_42:hero -->" in result

    def test_typography_injected(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        result = engine.render_email(
            [_section(EmailSectionType.CONTENT, texts=[_text("Hi")])],
            ctx,
        )
        assert 'font-family="Arial, Helvetica, sans-serif"' in result


# ---------------------------------------------------------------------------
# HTML escaping
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    def test_special_chars_in_text(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.CONTENT,
            texts=[_text("Tom & Jerry <script>alert(1)</script>")],
        )
        result = engine.render_section(s, ctx)
        assert "&amp;" in result
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_special_chars_in_button(self) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(
            EmailSectionType.CTA,
            buttons=[_button("Buy <em>now</em>")],
        )
        result = engine.render_section(s, ctx)
        assert "<em>" not in result
        assert "&lt;em&gt;" in result


# ---------------------------------------------------------------------------
# build_template_context
# ---------------------------------------------------------------------------


class TestBuildTemplateContext:
    def test_from_tokens(self) -> None:
        tokens = _tokens()
        ctx = build_template_context(tokens, container_width=640)
        assert ctx.container_width == 640
        assert ctx.palette.primary == "#333333"
        assert ctx.palette.background == "#ffffff"
        assert "Georgia" in ctx.typography.heading_font
        assert ctx.dark_colors == ()

    def test_dark_colors_forwarded(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Primary", hex="#333333")],
            typography=[],
            dark_colors=[ExtractedColor(name="Dark BG", hex="#1a1a1a")],
        )
        ctx = build_template_context(tokens)
        assert len(ctx.dark_colors) == 1
        assert ctx.dark_colors[0].hex == "#1a1a1a"


# ---------------------------------------------------------------------------
# Button min-height enforcement
# ---------------------------------------------------------------------------


class TestButtonMinHeight:
    @pytest.mark.parametrize(
        "section_type",
        [EmailSectionType.HERO, EmailSectionType.CTA, EmailSectionType.CONTENT],
    )
    def test_buttons_have_44px_height(self, section_type: EmailSectionType) -> None:
        engine = MjmlTemplateEngine()
        ctx = _ctx()
        s = _section(section_type, buttons=[_button("Click")])
        result = engine.render_section(s, ctx)
        if "<mj-button" in result:
            assert 'height="44px"' in result
