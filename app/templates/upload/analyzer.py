# pyright: reportUnnecessaryIsInstance=false
"""Static HTML analysis — detect sections, slots, tokens, ESP platform, complexity."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SectionInfo:
    """A detected section within the template."""

    section_id: str
    component_name: str
    element_count: int
    layout_type: str
    element: HtmlElement | None = field(default=None, repr=False)


@dataclass
class SlotInfo:
    """A detected fillable content region."""

    slot_id: str
    slot_type: str
    selector: str
    required: bool
    max_chars: int | None
    content_preview: str
    section_id: str


@dataclass
class TokenInfo:
    """Raw extracted token data from inline styles."""

    colors: dict[str, list[str]] = field(default_factory=lambda: {})
    fonts: dict[str, list[str]] = field(default_factory=lambda: {})
    font_sizes: dict[str, list[str]] = field(default_factory=lambda: {})
    spacing: dict[str, list[str]] = field(default_factory=lambda: {})
    font_weights: dict[str, list[str]] = field(default_factory=lambda: {})
    line_heights: dict[str, list[str]] = field(default_factory=lambda: {})
    letter_spacings: dict[str, list[str]] = field(default_factory=lambda: {})
    color_roles: dict[str, list[str]] = field(default_factory=lambda: {})
    responsive: dict[str, dict[str, list[str]]] = field(default_factory=lambda: {})
    responsive_breakpoints: list[str] = field(default_factory=list)


@dataclass
class ComplexityInfo:
    """Measured template complexity metrics."""

    column_count: int = 1
    nesting_depth: int = 0
    mso_conditional_count: int = 0
    total_elements: int = 0
    table_nesting_depth: int = 0
    has_vml: bool = False
    has_amp: bool = False

    @property
    def score(self) -> int:
        """Compute a 0-100 complexity score."""
        s = min(self.total_elements // 10, 30)
        s += min(self.table_nesting_depth * 5, 20)
        s += min(self.mso_conditional_count * 3, 15)
        s += min(self.column_count * 5, 15)
        if self.has_vml:
            s += 10
        if self.has_amp:
            s += 10
        return min(s, 100)


@dataclass
class WrapperInfo:
    """Preserved metadata from the outer centering wrapper table."""

    tag: str  # "table" or "div"
    width: str | None = None
    align: str | None = None
    style: str | None = None
    bgcolor: str | None = None
    cellpadding: str | None = None
    cellspacing: str | None = None
    border: str | None = None
    role: str | None = None
    inner_td_style: str | None = None
    mso_wrapper: str | None = None


@dataclass
class AnalysisResult:
    """Complete analysis output."""

    sections: list[SectionInfo]
    slots: list[SlotInfo]
    tokens: TokenInfo
    esp_platform: str | None
    complexity: ComplexityInfo
    layout_type: str
    wrapper: WrapperInfo | None = None


# ── ESP detection patterns ──

_ESP_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("salesforce", re.compile(r"%%[=]?[^%]+%%")),
    ("braze", re.compile(r"\{\{\$\{[^}]+\}\}\}")),
    ("braze", re.compile(r"connected_content", re.IGNORECASE)),
    ("mailchimp", re.compile(r"\*\|[A-Z_]+\|\*")),
    ("shopify", re.compile(r"\{%\s*(if|for|unless)\b")),
    ("liquid", re.compile(r"\{\{\s+\w+\s+\}\}")),
    ("sendgrid", re.compile(r"\{\{#if\b")),
    ("handlebars", re.compile(r"\{\{[^{}\s]+\}\}")),
    ("erb", re.compile(r"<%=?\s+\w+")),
]

# ── Component type detection keywords ──

_HERO_KEYWORDS = {"hero", "banner", "masthead", "jumbotron"}
_HEADER_KEYWORDS = {"header", "logo", "nav", "navigation", "topbar"}
_FOOTER_KEYWORDS = {"footer", "unsubscribe", "copyright", "legal", "address"}
_CTA_KEYWORDS = {"button", "cta", "call-to-action"}
_DIVIDER_KEYWORDS = {"divider", "spacer", "separator"}

_MSO_WRAPPER_RE = re.compile(
    r"(<!--\[if\s+mso\]>.*?<table[^>]*>.*?<tr>.*?<td[^>]*>.*?<!\[endif\]-->)",
    re.DOTALL | re.IGNORECASE,
)


class TemplateAnalyzer:
    """Analyzes raw HTML to extract template structure without LLM calls."""

    def analyze(self, sanitized_html: str) -> AnalysisResult:
        """Run full analysis pipeline."""
        tree = lxml_html.fromstring(sanitized_html)
        sections, wrapper_info = self._detect_sections(tree, sanitized_html)
        slots = self._extract_slots(tree, sections)
        tokens = self._extract_tokens(tree)
        esp = self._detect_esp_platform(sanitized_html)
        complexity = self._measure_complexity(tree, sanitized_html)
        layout = self._infer_layout_type(sections, complexity, sanitized_html)

        logger.info(
            "template_upload.analysis_complete",
            sections=len(sections),
            slots=len(slots),
            esp=esp,
            layout=layout,
        )
        return AnalysisResult(
            sections=sections,
            slots=slots,
            tokens=tokens,
            esp_platform=esp,
            complexity=complexity,
            layout_type=layout,
            wrapper=wrapper_info,
        )

    def _detect_sections(
        self, tree: HtmlElement, raw_html: str
    ) -> tuple[list[SectionInfo], WrapperInfo | None]:
        """Detect top-level structural sections in the email template."""
        sections: list[SectionInfo] = []
        wrapper_info: WrapperInfo | None = None
        body = tree.find(".//body")
        root = body if body is not None else tree

        # Look for top-level tables with role="presentation" or direct children
        candidates: list[HtmlElement] = []
        for child in root:
            if not isinstance(child, HtmlElement):
                continue
            if child.tag == "table":
                candidates.append(child)
            elif child.tag in ("div", "section", "header", "footer", "main"):
                candidates.append(child)
            elif child.tag == "center":
                # Common wrapper — look inside for tables
                for inner in child:
                    if isinstance(inner, HtmlElement) and inner.tag == "table":
                        candidates.append(inner)

        # If we found a single wrapper table, look inside it for nested tables as sections
        if len(candidates) == 1 and candidates[0].tag == "table":
            wrapper = candidates[0]
            inner_tables = wrapper.findall(".//tr/td//table")
            if len(inner_tables) >= 2:
                # Extract wrapper metadata before discarding
                wrapper_info = self._extract_wrapper_info(wrapper, raw_html)
                candidates = inner_tables

        for idx, elem in enumerate(candidates):
            component = self._classify_component(elem, idx, len(candidates))
            element_count = sum(1 for _ in elem.iter())
            section_id = f"section_{idx}"
            sections.append(
                SectionInfo(
                    section_id=section_id,
                    component_name=component,
                    element_count=element_count,
                    layout_type=self._section_layout_type(elem),
                    element=elem,
                )
            )

        if not sections:
            # Fallback: treat the whole document as one section
            element_count = len(list(root.iter()))
            sections.append(
                SectionInfo(
                    section_id="section_0",
                    component_name="content",
                    element_count=element_count,
                    layout_type="single_column",
                    element=root,
                )
            )

        return sections, wrapper_info

    def _extract_wrapper_info(self, wrapper: HtmlElement, raw_html: str) -> WrapperInfo:
        """Extract centering metadata from wrapper table before discarding it."""
        # Find the <td> child that contains the inner tables
        inner_td = wrapper.find(".//tr/td")
        inner_td_style = inner_td.get("style") if inner_td is not None else None

        # Search for MSO conditional wrapper in raw HTML *before* the wrapper table.
        # lxml strips comments, so we must regex the raw string. Only search the
        # portion before the wrapper <table> to avoid matching inner MSO ghost
        # tables (e.g. column-layout ghost tables inside sections).
        mso_wrapper: str | None = None
        source_line = wrapper.sourceline
        if source_line is not None:
            # sourceline is 1-based; grab everything before that line
            prefix = "\n".join(raw_html.splitlines()[: source_line - 1])
            mso_match = _MSO_WRAPPER_RE.search(prefix)
            mso_wrapper = mso_match.group(1) if mso_match else None

        return WrapperInfo(
            tag=str(wrapper.tag),
            width=wrapper.get("width"),
            align=wrapper.get("align"),
            style=wrapper.get("style"),
            bgcolor=wrapper.get("bgcolor"),
            cellpadding=wrapper.get("cellpadding"),
            cellspacing=wrapper.get("cellspacing"),
            border=wrapper.get("border"),
            role=wrapper.get("role"),
            inner_td_style=inner_td_style,
            mso_wrapper=mso_wrapper,
        )

    def _classify_component(self, elem: HtmlElement, idx: int, total: int) -> str:
        """Classify a section element into a component type."""
        text_content = (elem.text_content() or "").lower()
        class_attr = (elem.get("class") or "").lower()
        combined = f"{text_content} {class_attr}"

        if idx == 0 and any(kw in combined for kw in _HEADER_KEYWORDS):
            return "header"
        if idx == total - 1 and any(kw in combined for kw in _FOOTER_KEYWORDS):
            return "footer"
        if any(kw in combined for kw in _HERO_KEYWORDS):
            return "hero"
        if any(kw in combined for kw in _CTA_KEYWORDS):
            return "cta"
        if any(kw in combined for kw in _DIVIDER_KEYWORDS):
            return "divider"

        # Check for multi-column layout (2+ columns in any single row)
        for row in elem.findall(".//tr"):
            if len(row.findall("td")) >= 2:
                return "columns"

        # Check for large image (hero heuristic)
        imgs = elem.findall(".//img")
        for img in imgs:
            width = img.get("width", "")
            if width.isdigit() and int(width) >= 500:
                return "hero"

        return "content"

    def _section_layout_type(self, elem: HtmlElement) -> str:
        """Determine layout type of a section (single_column, multi_column)."""
        rows = elem.findall(".//tr")
        for row in rows:
            tds = row.findall("td")
            if len(tds) >= 2:
                return "multi_column"
        return "single_column"

    def _extract_slots(self, tree: HtmlElement, sections: list[SectionInfo]) -> list[SlotInfo]:  # noqa: ARG002
        """Identify fillable content regions within sections."""
        slots: list[SlotInfo] = []
        slot_counter: dict[str, int] = {}

        for section in sections:
            elem = section.element
            if elem is None:
                continue

            # Text slots: headings and paragraphs with meaningful text
            for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                for heading in elem.iter(tag):
                    text = (heading.text_content() or "").strip()
                    if len(text) >= 5:
                        slot_id = self._make_slot_id(section.section_id, "headline", slot_counter)
                        slots.append(
                            SlotInfo(
                                slot_id=slot_id,
                                slot_type="headline",
                                selector=f"{section.section_id} {tag}",
                                required=section.component_name == "hero",
                                max_chars=self._estimate_max_chars(heading),
                                content_preview=text[:80],
                                section_id=section.section_id,
                            )
                        )

            for p in elem.iter("p"):
                text = (p.text_content() or "").strip()
                if len(text) >= 20:
                    slot_id = self._make_slot_id(section.section_id, "body", slot_counter)
                    slots.append(
                        SlotInfo(
                            slot_id=slot_id,
                            slot_type="body",
                            selector=f"{section.section_id} p",
                            required=False,
                            max_chars=self._estimate_max_chars(p),
                            content_preview=text[:80],
                            section_id=section.section_id,
                        )
                    )

            # Image slots (non-tracking pixels)
            for img in elem.iter("img"):
                width = img.get("width", "0")
                height = img.get("height", "0")
                w = int(width) if width.isdigit() else 0
                h = int(height) if height.isdigit() else 0
                if w <= 2 and h <= 2:
                    continue  # Skip tracking pixels
                slot_id = self._make_slot_id(section.section_id, "image", slot_counter)
                src = img.get("src", "")
                slots.append(
                    SlotInfo(
                        slot_id=slot_id,
                        slot_type="image",
                        selector=f"{section.section_id} img",
                        required=section.component_name == "hero",
                        max_chars=None,
                        content_preview=src[:80] if src else "",
                        section_id=section.section_id,
                    )
                )

            # CTA slots (links with button styling)
            for a in elem.iter("a"):
                style = (a.get("style") or "").lower()
                class_attr = (a.get("class") or "").lower()
                text = (a.text_content() or "").strip()
                is_button = (
                    "padding" in style
                    or "background" in style
                    or "button" in class_attr
                    or "btn" in class_attr
                )
                if is_button and len(text) >= 2:
                    slot_id = self._make_slot_id(section.section_id, "cta", slot_counter)
                    slots.append(
                        SlotInfo(
                            slot_id=slot_id,
                            slot_type="cta",
                            selector=f"{section.section_id} a",
                            required=section.component_name in ("hero", "cta"),
                            max_chars=50,
                            content_preview=text[:50],
                            section_id=section.section_id,
                        )
                    )

        return slots

    def _make_slot_id(self, section_id: str, slot_type: str, counter: dict[str, int]) -> str:
        """Generate a unique slot ID."""
        key = f"{section_id}_{slot_type}"
        counter[key] = counter.get(key, 0) + 1
        return f"{key}_{counter[key]}"

    def _estimate_max_chars(self, elem: HtmlElement) -> int | None:
        """Estimate max chars from container width heuristic."""
        parent = elem.getparent()
        if parent is not None:
            width = parent.get("width", "")
            if width.isdigit():
                # ~8px per character is a rough heuristic
                return max(int(width) // 8, 20)
        return None

    def _extract_tokens(self, tree: HtmlElement) -> TokenInfo:
        """Extract design tokens from inline styles."""
        hex_pattern = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
        font_pattern = re.compile(r"font-family:\s*([^;]+)")
        font_size_pattern = re.compile(r"font-size:\s*(\d+(?:px|em|rem|pt))")
        padding_pattern = re.compile(r"padding[^:]*:\s*(\d+(?:px|em|rem))")
        font_weight_pattern = re.compile(r"font-weight:\s*(\d{3}|bold|normal|lighter|bolder)")
        line_height_pattern = re.compile(r"line-height:\s*([\d.]+(?:px|em|rem|%)?)")
        letter_spacing_pattern = re.compile(r"letter-spacing:\s*(-?[\d.]+(?:px|em|rem)?)")
        padding_side_pattern = re.compile(r"padding-(top|right|bottom|left):\s*(\d+(?:px|em|rem))")

        bg_colors: list[str] = []
        text_colors: list[str] = []
        all_colors: list[str] = []
        fonts_heading: list[str] = []
        fonts_body: list[str] = []
        font_sizes: list[str] = []
        spacings: list[str] = []
        font_weights_heading: list[str] = []
        font_weights_body: list[str] = []
        line_heights_heading: list[str] = []
        line_heights_body: list[str] = []
        letter_spacings_all: list[str] = []
        color_roles: dict[str, list[str]] = {
            "link": [],
            "heading_text": [],
            "muted": [],
            "accent": [],
        }

        for elem in tree.iter():
            if not isinstance(elem, HtmlElement):
                continue
            style = elem.get("style", "")
            if not style:
                continue

            tag = elem.tag

            # Colors
            for match in hex_pattern.finditer(style):
                color = match.group().upper()
                all_colors.append(color)
                lower_style = style.lower()
                if "background" in lower_style[: match.start()]:
                    bg_colors.append(color)
                elif "color" in lower_style[: match.start()]:
                    text_colors.append(color)

            # Fonts
            for match in font_pattern.finditer(style):
                font_stack = match.group(1).strip().strip(";").strip("'\"")
                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    fonts_heading.append(font_stack)
                else:
                    fonts_body.append(font_stack)

            # Font sizes
            for match in font_size_pattern.finditer(style):
                font_sizes.append(match.group(1))

            # Spacing (shorthand)
            for match in padding_pattern.finditer(style):
                spacings.append(match.group(1))

            # Per-side padding (longhand from 31.2 expansion)
            for match in padding_side_pattern.finditer(style):
                spacings.append(match.group(2))

            # Font weights — classify by tag
            for match in font_weight_pattern.finditer(style):
                val = match.group(1)
                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    font_weights_heading.append(val)
                else:
                    font_weights_body.append(val)

            # Line heights
            for match in line_height_pattern.finditer(style):
                val = match.group(1)
                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    line_heights_heading.append(val)
                else:
                    line_heights_body.append(val)

            # Letter spacing
            for match in letter_spacing_pattern.finditer(style):
                letter_spacings_all.append(match.group(1))

            # Color roles by element context
            if tag == "a":
                for m in hex_pattern.finditer(style):
                    prefix = style.lower()[: m.start()]
                    if "color" in prefix:
                        color_roles["link"].append(m.group().upper())

        # Responsive extraction from <style> blocks
        responsive: dict[str, dict[str, list[str]]] = {}
        breakpoints: list[str] = []
        media_pattern = re.compile(r"@media[^{]*max-width:\s*(\d+px)[^{]*\{(.*?)\}", re.DOTALL)
        for style_el in tree.iter("style"):
            text = style_el.text or ""
            for m in media_pattern.finditer(text):
                bp = m.group(1)
                if bp not in breakpoints:
                    breakpoints.append(bp)
                block = m.group(2)
                bp_tokens: dict[str, list[str]] = responsive.setdefault(bp, {})
                for fs_m in font_size_pattern.finditer(block):
                    bp_tokens.setdefault("font_sizes", []).append(fs_m.group(1))
                for sp_m in padding_pattern.finditer(block):
                    bp_tokens.setdefault("spacing", []).append(sp_m.group(1))

        return TokenInfo(
            colors={
                "background": bg_colors,
                "text": text_colors,
                "all": all_colors,
            },
            fonts={
                "heading": fonts_heading,
                "body": fonts_body,
            },
            font_sizes={"all": font_sizes},
            spacing={"padding": spacings},
            font_weights={
                "heading": font_weights_heading,
                "body": font_weights_body,
            },
            line_heights={
                "heading": line_heights_heading,
                "body": line_heights_body,
            },
            letter_spacings={"all": letter_spacings_all},
            color_roles=color_roles,
            responsive=responsive,
            responsive_breakpoints=breakpoints,
        )

    def _detect_esp_platform(self, html: str) -> str | None:
        """Detect ESP platform from personalisation syntax."""
        for platform, pattern in _ESP_PATTERNS:
            if pattern.search(html):
                return platform
        return None

    def _measure_complexity(self, tree: HtmlElement, html: str) -> ComplexityInfo:
        """Measure template complexity metrics."""
        total_elements = sum(1 for _ in tree.iter())
        mso_count = html.count("<!--[if")

        # Max column count
        max_cols = 1
        for tr in tree.iter("tr"):
            tds = tr.findall("td")
            if len(tds) > max_cols:
                max_cols = len(tds)

        # Table nesting depth
        table_depth = self._max_table_depth(tree)

        # General nesting depth
        nesting = self._max_depth(tree)

        has_vml = "v:rect" in html or "v:roundrect" in html or "v:image" in html
        has_amp = "⚡4email" in html or "amp4email" in html.lower()

        return ComplexityInfo(
            column_count=max_cols,
            nesting_depth=nesting,
            mso_conditional_count=mso_count,
            total_elements=total_elements,
            table_nesting_depth=table_depth,
            has_vml=has_vml,
            has_amp=has_amp,
        )

    def _max_table_depth(self, elem: HtmlElement, depth: int = 0) -> int:
        """Calculate maximum table nesting depth."""
        max_d = depth
        for child in elem:
            if not isinstance(child, HtmlElement):
                continue
            child_depth = depth + 1 if child.tag == "table" else depth
            max_d = max(max_d, self._max_table_depth(child, child_depth))
        return max_d

    def _max_depth(self, elem: HtmlElement, depth: int = 0) -> int:
        """Calculate maximum element nesting depth."""
        max_d = depth
        for child in elem:
            if isinstance(child, HtmlElement):
                max_d = max(max_d, self._max_depth(child, depth + 1))
        return max_d

    def _infer_layout_type(
        self,
        sections: list[SectionInfo],
        complexity: ComplexityInfo,  # noqa: ARG002
        html: str,
    ) -> str:
        """Infer overall layout type: newsletter, promotional, transactional, retention."""
        html_lower = html.lower()

        # Transactional signals
        transactional_keywords = ["order", "receipt", "confirmation", "invoice", "shipping"]
        if sum(1 for kw in transactional_keywords if kw in html_lower) >= 2:
            return "transactional"

        # Retention signals
        retention_keywords = ["we miss you", "come back", "re-engage", "win back", "haven't seen"]
        if any(kw in html_lower for kw in retention_keywords):
            return "retention"

        # Newsletter: 4+ sections, repeating content patterns
        content_sections = [s for s in sections if s.component_name == "content"]
        if len(sections) >= 4 and len(content_sections) >= 2:
            return "newsletter"

        # Promotional: hero + CTA dominant
        has_hero = any(s.component_name == "hero" for s in sections)
        has_cta = any(s.component_name == "cta" for s in sections)
        if has_hero or has_cta:
            return "promotional"

        return "newsletter"
