"""Layout analysis for design file structures — pure computation, no I/O."""

from __future__ import annotations

import re
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


class NamingConvention(StrEnum):
    """Detected naming convention used in the design file."""

    MJML = "mjml"
    DESCRIPTIVE = "descriptive"
    GENERIC = "generic"
    CUSTOM = "custom"


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
    is_background: bool = False


@dataclass(frozen=True)
class ButtonElement:
    """A CTA button detected in the design."""

    node_id: str
    text: str
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class ColumnGroup:
    """Content grouped by column, preserving design structure."""

    column_idx: int
    node_id: str
    node_name: str
    texts: list[TextBlock] = field(default_factory=list)
    images: list[ImagePlaceholder] = field(default_factory=list)
    buttons: list[ButtonElement] = field(default_factory=list)
    width: float | None = None


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
    column_groups: list[ColumnGroup] = field(default_factory=list)
    classification_confidence: float | None = None
    content_roles: tuple[str, ...] = ()


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
    EmailSectionType.HEADER: ["header", "top-bar", "topbar", "logo-bar", "logo-header"],
    EmailSectionType.HERO: ["hero", "banner", "masthead", "feature", "mj-hero"],
    EmailSectionType.CONTENT: ["content", "body", "main", "article", "text", "product"],
    EmailSectionType.CTA: ["cta", "call-to-action", "button", "action"],
    EmailSectionType.FOOTER: ["footer", "bottom", "legal", "unsubscribe"],
    EmailSectionType.SOCIAL: ["social", "follow", "connect", "mj-social"],
    EmailSectionType.DIVIDER: ["divider", "separator", "hr", "line", "mj-divider"],
    EmailSectionType.SPACER: ["spacer", "gap", "padding", "mj-spacer"],
    EmailSectionType.NAV: ["nav", "navigation", "menu", "links", "mj-navbar"],
}

# MJML → EmailSectionType mapping
_MJ_SECTION_MAP: dict[str, EmailSectionType] = {
    "mj-section": EmailSectionType.CONTENT,
    "mj-wrapper": EmailSectionType.CONTENT,
    "mj-hero": EmailSectionType.HERO,
    "mj-navbar": EmailSectionType.NAV,
}

# MJML → content role mapping
_MJ_CONTENT_ROLES: dict[str, str] = {
    "mj-image": "image",
    "mj-text": "text",
    "mj-button": "button",
    "mj-column": "column",
    "mj-section": "section",
    "mj-wrapper": "wrapper",
    "mj-divider": "divider",
    "mj-spacer": "spacer",
    "mj-social": "social",
    "mj-navbar": "nav",
}

_FRAME_TYPES = frozenset({DesignNodeType.FRAME, DesignNodeType.GROUP, DesignNodeType.COMPONENT})

_GENERIC_NAME_RE = re.compile(r"(?i)^(frame|group|rectangle|ellipse|vector|text|instance)\s*\d*$")

_Y_TOLERANCE = 10.0  # pixels tolerance for column detection


def analyze_layout(
    structure: DesignFileStructure,
    *,
    naming_convention: str = "auto",
    section_name_map: dict[str, str] | None = None,
    button_name_hints: list[str] | None = None,
) -> DesignLayoutDescription:
    """Analyze a design file structure and detect email sections.

    Algorithm:
    1. Find the primary page (first page, or page named "email"/"design")
    2. Get top-level frames as section candidates
    3. Auto-detect or use provided naming convention
    4. Classify each frame by convention-specific strategy
    5. Detect column layouts (structure-first, position-fallback)
    6. Extract text, images, buttons from each section
    7. Calculate spacing between sections
    8. Sort sections by y-position (top to bottom)
    """
    if not structure.pages:
        return DesignLayoutDescription(file_name=structure.file_name)

    page = _find_primary_page(structure.pages)
    candidates = _get_section_candidates(page)

    if not candidates:
        return DesignLayoutDescription(file_name=structure.file_name)

    # Detect naming convention
    if naming_convention == "auto":
        convention = _detect_naming_convention(candidates)
    elif naming_convention == "custom" and section_name_map:
        convention = NamingConvention.CUSTOM
    else:
        try:
            convention = NamingConvention(naming_convention)
        except ValueError:
            convention = _detect_naming_convention(candidates)

    # Determine overall width from the widest top-level frame
    overall_width = max((c.width for c in candidates if c.width is not None), default=None)

    # Build sections
    sections: list[EmailSection] = []
    total = len(candidates)
    for idx, node in enumerate(candidates):
        section_type = _classify_section(
            node,
            convention,
            idx,
            total,
            section_name_map=section_name_map,
        )

        col_layout, col_count, col_groups = _detect_column_layout_with_groups(node, convention)
        texts = _detect_content_hierarchy(_extract_texts(node))
        images = _extract_images(node)
        buttons = _extract_buttons(node, extra_hints=button_name_hints)

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
                column_groups=col_groups,
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


