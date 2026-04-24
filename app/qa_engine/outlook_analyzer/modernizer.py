"""Applies safe modernizations to remove Word-engine dependencies."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.core.exceptions import DomainValidationError
from app.core.logging import get_logger
from app.qa_engine.outlook_analyzer.types import ModernizeResult, OutlookAnalysis

logger = get_logger(__name__)

# Valid targets
VALID_TARGETS = frozenset({"new_outlook", "dual_support", "audit_only"})

# MSO conditional patterns
# Bounded quantifiers prevent polynomial backtracking (py/polynomial-redos).
_MSO_BLOCK_RE = re.compile(
    r"<!--\[if\s{1,20}[^\]]{0,200}mso[^\]]{0,200}\]>.{0,100000}?<!\[endif\]-->",
    re.IGNORECASE | re.DOTALL,
)
_NON_MSO_BLOCK_RE = re.compile(
    r"<!--\[if\s{1,20}!mso\]><!-->(.{0,100000}?)<!--<!\[endif\]-->",
    re.IGNORECASE | re.DOTALL,
)
_MSO_CSS_PROP_RE = re.compile(
    r"\s{0,20}mso-[\w-]{1,100}\s{0,20}:[^;]{0,1000};?",
    re.IGNORECASE,
)
_EXTERNAL_CLASS_RULE_RE = re.compile(
    r"\.ExternalClass[^{]{0,1000}\{[^}]{0,5000}\}\s{0,20}",
    re.IGNORECASE,
)
_WORD_WRAP_RE = re.compile(
    r"word-(?:wrap|break)\s*:\s*break-(?:all|word)",
    re.IGNORECASE,
)


class OutlookModernizer:
    """Applies deterministic HTML transformations to remove Word-engine dependencies."""

    def modernize(
        self,
        html: str,
        analysis: OutlookAnalysis,
        target: str = "new_outlook",
    ) -> ModernizeResult:
        """Apply safe modernizations based on target mode.

        - new_outlook: Aggressively remove all Word hacks (New Outlook = Chromium)
        - dual_support: Keep hacks inside <!--[if mso]> for transition period
        - audit_only: Return analysis without modifications
        """
        if target not in VALID_TARGETS:
            raise DomainValidationError(
                f"Invalid target: {target}. Must be one of: {', '.join(sorted(VALID_TARGETS))}"
            )

        if target == "audit_only" or not analysis.dependencies:
            return ModernizeResult(
                html=html,
                changes_applied=0,
                bytes_before=len(html.encode()),
                bytes_after=len(html.encode()),
                target=target,
            )

        result_html = html
        changes = 0

        if target == "new_outlook":
            result_html, c = self._remove_mso_conditionals(result_html)
            changes += c
            result_html, c = self._remove_mso_css(result_html)
            changes += c
            result_html, c = self._remove_external_class(result_html)
            changes += c
            result_html, c = self._normalize_dpi_images(result_html)
            changes += c
            result_html, c = self._normalize_word_wrap(result_html)
            changes += c

        elif target == "dual_support":
            result_html, c = self._remove_mso_css_outside_conditionals(result_html)
            changes += c
            result_html, c = self._remove_external_class(result_html)
            changes += c
            result_html, c = self._normalize_dpi_images(result_html)
            changes += c
            result_html, c = self._normalize_word_wrap(result_html)
            changes += c

        # Sanitize output
        from app.ai.shared import sanitize_html_xss

        result_html = sanitize_html_xss(result_html)

        bytes_before = len(html.encode())
        bytes_after = len(result_html.encode())

        logger.info(
            "outlook_analyzer.modernize_completed",
            target=target,
            changes=changes,
            bytes_saved=bytes_before - bytes_after,
        )

        return ModernizeResult(
            html=result_html,
            changes_applied=changes,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
            target=target,
        )

    # --- Transformation methods ---

    def _remove_mso_conditionals(self, html: str) -> tuple[str, int]:
        """Strip all <!--[if mso]>...<![endif]--> blocks.

        Keep <!--[if !mso]> content (unwrap the conditional, keep the inner HTML).
        """
        changes = 0

        # First unwrap <!--[if !mso]><!--> content <!--<![endif]-->
        def unwrap_non_mso(m: re.Match[str]) -> str:
            nonlocal changes
            changes += 1
            return m.group(1)

        html = _NON_MSO_BLOCK_RE.sub(unwrap_non_mso, html)

        # Then remove all <!--[if *mso*]>...<![endif]--> blocks
        def remove_mso(_m: re.Match[str]) -> str:
            nonlocal changes
            changes += 1
            return ""

        html = _MSO_BLOCK_RE.sub(remove_mso, html)

        return html, changes

    def _remove_mso_css(self, html: str) -> tuple[str, int]:
        """Remove mso-* property declarations from all style contexts."""
        changes = 0

        def strip_mso_prop(_m: re.Match[str]) -> str:
            nonlocal changes
            changes += 1
            return ""

        html = _MSO_CSS_PROP_RE.sub(strip_mso_prop, html)
        return html, changes

    def _remove_mso_css_outside_conditionals(self, html: str) -> tuple[str, int]:
        """Remove mso-* CSS only outside <!--[if mso]> blocks (for dual_support)."""
        # Find all MSO conditional block ranges
        mso_ranges: list[tuple[int, int]] = []
        for m in _MSO_BLOCK_RE.finditer(html):
            mso_ranges.append((m.start(), m.end()))

        def in_mso_block(pos: int) -> bool:
            return any(start <= pos < end for start, end in mso_ranges)

        changes = 0
        parts: list[str] = []
        last_end = 0

        for m in _MSO_CSS_PROP_RE.finditer(html):
            if not in_mso_block(m.start()):
                parts.append(html[last_end : m.start()])
                last_end = m.end()
                changes += 1

        parts.append(html[last_end:])
        return "".join(parts), changes

    def _remove_external_class(self, html: str) -> tuple[str, int]:
        """Remove .ExternalClass CSS rules."""
        changes = 0

        def remove_rule(_m: re.Match[str]) -> str:
            nonlocal changes
            changes += 1
            return ""

        html = _EXTERNAL_CLASS_RULE_RE.sub(remove_rule, html)
        return html, changes

    def _normalize_dpi_images(self, html: str) -> tuple[str, int]:
        """Remove HTML width/height attributes from imgs that have CSS dimensions."""
        soup = BeautifulSoup(html, "html.parser")
        changes = 0

        for img in soup.find_all("img"):
            html_width = img.get("width")
            html_height = img.get("height")
            style = img.get("style", "")

            if not style:
                continue

            css_has_width = bool(re.search(r"width\s*:", str(style)))
            css_has_height = bool(re.search(r"height\s*:", str(style)))

            removed = False
            if html_width and css_has_width:
                del img["width"]
                removed = True
            if html_height and css_has_height:
                del img["height"]
                removed = True

            if removed:
                changes += 1

        if changes > 0:
            return str(soup), changes
        return html, 0

    def _normalize_word_wrap(self, html: str) -> tuple[str, int]:
        """Replace word-wrap hacks with standard overflow-wrap: break-word."""
        changes = 0

        def replace_wrap(_m: re.Match[str]) -> str:
            nonlocal changes
            changes += 1
            return "overflow-wrap: break-word"

        html = _WORD_WRAP_RE.sub(replace_wrap, html)
        return html, changes
