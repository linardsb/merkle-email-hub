"""DOM diff computation between original and rendered HTML."""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import html as lxml_html

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DOMDiff:
    """Structural diff between original and post-sanitizer HTML."""

    removed_elements: list[str] = field(default_factory=list)
    removed_attributes: dict[str, list[str]] = field(default_factory=dict)
    removed_css_properties: dict[str, list[str]] = field(default_factory=dict)
    added_elements: list[str] = field(default_factory=list)
    modified_styles: dict[str, tuple[str, str]] = field(default_factory=dict)


def _parse_inline_style(style: str) -> dict[str, str]:
    """Parse a CSS inline style string into a property->value dict."""
    props: dict[str, str] = {}
    for part in style.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        props[key.strip().lower()] = val.strip()
    return props


def _collect_attributes(root: lxml_html.HtmlElement) -> dict[str, dict[str, str]]:
    """Collect XPath->{attr: value} for all elements."""
    attrs: dict[str, dict[str, str]] = {}
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        path = root.getroottree().getpath(el)
        el_attrs = dict(el.attrib)
        if el_attrs:
            attrs[path] = el_attrs
    return attrs


def compute_dom_diff(original_html: str, rendered_html: str) -> DOMDiff:
    """Compute structural diff between original and rendered HTML.

    Identifies elements removed by sanitizer, stripped attributes,
    removed CSS properties, and style modifications.
    """
    try:
        orig_doc = lxml_html.fragment_fromstring(original_html, create_parent="div")
        rend_doc = lxml_html.fragment_fromstring(rendered_html, create_parent="div")
    except Exception:
        logger.debug("sandbox.dom_diff_parse_failed")
        return DOMDiff()

    # Element diff: find tags in original but not rendered
    orig_tags: dict[str, int] = {}
    for el in orig_doc.iter():
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag:
            orig_tags[tag] = orig_tags.get(tag, 0) + 1

    rend_tags: dict[str, int] = {}
    for el in rend_doc.iter():
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag:
            rend_tags[tag] = rend_tags.get(tag, 0) + 1

    removed_elements: list[str] = []
    for tag, count in orig_tags.items():
        rend_count = rend_tags.get(tag, 0)
        if rend_count < count:
            removed_elements.extend([tag] * (count - rend_count))

    added_elements: list[str] = []
    for tag, count in rend_tags.items():
        orig_count = orig_tags.get(tag, 0)
        if count > orig_count:
            added_elements.extend([tag] * (count - orig_count))

    # Attribute diff: compare attributes on elements that exist in both
    orig_attrs = _collect_attributes(orig_doc)
    rend_attrs = _collect_attributes(rend_doc)

    removed_attributes: dict[str, list[str]] = {}
    for path, attrs in orig_attrs.items():
        rend_el_attrs = rend_attrs.get(path, {})
        removed = [a for a in attrs if a not in rend_el_attrs and a != "style"]
        if removed:
            removed_attributes[path] = removed

    # CSS property diff: compare inline styles
    removed_css: dict[str, list[str]] = {}
    modified_styles: dict[str, tuple[str, str]] = {}

    for path, attrs in orig_attrs.items():
        orig_style = attrs.get("style", "")
        rend_style = rend_attrs.get(path, {}).get("style", "")
        if not orig_style:
            continue

        orig_props = _parse_inline_style(orig_style)
        rend_props = _parse_inline_style(rend_style)

        removed_props = [p for p in orig_props if p not in rend_props]
        if removed_props:
            removed_css[path] = removed_props

        for prop, val in orig_props.items():
            if prop in rend_props and rend_props[prop] != val:
                modified_styles[f"{path}::{prop}"] = (val, rend_props[prop])

    return DOMDiff(
        removed_elements=removed_elements,
        removed_attributes=removed_attributes,
        removed_css_properties=removed_css,
        added_elements=added_elements,
        modified_styles=modified_styles,
    )
