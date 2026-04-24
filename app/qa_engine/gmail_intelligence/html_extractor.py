from __future__ import annotations

import re
from html.parser import HTMLParser

from app.qa_engine.gmail_intelligence.types import EmailSignals

_URGENCY_RE = re.compile(
    r"\b(hurry|limited|expires?|ending soon|last chance|act now|"
    r"don't miss|only \d+|flash sale|while supplies)\b",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"(?:\$[\d,.]+|[\d,.]+\s*%\s*off|\d+%\s*discount)", re.IGNORECASE)
_UNSUBSCRIBE_RE = re.compile(r"unsubscribe|opt[\s-]?out|manage\s+preferences", re.IGNORECASE)
_SCHEMA_ORG_RE = re.compile(r'(?:itemtype|typeof)\s*=\s*["\']https?://schema\.org', re.IGNORECASE)
_PREVIEW_RE = re.compile(
    # Bounded char classes prevent polynomial backtracking (py/polynomial-redos).
    r'class\s{0,10}=\s{0,10}["\'][^"\']{0,1000}preview[^"\']{0,1000}["\']',
    re.IGNORECASE,
)


class _TextExtractor(HTMLParser):
    """Extract visible text, skip style/script tags."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = False
        self._skip_tags = {"style", "script", "head"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag.lower() in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._skip_tags:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self.parts.append(text)


def extract_signals(html: str) -> EmailSignals:
    """Extract text content and promotional signals from email HTML."""
    extractor = _TextExtractor()
    extractor.feed(html)
    plain_text = " ".join(extractor.parts)

    # Count links
    link_count = len(re.findall(r"<a\s", html, re.IGNORECASE))
    # Count images
    image_count = len(re.findall(r"<img\s", html, re.IGNORECASE))
    # Count CTAs (buttons/links with action text)
    cta_count = len(
        re.findall(
            r"(?:shop now|buy now|get started|sign up|learn more|view|download|order|"
            r"subscribe|claim|redeem|activate|book now|try free|start)",
            plain_text,
            re.IGNORECASE,
        )
    )

    # Extract preview text (first hidden div or explicit preview class)
    preview_text = ""
    preview_match = _PREVIEW_RE.search(html)
    if preview_match:
        # Get text content of the preview element (simplified)
        start = preview_match.end()
        end_tag = html.find("</", start)
        if end_tag > start:
            preview_text = re.sub(r"<[^>]{1,10000}>", "", html[start:end_tag]).strip()

    return EmailSignals(
        has_unsubscribe=bool(_UNSUBSCRIBE_RE.search(html)),
        has_schema_org=bool(_SCHEMA_ORG_RE.search(html)),
        cta_count=cta_count,
        price_mentions=len(_PRICE_RE.findall(plain_text)),
        urgency_words=len(_URGENCY_RE.findall(plain_text)),
        link_count=link_count,
        image_count=image_count,
        plain_text=plain_text[:10_000],  # Cap for LLM context
        preview_text=preview_text,
    )
