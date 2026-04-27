# ruff: noqa: ARG001
"""Accessibility (WCAG AA) custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

import re

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import register_custom_check

# ---------------------------------------------------------------------------
# Custom check functions — accessibility (WCAG AA)
# ---------------------------------------------------------------------------

_A11Y_DEFAULTS: dict[str, float | int] = {
    "deduction_table_no_role": 0.10,
    "deduction_table_mixed_signals": 0.10,
    "deduction_data_table_no_headers": 0.10,
    "deduction_img_no_alt": 0.10,
    "deduction_tracking_pixel_alt": 0.05,
    "deduction_linked_img_no_alt": 0.10,
    "deduction_no_headings": 0.10,
    "deduction_skipped_heading": 0.10,
    "deduction_generic_link_text": 0.08,
    "deduction_empty_link": 0.10,
    "deduction_redundant_links": 0.05,
    "deduction_non_semantic_emphasis": 0.05,
    "deduction_preview_padding_no_aria": 0.08,
    "deduction_spacer_no_aria": 0.05,
    "deduction_separator_no_aria": 0.05,
    "deduction_outline_removed": 0.10,
    "deduction_br_spacing": 0.05,
    "deduction_dark_unsafe_colors": 0.08,
    "deduction_dark_no_overrides": 0.10,
    "deduction_input_no_label": 0.10,
    "deduction_required_no_aria": 0.08,
    "max_table_issues_reported": 5,
    "max_img_issues_reported": 5,
    "max_heading_issues_reported": 5,
    "max_link_issues_reported": 5,
    "max_content_issues_reported": 5,
    "max_form_issues_reported": 5,
}

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

_GENERIC_LINK_TEXT = frozenset(
    {
        "click here",
        "here",
        "read more",
        "learn more",
        "more",
        "this",
        "link",
        "go",
        "see more",
        "find out more",
        "details",
        "info",
    }
)

_DATA_TABLE_SIGNALS = frozenset({"th", "caption", "thead", "tbody", "tfoot"})

_SEPARATOR_CHARS = frozenset({"|", "\u2022", "\u00b7", "\u2013", "\u2014"})


def _a11y_param(config: QACheckConfig | None, key: str) -> float | int:
    if config:
        val: float | int = config.params.get(key, _A11Y_DEFAULTS[key])
        return val
    return _A11Y_DEFAULTS[key]


def _is_tracking_pixel(img: HtmlElement) -> bool:
    """Detect tracking pixel / spacer images."""
    w = img.get("width", "")
    h = img.get("height", "")
    style = (img.get("style") or "").lower()

    # 1x1 or 0x0 via attributes
    if w in ("0", "1") and h in ("0", "1"):
        return True
    # Via inline style
    if "width:1px" in style.replace(" ", "") and "height:1px" in style.replace(" ", ""):
        return True
    if "width:0" in style.replace(" ", "") or "height:0" in style.replace(" ", ""):
        return True
    if "display:none" in style.replace(" ", ""):
        return True
    return "visibility:hidden" in style.replace(" ", "")


def _has_data_table_signals(table: HtmlElement) -> bool:
    """Check if a table has data-table signals."""
    role = (table.get("role") or "").lower()
    if role in ("table", "grid"):
        return True
    if table.get("summary") is not None:
        return True
    for child in table.iter():
        if isinstance(child.tag, str) and child.tag.lower() in _DATA_TABLE_SIGNALS:
            return True
    return False


# --- B3: Layout table role detection ---


def layout_table_heuristic(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Layout tables without role='presentation'."""
    deduction = float(_a11y_param(config, "deduction_table_no_role"))
    cap = int(_a11y_param(config, "max_table_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role == "presentation":
            continue
        if _has_data_table_signals(table):
            continue
        # This is a layout table without role=presentation
        if len(issues) < cap:
            issues.append(
                "Layout table missing role='presentation' — "
                "screen readers announce table structure to users"
            )
        total += deduction

    return issues, total


# --- B4: Mixed signals on presentation tables ---


def table_mixed_signals(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Tables with role='presentation' that also have data-table signals."""
    deduction = float(_a11y_param(config, "deduction_table_mixed_signals"))
    cap = int(_a11y_param(config, "max_table_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role != "presentation":
            continue
        signals: list[str] = []
        if table.get("summary") is not None:
            signals.append("summary")
        for child in table.iter():
            if child is table:
                continue
            if isinstance(child.tag, str) and child.tag.lower() in ("th", "caption"):
                signals.append(f"<{child.tag.lower()}>")
        if signals:
            if len(issues) < cap:
                issues.append(
                    f"Table with role='presentation' has conflicting data-table signals: "
                    f"{', '.join(signals)}"
                )
            total += deduction

    return issues, total


# --- B5: Data table headers with scope ---


def data_table_headers(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Data tables: <th> must have scope='col' or scope='row'."""
    deduction = float(_a11y_param(config, "deduction_data_table_no_headers"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role == "presentation":
            continue
        if not _has_data_table_signals(table):
            continue
        # This is a data table — check th elements
        for th in table.iter("th"):
            scope = (th.get("scope") or "").lower()
            if scope not in ("col", "row"):
                issues.append("Data table <th> missing scope='col' or scope='row'")
                total += deduction
                break  # One issue per table is enough

    return issues, total


# --- C6: Image alt attribute ---


def img_alt_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """All <img> must have alt attribute (alt='' is valid for decorative)."""
    deduction = float(_a11y_param(config, "deduction_img_no_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        if img.get("alt") is None:
            src = img.get("src", "")
            basename = src.rsplit("/", 1)[-1][:40] if src else "unknown"
            if len(issues) < cap:
                issues.append(f"<img> missing alt attribute (src: {basename})")
            total += deduction

    return issues, total


# --- C7: Tracking pixel alt ---


def tracking_pixel_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Tracking pixels/spacers must have alt='' (empty, not missing, not descriptive)."""
    deduction = float(_a11y_param(config, "deduction_tracking_pixel_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        if not _is_tracking_pixel(img):
            continue
        alt = img.get("alt")
        if alt is None:
            if len(issues) < cap:
                issues.append("Tracking pixel missing alt='' — add empty alt attribute")
            total += deduction
        elif alt != "":
            if len(issues) < cap:
                issues.append(
                    f"Tracking pixel has descriptive alt=\"{alt[:30]}\" — should be alt='' (empty)"
                )
            total += deduction

    return issues, total


# --- C8: Linked image alt ---


def linked_img_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """<a> containing only <img> — the img alt is the link's accessible name."""
    deduction = float(_a11y_param(config, "deduction_linked_img_no_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        imgs = list(a_tag.iter("img"))
        if not imgs:
            continue
        # Check if <a> has text content besides the image
        text = (a_tag.text_content() or "").strip()
        # Remove img alt text from consideration
        img_alts = "".join((img.get("alt") or "") for img in imgs)
        remaining_text = text.replace(img_alts, "").strip() if img_alts else text
        if remaining_text:
            continue  # Text link alongside image — text provides accessible name

        # Only image(s) inside <a> — check alt
        for img in imgs:
            alt = img.get("alt")
            if alt is None or alt == "":
                if len(issues) < cap:
                    issues.append("Linked image with empty/missing alt — no accessible name")
                total += deduction
                break  # One issue per link

    return issues, total


# --- D9: Headings present ---


def headings_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Email body should contain heading elements for navigation."""
    deduction = float(_a11y_param(config, "deduction_no_headings"))
    body = doc.find(".//body")
    if body is None:
        return [], 0.0

    for tag in _HEADING_TAGS:
        if list(body.iter(tag)):
            return [], 0.0

    return [
        "No heading elements (h1-h6) found — screen reader users cannot navigate by heading"
    ], deduction


# --- D11: Heading hierarchy ---


def heading_hierarchy(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Heading levels must not skip (e.g., h1 -> h3 without h2)."""
    deduction = float(_a11y_param(config, "deduction_skipped_heading"))
    cap = int(_a11y_param(config, "max_heading_issues_reported"))
    issues: list[str] = []
    total = 0.0

    levels: list[int] = []
    body = doc.find(".//body")
    if body is None:
        return [], 0.0

    for el in body.iter():
        if isinstance(el.tag, str) and el.tag.lower() in _HEADING_TAGS:
            levels.append(int(el.tag[1]))

    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            if len(issues) < cap:
                issues.append(f"Skipped heading level: h{levels[i - 1]} → h{levels[i]}")
            total += deduction

    return issues, total


# --- E12: Generic link text ---


def generic_link_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Links should not use generic text like 'click here'."""
    deduction = float(_a11y_param(config, "deduction_generic_link_text"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        text = (a_tag.text_content() or "").strip().lower()
        if text in _GENERIC_LINK_TEXT:
            if len(issues) < cap:
                issues.append(f'Generic link text "{text}" — use descriptive text')
            total += deduction

    return issues, total


# --- E13: Empty links ---


def empty_links(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Links must have accessible name (text, aria-label, or img alt)."""
    deduction = float(_a11y_param(config, "deduction_empty_link"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        # Check for text content
        text = (a_tag.text_content() or "").strip()
        if text:
            continue
        # Check for aria-label
        if a_tag.get("aria-label"):
            continue
        # Check for img with non-empty alt
        has_img_alt = False
        for img in a_tag.iter("img"):
            alt = img.get("alt")
            if alt and alt.strip():
                has_img_alt = True
                break
        if has_img_alt:
            continue

        if len(issues) < cap:
            issues.append("Empty link — no text, aria-label, or image alt")
        total += deduction

    return issues, total


# --- E14: Redundant adjacent links ---


def redundant_links(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Consecutive <a> elements in same parent with same href."""
    deduction = float(_a11y_param(config, "deduction_redundant_links"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for parent in doc.iter():
        children = [c for c in parent if isinstance(c.tag, str) and c.tag.lower() == "a"]
        if len(children) < 2:
            continue
        for i in range(len(children) - 1):
            href1 = (children[i].get("href") or "").rstrip("/")
            href2 = (children[i + 1].get("href") or "").rstrip("/")
            if href1 and href1 == href2:
                if len(issues) < cap:
                    issues.append(
                        "Redundant adjacent links to same URL — wrap image and text in a single <a>"
                    )
                total += deduction

    return issues, total


# --- F15: Semantic emphasis ---


def semantic_emphasis(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Use <strong>/<em> not <b>/<i> for emphasis."""
    deduction = float(_a11y_param(config, "deduction_non_semantic_emphasis"))

    b_count = len(list(doc.iter("b")))
    i_count = len(list(doc.iter("i")))
    total_count = b_count + i_count

    if total_count > 0:
        return [
            f"{total_count} <b>/<i> tag(s) found — use <strong>/<em> for semantic emphasis"
        ], deduction
    return [], 0.0


# --- F16: Preview padding aria-hidden ---


def preview_padding_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Preview text padding (&zwnj;&nbsp; runs) must have aria-hidden='true'."""
    deduction = float(_a11y_param(config, "deduction_preview_padding_no_aria"))

    # Search for 3+ consecutive ZWNJ or NBSP characters
    padding_pattern = re.compile(r"[\u200c\u00a0]{3,}")

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        # Check element text
        for text in [el.text, el.tail]:
            if text and padding_pattern.search(text):
                # Walk up to check if any ancestor has aria-hidden
                current: HtmlElement | None = el
                hidden = False
                while current is not None:
                    if isinstance(current.tag, str) and current.get("aria-hidden") == "true":
                        hidden = True
                        break
                    current = current.getparent()
                if not hidden:
                    return [
                        "Preview text padding (repeated \\u200c/\\u00a0) without aria-hidden='true'"
                    ], deduction

    return [], 0.0


# --- F17: Spacer cells/images aria-hidden ---


def spacer_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Spacer cells (&nbsp; only) and spacer images without aria-hidden."""
    deduction = float(_a11y_param(config, "deduction_spacer_no_aria"))
    cap = int(_a11y_param(config, "max_content_issues_reported"))
    issues: list[str] = []
    total = 0.0

    # Spacer images
    for img in doc.iter("img"):
        src = (img.get("src") or "").lower()
        if ("spacer" in src or "blank" in src) and img.get("aria-hidden") != "true":
            if len(issues) < cap:
                issues.append("Spacer image without aria-hidden='true'")
            total += deduction

    return issues, total


# --- F18: Separator chars aria-hidden ---


def separator_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Separator characters (|, bullet, dash) should have aria-hidden."""
    deduction = float(_a11y_param(config, "deduction_separator_no_aria"))
    cap = int(_a11y_param(config, "max_content_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.lower() in ("style", "script", "head"):
            continue
        text = (el.text_content() or "").strip()
        if len(text) <= 2 and text and text in _SEPARATOR_CHARS and el.get("aria-hidden") != "true":
            if len(issues) < cap:
                issues.append(f"Separator character '{text}' without aria-hidden='true'")
            total += deduction

    return issues, total


# --- F19: Outline removal ---


def outline_removal(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """outline:none/outline:0 found without replacement focus style."""
    deduction = float(_a11y_param(config, "deduction_outline_removed"))

    outline_pattern = re.compile(r"outline\s*:\s*(none|0)\b")

    # Check <style> blocks
    for style in doc.iter("style"):
        if style.text and outline_pattern.search(style.text):
            return [
                "outline:none/outline:0 found in styles — "
                "removes visible focus indicator for keyboard users"
            ], deduction

    # Check inline styles
    for el in doc.iter():
        if isinstance(el.tag, str):
            inline = el.get("style") or ""
            if outline_pattern.search(inline):
                return [
                    "outline:none/outline:0 found in inline style — removes visible focus indicator"
                ], deduction

    return [], 0.0


# --- F20: Consecutive <br> ---


def consecutive_br(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Consecutive <br> tags used for spacing instead of block elements."""
    deduction = float(_a11y_param(config, "deduction_br_spacing"))
    issues: list[str] = []
    total = 0.0

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        children = list(el)
        for i, child in enumerate(children):
            if not isinstance(child.tag, str):
                continue
            if child.tag.lower() == "br" and i + 1 < len(children):
                tail = (child.tail or "").strip()
                next_child = children[i + 1]
                if not tail and isinstance(next_child.tag, str) and next_child.tag.lower() == "br":
                    issues.append("Consecutive <br> for spacing — use <p> or table cell padding")
                    total += deduction
                    return issues, total  # Single issue is enough

    return issues, total


# --- G21: Dark mode unsafe colors ---


def dark_unsafe_colors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Dark mode styles using pure #ffffff/#000000 pairs."""
    deduction = float(_a11y_param(config, "deduction_dark_unsafe_colors"))

    # Collect all <style> text
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    combined = "\n".join(css_texts)

    # Find @media (prefers-color-scheme: dark) blocks
    dark_blocks = re.findall(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        combined,
        re.IGNORECASE,
    )
    if not dark_blocks:
        return [], 0.0

    dark_css = " ".join(dark_blocks).lower()

    # Check for pure black/white pairs
    pure_white = re.search(
        r"(?:color|background(?:-color)?)\s*:\s*(?:#fff(?:fff)?|white)\b", dark_css
    )
    pure_black = re.search(
        r"(?:color|background(?:-color)?)\s*:\s*(?:#000(?:000)?|black)\b", dark_css
    )

    if pure_white and pure_black:
        return [
            "Dark mode uses pure #ffffff/#000000 — "
            "these invert unpredictably; use #f0f0f0 on #1a1a1a instead"
        ], deduction

    return [], 0.0


# --- G22: Dark mode meta without matching styles ---


def dark_no_overrides(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """color-scheme meta present but no @media (prefers-color-scheme: dark) styles."""
    deduction = float(_a11y_param(config, "deduction_dark_no_overrides"))

    # Check for dark mode meta tag
    has_meta = False
    for meta in doc.iter("meta"):
        name = (meta.get("name") or "").lower()
        content = (meta.get("content") or "").lower()
        if name == "color-scheme" and "dark" in content:
            has_meta = True
            break
        if name == "supported-color-schemes" and "dark" in content:
            has_meta = True
            break

    if not has_meta:
        return [], 0.0  # No dark mode declared — no issue

    # Check for matching dark mode styles
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    combined = "\n".join(css_texts)

    if not re.search(r"prefers-color-scheme\s*:\s*dark", combined, re.IGNORECASE):
        return [
            "color-scheme meta declares dark mode but no @media (prefers-color-scheme: dark) styles — "
            "clients will force-invert unpredictably"
        ], deduction

    # Check if dark mode block has color overrides
    dark_blocks = re.findall(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        combined,
        re.IGNORECASE,
    )
    dark_css = " ".join(dark_blocks).lower()
    if not re.search(r"(?:color|background)", dark_css):
        return [
            "Dark mode @media block has no color overrides — "
            "add explicit color and background-color rules"
        ], deduction

    return [], 0.0


# --- H23: Form input labels ---


def input_label(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Form inputs must have associated <label>, aria-label, or aria-labelledby."""
    deduction = float(_a11y_param(config, "deduction_input_no_label"))
    cap = int(_a11y_param(config, "max_form_issues_reported"))
    issues: list[str] = []
    total = 0.0

    # Collect label[for] references
    label_fors: set[str] = set()
    for label in doc.iter("label"):
        for_val = label.get("for")
        if for_val:
            label_fors.add(for_val)

    skip_types = frozenset({"hidden", "submit", "button", "image", "reset"})

    for tag_name in ("input", "select", "textarea"):
        for el in doc.iter(tag_name):
            if tag_name == "input":
                inp_type = (el.get("type") or "text").lower()
                if inp_type in skip_types:
                    continue

            # Check for label association
            el_id = el.get("id")
            if el_id and el_id in label_fors:
                continue
            # Check if nested inside <label>
            parent: HtmlElement | None = el.getparent()
            nested_in_label = False
            while parent is not None:
                if isinstance(parent.tag, str) and parent.tag.lower() == "label":
                    nested_in_label = True
                    break
                parent = parent.getparent()
            if nested_in_label:
                continue
            # Check for aria-label or aria-labelledby
            if el.get("aria-label") or el.get("aria-labelledby"):
                continue

            has_placeholder = bool(el.get("placeholder"))
            if len(issues) < cap:
                if has_placeholder:
                    issues.append(
                        f"<{tag_name}> has only placeholder — not a substitute for <label>"
                    )
                else:
                    issues.append(f"<{tag_name}> missing associated <label> or aria-label")
            total += deduction

    return issues, total


# --- H24: Required fields aria-required ---


def required_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Required fields must have aria-required='true'."""
    deduction = float(_a11y_param(config, "deduction_required_no_aria"))
    cap = int(_a11y_param(config, "max_form_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for tag_name in ("input", "select", "textarea"):
        for el in doc.iter(tag_name):
            if el.get("required") is not None and el.get("aria-required") != "true":
                if len(issues) < cap:
                    issues.append(f"Required <{tag_name}> missing aria-required='true'")
                total += deduction

    return issues, total


# Register all accessibility custom checks
register_custom_check("layout_table_heuristic", layout_table_heuristic)
register_custom_check("table_mixed_signals", table_mixed_signals)
register_custom_check("data_table_headers", data_table_headers)
register_custom_check("img_alt_present", img_alt_present)
register_custom_check("tracking_pixel_alt", tracking_pixel_alt)
register_custom_check("linked_img_alt", linked_img_alt)
register_custom_check("headings_present", headings_present)
register_custom_check("heading_hierarchy", heading_hierarchy)
register_custom_check("generic_link_text", generic_link_text)
register_custom_check("empty_links", empty_links)
register_custom_check("redundant_links", redundant_links)
register_custom_check("semantic_emphasis", semantic_emphasis)
register_custom_check("preview_padding_aria", preview_padding_aria)
register_custom_check("spacer_aria", spacer_aria)
register_custom_check("separator_aria", separator_aria)
register_custom_check("outline_removal", outline_removal)
register_custom_check("consecutive_br", consecutive_br)
register_custom_check("dark_unsafe_colors", dark_unsafe_colors)
register_custom_check("dark_no_overrides", dark_no_overrides)
register_custom_check("input_label", input_label)
register_custom_check("required_aria", required_aria)
