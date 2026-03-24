"""Layout analysis for design file structures — pure computation, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType


class EmailSectionType(StrEnum):
    """Recognised email section types."""

    HEADER = "header"
    PREHEADER = "preheader"
    HERO = "hero"
    CONTENT = "content"
    CTA = "cta"
    FOOTER = "footer"
    SOCIAL = "social"
    DIVIDER = "divider"
    SPACER = "spacer"
    NAV = "nav"
    UNKNOWN = "unknown"


class ColumnLayout(StrEnum):
    """Column layout detected in a section."""

    SINGLE = "single"
    TWO_COLUMN = "two-column"
    THREE_COLUMN = "three-column"
    MULTI_COLUMN = "multi-column"


@dataclass(frozen=True)
class TextBlock:
    """A text element extracted from the design."""

    node_id: str
    content: str
    font_size: float | None = None
    is_heading: bool = False
    font_family: str | None = None
    font_weight: int | None = None
    line_height: float | None = None
    letter_spacing: float | None = None


@dataclass(frozen=True)
class ImagePlaceholder:
    """An image placeholder detected in the design."""

    node_id: str
    node_name: str
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class ButtonElement:
    """A CTA button detected in the design."""

    node_id: str
    text: str
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class EmailSection:
    """A detected email section with its content."""

    section_type: EmailSectionType
    node_id: str
    node_name: str
    y_position: float | None = None
    width: float | None = None
    height: float | None = None
    column_layout: ColumnLayout = ColumnLayout.SINGLE
    column_count: int = 1
    texts: list[TextBlock] = field(default_factory=list[TextBlock])
    images: list[ImagePlaceholder] = field(default_factory=list[ImagePlaceholder])
    buttons: list[ButtonElement] = field(default_factory=list[ButtonElement])
    spacing_after: float | None = None
    bg_color: str | None = None
    padding_top: float | None = None
    padding_right: float | None = None
    padding_bottom: float | None = None
    padding_left: float | None = None
    item_spacing: float | None = None
    element_gaps: tuple[float, ...] = ()


@dataclass(frozen=True)
class DesignLayoutDescription:
    """Complete layout analysis result."""

    file_name: str
    overall_width: float | None = None
    sections: list[EmailSection] = field(default_factory=list[EmailSection])
    total_text_blocks: int = 0
    total_images: int = 0
    spacing_map: dict[str, dict[str, float]] = field(default_factory=dict)


# ── Name-based section detection ──

_SECTION_PATTERNS: dict[EmailSectionType, list[str]] = {
    EmailSectionType.PREHEADER: ["preheader", "pre-header", "preview"],
    EmailSectionType.HEADER: ["header", "top-bar", "topbar", "logo-bar"],
    EmailSectionType.HERO: ["hero", "banner", "masthead", "feature"],
    EmailSectionType.CONTENT: ["content", "body", "main", "article", "text"],
    EmailSectionType.CTA: ["cta", "call-to-action", "button", "action"],
    EmailSectionType.FOOTER: ["footer", "bottom", "legal", "unsubscribe"],
    EmailSectionType.SOCIAL: ["social", "follow", "connect"],
    EmailSectionType.DIVIDER: ["divider", "separator", "hr", "line"],
    EmailSectionType.SPACER: ["spacer", "gap", "padding"],
    EmailSectionType.NAV: ["nav", "navigation", "menu", "links"],
}

_Y_TOLERANCE = 10.0  # pixels tolerance for column detection


def analyze_layout(structure: DesignFileStructure) -> DesignLayoutDescription:
    """Analyze a design file structure and detect email sections.

    Algorithm:
    1. Find the primary page (first page, or page named "email"/"design")
    2. Get top-level frames as section candidates
    3. Classify each frame by name pattern match, then position fallback
    4. Detect column layouts within each section via x/y positions of children
    5. Extract text, images, buttons from each section
    6. Calculate spacing between sections
    7. Sort sections by y-position (top to bottom)
    """
    if not structure.pages:
        return DesignLayoutDescription(file_name=structure.file_name)

    page = _find_primary_page(structure.pages)
    candidates = _get_section_candidates(page)

    if not candidates:
        return DesignLayoutDescription(file_name=structure.file_name)

    # Determine overall width from the widest top-level frame
    overall_width = max((c.width for c in candidates if c.width is not None), default=None)

    # Build sections
    sections: list[EmailSection] = []
    total = len(candidates)
    for idx, node in enumerate(candidates):
        section_type = _classify_by_name(node.name)
        if section_type == EmailSectionType.UNKNOWN:
            section_type = _classify_by_position(node, idx, total, _has_large_image_child(node))

        col_layout, col_count = _detect_column_layout(node)
        texts = _detect_content_hierarchy(_extract_texts(node))
        images = _extract_images(node)
        buttons = _extract_buttons(node)

        sections.append(
            EmailSection(
                section_type=section_type,
                node_id=node.id,
                node_name=node.name,
                y_position=node.y,
                width=node.width,
                height=node.height,
                column_layout=col_layout,
                column_count=col_count,
                texts=texts,
                images=images,
                buttons=buttons,
                bg_color=node.fill_color,
                padding_top=node.padding_top,
                padding_right=node.padding_right,
                padding_bottom=node.padding_bottom,
                padding_left=node.padding_left,
                item_spacing=node.item_spacing,
            )
        )

    # Sort by y-position (top to bottom)
    sections.sort(key=lambda s: s.y_position if s.y_position is not None else 0.0)

    # Calculate spacing between sections
    sections = _calculate_spacing(sections)

    total_text_blocks = sum(len(s.texts) for s in sections)
    total_images = sum(len(s.images) for s in sections)

    spacing_map = generate_spacing_map(sections)

    return DesignLayoutDescription(
        file_name=structure.file_name,
        overall_width=overall_width,
        sections=sections,
        total_text_blocks=total_text_blocks,
        total_images=total_images,
        spacing_map=spacing_map,
    )


def _find_primary_page(pages: list[DesignNode]) -> DesignNode:
    """Find the primary page — prefer one named 'email' or 'design'."""
    for page in pages:
        lower_name = page.name.lower()
        if "email" in lower_name or "design" in lower_name:
            return page
    return pages[0]


def _get_section_candidates(page: DesignNode) -> list[DesignNode]:
    """Get top-level frames from a page as section candidates.

    When a single large wrapper frame is found (e.g. a full email design),
    use its children as section candidates instead of treating the wrapper
    as one section.
    """
    top_frames = [
        child
        for child in page.children
        if child.type in (DesignNodeType.FRAME, DesignNodeType.COMPONENT, DesignNodeType.GROUP)
    ]

    # If there's exactly one tall frame with multiple children, unwrap it —
    # it's likely a full-email wrapper (e.g. "EmailLove" containing mj-wrappers)
    if len(top_frames) == 1:
        wrapper = top_frames[0]
        inner = [
            child
            for child in wrapper.children
            if child.type in (DesignNodeType.FRAME, DesignNodeType.COMPONENT, DesignNodeType.GROUP)
        ]
        if len(inner) >= 2:
            return inner

    return top_frames


def _classify_by_name(name: str) -> EmailSectionType:
    """Match frame name against known email section patterns (case-insensitive)."""
    lower = name.lower().strip()
    for section_type, patterns in _SECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in lower:
                return section_type
    return EmailSectionType.UNKNOWN


def _classify_by_position(
    node: DesignNode,
    index: int,
    total: int,
    has_large_image: bool,
) -> EmailSectionType:
    """Fallback: classify by position + dimensions when name doesn't match.

    Uses height, position, and child content to infer section type.
    """
    height = node.height or 0

    # Very short sections are spacers/dividers
    if height <= 30:
        return EmailSectionType.SPACER
    if 30 < height <= 60:
        return EmailSectionType.DIVIDER

    # First section is header/nav
    if index == 0:
        return EmailSectionType.HEADER

    # Last section is footer
    if index == total - 1:
        return EmailSectionType.FOOTER

    # Second-to-last short section is often social links
    if index == total - 2 and height <= 150:
        return EmailSectionType.SOCIAL

    # Tall section near the top with or without large image → hero
    if index == 1 and height >= 300:
        return EmailSectionType.HERO
    if has_large_image and height >= 300:
        return EmailSectionType.HERO

    # Short section with button-sized height → CTA
    if 60 < height <= 150:
        return EmailSectionType.CTA

    return EmailSectionType.CONTENT


def _detect_column_layout(node: DesignNode) -> tuple[ColumnLayout, int]:
    """Detect column layout from children's x/y positions.

    Children at the same y-position (within tolerance) with
    adjacent x-positions are treated as columns.
    """
    frame_children = [
        c
        for c in node.children
        if c.type in (DesignNodeType.FRAME, DesignNodeType.GROUP, DesignNodeType.COMPONENT)
        and c.x is not None
        and c.y is not None
    ]

    if len(frame_children) < 2:
        return ColumnLayout.SINGLE, 1

    # Group by y-position (within tolerance)
    y_groups: dict[float, list[DesignNode]] = {}
    for child in frame_children:
        if child.y is None:
            continue  # already filtered, but guard for type checker
        placed = False
        for ref_y in y_groups:
            if abs(child.y - ref_y) <= _Y_TOLERANCE:
                y_groups[ref_y].append(child)
                placed = True
                break
        if not placed:
            y_groups[child.y] = [child]

    # Find the largest group of children at the same y level
    max_group = max(y_groups.values(), key=len)
    col_count = len(max_group)

    if col_count >= 4:
        return ColumnLayout.MULTI_COLUMN, col_count
    if col_count == 3:
        return ColumnLayout.THREE_COLUMN, 3
    if col_count == 2:
        return ColumnLayout.TWO_COLUMN, 2
    return ColumnLayout.SINGLE, 1


def _extract_texts(node: DesignNode) -> list[TextBlock]:
    """Recursively extract text blocks from TEXT nodes."""
    results: list[TextBlock] = []
    _walk_for_texts(node, results)
    return results


def _walk_for_texts(node: DesignNode, results: list[TextBlock]) -> None:
    """Walk tree collecting TEXT nodes."""
    if node.type == DesignNodeType.TEXT and node.text_content:
        # Use actual font_size from design tool; fall back to bounding box height
        results.append(
            TextBlock(
                node_id=node.id,
                content=node.text_content,
                font_size=node.font_size if node.font_size is not None else node.height,
                is_heading=False,
                font_family=node.font_family,
                font_weight=node.font_weight,
                line_height=node.line_height_px,
                letter_spacing=node.letter_spacing_px,
            )
        )
    for child in node.children:
        _walk_for_texts(child, results)


def _extract_images(node: DesignNode) -> list[ImagePlaceholder]:
    """Identify IMAGE nodes and FRAMEs containing only an IMAGE child."""
    results: list[ImagePlaceholder] = []
    _walk_for_images(node, results)
    return results


def _walk_for_images(node: DesignNode, results: list[ImagePlaceholder]) -> None:
    """Walk tree collecting IMAGE nodes."""
    if node.type == DesignNodeType.IMAGE:
        results.append(
            ImagePlaceholder(
                node_id=node.id,
                node_name=node.name,
                width=node.width,
                height=node.height,
            )
        )
    elif (
        node.type in (DesignNodeType.FRAME, DesignNodeType.GROUP)
        and len(node.children) == 1
        and node.children[0].type == DesignNodeType.IMAGE
    ):
        # Frame wrapping a single image
        img = node.children[0]
        results.append(
            ImagePlaceholder(
                node_id=img.id,
                node_name=img.name,
                width=img.width,
                height=img.height,
            )
        )
    else:
        for child in node.children:
            _walk_for_images(child, results)


def _extract_buttons(node: DesignNode) -> list[ButtonElement]:
    """Detect buttons: small frames with a TEXT child containing short text."""
    results: list[ButtonElement] = []
    _walk_for_buttons(node, results)
    return results


def _walk_for_buttons(node: DesignNode, results: list[ButtonElement]) -> None:
    """Walk tree looking for button-like elements."""
    # A button is a small FRAME/COMPONENT with a TEXT child that has short text
    if node.type in (DesignNodeType.FRAME, DesignNodeType.COMPONENT, DesignNodeType.INSTANCE):
        text_children = [
            c for c in node.children if c.type == DesignNodeType.TEXT and c.text_content
        ]
        if (
            len(text_children) == 1
            and text_children[0].text_content
            and len(text_children[0].text_content) <= 30
            and node.height is not None
            and node.height <= 80
        ):
            # Check if name also hints at button/CTA
            lower_name = node.name.lower()
            name_hints = ("button", "btn", "cta", "action", "link")
            is_button_name = any(h in lower_name for h in name_hints)
            # Accept if name hints OR frame is compact with short text
            if is_button_name or (node.width is not None and node.width <= 300):
                results.append(
                    ButtonElement(
                        node_id=node.id,
                        text=text_children[0].text_content,
                        width=node.width,
                        height=node.height,
                    )
                )
                return  # Don't recurse into button internals

    for child in node.children:
        _walk_for_buttons(child, results)


def _has_large_image_child(node: DesignNode) -> bool:
    """Check if node has a single IMAGE child taking >60% of parent width."""
    if node.width is None or node.width == 0:
        return False

    image_children = [c for c in node.children if c.type == DesignNodeType.IMAGE]
    if len(image_children) != 1:
        return False

    img = image_children[0]
    if img.width is None:
        return False

    return img.width / node.width > 0.6


def _detect_content_hierarchy(texts: list[TextBlock]) -> list[TextBlock]:
    """Mark headings based on relative font size (largest = heading)."""
    if not texts:
        return texts

    sizes = [t.font_size for t in texts if t.font_size is not None]
    if not sizes:
        return texts

    max_size = max(sizes)
    # Anything within 80% of max size is considered a heading
    threshold = max_size * 0.8

    return [
        TextBlock(
            node_id=t.node_id,
            content=t.content,
            font_size=t.font_size,
            is_heading=t.font_size is not None and t.font_size >= threshold,
            font_family=t.font_family,
            font_weight=t.font_weight,
            line_height=t.line_height,
            letter_spacing=t.letter_spacing,
        )
        for t in texts
    ]


def _calculate_spacing(sections: list[EmailSection]) -> list[EmailSection]:
    """Calculate spacing between consecutive sections."""
    if len(sections) < 2:
        return sections

    result: list[EmailSection] = []
    for i, section in enumerate(sections):
        spacing: float | None = None
        if i < len(sections) - 1:
            current_bottom = _section_bottom(section)
            next_top = sections[i + 1].y_position
            if current_bottom is not None and next_top is not None:
                spacing = max(0.0, next_top - current_bottom)

        result.append(
            EmailSection(
                section_type=section.section_type,
                node_id=section.node_id,
                node_name=section.node_name,
                y_position=section.y_position,
                width=section.width,
                height=section.height,
                column_layout=section.column_layout,
                column_count=section.column_count,
                texts=section.texts,
                images=section.images,
                buttons=section.buttons,
                spacing_after=spacing,
                bg_color=section.bg_color,
                padding_top=section.padding_top,
                padding_right=section.padding_right,
                padding_bottom=section.padding_bottom,
                padding_left=section.padding_left,
                item_spacing=section.item_spacing,
                element_gaps=_compute_element_gaps(section),
            )
        )
    return result


def _compute_element_gaps(section: EmailSection) -> tuple[float, ...]:
    """Compute gaps between consecutive elements using auto-layout item_spacing."""
    if section.item_spacing is not None:
        n_children = len(section.texts) + len(section.images) + len(section.buttons)
        if n_children > 1:
            return tuple(section.item_spacing for _ in range(n_children - 1))
    return ()


def generate_spacing_map(sections: list[EmailSection]) -> dict[str, dict[str, float]]:
    """Build per-section spacing specification from layout analysis."""
    result: dict[str, dict[str, float]] = {}
    for section in sections:
        entry: dict[str, float] = {}
        if section.padding_top is not None:
            entry["padding_top"] = section.padding_top
        if section.padding_right is not None:
            entry["padding_right"] = section.padding_right
        if section.padding_bottom is not None:
            entry["padding_bottom"] = section.padding_bottom
        if section.padding_left is not None:
            entry["padding_left"] = section.padding_left
        if section.item_spacing is not None:
            entry["item_spacing"] = section.item_spacing
        if section.spacing_after is not None:
            entry["spacing_after"] = section.spacing_after
        if entry:
            result[section.node_id] = entry
    return result


def _section_bottom(section: EmailSection) -> float | None:
    """Get the bottom y-coordinate of a section."""
    if section.y_position is None or section.height is None:
        return None
    return section.y_position + section.height
