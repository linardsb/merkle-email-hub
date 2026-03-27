"""Match layout-analyzed EmailSections to pre-built component slugs and extract slot fills."""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from app.design_sync.figma.layout_analyzer import (
    ColumnGroup,
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    TextBlock,
)


@dataclass(frozen=True)
class SlotFill:
    """A value to inject into a component template slot."""

    slot_id: str
    value: str
    slot_type: str = "text"  # "text" | "image" | "cta" | "attr"
    attr_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TokenOverride:
    """A design token override for inline style replacement."""

    css_property: str
    target_class: str  # CSS class on the target element (e.g. "textblock-heading")
    value: str


@dataclass(frozen=True)
class ComponentMatch:
    """Result of matching an EmailSection to a component template."""

    section_idx: int
    section: EmailSection
    component_slug: str
    slot_fills: list[SlotFill]
    token_overrides: list[TokenOverride]
    spacing_after: float | None = None
    confidence: float = 1.0
    mjml_template: str | None = None


def match_section(
    section: EmailSection,
    idx: int,
    *,
    container_width: int = 600,
    image_urls: dict[str, str] | None = None,
) -> ComponentMatch:
    """Match a single EmailSection to a component slug with slot fills."""
    # Column layouts override section type for CONTENT sections
    if section.column_layout != ColumnLayout.SINGLE:
        slug = _match_column_layout(section)
        fills = _build_column_fills(section, image_urls=image_urls)
        overrides = _build_token_overrides(section)
        return ComponentMatch(
            section_idx=idx,
            section=section,
            component_slug=slug,
            slot_fills=fills,
            token_overrides=overrides,
            spacing_after=section.spacing_after,
        )

    slug, confidence = _match_by_type(section)
    fills = _build_slot_fills(slug, section, container_width, image_urls=image_urls)
    overrides = _build_token_overrides(section)

    return ComponentMatch(
        section_idx=idx,
        section=section,
        component_slug=slug,
        slot_fills=fills,
        token_overrides=overrides,
        spacing_after=section.spacing_after,
        confidence=confidence,
    )


def match_all(
    sections: list[EmailSection],
    *,
    container_width: int = 600,
    image_urls: dict[str, str] | None = None,
) -> list[ComponentMatch]:
    """Match all sections in order."""
    return [
        match_section(
            section,
            idx,
            container_width=container_width,
            image_urls=image_urls,
        )
        for idx, section in enumerate(sections)
    ]


# ── Private helpers ──


def _match_column_layout(section: EmailSection) -> str:
    """Map ColumnLayout to a column component slug."""
    mapping = {
        ColumnLayout.TWO_COLUMN: "column-layout-2",
        ColumnLayout.THREE_COLUMN: "column-layout-3",
        ColumnLayout.MULTI_COLUMN: "column-layout-4",
    }
    return mapping.get(section.column_layout, "column-layout-2")


def _match_by_type(section: EmailSection) -> tuple[str, float]:
    """Map EmailSectionType to component slug + confidence."""
    st = section.section_type
    has_images = bool(section.images)
    has_texts = bool(section.texts)
    has_buttons = bool(section.buttons)
    has_headings = any(t.is_heading for t in section.texts)

    if st == EmailSectionType.PREHEADER:
        return "preheader", 1.0

    if st == EmailSectionType.HEADER:
        if has_images:
            return "logo-header", 1.0
        if len(section.texts) > 2:
            return "email-header", 1.0
        return "email-header", 0.9

    if st == EmailSectionType.HERO:
        if has_images and (has_texts or has_buttons):
            return "hero-block", 1.0
        if has_images:
            return "full-width-image", 1.0
        return "hero-block", 0.8

    if st == EmailSectionType.CONTENT:
        return _match_content(section, has_images, has_texts, has_buttons, has_headings)

    if st == EmailSectionType.CTA:
        return "cta-button", 1.0

    if st == EmailSectionType.FOOTER:
        return "email-footer", 1.0

    if st == EmailSectionType.SOCIAL:
        return "social-icons", 1.0

    if st == EmailSectionType.DIVIDER:
        return "divider", 1.0

    if st == EmailSectionType.SPACER:
        return "spacer", 1.0

    if st == EmailSectionType.NAV:
        return "navigation-bar", 1.0

    # UNKNOWN fallback
    if has_images and has_texts:
        return "article-card", 0.7
    if has_images:
        return "image-block", 0.7
    return "text-block", 0.7


