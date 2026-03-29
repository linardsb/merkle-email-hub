"""Centering wrapper detection and injection for email HTML."""

from __future__ import annotations

import re

from lxml import etree
from lxml import html as lxml_html
from lxml.html import HtmlElement

_MAX_WIDTH_MARGIN_RE = re.compile(
    r"max-width\s*:\s*\d+px\s*;\s*margin\s*:\s*0\s+auto",
    re.IGNORECASE,
)
_MSO_WRAPPER_RE = re.compile(
    r"<!--\[if\s+mso\]>.*?<table[^>]*>.*?<tr>.*?<td[^>]*>.*?<!\[endif\]-->",
    re.DOTALL | re.IGNORECASE,
)


def detect_centering(html: str) -> bool:
    """Check if HTML body content has a centering wrapper.

    Looks for:
    - <table ... align="center"> at the top level
    - <div style="max-width: Npx; margin: 0 auto;">
    - MSO conditional wrapper table before body content
    """
    tree = lxml_html.fromstring(html)
    body = tree.find(".//body")
    root = body if body is not None else tree

    for child in root:
        if not isinstance(child, HtmlElement):
            continue
        if child.tag == "table":
            align = (child.get("align") or "").lower()
            if align == "center":
                return True
            style = child.get("style") or ""
            if _MAX_WIDTH_MARGIN_RE.search(style):
                return True
        elif child.tag == "div":
            style = child.get("style") or ""
            if _MAX_WIDTH_MARGIN_RE.search(style):
                return True
        elif child.tag == "center":
            return True

    # Check for MSO conditional wrapper in raw HTML
    return bool(_MSO_WRAPPER_RE.search(html))


def inject_centering_wrapper(
    html: str,
    width: int = 600,
    mso_wrapper: str | None = None,
) -> str:
    """Wrap body content in a standard email centering pattern if not already centered.

    Args:
        html: Full HTML string (with <html>/<body> tags).
        width: Container width in pixels.
        mso_wrapper: Original MSO conditional block to use verbatim.
                     If None, generates a standard one.

    Returns:
        HTML with centering wrapper added, or unchanged if already centered.
    """
    if detect_centering(html):
        return html

    tree = lxml_html.fromstring(html)
    body = tree.find(".//body")
    root = body if body is not None else tree

    # Serialize body children as HTML fragments
    fragments: list[str] = []
    if root.text:
        fragments.append(root.text)
    for child in root:
        fragments.append(etree.tostring(child, encoding="unicode", method="html"))
    inner_html = "\n".join(fragments)

    # Build MSO block
    if mso_wrapper is None:
        mso_open = (
            f"<!--[if mso]>\n"
            f'<table role="presentation" cellpadding="0" cellspacing="0" '
            f'width="{width}" align="center"><tr><td>\n'
            f"<![endif]-->"
        )
    else:
        mso_open = mso_wrapper

    mso_close = "<!--[if mso]>\n</td></tr></table>\n<![endif]-->"

    wrapper = (
        f"{mso_open}\n"
        f'<div style="max-width: {width}px; margin: 0 auto;">\n'
        f"{inner_html}\n"
        f"</div>\n"
        f"{mso_close}"
    )

    # Replace body content
    for child in list(root):
        root.remove(child)
    root.text = None

    # Re-serialize the whole document with the wrapper injected as body content
    head = tree.find(".//head")
    head_html = ""
    if head is not None:
        head_html = etree.tostring(head, encoding="unicode", method="html")

    return f"<html>\n{head_html}\n<body>\n{wrapper}\n</body>\n</html>"