def _detect_naming_convention(candidates: list[DesignNode]) -> NamingConvention:
    """Auto-detect which naming convention the design uses."""
    names: list[str] = []
    for c in candidates:
        names.append(c.name.lower())
        for child in c.children:
            names.append(child.name.lower())

    total = len(names) or 1
    mj_count = sum(1 for n in names if n.startswith("mj-"))
    pattern_count = sum(
        1
        for n in names
        for patterns in _SECTION_PATTERNS.values()
        for p in patterns
        if p in n and not p.startswith("mj-")
    )
    generic_count = sum(1 for n in names if _is_generic_name(n))

    if mj_count / total > 0.3:
        return NamingConvention.MJML
    if pattern_count / total > 0.2:
        return NamingConvention.DESCRIPTIVE
    if generic_count / total > 0.5:
        return NamingConvention.GENERIC
    return NamingConvention.DESCRIPTIVE


def _is_generic_name(name: str) -> bool:
    """Check if name is Figma auto-generated (Frame 1, Group 2, etc.)."""
    return bool(_GENERIC_NAME_RE.match(name.strip()))


def _classify_section(
    node: DesignNode,
    convention: NamingConvention,
    index: int,
    total: int,
    *,
    section_name_map: dict[str, str] | None = None,
) -> EmailSectionType:
    """Classify a section using the detected naming convention."""
    # Custom map checked first
    if section_name_map:
        mapped = section_name_map.get(node.name.lower().strip())
        if mapped:
            try:
                return EmailSectionType(mapped)
            except ValueError:
                pass

    if convention == NamingConvention.MJML:
        return _classify_mj_section(node, index, total)

    # Descriptive and generic both try name first, then fall back
    section_type = _classify_by_name(node.name)
    if section_type != EmailSectionType.UNKNOWN:
        return section_type

    # For generic names, try content-based heuristics first
    if convention == NamingConvention.GENERIC:
        texts = _extract_texts(node)
        images = _extract_images(node)
        buttons = _extract_buttons(node)
        return _classify_by_content(node, texts, images, buttons, index, total)

    return _classify_by_position(node, index, total, _has_large_image_child(node))


def _classify_mj_section(
    node: DesignNode,
    index: int,
    total: int,
) -> EmailSectionType:
    """Classify a section using MJML naming conventions."""
    name = node.name.lower().strip()

    # Walk children first to infer type from content roles — child roles
    # take priority over generic mj-section/mj-wrapper direct mapping
    child_roles: set[str] = set()
    for child in _walk_mj_children(node):
        role = _get_mj_role(child.name)
        if role:
            child_roles.add(role)

    # Also detect by node type (IMAGE nodes without mj-* names)
    for child in _walk_mj_children(node):
        if child.type == DesignNodeType.IMAGE:
            child_roles.add("image")
        elif child.type == DesignNodeType.TEXT and child.text_content:
            child_roles.add("text")

    # Filter out structural roles — only use content roles for classification
    _STRUCTURAL_ROLES = {"section", "column", "wrapper"}
    content_roles = child_roles - _STRUCTURAL_ROLES

    # Specific content roles override the generic mj-section/mj-wrapper mapping
    if content_roles == {"image"} and _has_large_image_child(node):
        return EmailSectionType.HERO
    if "social" in content_roles:
        return EmailSectionType.SOCIAL
    if "nav" in content_roles:
        return EmailSectionType.NAV
    if content_roles == {"divider"} or (content_roles == {"divider", "text"}):
        return EmailSectionType.DIVIDER
    if content_roles == {"spacer"}:
        return EmailSectionType.SPACER

    # Image-only at top → HERO
    if content_roles == {"image"} and index <= 1:
        return EmailSectionType.HERO

    # Text + button + image → rich content
    if "image" in content_roles and "text" in content_roles and "button" in content_roles:
        return EmailSectionType.CONTENT
    if "button" in content_roles and "text" in content_roles and "image" not in content_roles:
        # Many texts with short content → likely NAV
        texts = _extract_texts(node)
        if len(texts) >= 4 and all(len(t.content) <= 30 for t in texts):
            return EmailSectionType.NAV
        return EmailSectionType.CONTENT

    # Last section with only text → FOOTER
    if index == total - 1 and content_roles <= {"text"}:
        return EmailSectionType.FOOTER

    # Direct mj-* type mapping (for mj-hero, mj-navbar, etc.)
    if name in _MJ_SECTION_MAP:
        return _MJ_SECTION_MAP[name]

    # Fall back to descriptive name matching, then position
    section_type = _classify_by_name(node.name)
    if section_type != EmailSectionType.UNKNOWN:
        return section_type
    return _classify_by_position(node, index, total, _has_large_image_child(node))