def _all_images_are_icons(section: EmailSection, threshold: float = 30.0) -> bool:
    """Check if all images in a section are tiny icons (≤ threshold px)."""
    if not section.images:
        return False
    return all(
        (img.width is not None and img.width <= threshold)
        and (img.height is not None and img.height <= threshold)
        for img in section.images
    )


def _match_content(
    section: EmailSection,
    has_images: bool,
    has_texts: bool,
    has_buttons: bool,
    has_headings: bool,
) -> tuple[str, float]:
    """Determine the best component for a CONTENT section."""
    if has_images and has_texts:
        # Tiny icons paired with text = link list / nav, not a real image card
        if _all_images_are_icons(section):
            return "navigation-bar", 0.9
        # Image + text + optional CTA = article card
        return "article-card", 1.0
    if has_images and len(section.images) >= 2:
        return "image-grid", 0.9
    if has_images:
        return "image-block", 1.0
    if has_headings and has_buttons:
        # Heading + body + CTA = text-block (CTA appended)
        return "text-block", 1.0
    if has_texts:
        return "text-block", 1.0
    # Empty content section — treat as spacer
    return "spacer", 0.5


def _build_slot_fills(
    slug: str,
    section: EmailSection,
    container_width: int,
    *,
    image_urls: dict[str, str] | None = None,
) -> list[SlotFill]:
    """Build slot fills for a given component slug from section content."""
    builders: dict[str, _SlotBuilder] = {
        "preheader": _fills_preheader,
        "email-header": _fills_email_header,
        "logo-header": _fills_logo_header,
        "hero-block": _fills_hero,
        "full-width-image": _fills_full_width_image,
        "text-block": _fills_text_block,
        "article-card": _fills_article_card,
        "image-block": _fills_image_block,
        "image-grid": _fills_image_grid,
        "cta-button": _fills_cta,
        "email-footer": _fills_footer,
        "spacer": _fills_spacer,
        "social-icons": _fills_social,
        "divider": _fills_divider,
        "navigation-bar": _fills_nav,
    }
    builder = builders.get(slug)
    if builder:
        return builder(section, container_width, image_urls=image_urls)
    return []


# Type alias for slot builder functions
type _SlotBuilder = _SlotBuilderCallable
type _SlotBuilderCallable = object  # Callable[[EmailSection, int], list[SlotFill]]


def _first_heading(texts: list[TextBlock]) -> TextBlock | None:
    """Return the first heading text block."""
    return next((t for t in texts if t.is_heading), None)


def _first_body(texts: list[TextBlock]) -> TextBlock | None:
    """Return the first non-heading text block."""
    return next((t for t in texts if not t.is_heading), None)


def _body_texts(texts: list[TextBlock]) -> list[TextBlock]:
    """Return all non-heading text blocks."""
    return [t for t in texts if not t.is_heading]


def _safe_text(text: str) -> str:
    """HTML-escape text content."""
    return html.escape(text, quote=False)


def _resolve_image_url(
    node_id: str,
    image_urls: dict[str, str] | None,
) -> str:
    """Resolve image URL from the asset map, falling back to a placeholder."""
    if image_urls:
        url = image_urls.get(node_id)
        if url:
            return url
    # Fallback — will 404 but keeps the node_id for debugging
    return f"/api/v1/design-sync/assets/{node_id}.png"


