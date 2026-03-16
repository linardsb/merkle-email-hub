"""Code-aware HTML chunking that respects structural boundaries.

Splits HTML emails by semantic sections: <style> blocks, MSO conditionals,
and structural body elements (<table>, <div>, <section>). Falls back to
generic chunk_text() on parse errors or non-HTML content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import lxml.html as lxml_html

from app.knowledge.chunking import ChunkResult, chunk_text

# Reuse MSO patterns from qa_engine (same regexes, avoid import coupling)
_MSO_OPENER_RE = re.compile(r"<!--\[if\s+([^\]]+)\]>", re.IGNORECASE)
_MSO_CLOSER_RE = re.compile(r"<!\[endif\]-->")
_HTML_DETECT_RE = re.compile(r"<!DOCTYPE|<html|<table", re.IGNORECASE)
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_STRUCTURAL_TAGS = frozenset({"table", "div", "section"})


@dataclass
class HTMLChunkResult:
    """A chunk of HTML with structural metadata."""

    content: str
    chunk_index: int
    section_type: str | None = None
    summary: str | None = None
    metadata: dict[str, str | int | None] = field(
        default_factory=lambda: dict[str, str | int | None]()
    )


def is_html_content(text: str) -> bool:
    """Check if text appears to be HTML content."""
    return bool(_HTML_DETECT_RE.search(text[:500]))


def chunk_html(
    html: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
) -> list[HTMLChunkResult]:
    """Split HTML into structure-aware chunks.

    1. Extract <style> blocks as standalone chunks
    2. Extract MSO conditional blocks as standalone chunks
    3. Split <body> by first-level structural elements
    4. Recurse into nested elements if sections exceed chunk_size
    5. Fall back to chunk_text() on parse errors

    Args:
        html: Full HTML document string.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap chars between adjacent body chunks.

    Returns:
        List of HTMLChunkResult with section_type metadata.
    """
    if not html or not html.strip():
        return []

    html = html.strip()

    # Non-HTML → delegate to text chunker
    if not is_html_content(html):
        return _from_text_chunks(chunk_text(html, chunk_size, chunk_overlap))

    try:
        return _chunk_html_internal(html, chunk_size, chunk_overlap)
    except Exception:
        # Parse failure → graceful fallback
        return _from_text_chunks(chunk_text(html, chunk_size, chunk_overlap))


def _chunk_html_internal(
    html: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[HTMLChunkResult]:
    """Internal HTML chunking (may raise on malformed HTML)."""
    results: list[HTMLChunkResult] = []
    idx = 0

    # 1. Extract <style> blocks (from raw HTML, before DOM parsing strips them)
    style_chunks = _extract_style_blocks(html)
    for content in style_chunks:
        if content.strip():
            results.append(
                HTMLChunkResult(
                    content=content.strip(),
                    chunk_index=idx,
                    section_type="style",
                    summary=f"CSS style block ({len(content)} chars)",
                )
            )
            idx += 1

    # 2. Extract MSO conditional blocks (regex on raw HTML)
    mso_chunks = _extract_mso_blocks(html)
    for content in mso_chunks:
        if content.strip():
            results.append(
                HTMLChunkResult(
                    content=content.strip(),
                    chunk_index=idx,
                    section_type="mso_conditional",
                    summary=f"MSO conditional block ({len(content)} chars)",
                )
            )
            idx += 1

    # 3. Parse DOM and split body by structural elements
    doc = lxml_html.document_fromstring(html)
    body = doc.body
    if body is None:
        # No body → single chunk of entire HTML
        if len(html) <= chunk_size:
            results.append(
                HTMLChunkResult(
                    content=html,
                    chunk_index=idx,
                    section_type="body",
                )
            )
        else:
            text_chunks = chunk_text(html, chunk_size, chunk_overlap)
            results.extend(_from_text_chunks(text_chunks, start_index=idx))
        return results

    # Get first-level structural children
    structural_sections = _split_body_structural(body)

    # Collect body parts, then merge small adjacent ones
    body_parts: list[str] = []
    for section_html in structural_sections:
        if not section_html.strip():
            continue
        if len(section_html) <= chunk_size:
            body_parts.append(section_html.strip())
        else:
            # Recurse into nested elements
            sub_chunks = _split_nested(section_html, chunk_size, chunk_overlap)
            body_parts.extend(s.strip() for s in sub_chunks if s.strip())

    # Merge small adjacent parts
    merged_parts = _merge_small_chunks(body_parts, chunk_size)
    for part in merged_parts:
        results.append(
            HTMLChunkResult(
                content=part,
                chunk_index=idx,
                section_type="section",
            )
        )
        idx += 1

    # Edge case: no chunks produced (e.g. empty body)
    if not results:
        return _from_text_chunks(chunk_text(html, chunk_size, chunk_overlap))

    return results


def _extract_style_blocks(html: str) -> list[str]:
    """Extract complete <style>...</style> blocks from raw HTML."""
    return [m.group(0) for m in _STYLE_BLOCK_RE.finditer(html)]


def _extract_mso_blocks(html: str) -> list[str]:
    """Extract MSO conditional blocks (<!--[if ...]>...<![endif]-->).

    Finds opener→closer pairs and returns the full block including comments.
    Skips non-MSO conditionals (<!--[if !mso]>).
    """
    blocks: list[str] = []
    for m in _MSO_OPENER_RE.finditer(html):
        condition = m.group(1).strip()
        if condition.lower().startswith("!mso"):
            continue
        # Find matching closer after this opener
        closer = _MSO_CLOSER_RE.search(html, m.end())
        if closer:
            block = html[m.start() : closer.end()]
            blocks.append(block)
    return blocks


def _split_body_structural(body: lxml_html.HtmlElement) -> list[str]:
    """Split body into first-level structural element HTML strings."""
    from lxml.html import tostring as html_tostring

    sections: list[str] = []
    current_inline: list[str] = []

    for child in body:
        tag = child.tag if isinstance(child.tag, str) else ""
        child_html = html_tostring(child, encoding="unicode")

        if tag.lower() in _STRUCTURAL_TAGS:
            # Flush accumulated inline content
            if current_inline:
                sections.append("\n".join(current_inline))
                current_inline = []
            sections.append(child_html)
        else:
            current_inline.append(child_html)

    # Flush remaining inline content
    if current_inline:
        sections.append("\n".join(current_inline))

    return sections


def _split_nested(
    section_html: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursively split an oversized section by its children.

    For tables: split by rows. For divs: split by child divs/elements.
    If children are still too large, fall back to text chunking.
    """
    try:
        fragment = lxml_html.fragment_fromstring(section_html, create_parent=False)
    except Exception:
        return [c.content for c in chunk_text(section_html, chunk_size, chunk_overlap)]

    from lxml.html import tostring as html_tostring

    # If it's a single element, try splitting by its children
    if hasattr(fragment, "tag"):
        children_html: list[str] = []
        for child in fragment:
            child_str = html_tostring(child, encoding="unicode")
            if len(child_str) <= chunk_size:
                children_html.append(child_str)
            else:
                # Recurse one more level
                sub = _split_nested(child_str, chunk_size, chunk_overlap)
                children_html.extend(sub)

        if children_html:
            # Merge small adjacent chunks
            return _merge_small_chunks(children_html, chunk_size)

    # Can't split further → text fallback
    return [c.content for c in chunk_text(section_html, chunk_size, chunk_overlap)]


def _merge_small_chunks(parts: list[str], chunk_size: int) -> list[str]:
    """Merge adjacent small HTML fragments to avoid tiny chunks."""
    if not parts:
        return []

    merged: list[str] = []
    current = parts[0]

    for part in parts[1:]:
        combined = current + "\n" + part
        if len(combined) <= chunk_size:
            current = combined
        else:
            merged.append(current)
            current = part

    if current.strip():
        merged.append(current)

    return merged


def _from_text_chunks(
    chunks: list[ChunkResult],
    start_index: int = 0,
) -> list[HTMLChunkResult]:
    """Convert generic ChunkResults to HTMLChunkResults (text fallback)."""
    return [
        HTMLChunkResult(
            content=c.content,
            chunk_index=start_index + i,
            section_type="text_fallback",
            metadata=c.metadata,
        )
        for i, c in enumerate(chunks)
    ]