def _walk_mj_children(node: DesignNode, max_depth: int = 5) -> list[DesignNode]:
    """Walk up to max_depth levels to find mj-* named children.

    MJML designs nest content 3-4 levels deep:
    mj-wrapper > mj-section > mj-column > mj-image-Frame > mj-image
    So we need to walk deeper than 2 levels.
    """
    result: list[DesignNode] = []

    def _recurse(n: DesignNode, depth: int) -> None:
        if depth > max_depth:
            return
        for child in n.children:
            result.append(child)
            _recurse(child, depth + 1)

    _recurse(node, 0)
    return result


def _get_mj_role(name: str) -> str | None:
    """Get content role from mj-* name (checking both exact and prefix match)."""
    lower = name.lower().strip()
    if lower in _MJ_CONTENT_ROLES:
        return _MJ_CONTENT_ROLES[lower]
    for prefix, role in _MJ_CONTENT_ROLES.items():
        if lower.startswith(prefix):
            return role
    return None


_SOCIAL_URL_RE = re.compile(
    r"(?i)(?:facebook|twitter|x|instagram|linkedin|youtube|tiktok|pinterest)\.com",
)

_LEGAL_TEXT_RE = re.compile(r"©|copyright|\ball rights reserved\b", re.IGNORECASE)

_UNSUBSCRIBE_RE = re.compile(r"\bunsubscribe\b", re.IGNORECASE)


def _classify_by_content(
    node: DesignNode,
    texts: list[TextBlock],
    images: list[ImagePlaceholder],
    buttons: list[ButtonElement],
    index: int,
    total: int,
) -> EmailSectionType:
    """Infer section type from content when names are unhelpful."""
    has_images = len(images) > 0
    has_texts = len(texts) > 0
    has_buttons = len(buttons) > 0
    all_text = " ".join(t.content for t in texts) if has_texts else ""

    # Full-width image near top → hero
    if _has_large_image_child(node) and not has_texts and index <= 1:
        return EmailSectionType.HERO

    # Large image + text overlay near top (tall section) → hero
    if _has_large_image_child(node) and has_texts and index <= 1:
        height = node.height or 0
        if height >= 300:
            return EmailSectionType.HERO

    # Text + button near top with large heading → hero
    if has_texts and has_buttons and not has_images and index <= 2:
        heading_sizes = [t.font_size for t in texts if t.font_size and t.font_size > 20]
        if heading_sizes:
            return EmailSectionType.HERO

    # Section with ©/copyright/unsubscribe text → footer (regardless of position)
    if has_texts and (_LEGAL_TEXT_RE.search(all_text) or _UNSUBSCRIBE_RE.search(all_text)):
        return EmailSectionType.FOOTER

    # Social platform URLs → social
    if has_texts and _SOCIAL_URL_RE.search(all_text):
        return EmailSectionType.SOCIAL

    # Button-only section → CTA
    if has_buttons and not has_texts and not has_images:
        return EmailSectionType.CTA

    # Many short texts → navigation
    if len(texts) >= 4 and all(len(t.content) < 30 for t in texts):
        return EmailSectionType.NAV

    # Small text at bottom → footer
    if index >= total - 2 and has_texts and not has_images:
        avg_size = sum(t.font_size or 14 for t in texts) / len(texts)
        if avg_size <= 13:
            return EmailSectionType.FOOTER

    return _classify_by_position(node, index, total, _has_large_image_child(node))


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
    """Detect column layout from children's positions (backward-compat wrapper)."""
    layout, count, _groups = _detect_column_layout_with_groups(node)
    return layout, count


def _detect_column_layout_with_groups(
    node: DesignNode,
    convention: NamingConvention = NamingConvention.GENERIC,
) -> tuple[ColumnLayout, int, list[ColumnGroup]]:
    """Detect column layout using structure first, position fallback.

    Returns (layout_type, column_count, column_groups).
    """
    # Strategy 1: MJML — look for mj-column children
    if convention == NamingConvention.MJML:
        columns = _detect_mj_columns(node)
        if columns:
            return _layout_from_count(len(columns)), len(columns), columns

    # Strategy 2: Auto-layout HORIZONTAL means children are columns
    if node.layout_mode == "HORIZONTAL":
        frame_children = [
            c
            for c in node.children
            if c.type in _FRAME_TYPES and c.width is not None and c.width > 40
        ]
        if len(frame_children) >= 2:
            columns = _build_column_groups(frame_children)
            return _layout_from_count(len(columns)), len(columns), columns

    # Strategy 3: Position-based — group by Y-position (existing logic)
    columns = _detect_position_columns(node)
    count = len(columns) if columns else 1
    return _layout_from_count(count), count, columns


