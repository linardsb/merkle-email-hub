"""CSS inliner — inject optimized styles as inline style attributes."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Bounded quantifiers prevent polynomial backtracking (py/polynomial-redos).
_STYLE_BLOCK_RE = re.compile(
    r"<style[^>]{0,2000}>(.{0,200000}?)</style>", re.DOTALL | re.IGNORECASE
)
_MSO_COMMENT_RE = re.compile(
    r"<!--\[if\s{1,20}mso.{0,500}?\]>.{0,100000}?<!\[endif\]-->",
    re.DOTALL | re.IGNORECASE,
)


def extract_styles(html: str) -> tuple[str, list[str]]:
    """Extract <style> blocks from HTML, returning (html_without_styles, css_blocks).

    Preserves MSO conditional comments — those are NOT extracted.
    """
    css_blocks: list[str] = []

    # Temporarily protect MSO conditionals
    mso_placeholders: dict[str, str] = {}
    protected = html
    for i, m in enumerate(_MSO_COMMENT_RE.finditer(html)):
        placeholder = f"__MSO_PLACEHOLDER_{i}__"
        mso_placeholders[placeholder] = m.group(0)
        protected = protected.replace(m.group(0), placeholder, 1)

    # Extract non-MSO style blocks
    for m in _STYLE_BLOCK_RE.finditer(protected):
        css_blocks.append(m.group(1).strip())
    cleaned = _STYLE_BLOCK_RE.sub("", protected)

    # Restore MSO conditionals
    for placeholder, original in mso_placeholders.items():
        cleaned = cleaned.replace(placeholder, original)

    return cleaned, css_blocks


def parse_css_rules(css_text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Parse CSS text into (selector, [(property, value), ...]) tuples.

    Handles simple selectors only — no @media, @keyframes etc.
    Those should be preserved in a <style> block.
    """
    rules: list[tuple[str, list[tuple[str, str]]]] = []
    # Remove comments (bounded body prevents polynomial backtracking)
    css_text = re.sub(r"/\*.{0,100000}?\*/", "", css_text, flags=re.DOTALL)

    # Split into rule blocks (simple brace matching, bounded body)
    parts = re.split(r"\{([^}]{0,10000})\}", css_text)

    for i in range(0, len(parts) - 1, 2):
        selector = parts[i].strip()
        declarations_text = parts[i + 1].strip()

        if not selector or selector.startswith("@"):
            continue

        declarations: list[tuple[str, str]] = []
        for decl in declarations_text.split(";"):
            decl = decl.strip()
            if ":" not in decl:
                continue
            prop, val = decl.split(":", 1)
            declarations.append((prop.strip(), val.strip()))

        if declarations:
            rules.append((selector, declarations))

    return rules


def inline_styles(html: str, css_rules: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """Apply CSS rules as inline styles on matching elements.

    Uses BeautifulSoup for element matching. Existing inline styles
    take precedence (are not overwritten).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Collect and apply styles per selector
    for selector, declarations in css_rules:
        try:
            elements = soup.select(selector)
        except Exception:  # noqa: S112
            continue  # Skip selectors BS4 can't handle

        for el in elements:
            # Parse existing inline styles
            existing_raw = el.get("style", "")
            existing_str = existing_raw if isinstance(existing_raw, str) else str(existing_raw)
            existing: dict[str, str] = {}
            if existing_str:
                for part in existing_str.split(";"):
                    part = part.strip()
                    if ":" in part:
                        k, v = part.split(":", 1)
                        existing[k.strip()] = v.strip()

            # Merge — existing inline styles win
            for prop, val in declarations:
                if prop not in existing:
                    existing[prop] = val

            # Write back
            style_str = "; ".join(f"{k}: {v}" for k, v in existing.items())
            if style_str:
                el["style"] = style_str

    return str(soup)