def _fills_preheader(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    if section.texts:
        fills.append(SlotFill("preheader_text", _safe_text(section.texts[0].content)))
    return fills


def _fills_email_header(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    # email-header has no data-slot attributes (fixed nav links template)
    # We return text fills as hints for future slot injection
    return []


def _fills_logo_header(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    if section.images:
        img = section.images[0]
        overrides: dict[str, str] = {}
        if img.width:
            overrides["width"] = str(int(img.width))
        if img.height:
            overrides["height"] = str(int(img.height))
        fills.append(
            SlotFill(
                "logo_url",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
                attr_overrides=overrides,
            )
        )
        fills.append(SlotFill("logo_alt", img.node_name))
    return fills


def _fills_hero(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    # Background image
    if section.images:
        img = section.images[0]
        fills.append(
            SlotFill(
                "hero_image",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
            )
        )
    # Headline
    heading = _first_heading(section.texts)
    if heading:
        fills.append(SlotFill("headline", _safe_text(heading.content)))
    # Subtext
    body = _first_body(section.texts)
    if body:
        fills.append(SlotFill("subtext", _safe_text(body.content)))
    # CTA
    if section.buttons:
        btn = section.buttons[0]
        fills.append(SlotFill("cta_text", _safe_text(btn.text)))
        fills.append(SlotFill("cta_url", "#", slot_type="cta"))
    return fills


def _fills_full_width_image(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    if section.images:
        img = section.images[0]
        overrides: dict[str, str] = {}
        if img.width:
            overrides["width"] = str(int(img.width))
        fills.append(
            SlotFill(
                "image_url",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
                attr_overrides=overrides,
            )
        )
        fills.append(SlotFill("image_alt", img.node_name))
    return fills


def _fills_text_block(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    heading = _first_heading(section.texts)
    if heading:
        fills.append(SlotFill("heading", _safe_text(heading.content)))
    bodies = _body_texts(section.texts)
    if bodies:
        joined = " ".join(b.content for b in bodies)
        fills.append(SlotFill("body", _safe_text(joined)))
    elif not heading and section.texts:
        # All texts are headings — use first as heading, rest as body
        fills.append(SlotFill("heading", _safe_text(section.texts[0].content)))
        if len(section.texts) > 1:
            joined = " ".join(t.content for t in section.texts[1:])
            fills.append(SlotFill("body", _safe_text(joined)))
    return fills


def _fills_article_card(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    if section.images:
        img = section.images[0]
        fills.append(
            SlotFill(
                "image_url",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
            )
        )
        fills.append(SlotFill("image_alt", img.node_name))
    heading = _first_heading(section.texts)
    if heading:
        fills.append(SlotFill("heading", _safe_text(heading.content)))
    body = _first_body(section.texts)
    if body:
        fills.append(SlotFill("body_text", _safe_text(body.content)))
    if section.buttons:
        btn = section.buttons[0]
        fills.append(SlotFill("cta_text", _safe_text(btn.text)))
        fills.append(SlotFill("cta_url", "#", slot_type="cta"))
    return fills


def _fills_image_block(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    """Fill image-block: replace placeholder src + alt on the <img> tag.

    The image-block seed has no data-slot attrs, so we use image_url/image_alt
    slots. The renderer's _fill_image_slot handles src replacement on any
    <img> tag with a matching data-slot, and we also directly replace the
    placeholder URL via a token override.
    """
    fills: list[SlotFill] = []
    if section.images:
        img = section.images[0]
        fills.append(
            SlotFill(
                "image_url",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
            )
        )
        fills.append(SlotFill("image_alt", img.node_name))
    return fills


def _fills_image_grid(
    section: EmailSection,
    _cw: int,
    *,
    image_urls: dict[str, str] | None = None,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    for i, img in enumerate(section.images[:2], start=1):
        fills.append(
            SlotFill(
                f"image_{i}",
                _resolve_image_url(img.node_id, image_urls),
                slot_type="image",
            )
        )
    return fills


def _fills_cta(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    fills: list[SlotFill] = []
    if section.buttons:
        btn = section.buttons[0]
        fills.append(SlotFill("cta_text", _safe_text(btn.text)))
        fills.append(SlotFill("cta_url", "#", slot_type="cta"))
    return fills


def _fills_footer(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    """Build footer content from section texts.

    Generates <p> blocks for each text line, preserving the Figma content
    (social links, unsubscribe text, legal copy, etc.).
    """
    if not section.texts:
        return []

    parts: list[str] = []
    for text in section.texts:
        escaped = _safe_text(text.content)
        parts.append(
            f'<p style="margin:0 0 12px 0;font-family:Arial,sans-serif;'
            f'font-size:12px;color:#666666;line-height:1.5;">{escaped}</p>'
        )

    return [SlotFill("footer_content", "\n      ".join(parts))]


def _fills_spacer(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    height = int(section.height or 32)
    return [SlotFill("spacer_height", str(height))]


def _fills_social(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    # social-icons has no data-slot — uses fixed template HTML
    return []


def _fills_divider(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    return []


def _fills_nav(
    section: EmailSection,
    _cw: int,
    **_kw: object,
) -> list[SlotFill]:
    """Build nav link HTML from section buttons and/or texts.

    Buttons are preferred (they have explicit text labels from the Figma design).
    Falls back to non-heading texts if no buttons are detected.
    The first heading text becomes a label prefix (e.g. "Stores (LaB)").
    """
    if not section.buttons and not section.texts:
        return []

    link_parts: list[str] = []

    # Use buttons as nav links (they have explicit labels)
    if section.buttons:
        for btn in section.buttons:
            escaped = _safe_text(btn.text)
            link_parts.append(
                f'<a class="navbar-link" href="#" style="color:#333333;'
                f'text-decoration:none;padding:0 12px;">{escaped}</a>'
            )
    else:
        # Fallback: use texts as links (skip headings unless ALL are headings)
        body_texts = [t for t in section.texts if not t.is_heading]
        link_texts = body_texts or section.texts
        for text in link_texts:
            escaped = _safe_text(text.content)
            link_parts.append(
                f'<a class="navbar-link" href="#" style="color:#333333;'
                f'text-decoration:none;padding:0 12px;">{escaped}</a>'
            )

    if not link_parts:
        return []

    return [SlotFill("nav_links", "\n      ".join(link_parts))]


def _build_column_fills(
    section: EmailSection,
    *,
    image_urls: dict[str, str] | None = None,
) -> list[SlotFill]:
    """Build slot fills for column layout components (col_1, col_2, etc.)."""
    # Use column_groups when available (structure-aware)
    if section.column_groups:
        return _build_column_fills_from_groups(
            section.column_groups,
            image_urls=image_urls,
        )

    # Fallback: distribute content round-robin across columns
    fills: list[SlotFill] = []
    col_count = section.column_count or 2

    for col_idx in range(1, col_count + 1):
        col_texts: list[str] = []
        for i, text in enumerate(section.texts):
            if (i % col_count) + 1 == col_idx:
                col_texts.append(_safe_text(text.content))

        col_images: list[str] = []
        for i, img in enumerate(section.images):
            if (i % col_count) + 1 == col_idx:
                url = _resolve_image_url(img.node_id, image_urls)
                col_images.append(
                    f'<img src="{html.escape(url)}" '
                    f'alt="{html.escape(img.node_name)}" '
                    f'style="display:block;width:100%;height:auto;border:0;" />'
                )

        content_parts = col_images + col_texts
        if content_parts:
            fills.append(SlotFill(f"col_{col_idx}", "\n".join(content_parts)))
    return fills


def _build_column_fills_from_groups(
    groups: list[ColumnGroup],
    *,
    image_urls: dict[str, str] | None = None,
) -> list[SlotFill]:
    """Build column fills from actual column groups (preserves design structure)."""
    fills: list[SlotFill] = []
    for group in groups:
        col_parts: list[str] = []
        # Images first (design order)
        for img in group.images:
            url = _resolve_image_url(img.node_id, image_urls)
            col_parts.append(
                f'<img src="{html.escape(url)}" '
                f'alt="{html.escape(img.node_name)}" '
                f'style="display:block;width:100%;height:auto;border:0;" />'
            )
        # Texts in order
        for text in group.texts:
            col_parts.append(_safe_text(text.content))
        # Buttons
        for btn in group.buttons:
            col_parts.append(_safe_text(btn.text))

        if col_parts:
            fills.append(SlotFill(f"col_{group.column_idx}", "\n".join(col_parts)))
    return fills


def _build_token_overrides(section: EmailSection) -> list[TokenOverride]:
    """Extract token overrides from section properties."""
    overrides: list[TokenOverride] = []

    if section.bg_color:
        overrides.append(TokenOverride("background-color", "_outer", section.bg_color))

    # Font overrides from first heading text
    for text in section.texts:
        if text.is_heading and text.font_family:
            overrides.append(TokenOverride("font-family", "_heading", text.font_family))
            break

    for text in section.texts:
        if not text.is_heading and text.font_family:
            overrides.append(TokenOverride("font-family", "_body", text.font_family))
            break

    # Padding overrides
    padding_parts: list[str] = []
    if section.padding_top is not None:
        padding_parts.append(f"{int(section.padding_top)}px")
    if section.padding_right is not None:
        padding_parts.append(f"{int(section.padding_right)}px")
    if section.padding_bottom is not None:
        padding_parts.append(f"{int(section.padding_bottom)}px")
    if section.padding_left is not None:
        padding_parts.append(f"{int(section.padding_left)}px")

    if len(padding_parts) == 4:
        overrides.append(TokenOverride("padding", "_cell", " ".join(padding_parts)))

    return overrides