def _layout_from_count(count: int) -> ColumnLayout:
    """Map column count to ColumnLayout enum."""
    if count >= 4:
        return ColumnLayout.MULTI_COLUMN
    if count == 3:
        return ColumnLayout.THREE_COLUMN
    if count == 2:
        return ColumnLayout.TWO_COLUMN
    return ColumnLayout.SINGLE


def _detect_mj_columns(node: DesignNode) -> list[ColumnGroup]:
    """Find mj-column children and extract their content."""
    # Walk one level to find mj-section, then its mj-column children
    section_node = node
    for child in node.children:
        if child.name.lower().startswith("mj-section"):
            section_node = child
            break

    all_columns: list[ColumnGroup] = []
    col_idx = 0
    for child in section_node.children:
        if child.name.lower().startswith("mj-column"):
            texts = _extract_texts(child)
            images = _extract_images(child)
            buttons = _extract_buttons(child)

            # Skip spacer-only columns (e.g., mj-column containing only mj-spacer)
            has_content = bool(texts or images or buttons)
            if not has_content:
                # Check if all children are spacers
                is_spacer = all(
                    c.name.lower().startswith("mj-spacer") or c.name.lower().startswith("spacer")
                    for c in child.children
                )
                if is_spacer:
                    continue

            col_idx += 1
            all_columns.append(
                ColumnGroup(
                    column_idx=col_idx,
                    node_id=child.id,
                    node_name=child.name,
                    texts=texts,
                    images=images,
                    buttons=buttons,
                    width=child.width,
                )
            )
    return all_columns


def _build_column_groups(frame_children: list[DesignNode]) -> list[ColumnGroup]:
    """Build ColumnGroup from a list of frame children (auto-layout columns)."""
    groups: list[ColumnGroup] = []
    for idx, child in enumerate(frame_children, 1):
        groups.append(
            ColumnGroup(
                column_idx=idx,
                node_id=child.id,
                node_name=child.name,
                texts=_extract_texts(child),
                images=_extract_images(child),
                buttons=_extract_buttons(child),
                width=child.width,
            )
        )
    return groups


def _detect_position_columns(node: DesignNode) -> list[ColumnGroup]:
    """Position-based column detection (Y-grouping)."""
    frame_children = [
        c for c in node.children if c.type in _FRAME_TYPES and c.x is not None and c.y is not None
    ]

    if len(frame_children) < 2:
        return []

    # Group by y-position (within tolerance)
    y_groups: dict[float, list[DesignNode]] = {}
    for child in frame_children:
        if child.y is None:
            continue
        placed = False
        for ref_y in y_groups:
            if abs(child.y - ref_y) <= _Y_TOLERANCE:
                y_groups[ref_y].append(child)
                placed = True
                break
        if not placed:
            y_groups[child.y] = [child]

    max_group = max(y_groups.values(), key=len)
    if len(max_group) < 2:
        return []

    # Sort by x-position and build groups
    max_group.sort(key=lambda c: c.x if c.x is not None else 0.0)
    return _build_column_groups(max_group)


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
    """Walk tree collecting IMAGE nodes and FRAME nodes with IMAGE fills."""
    if node.type == DesignNodeType.IMAGE:
        results.append(
            ImagePlaceholder(
                node_id=node.id,
                node_name=node.name,
                width=node.width,
                height=node.height,
            )
        )
    elif node.type == DesignNodeType.FRAME and node.image_ref:
        # Frame with IMAGE fill → treat as background image
        results.append(
            ImagePlaceholder(
                node_id=node.id,
                node_name=node.name,
                width=node.width,
                height=node.height,
                is_background=True,
            )
        )
        # Still recurse into children (frame has content over the bg)
        for child in node.children:
            _walk_for_images(child, results)
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


def _extract_buttons(
    node: DesignNode,
    *,
    extra_hints: list[str] | None = None,
) -> list[ButtonElement]:
    """Detect buttons: small frames with a TEXT child containing short text."""
    results: list[ButtonElement] = []
    _walk_for_buttons(node, results, extra_hints=extra_hints)
    return results


_DEFAULT_BUTTON_HINTS = ("button", "btn", "cta", "action", "link", "mj-button")


def _walk_for_buttons(
    node: DesignNode,
    results: list[ButtonElement],
    *,
    extra_hints: list[str] | None = None,
) -> None:
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
            hints = _DEFAULT_BUTTON_HINTS
            if extra_hints:
                hints = (*_DEFAULT_BUTTON_HINTS, *extra_hints)
            is_button_name = any(h in lower_name for h in hints)
            # Accept if name hints OR frame has a visible fill (real buttons have backgrounds)
            has_fill = bool(
                node.fill_color and node.fill_color.upper() not in ("#FFFFFF", "#FFF", "")
            )
            if is_button_name or has_fill:
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
        _walk_for_buttons(child, results, extra_hints=extra_hints)


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
                column_groups=section.column_groups,
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
