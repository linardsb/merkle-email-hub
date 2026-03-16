"""Multi-representation chunk summarizer for improved embedding quality.

Generates human-readable summaries of HTML/CSS chunks so that embeddings
capture semantic meaning rather than raw markup syntax. Summaries are used
for embedding; original content is returned at search time.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# CSS property extraction
_CSS_RULE_RE = re.compile(r"([^{]+)\{([^}]+)\}", re.DOTALL)
_CSS_PROPERTY_RE = re.compile(r"([\w-]+)\s*:")


@dataclass(frozen=True)
class ChunkSummary:
    """Result of summarizing a chunk."""

    index: int
    summary: str | None  # None = no summary generated, embed content directly


class ChunkSummarizer:
    """Generates summaries for document chunks by section_type.

    Routing:
    - section_type="style" -> deterministic CSS summary (list selectors + properties)
    - section_type="mso_conditional" -> deterministic MSO description
    - section_type="section" or "body" -> LLM summary (HTML body sections)
    - section_type=None (plain text) -> skip (prose embeds well already)
    """

    async def summarize(
        self,
        chunks: list[tuple[int, str, str | None]],
    ) -> list[ChunkSummary]:
        """Summarize a batch of chunks.

        Args:
            chunks: List of (chunk_index, content, section_type) tuples.

        Returns:
            ChunkSummary per chunk. summary=None means "embed content directly".
        """
        results: list[ChunkSummary] = []
        llm_queue: list[tuple[int, str]] = []  # (position_in_results, content)

        for chunk_index, content, section_type in chunks:
            if section_type == "style":
                summary = self.summarize_css_block(content)
                results.append(ChunkSummary(index=chunk_index, summary=summary))
            elif section_type == "mso_conditional":
                summary = self.summarize_mso_block(content)
                results.append(ChunkSummary(index=chunk_index, summary=summary))
            elif section_type in ("section", "body"):
                # Queue for LLM summarization
                results.append(ChunkSummary(index=chunk_index, summary=None))  # placeholder
                llm_queue.append((len(results) - 1, content))
            else:
                # Plain text or unknown — skip summarization
                results.append(ChunkSummary(index=chunk_index, summary=None))

        # Run LLM summaries with concurrency limit
        if llm_queue:
            llm_summaries = await self._summarize_html_batch([content for _, content in llm_queue])
            for (pos, _content), llm_summary in zip(llm_queue, llm_summaries, strict=True):
                results[pos] = ChunkSummary(index=results[pos].index, summary=llm_summary)

        return results

    @staticmethod
    def summarize_css_block(css: str) -> str:
        """Deterministic CSS summary: list selectors and property names.

        Example output:
            "CSS rules: .header (background-color, padding, font-family);
             @media (max-width: 600px) .header (display, width)"
        """
        rules: list[str] = []
        for match in _CSS_RULE_RE.finditer(css):
            selector = match.group(1).strip()
            body = match.group(2)
            # Clean selector (remove <style> tags if present)
            selector = re.sub(r"</?style[^>]*>", "", selector).strip()
            if not selector:
                continue
            # Collapse whitespace
            selector = re.sub(r"\s+", " ", selector)
            props = _CSS_PROPERTY_RE.findall(body)
            if props:
                rules.append(f"{selector} ({', '.join(props)})")

        if not rules:
            return f"CSS style block ({len(css)} chars)"

        return "CSS rules: " + "; ".join(rules)

    @staticmethod
    def summarize_mso_block(html: str) -> str:
        """Deterministic MSO conditional summary.

        Example output:
            "MSO conditional block [if mso | IE]: 2 tables, VML shape,
             fallback content for Outlook rendering"
        """
        # Extract condition
        condition_match = re.search(r"<!--\[if\s+([^\]]+)\]>", html, re.IGNORECASE)
        condition = condition_match.group(1).strip() if condition_match else "mso"

        # Count structural elements
        tables = len(re.findall(r"<table", html, re.IGNORECASE))
        vml = len(re.findall(r"<v:", html, re.IGNORECASE))

        parts = [f"MSO conditional block [if {condition}]"]
        if tables:
            parts.append(f"{tables} table{'s' if tables > 1 else ''}")
        if vml:
            parts.append(f"{vml} VML element{'s' if vml > 1 else ''}")

        return parts[0] + (": " + ", ".join(parts[1:]) if len(parts) > 1 else "")

    async def _summarize_html_batch(self, contents: list[str]) -> list[str | None]:
        """LLM-summarize HTML body sections with concurrency limit.

        One LLM call per chunk. On failure, returns None (embed content directly).
        Uses a single shared httpx client for connection pooling.
        """
        settings = get_settings()
        if not settings.knowledge.multi_rep_api_key:
            logger.warning("knowledge.summarizer.no_api_key")
            return [None] * len(contents)

        semaphore = asyncio.Semaphore(settings.knowledge.multi_rep_max_concurrency)

        async with httpx.AsyncClient(timeout=30.0) as client:

            async def _summarize_one(content: str) -> str | None:
                async with semaphore:
                    return await self._llm_summarize(client, content, settings)

            return list(await asyncio.gather(*[_summarize_one(c) for c in contents]))

    @staticmethod
    async def _llm_summarize(
        client: httpx.AsyncClient,
        html: str,
        settings: object,
    ) -> str | None:
        """Call LLM to summarize a single HTML section. Best-effort."""
        truncated = html[:4000]  # Cap input to avoid token overflow
        knowledge = settings.knowledge  # type: ignore[attr-defined]

        try:
            response = await client.post(
                f"{knowledge.multi_rep_api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {knowledge.multi_rep_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": knowledge.multi_rep_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an email HTML analyst. Given an HTML section from "
                                "an email template, write a 1-2 sentence summary describing "
                                "what this section does, its layout approach, and key CSS "
                                "techniques used. Focus on semantic meaning, not syntax. "
                                "Return ONLY the summary text, no quotes or prefixes."
                            ),
                        },
                        {"role": "user", "content": truncated},
                    ],
                    "temperature": 0.0,
                },
            )
            response.raise_for_status()
            data = response.json()
            summary: str = data["choices"][0]["message"]["content"].strip()
            return summary if summary else None
        except Exception:
            logger.warning(
                "knowledge.summarizer.llm_failed",
                exc_info=True,
            )
            return None
