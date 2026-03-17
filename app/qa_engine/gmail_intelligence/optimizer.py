"""Preview text and subject line optimizer for Gmail AI summaries."""

from __future__ import annotations

import json

from app.ai.sanitize import sanitize_prompt
from app.core.logging import get_logger
from app.qa_engine.gmail_intelligence.html_extractor import extract_signals
from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor
from app.qa_engine.gmail_intelligence.prompts import OPTIMIZATION_SYSTEM_PROMPT
from app.qa_engine.gmail_intelligence.types import OptimizedPreview

logger = get_logger(__name__)


class PreviewTextOptimizer:
    """Suggests subject/preview text improvements for better AI summaries."""

    async def optimize(
        self,
        html: str,
        subject: str,
        from_name: str,
        target_summary: str | None = None,
    ) -> OptimizedPreview:
        """Generate optimized subject/preview text suggestions.

        Args:
            html: Email HTML content.
            subject: Current subject line.
            from_name: Sender display name.
            target_summary: Optional desired summary to optimize toward.

        Returns:
            OptimizedPreview with suggested alternatives and reasoning.
        """
        signals = extract_signals(html)

        parts = [
            f"Subject: {subject}",
            f"From: {from_name}",
        ]
        if signals.preview_text:
            parts.append(f"Current preview text: {signals.preview_text}")

        parts.append(f"\nEmail body text (abbreviated):\n{signals.plain_text[:4000]}")

        if target_summary:
            parts.append(f"\nDesired summary tone/focus: {target_summary}")

        user_message = sanitize_prompt("\n".join(parts))

        raw = await GmailSummaryPredictor._call_llm(
            user_message,
            OPTIMIZATION_SYSTEM_PROMPT,
        )

        return self._parse_optimization(raw, subject, signals.preview_text)

    @staticmethod
    def _parse_optimization(
        raw: str,
        original_subject: str,
        original_preview: str,
    ) -> OptimizedPreview:
        """Parse LLM JSON response into OptimizedPreview."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("gmail_intelligence.optimize.parse_failed", raw_length=len(raw))
            return OptimizedPreview(
                original_subject=original_subject,
                original_preview=original_preview,
                reasoning="Unable to generate optimization suggestions",
            )

        return OptimizedPreview(
            original_subject=original_subject,
            suggested_subjects=[str(s) for s in data.get("suggested_subjects", [])],
            original_preview=original_preview,
            suggested_previews=[str(s) for s in data.get("suggested_previews", [])],
            reasoning=str(data.get("reasoning", "")),
        )
