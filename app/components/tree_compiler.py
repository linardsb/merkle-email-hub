"""Deterministic compiler: EmailTree -> complete email HTML.

Walks an EmailTree, resolves each section against the component
manifest, fills slots via lxml DOM manipulation, and assembles
the result inside the Email Shell document wrapper.

100% deterministic — identical input produces identical output.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.components.data.seeds import COMPONENT_SEEDS
from app.components.sanitize import sanitize_component_html
from app.components.tree_schema import (
    ButtonSlot,
    EmailTree,
    HtmlSlot,
    ImageSlot,
    SlotValue,
    TextSlot,
    TreeSection,
    validate_tree_against_manifest,
)
from app.core.exceptions import CompilationError
from app.core.logging import get_logger

logger = get_logger(__name__)

_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel"})

_DATA_SLOT_RE = re.compile(r'data-slot="([^"]+)"')


@dataclass(frozen=True, slots=True)
class CompiledEmail:
    """Result of a successful tree compilation."""

    html: str
    sections_compiled: int
    custom_sections: int
    compilation_ms: int


def _validate_url_scheme(href: str) -> bool:
    """Check that a URL uses an allowed scheme."""
    scheme = href.split(":", 1)[0].lower() if ":" in href else ""
    return scheme in _SAFE_URL_SCHEMES


def _md5(data: str) -> str:
    return hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()


def _parse_style(style: str) -> dict[str, str]:
    """Parse an inline CSS style string into a dict."""
    result: dict[str, str] = {}
    for part in style.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        prop, _, val = part.partition(":")
        result[prop.strip()] = val.strip()
    return result


def _serialize_style(styles: dict[str, str]) -> str:
    """Serialize a style dict back to an inline CSS string."""
    return "; ".join(f"{k}: {v}" for k, v in styles.items())


class TreeCompiler:
    """Compile an EmailTree into complete email HTML.

    Loads the component manifest once at construction. Each ``compile()``
    call is stateless apart from the per-section cache.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        self._slug_to_html: dict[str, str] = {}
        self._slug_to_slots: dict[str, list[str]] = {}
        self._manifest_slugs: set[str] = set()
        self._slot_definitions: dict[str, list[str]] = {}
        self._shell_html: str = ""

        self._section_cache: dict[tuple[str, str, str], str] = {}
        self._file_mtimes: dict[str, float] = {}
        self._template_dir = template_dir

        self._load_manifest()

    def _load_manifest(self) -> None:
        """Build lookup tables from COMPONENT_SEEDS."""
        for seed in COMPONENT_SEEDS:
            slug: str = seed["slug"]
            html_source: str = seed.get("html_source", "")
            self._slug_to_html[slug] = html_source
            self._manifest_slugs.add(slug)

            # Extract slot IDs from HTML data-slot attributes
            slot_ids = [m.group(1) for m in _DATA_SLOT_RE.finditer(html_source)]
            self._slug_to_slots[slug] = slot_ids
            self._slot_definitions[slug] = slot_ids

        # Email shell is always the first inline seed
        shell_seed = next(
            (s for s in COMPONENT_SEEDS if s["slug"] == "email-shell"),
            None,
        )
        if shell_seed is None:
            msg = "email-shell component not found in manifest"
            raise CompilationError(msg)
        self._shell_html = shell_seed["html_source"]

    def compile(self, tree: EmailTree) -> CompiledEmail:
        """Compile an EmailTree into complete email HTML."""
        t0 = time.monotonic()

        # Validate tree against manifest
        errors = validate_tree_against_manifest(
            tree,
            self._manifest_slugs | {"__custom__"},
            self._slot_definitions,
        )
        if errors:
            msg = f"Tree validation failed: {'; '.join(errors)}"
            raise CompilationError(msg)

        # Compile each section
        section_htmls: list[str] = []
        custom_count = 0
        for section in tree.sections:
            compiled = self._compile_section(section)
            section_htmls.append(compiled)
            if section.component_slug == "__custom__":
                custom_count += 1

        body_html = "\n".join(section_htmls)

        # Build the full document
        dark_palette = tree.metadata.design_tokens.get("dark_palette", {})
        full_html = self._build_shell(
            subject=tree.metadata.subject,
            preheader=tree.metadata.preheader,
            body_html=body_html,
            dark_palette=dark_palette,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "tree_compiler.compile_completed",
            sections=len(tree.sections),
            custom_sections=custom_count,
            compilation_ms=elapsed_ms,
        )

        return CompiledEmail(
            html=full_html,
            sections_compiled=len(tree.sections),
            custom_sections=custom_count,
            compilation_ms=elapsed_ms,
        )

    def _compile_section(self, section: TreeSection) -> str:
        """Route to custom or component compilation."""
        if section.component_slug == "__custom__":
            return self._compile_custom(section)

        # Check cache
        cache_key = self._cache_key(section)
        cached = self._section_cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._compile_component(section)
        self._section_cache[cache_key] = result
        return result

    def _compile_custom(self, section: TreeSection) -> str:
        """Compile a custom HTML section."""
        if not section.custom_html:
            msg = "__custom__ section requires custom_html"
            raise CompilationError(msg)
        return sanitize_component_html(section.custom_html)

    def _compile_component(self, section: TreeSection) -> str:
        """Compile a component section by filling slots in the template HTML."""
        slug = section.component_slug
        template_html = self._slug_to_html.get(slug)
        if template_html is None:
            msg = f"Unknown component slug: '{slug}'"
            raise CompilationError(msg)

        # Parse the template HTML
        # Use document_fromstring for multi-root fragments, then extract body children
        try:
            doc = lxml_html.document_fromstring(f"<html><body>{template_html}</body></html>")
        except Exception as exc:
            msg = f"Failed to parse HTML for component '{slug}': {exc}"
            raise CompilationError(msg) from exc

        body = doc.find(".//body")
        if body is None:
            msg = f"No body found in parsed HTML for component '{slug}'"
            raise CompilationError(msg)

        # Fill slots
        for slot_id, value in section.slot_fills.items():
            elements = body.cssselect(f'[data-slot="{slot_id}"]')
            if not elements:
                continue
            self._fill_slot(elements[0], slot_id, value)

        # Apply style overrides to the first real element child (component root)
        # body iterator can yield Comment nodes — skip them (tag is callable)
        if section.style_overrides:
            for child in body:
                if not callable(child.tag):
                    self._apply_style_overrides(child, section.style_overrides)
                    break

        # Serialize back — collect all children of body
        parts: list[str] = []
        if body.text:
            parts.append(body.text)
        for child in body:
            serialized = lxml_html.tostring(child, encoding="unicode")
            parts.append(serialized)
            if child.tail:
                parts.append(child.tail)

        return "".join(parts)

    def _fill_slot(
        self,
        element: HtmlElement,
        _slot_id: str,
        value: SlotValue,
    ) -> None:
        """Dispatch slot filling to type-specific handler."""
        if isinstance(value, TextSlot):
            self._fill_text(element, value)
        elif isinstance(value, ImageSlot):
            self._fill_image(element, value)
        elif isinstance(value, ButtonSlot):
            self._fill_button(element, value)
        else:
            self._fill_html(element, value)

    def _fill_text(self, el: HtmlElement, slot: TextSlot) -> None:
        """Fill a text slot — set element text content."""
        # Clear existing children and text
        for child in list(el):
            # Preserve children that are data-slot elements (nested slots)
            if child.get("data-slot") is not None:
                continue
            el.remove(child)
        el.text = html_lib.escape(slot.text)

    def _fill_image(self, el: HtmlElement, slot: ImageSlot) -> None:
        """Fill an image slot — set src/alt/width/height on img element."""
        if el.tag == "img":
            el.set("src", slot.src)
            el.set("alt", slot.alt)
            el.set("width", str(slot.width))
            el.set("height", str(slot.height))
        else:
            # Create img child inside container element
            for child in list(el):
                if child.tag == "img":
                    el.remove(child)
            img = lxml_html.fragment_fromstring(
                f'<img src="{html_lib.escape(slot.src, quote=True)}" '
                f'alt="{html_lib.escape(slot.alt, quote=True)}" '
                f'width="{slot.width}" height="{slot.height}" '
                f'style="display: block; border: 0; outline: none;" />',
                create_parent=False,
            )
            el.insert(0, img)

    def _fill_button(self, el: HtmlElement, slot: ButtonSlot) -> None:
        """Fill a button slot — set href, colors, and text on <a> element."""
        if not _validate_url_scheme(slot.href):
            msg = f"Unsafe URL scheme in button href: '{slot.href}'"
            raise CompilationError(msg)

        if el.tag == "a":
            el.set("href", slot.href)
            # Apply color overrides
            styles = _parse_style(el.get("style") or "")
            styles["background-color"] = slot.bg_color
            styles["color"] = slot.text_color
            el.set("style", _serialize_style(styles))
            # Set text on inner span if exists, otherwise on element itself
            inner_spans = el.cssselect("[data-slot]")
            if inner_spans:
                inner_spans[0].text = html_lib.escape(slot.text)
            else:
                el.text = html_lib.escape(slot.text)
        else:
            # Find <a> child and fill it
            links = el.cssselect("a")
            if links:
                self._fill_button(links[0], slot)

    def _fill_html(self, el: HtmlElement, slot: HtmlSlot) -> None:
        """Fill an HTML slot — sanitize and inject raw HTML."""
        sanitized = sanitize_component_html(slot.html)
        # Clear existing content
        el.text = None
        for child in list(el):
            el.remove(child)
        # Parse sanitized HTML and append children
        try:
            wrapper = lxml_html.fragment_fromstring(
                f"<div>{sanitized}</div>",
                create_parent=False,
            )
            el.text = wrapper.text
            for child in list(wrapper):
                el.append(child)
        except Exception:
            # Fallback: insert as escaped text
            el.text = sanitized

    def _apply_style_overrides(
        self,
        root: HtmlElement,
        overrides: dict[str, str],
    ) -> None:
        """Merge style overrides into the root element's style attribute."""
        styles = _parse_style(root.get("style") or "")
        styles.update(overrides)
        root.set("style", _serialize_style(styles))

    def _inject_design_tokens(
        self,
        shell_html: str,
        tokens: dict[str, dict[str, str]],
    ) -> str:
        """Replace CSS custom property defaults in <style> block."""
        if not tokens:
            return shell_html
        result = shell_html
        for values in tokens.values():
            for prop, val in values.items():
                # Replace var(--prop, default) patterns
                pattern = re.compile(rf"var\(--{re.escape(prop)},\s*[^)]+\)")
                result = pattern.sub(f"var(--{prop}, {val})", result)
        return result

    def _build_shell(
        self,
        subject: str,
        preheader: str,
        body_html: str,
        dark_palette: dict[str, str],
    ) -> str:
        """Assemble the full email document from the shell template."""
        result = self._shell_html

        # Fill email_title in <title> tag
        result = re.sub(
            r'(<title\s+data-slot="email_title">)[^<]*(</title>)',
            rf"\g<1>{html_lib.escape(subject)}\2",
            result,
        )

        # Fill preheader
        result = re.sub(
            r'(<div\s+data-slot="preheader"[^>]*>)[^<]*(</div>)',
            rf"\g<1>{html_lib.escape(preheader)}\2",
            result,
        )

        # Fill email_body — inject sections into the body div
        result = re.sub(
            r'(<div[^>]*data-slot="email_body"[^>]*>).*?(</div>)',
            rf"\g<1>\n{body_html}\n\2",
            result,
            flags=re.DOTALL,
        )

        # Inject dark palette overrides if present
        if dark_palette:
            dark_rules = "\n".join(
                f"      .dark-bg {{ {prop}: {val} !important; }}"
                for prop, val in dark_palette.items()
            )
            dark_block = f"\n    @media (prefers-color-scheme: dark) {{\n{dark_rules}\n    }}"
            # Insert before closing </style>
            result = result.replace("</style>", f"{dark_block}\n  </style>", 1)

        return result

    def _cache_key(self, section: TreeSection) -> tuple[str, str, str]:
        """Build a cache key from section data."""
        slot_json = json.dumps(
            {k: v.model_dump() for k, v in section.slot_fills.items()},
            sort_keys=True,
        )
        override_json = json.dumps(section.style_overrides, sort_keys=True)
        return (section.component_slug, _md5(slot_json), _md5(override_json))
