"""Static analyzer for Word rendering engine dependencies in email HTML."""

from __future__ import annotations

import bisect
import re
from collections import Counter

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.qa_engine.outlook_analyzer.types import (
    ModernizationStep,
    OutlookAnalysis,
    OutlookDependency,
)

logger = get_logger(__name__)

# --- Compiled regex patterns ---

# VML element tags
_VML_TAG_RE = re.compile(
    r"<v:(roundrect|rect|oval|shape|textbox|fill|stroke|shadow|image)\b",
    re.IGNORECASE,
)

# MSO conditional blocks
_MSO_OPENER_RE = re.compile(r"<!--\[if\s+([^\]]*mso[^\]]*)\]>", re.IGNORECASE)
_MSO_CLOSER_RE = re.compile(r"<!\[endif\]-->")
_NON_MSO_OPENER_RE = re.compile(r"<!--\[if\s+!mso\]>", re.IGNORECASE)

# MSO CSS properties
_MSO_CSS_RE = re.compile(r"(mso-[\w-]+)\s*:", re.IGNORECASE)
_MSO_CSS_PROPERTIES = frozenset(
    {
        "mso-line-height-rule",
        "mso-table-lspace",
        "mso-table-rspace",
        "mso-padding-alt",
        "mso-border-alt",
        "mso-font-alt",
        "mso-style-name",
        "mso-style-type",
        "mso-ansi-font-size",
        "mso-bidi-font-size",
        "mso-font-charset",
        "mso-generic-font-family",
        "mso-font-pitch",
        "mso-font-signature",
        "mso-text-raise",
        "mso-highlight",
        "mso-margin-top-alt",
        "mso-margin-bottom-alt",
        "mso-element",
        "mso-element-frame-width",
        "mso-element-wrap",
    }
)

# .ExternalClass
_EXTERNAL_CLASS_RE = re.compile(r"\.ExternalClass\b", re.IGNORECASE)

# Word-wrap hacks
_WORD_WRAP_RE = re.compile(r"word-(?:wrap|break)\s*:\s*break-(?:all|word)", re.IGNORECASE)

# Modernization descriptions per type
_MODERNIZATION_DESCRIPTIONS: dict[str, str] = {
    "vml_shape": "Remove VML shapes and replace with CSS border-radius + background-color",
    "ghost_table": "Unwrap ghost tables into CSS-layout <div> elements",
    "mso_conditional": "Strip MSO conditional comment blocks",
    "mso_css": "Remove mso-* CSS property declarations",
    "dpi_image": "Normalize DPI-compensated images to CSS-only dimensions",
    "external_class": "Remove .ExternalClass CSS rules (Outlook.com specific)",
    "word_wrap_hack": "Replace word-wrap hacks with standard overflow-wrap",
}


