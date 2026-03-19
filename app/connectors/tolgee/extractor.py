"""HTML → translatable key extraction for Tolgee TMS integration."""

from __future__ import annotations

import re
from html.parser import HTMLParser

from app.connectors.tolgee.schemas import TranslationKey
from app.core.logging import get_logger

logger = get_logger(__name__)

# Elements whose text content is translatable
_TRANSLATABLE_ELEMENTS = frozenset(
    {
        "td",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "a",
        "span",
        "li",
        "th",
    }
)

# Attributes that contain translatable text
_TRANSLATABLE_ATTRS = frozenset({"alt", "title"})

# Content that should NOT be extracted for translation
_SKIP_PATTERN = re.compile(
    r"^("
    r"https?://\S+"  # URLs
    r"|[\w.+-]+@[\w-]+\.[\w.]+"  # Email addresses
    r"|(?:\{\{.*\}\}|<%.*%>|\{%.*%\})"  # Template tags (Liquid, Handlebars, ERB)
    r"|&\w+;"  # HTML entities
    r"|\s*$"  # Whitespace-only
    r"|\d+(\.\d+)?%?"  # Pure numbers/percentages
    r")$",
    re.DOTALL,
)

# ICU message format pattern — preserve as-is (translators handle ICU in Tolgee)
_ICU_PATTERN = re.compile(r"\{[\w]+,\s*(plural|select|selectordinal)\s*,")


class _KeyExtractor(HTMLParser):
    """Extract translatable content from email HTML."""

    def __init__(self, template_id: int, namespace: str) -> None:
        super().__init__()
        self.template_id = template_id
        self.namespace = namespace
        self.keys: list[TranslationKey] = []
        self._tag_stack: list[str] = []
        self._current_section: str = "body"
        self._skip_depth: int = 0
        self._seen_keys: set[str] = set()  # Deduplicate
        self._element_counters: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag)

        # Track sections from data-section attributes
        attr_dict = dict(attrs)
        section = attr_dict.get("data-section")
        if section:
            self._current_section = section

        # Skip non-visible elements
        if tag in ("style", "script", "head"):
            self._skip_depth += 1
            return

        # Extract translatable attributes (alt, title)
        if self._skip_depth == 0:
            for attr_name in _TRANSLATABLE_ATTRS:
                value = attr_dict.get(attr_name)
                if value and not _SKIP_PATTERN.match(value.strip()):
                    self._add_key(tag, value.strip(), attr_name)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script", "head"):
            self._skip_depth = max(0, self._skip_depth - 1)
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if not text or _SKIP_PATTERN.match(text):
            return
        # Only extract from translatable elements
        current_tag = self._tag_stack[-1] if self._tag_stack else ""
        if current_tag in _TRANSLATABLE_ELEMENTS:
            self._add_key(current_tag, text, "text")

    def _add_key(self, element: str, source_text: str, attr_type: str) -> None:
        """Add a translation key, deduplicating by source text."""
        # Generate counter-based unique key
        counter_key = f"{self._current_section}.{element}"
        count = self._element_counters.get(counter_key, 0) + 1
        self._element_counters[counter_key] = count

        suffix = f"_{count}" if count > 1 else ""
        key = f"template_{self.template_id}.{self._current_section}.{element}{suffix}"

        if attr_type != "text":
            key = f"{key}.{attr_type}"

        # Deduplicate
        if key in self._seen_keys:
            return
        self._seen_keys.add(key)

        # Detect ICU format — add context hint for translators
        context = None
        if _ICU_PATTERN.search(source_text):
            context = "ICU message format — preserve {placeholders} and plural/select syntax"

        self.keys.append(
            TranslationKey(
                key=key,
                source_text=source_text,
                context=context,
                namespace=self.namespace,
            )
        )


def extract_keys(
    html: str,
    template_id: int,
    *,
    namespace: str = "email",
    subject: str | None = None,
    preheader: str | None = None,
) -> list[TranslationKey]:
    """Extract translatable keys from email HTML + metadata.

    Args:
        html: Email HTML source
        template_id: Hub template ID (used in key naming)
        namespace: Tolgee namespace (default "email")
        subject: Template subject line (extracted as separate key)
        preheader: Template preheader text (extracted as separate key)

    Returns:
        List of TranslationKey with unique key names and source text.
    """
    keys: list[TranslationKey] = []

    # Extract subject and preheader as top-level keys
    if subject and not _SKIP_PATTERN.match(subject.strip()):
        keys.append(
            TranslationKey(
                key=f"template_{template_id}.meta.subject",
                source_text=subject.strip(),
                context="Email subject line — keep under 60 characters",
                namespace=namespace,
            )
        )
    if preheader and not _SKIP_PATTERN.match(preheader.strip()):
        keys.append(
            TranslationKey(
                key=f"template_{template_id}.meta.preheader",
                source_text=preheader.strip(),
                context="Email preheader/preview text — keep under 100 characters",
                namespace=namespace,
            )
        )

    # Parse HTML for content keys
    extractor = _KeyExtractor(template_id, namespace)
    extractor.feed(html)
    keys.extend(extractor.keys)

    logger.info(
        "tolgee.keys_extracted",
        template_id=template_id,
        key_count=len(keys),
        namespace=namespace,
    )
    return keys
