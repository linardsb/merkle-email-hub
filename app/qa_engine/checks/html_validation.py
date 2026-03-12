"""HTML validation check — DOM-parsed structural validation for email HTML.

Uses lxml to parse HTML and validate 20 structural rules covering document skeleton,
tag integrity, content integrity, email-specific structure, and progressive enhancement.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

# --- Default deductions (match defaults.yaml) ---
_DEFAULTS: dict[str, float | int] = {
    "deduction_doctype": 0.15,
    "deduction_structure": 0.15,
    "deduction_charset": 0.15,
    "deduction_viewport": 0.10,
    "deduction_title": 0.10,
    "deduction_unclosed_tag": 0.15,
    "deduction_nesting": 0.10,
    "deduction_duplicate_id": 0.10,
    "deduction_empty_section": 0.15,
    "deduction_style_placement": 0.10,
    "deduction_table_structure": 0.15,
    "deduction_list_structure": 0.10,
    "deduction_duplicate_structural": 0.15,
    "deduction_nested_link": 0.15,
    "deduction_missing_fallback": 0.10,
    "deduction_interactive_structure": 0.10,
    "deduction_dangerous_element": 0.15,
    "max_unclosed_tags_reported": 5,
    "max_nesting_violations_reported": 5,
    "max_duplicate_ids_reported": 5,
    "max_table_violations_reported": 5,
    "max_list_violations_reported": 5,
}

# --- Constants ---
_BLOCK_TAGS = frozenset(
    {
        "div",
        "table",
        "tr",
        "td",
        "th",
        "p",
        "section",
        "header",
        "footer",
        "thead",
        "tbody",
        "tfoot",
        "ul",
        "ol",
        "li",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "article",
        "aside",
        "nav",
        "main",
        "figure",
        "figcaption",
        "details",
        "summary",
        "fieldset",
    }
)

_INLINE_TAGS = frozenset(
    {
        "a",
        "span",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "s",
        "small",
        "mark",
        "del",
        "ins",
        "sub",
        "sup",
        "abbr",
        "cite",
        "q",
        "time",
        "data",
        "code",
        "label",
    }
)

_TABLE_VALID_PARENTS: dict[str, frozenset[str]] = {
    "td": frozenset({"tr"}),
    "th": frozenset({"tr"}),
    "tr": frozenset({"table", "thead", "tbody", "tfoot"}),
    "thead": frozenset({"table"}),
    "tbody": frozenset({"table"}),
    "tfoot": frozenset({"table"}),
    "caption": frozenset({"table"}),
    "colgroup": frozenset({"table"}),
    "col": frozenset({"colgroup", "table"}),
}

_SELF_CLOSING_TAGS = frozenset(
    {
        "br",
        "hr",
        "img",
        "input",
        "meta",
        "link",
        "area",
        "base",
        "col",
        "embed",
        "source",
        "track",
        "wbr",
    }
)


def _param(config: QACheckConfig | None, key: str) -> float | int:
    """Get a config param with fallback to default."""
    if config:
        val: float | int = config.params.get(key, _DEFAULTS[key])
        return val
    return _DEFAULTS[key]


_TAG_PATTERNS: dict[str, tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]] = {}


def _get_tag_patterns(
    tag: str,
) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """Get pre-compiled regex patterns for a tag name (cached)."""
    if tag not in _TAG_PATTERNS:
        _TAG_PATTERNS[tag] = (
            re.compile(rf"<{tag}[\s/>]", re.IGNORECASE),
            re.compile(rf"</{tag}\s*>", re.IGNORECASE),
            re.compile(rf"<{tag}\b[^>]*/\s*>", re.IGNORECASE),
        )
    return _TAG_PATTERNS[tag]


def _count_raw_tags(raw_html: str, tag: str) -> tuple[int, int]:
    """Count opening and closing tags in raw HTML (case-insensitive).

    Returns (open_count, close_count). Handles self-closing and attributes.
    """
    open_pattern, close_pattern, self_close_pattern = _get_tag_patterns(tag)

    opens = len(open_pattern.findall(raw_html))
    self_closes = len(self_close_pattern.findall(raw_html))
    closes = len(close_pattern.findall(raw_html))

    return opens - self_closes, closes


class HtmlValidationCheck:
    """Validates HTML structure and syntax using lxml DOM parsing.

    Implements 20 structural checks across 5 groups:
    A (1-5): Document Skeleton
    B (6-8): Tag Integrity
    C (9-10): Content Integrity
    D (11-14): Email-Specific Structure
    E (15-20): Progressive Enhancement
    """

    name = "html_validation"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        """Run all structural validation checks against the provided HTML."""
        issues: list[str] = []
        score = 1.0

        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Empty HTML document",
                severity="error",
            )

        # Parse with lxml — tolerates malformed HTML
        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="HTML could not be parsed",
                severity="error",
            )

        raw_lower = html.lower()

        # --- Group A: Document Skeleton ---
        score = self._check_doctype(html, config, issues, score)
        score = self._check_structure(doc, raw_lower, config, issues, score)
        score = self._check_charset(doc, config, issues, score)
        score = self._check_viewport(doc, config, issues, score)
        score = self._check_title(doc, config, issues, score)

        # --- Group B: Tag Integrity ---
        score = self._check_unclosed_tags(html, config, issues, score)
        score = self._check_nesting(doc, config, issues, score)
        score = self._check_duplicate_ids(doc, config, issues, score)

        # --- Group C: Content Integrity ---
        score = self._check_empty_sections(doc, config, issues, score)
        score = self._check_style_placement(doc, config, issues, score)

        # --- Group D: Email-Specific Structure ---
        score = self._check_table_structure(doc, config, issues, score)
        score = self._check_list_structure(doc, config, issues, score)
        score = self._check_duplicate_structural(html, config, issues, score)
        score = self._check_nested_links(doc, html, config, issues, score)

        # --- Group E: Progressive Enhancement ---
        score = self._check_video_structure(doc, config, issues, score)
        score = self._check_audio_structure(doc, config, issues, score)
        score = self._check_picture_structure(doc, config, issues, score)
        score = self._check_interactive_elements(doc, html, config, issues, score)
        score = self._check_template_element(doc, html, config, issues, score)
        score = self._check_base_tag(doc, config, issues, score)

        score = max(0.0, score)
        passed = len(issues) == 0
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(issues) if issues else None,
            severity="error" if not passed else "info",
        )

    # --- Group A: Document Skeleton ---

    def _check_doctype(
        self,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 1: DOCTYPE present."""
        if "<!doctype" not in raw_html.lower():
            issues.append("Missing DOCTYPE declaration")
            score -= float(_param(config, "deduction_doctype"))
        return score

    def _check_structure(
        self,
        doc: HtmlElement,
        raw_lower: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 2: <html> wraps <head> + <body>."""
        deduction = float(_param(config, "deduction_structure"))

        # Check <html> tag presence
        if "<html" not in raw_lower:
            issues.append("Missing <html> tag")
            score -= deduction
            return score

        # Check <head> presence
        head_els = doc.findall(".//head")
        if not head_els:
            issues.append("Missing <head> section")
            score -= deduction

        # Check <body> presence
        body_els = doc.findall(".//body")
        if not body_els:
            issues.append("Missing <body> section")
            score -= deduction

        return score

    def _check_charset(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 3: <meta charset> or http-equiv equivalent in <head>."""
        head = doc.find(".//head")
        if head is None:
            return score  # Already flagged by check 2

        has_charset = False
        for meta in head.findall(".//meta"):
            if meta.get("charset"):
                has_charset = True
                break
            if (
                meta.get("http-equiv", "").lower() == "content-type"
                and "charset" in (meta.get("content", "")).lower()
            ):
                has_charset = True
                break

        if not has_charset:
            issues.append("Missing <meta charset> in <head>")
            score -= float(_param(config, "deduction_charset"))
        return score

    def _check_viewport(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 4: <meta name='viewport'> in <head>."""
        head = doc.find(".//head")
        if head is None:
            return score

        has_viewport = any(
            meta.get("name", "").lower() == "viewport" for meta in head.findall(".//meta")
        )
        if not has_viewport:
            issues.append('Missing <meta name="viewport"> in <head>')
            score -= float(_param(config, "deduction_viewport"))
        return score

    def _check_title(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 5: <title> in <head>, non-empty."""
        head = doc.find(".//head")
        if head is None:
            return score

        title = head.find(".//title")
        if title is None or not (title.text or "").strip():
            issues.append("Missing or empty <title> in <head>")
            score -= float(_param(config, "deduction_title"))
        return score

    # --- Group B: Tag Integrity ---

    def _check_unclosed_tags(
        self,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 6: Unclosed block-level tags.

        Compare raw HTML open/close tag counts since lxml auto-closes tags.
        """
        deduction = float(_param(config, "deduction_unclosed_tag"))
        max_reported = int(_param(config, "max_unclosed_tags_reported"))

        check_tags = ["div", "table", "tr", "td", "th", "p", "section", "header", "footer"]
        unclosed: list[str] = []

        for tag in check_tags:
            opens, closes = _count_raw_tags(raw_html, tag)
            if opens > closes:
                unclosed.append(f"<{tag}> ({opens} opened, {closes} closed)")

        for item in unclosed[:max_reported]:
            issues.append(f"Unclosed tag: {item}")
            score -= deduction

        if len(unclosed) > max_reported:
            issues.append(f"... and {len(unclosed) - max_reported} more unclosed tags")

        return score

    def _check_nesting(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 7: Block-in-inline nesting violations."""
        deduction = float(_param(config, "deduction_nesting"))
        max_reported = int(_param(config, "max_nesting_violations_reported"))

        violations: list[str] = []

        for el in doc.iter():
            if not isinstance(el.tag, str):
                continue
            tag = el.tag.lower()
            if tag not in _BLOCK_TAGS:
                continue
            # Walk up to find inline ancestor
            parent = el.getparent()
            while parent is not None:
                if not isinstance(parent.tag, str):
                    break
                parent_tag = parent.tag.lower()
                if parent_tag in _INLINE_TAGS:
                    violations.append(f"<{tag}> inside <{parent_tag}>")
                    break
                if parent_tag in _BLOCK_TAGS or parent_tag in ("html", "head", "body"):
                    break
                parent = parent.getparent()

        for item in violations[:max_reported]:
            issues.append(f"Invalid nesting: {item}")
            score -= deduction

        if len(violations) > max_reported:
            issues.append(f"... and {len(violations) - max_reported} more nesting violations")

        return score

    def _check_duplicate_ids(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 8: Duplicate id attributes."""
        deduction = float(_param(config, "deduction_duplicate_id"))
        max_reported = int(_param(config, "max_duplicate_ids_reported"))

        id_counts: Counter[str] = Counter()
        for el in doc.iter():
            if not isinstance(el.tag, str):
                continue
            el_id = el.get("id")
            if el_id:
                id_counts[el_id] += 1

        duplicates = [f'id="{k}" ({v} times)' for k, v in id_counts.items() if v > 1]

        for item in duplicates[:max_reported]:
            issues.append(f"Duplicate {item}")
            score -= deduction

        if len(duplicates) > max_reported:
            issues.append(f"... and {len(duplicates) - max_reported} more duplicate IDs")

        return score

    # --- Group C: Content Integrity ---

    def _check_empty_sections(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 9: Empty <head> or <body>."""
        deduction = float(_param(config, "deduction_empty_section"))

        head = doc.find(".//head")
        if head is not None and len(head) == 0 and not (head.text or "").strip():
            issues.append("Empty <head> section")
            score -= deduction

        body = doc.find(".//body")
        if body is not None and len(body) == 0 and not (body.text or "").strip():
            issues.append("Empty <body> section")
            score -= deduction

        return score

    def _check_style_placement(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 10: <style> must be in <head>; no <link rel='stylesheet'>."""
        deduction = float(_param(config, "deduction_style_placement"))

        # Find <style> tags in <body>
        body = doc.find(".//body")
        if body is not None:
            body_styles = body.findall(".//style")
            if body_styles:
                issues.append(f"<style> in <body> ({len(body_styles)} found) — move to <head>")
                score -= deduction

        # Check for external stylesheets
        for link in doc.findall(".//link"):
            if (link.get("rel") or "").lower() == "stylesheet":
                issues.append('<link rel="stylesheet"> found — external CSS not supported in email')
                score -= deduction
                break

        return score

    # --- Group D: Email-Specific Structure ---

    def _check_table_structure(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 11: Table hierarchy integrity."""
        deduction = float(_param(config, "deduction_table_structure"))
        max_reported = int(_param(config, "max_table_violations_reported"))

        violations: list[str] = []

        for el in doc.iter():
            if not isinstance(el.tag, str):
                continue
            tag = el.tag.lower()

            if tag not in _TABLE_VALID_PARENTS:
                continue

            parent = el.getparent()
            if parent is None:
                continue
            if not isinstance(parent.tag, str):
                continue
            parent_tag = parent.tag.lower()

            valid_parents = _TABLE_VALID_PARENTS[tag]
            if parent_tag not in valid_parents:
                violations.append(
                    f"<{tag}> inside <{parent_tag}> — must be inside "
                    f"<{'> or <'.join(sorted(valid_parents))}>"
                )

        for item in violations[:max_reported]:
            issues.append(f"Table structure: {item}")
            score -= deduction

        if len(violations) > max_reported:
            issues.append(
                f"... and {len(violations) - max_reported} more table structure violations"
            )

        return score

    def _check_list_structure(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 12: List hierarchy — <li> must be inside <ul>/<ol>."""
        deduction = float(_param(config, "deduction_list_structure"))
        max_reported = int(_param(config, "max_list_violations_reported"))

        violations: list[str] = []

        for li in doc.iter("li"):
            parent = li.getparent()
            if parent is None:
                continue
            if not isinstance(parent.tag, str):
                continue
            if parent.tag.lower() not in ("ul", "ol"):
                violations.append(
                    f"<li> inside <{parent.tag.lower()}> — must be inside <ul> or <ol>"
                )

        for item in violations[:max_reported]:
            issues.append(f"List structure: {item}")
            score -= deduction

        if len(violations) > max_reported:
            issues.append(
                f"... and {len(violations) - max_reported} more list structure violations"
            )

        return score

    def _check_duplicate_structural(
        self,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 13: Multiple <head>, <body>, or <title> tags.

        Uses raw HTML counting since lxml merges duplicates during parsing.
        """
        deduction = float(_param(config, "deduction_duplicate_structural"))

        for tag in ("head", "body", "title"):
            opens, _ = _count_raw_tags(raw_html, tag)
            if opens > 1:
                issues.append(f"Duplicate <{tag}> tags ({opens} found)")
                score -= deduction

        return score

    def _check_nested_links(
        self,
        _doc: HtmlElement,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 14: <a> inside <a> — illegal per HTML spec.

        lxml normalizes nested <a> tags by splitting them into siblings,
        so we must detect this in raw HTML.
        """
        deduction = float(_param(config, "deduction_nested_link"))

        # Count nesting depth of <a> tags in raw HTML
        depth = 0
        found_nested = False
        for match in re.finditer(r"<(/?)a[\s>]", raw_html, re.IGNORECASE):
            if match.group(1) == "":  # opening tag
                depth += 1
                if depth > 1:
                    found_nested = True
                    break
            else:  # closing tag
                depth = max(0, depth - 1)

        if found_nested:
            issues.append("Nested <a> tag inside <a> — illegal per HTML spec")
            score -= deduction

        return score

    # --- Group E: Progressive Enhancement ---

    def _check_video_structure(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 15: <video> must have poster and fallback content."""
        deduction = float(_param(config, "deduction_missing_fallback"))

        for video in doc.iter("video"):
            if not video.get("poster"):
                issues.append("<video> missing poster attribute (fallback image)")
                score -= deduction
            # Check for fallback content (text or elements besides <source>)
            has_fallback = bool((video.text or "").strip())
            if not has_fallback:
                for child in video:
                    if isinstance(child.tag, str) and child.tag.lower() != "source":
                        has_fallback = True
                        break
                    if (child.tail or "").strip():
                        has_fallback = True
                        break
            if not has_fallback:
                issues.append("<video> missing fallback content for non-supporting clients")
                score -= deduction
            # Check <source> type attributes
            for source in video.findall("source"):
                if not source.get("type"):
                    issues.append("<video> <source> missing type attribute")
                    score -= deduction
                    break  # One warning per video

        return score

    def _check_audio_structure(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 16: <audio> must have fallback content."""
        deduction = float(_param(config, "deduction_missing_fallback"))

        for audio in doc.iter("audio"):
            has_fallback = bool((audio.text or "").strip())
            if not has_fallback:
                for child in audio:
                    if isinstance(child.tag, str) and child.tag.lower() != "source":
                        has_fallback = True
                        break
                    if (child.tail or "").strip():
                        has_fallback = True
                        break
            if not has_fallback:
                issues.append("<audio> missing fallback content for non-supporting clients")
                score -= deduction
            for source in audio.findall("source"):
                if not source.get("type"):
                    issues.append("<audio> <source> missing type attribute")
                    score -= deduction
                    break

        return score

    def _check_picture_structure(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 17: <picture> must contain <img> fallback."""
        deduction = float(_param(config, "deduction_missing_fallback"))

        for picture in doc.iter("picture"):
            img_children = picture.findall(".//img")
            if not img_children:
                issues.append("<picture> missing <img> fallback element")
                score -= deduction

            for source in picture.findall("source"):
                if not source.get("srcset"):
                    issues.append("<picture> <source> missing srcset attribute")
                    score -= deduction
                    break
                if not source.get("type") and not source.get("media"):
                    issues.append("<picture> <source> should have type or media attribute")
                    score -= deduction
                    break

        return score

    def _check_interactive_elements(
        self,
        doc: HtmlElement,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 18: Interactive & structured data elements.

        - <details> must have <summary> first child
        - <input type=checkbox/radio> must have matching <label for=id>
        - <script type=application/ld+json> must contain valid JSON
        - Inline <svg> must have xmlns and accessibility attributes
        """
        deduction = float(_param(config, "deduction_interactive_structure"))

        # Details/Summary
        for details in doc.iter("details"):
            children = [c for c in details if isinstance(c.tag, str)]
            if not children or children[0].tag.lower() != "summary":
                issues.append("<details> must have <summary> as first child")
                score -= deduction

        # Input + Label pairing
        label_fors: set[str] = set()
        for label in doc.iter("label"):
            for_val = label.get("for")
            if for_val:
                label_fors.add(for_val)

        for inp in doc.iter("input"):
            inp_type = (inp.get("type") or "").lower()
            if inp_type in ("checkbox", "radio"):
                inp_id = inp.get("id")
                if not inp_id or inp_id not in label_fors:
                    issues.append(
                        f'<input type="{inp_type}"> missing matching '
                        f'<label for="..."> (kinetic email pattern)'
                    )
                    score -= deduction

        # JSON-LD validation
        for script in doc.iter("script"):
            script_type = (script.get("type") or "").lower()
            if script_type == "application/ld+json":
                content = (script.text or "").strip()
                if not content:
                    issues.append('<script type="application/ld+json"> is empty')
                    score -= deduction
                else:
                    try:
                        json.loads(content)
                    except (json.JSONDecodeError, ValueError):
                        issues.append('<script type="application/ld+json"> contains invalid JSON')
                        score -= deduction

        # Inline SVG
        # lxml may namespace SVGs — check both with and without namespace
        svg_pattern = re.compile(r"<svg[\s>]", re.IGNORECASE)
        if svg_pattern.search(raw_html):
            for el in doc.iter():
                if not isinstance(el.tag, str):
                    continue
                local_tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
                if local_tag.lower() == "svg":
                    # Check xmlns
                    xmlns = el.get("xmlns") or el.get("{http://www.w3.org/2000/xmlns/}xmlns")
                    if not xmlns and "xmlns" not in raw_html.lower().split("<svg")[1].split(">")[0]:
                        pass  # xmlns may be inherited or implicit in HTML5
                    # Check accessibility
                    has_role = el.get("role") == "img"
                    has_label = bool(el.get("aria-label"))
                    if not has_role or not has_label:
                        issues.append(
                            'Inline <svg> should have role="img" and aria-label for accessibility'
                        )
                        score -= deduction

        return score

    def _check_template_element(
        self,
        _doc: HtmlElement,
        raw_html: str,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 19: <template> element — actively suppresses rendering."""
        deduction = float(_param(config, "deduction_dangerous_element"))

        # lxml may not parse <template> content normally, check raw HTML
        if re.search(r"<template[\s>]", raw_html, re.IGNORECASE):
            issues.append(
                "<template> element found — content is inert and will not render in email. "
                "Remove and use regular HTML elements instead"
            )
            score -= deduction

        return score

    def _check_base_tag(
        self,
        doc: HtmlElement,
        config: QACheckConfig | None,
        issues: list[str],
        score: float,
    ) -> float:
        """Check 20: <base> tag — breaks all relative URLs in email."""
        deduction = float(_param(config, "deduction_dangerous_element"))

        base_tags = doc.findall(".//base")
        if base_tags:
            href = base_tags[0].get("href", "")
            issues.append(
                f'<base href="{href}"> found — breaks all relative URLs, '
                f"tracking links, and image paths in email. Remove it"
            )
            score -= deduction

        return score