class OutlookDependencyDetector:
    """Scans email HTML for Word rendering engine dependencies."""

    def analyze(self, html: str) -> OutlookAnalysis:
        """Parse HTML and return structured dependency report.

        All detection is regex/DOM-based -- no LLM calls.
        """
        if not html or not html.strip():
            return OutlookAnalysis()

        line_offsets = self._build_line_offsets(html)
        deps: list[OutlookDependency] = []

        # 1. VML shapes
        deps.extend(self._detect_vml(html, line_offsets))

        # 2. MSO conditionals (and ghost tables within them)
        mso_deps, ghost_deps = self._detect_mso_and_ghosts(html, line_offsets)
        deps.extend(mso_deps)
        deps.extend(ghost_deps)

        # 3. MSO CSS properties
        deps.extend(self._detect_mso_css(html, line_offsets))

        # 4. DPI-compensated images
        deps.extend(self._detect_dpi_images(html))

        # 5. .ExternalClass
        deps.extend(self._detect_external_class(html, line_offsets))

        # 6. Word-wrap hacks
        deps.extend(self._detect_word_wrap(html, line_offsets))

        # Aggregate
        type_counts = Counter(d.type for d in deps)
        removable = [d for d in deps if d.removable]
        byte_savings = sum(len(d.code_snippet.encode()) for d in removable)

        # Build modernization plan
        plan = self._build_modernization_plan(deps, type_counts)

        logger.info(
            "outlook_analyzer.analysis_completed",
            total=len(deps),
            removable=len(removable),
            byte_savings=byte_savings,
        )

        return OutlookAnalysis(
            dependencies=deps,
            total_count=len(deps),
            removable_count=len(removable),
            byte_savings=byte_savings,
            modernization_plan=plan,
            vml_count=type_counts.get("vml_shape", 0),
            ghost_table_count=type_counts.get("ghost_table", 0),
            mso_conditional_count=type_counts.get("mso_conditional", 0),
            mso_css_count=type_counts.get("mso_css", 0),
            dpi_image_count=type_counts.get("dpi_image", 0),
            external_class_count=type_counts.get("external_class", 0),
            word_wrap_count=type_counts.get("word_wrap_hack", 0),
        )

    # --- Detection methods ---

    def _detect_vml(self, html: str, line_offsets: list[int]) -> list[OutlookDependency]:
        deps: list[OutlookDependency] = []
        for m in _VML_TAG_RE.finditer(html):
            line_num = self._offset_to_line(line_offsets, m.start())
            snippet = self._snippet(html, m.start(), m.end())
            deps.append(
                OutlookDependency(
                    type="vml_shape",
                    location=f"line {line_num}, <v:{m.group(1)}>",
                    line_number=line_num,
                    code_snippet=snippet,
                    severity="high",
                    removable=True,
                    modern_replacement="CSS border-radius + background-color for buttons; CSS clip-path for shapes",
                )
            )
        return deps

    def _detect_mso_and_ghosts(
        self, html: str, line_offsets: list[int]
    ) -> tuple[list[OutlookDependency], list[OutlookDependency]]:
        mso_deps: list[OutlookDependency] = []
        ghost_deps: list[OutlookDependency] = []

        for opener in _MSO_OPENER_RE.finditer(html):
            # Skip <!--[if !mso]> (non-mso conditionals)
            if _NON_MSO_OPENER_RE.match(html, opener.start()):
                continue

            closer = _MSO_CLOSER_RE.search(html, opener.end())
            if not closer:
                continue

            block_content = html[opener.end() : closer.start()]
            line_num = self._offset_to_line(line_offsets, opener.start())
            snippet = self._snippet(html, opener.start(), closer.end())

            # Check if this is a ghost table (table with no visible text content)
            if self._is_ghost_table(block_content):
                ghost_deps.append(
                    OutlookDependency(
                        type="ghost_table",
                        location=f"line {line_num}, ghost table in MSO conditional",
                        line_number=line_num,
                        code_snippet=snippet,
                        severity="high",
                        removable=True,
                        modern_replacement="Remove table, unwrap content into <div> with CSS layout",
                    )
                )

            mso_deps.append(
                OutlookDependency(
                    type="mso_conditional",
                    location=f"line {line_num}, <!--[if {opener.group(1)}]>",
                    line_number=line_num,
                    code_snippet=snippet,
                    severity="medium",
                    removable=True,
                    modern_replacement="Remove conditional block (New Outlook uses Chromium)",
                )
            )

        return mso_deps, ghost_deps

    def _detect_mso_css(self, html: str, line_offsets: list[int]) -> list[OutlookDependency]:
        deps: list[OutlookDependency] = []
        seen: set[tuple[int, str]] = set()
        for m in _MSO_CSS_RE.finditer(html):
            prop_name = m.group(1).lower()
            if prop_name not in _MSO_CSS_PROPERTIES:
                continue
            # Deduplicate by line to avoid noisy reports
            line_num = self._offset_to_line(line_offsets, m.start())
            key = (line_num, prop_name)
            if key in seen:
                continue
            seen.add(key)

            snippet = self._snippet(html, m.start(), m.end())
            deps.append(
                OutlookDependency(
                    type="mso_css",
                    location=f"line {line_num}, {prop_name}",
                    line_number=line_num,
                    code_snippet=snippet,
                    severity="low",
                    removable=True,
                    modern_replacement="Remove property (no standard CSS equivalent needed)",
                )
            )
        return deps

    def _detect_dpi_images(self, html: str) -> list[OutlookDependency]:
        deps: list[OutlookDependency] = []
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            html_width = img.get("width")
            html_height = img.get("height")
            style = img.get("style", "")

            if not html_width and not html_height:
                continue
            if not style:
                continue

            # Check for CSS width/height in style
            css_width = re.search(r"width\s*:\s*(\d+)", str(style))
            css_height = re.search(r"height\s*:\s*(\d+)", str(style))

            if not css_width and not css_height:
                continue

            # Check if values differ (DPI compensation)
            has_mismatch = False
            if html_width and css_width:
                try:
                    if int(str(html_width)) != int(css_width.group(1)):
                        has_mismatch = True
                except ValueError:
                    pass
            if html_height and css_height:
                try:
                    if int(str(html_height)) != int(css_height.group(1)):
                        has_mismatch = True
                except ValueError:
                    pass

            if has_mismatch:
                # Find approximate line number from source position
                src = img.get("src", "unknown")
                line_num = self._find_element_line(html, f'src="{src}"')
                snippet = str(img)[:200]
                deps.append(
                    OutlookDependency(
                        type="dpi_image",
                        location=f'line {line_num}, <img src="{src}">',
                        line_number=line_num,
                        code_snippet=snippet,
                        severity="low",
                        removable=True,
                        modern_replacement="Use CSS dimensions only",
                    )
                )
        return deps

    def _detect_external_class(self, html: str, line_offsets: list[int]) -> list[OutlookDependency]:
        deps: list[OutlookDependency] = []
        for m in _EXTERNAL_CLASS_RE.finditer(html):
            line_num = self._offset_to_line(line_offsets, m.start())
            snippet = self._snippet(html, m.start(), m.end())
            deps.append(
                OutlookDependency(
                    type="external_class",
                    location=f"line {line_num}, .ExternalClass rule",
                    line_number=line_num,
                    code_snippet=snippet,
                    severity="medium",
                    removable=True,
                    modern_replacement="Remove .ExternalClass rules (Outlook.com specific)",
                )
            )
        return deps

    def _detect_word_wrap(self, html: str, line_offsets: list[int]) -> list[OutlookDependency]:
        deps: list[OutlookDependency] = []
        for m in _WORD_WRAP_RE.finditer(html):
            line_num = self._offset_to_line(line_offsets, m.start())
            snippet = self._snippet(html, m.start(), m.end())
            deps.append(
                OutlookDependency(
                    type="word_wrap_hack",
                    location=f"line {line_num}, {m.group(0)}",
                    line_number=line_num,
                    code_snippet=snippet,
                    severity="low",
                    removable=True,
                    modern_replacement="Use standard overflow-wrap: break-word",
                )
            )
        return deps

    # --- Helpers ---

    def _build_line_offsets(self, html: str) -> list[int]:
        """Build sorted list of character offsets where each line starts."""
        offsets = [0]
        for i, ch in enumerate(html):
            if ch == "\n":
                offsets.append(i + 1)
        return offsets

    def _offset_to_line(self, line_offsets: list[int], offset: int) -> int:
        """Convert character offset to 1-based line number via binary search."""
        idx = bisect.bisect_right(line_offsets, offset) - 1
        return max(1, idx + 1)

    def _snippet(self, html: str, start: int, end: int, max_len: int = 200) -> str:
        """Extract and trim code snippet around a match."""
        # Extend to capture more context
        context_end = min(len(html), end + 80)
        raw = html[start:context_end].strip()
        if len(raw) > max_len:
            return raw[:max_len]
        return raw

    def _find_element_line(self, html: str, marker: str) -> int:
        """Find 1-based line number of a marker string in HTML."""
        idx = html.find(marker)
        if idx == -1:
            return 1
        return html[:idx].count("\n") + 1

    def _is_ghost_table(self, block_content: str) -> bool:
        """Check if MSO block contains only a table wrapper with no visible text."""
        stripped = block_content.strip()
        if not stripped:
            return False
        # Must contain a table
        if "<table" not in stripped.lower():
            return False
        # Parse and check for visible text content
        soup = BeautifulSoup(stripped, "html.parser")
        text = soup.get_text(strip=True)
        # Ghost tables have no meaningful text — they're pure structure
        return len(text) == 0

    def _build_modernization_plan(
        self,
        deps: list[OutlookDependency],
        type_counts: Counter[str],
    ) -> list[ModernizationStep]:
        """Group dependencies by type into modernization steps."""
        plan: list[ModernizationStep] = []
        for dep_type, count in sorted(type_counts.items()):
            desc = _MODERNIZATION_DESCRIPTIONS.get(dep_type, f"Remove {dep_type}")
            type_deps = [d for d in deps if d.type == dep_type and d.removable]
            savings = sum(len(d.code_snippet.encode()) for d in type_deps)
            plan.append(
                ModernizationStep(
                    description=desc,
                    dependency_type=dep_type,
                    removals=count,
                    byte_savings=savings,
                )
            )
        return plan
