"""Gmail AI summary predictor — LLM-based simulation of Gemini summarization."""

from __future__ import annotations

import json

import httpx

from app.ai.sanitize import sanitize_prompt
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.gmail_intelligence.html_extractor import extract_signals
from app.qa_engine.gmail_intelligence.prompts import PREDICTION_SYSTEM_PROMPT
from app.qa_engine.gmail_intelligence.types import EmailSignals, GmailPrediction

logger = get_logger(__name__)

_VALID_CATEGORIES = frozenset({"Primary", "Promotions", "Updates", "Social", "Forums"})


class GmailSummaryPredictor:
    """Predicts how Gmail's AI will summarize an email."""

    async def predict(
        self,
        html: str,
        subject: str,
        from_name: str,
    ) -> GmailPrediction:
        """Generate a predicted Gmail AI summary.

        Args:
            html: Email HTML content.
            subject: Email subject line.
            from_name: Sender display name.

        Returns:
            GmailPrediction with summary, category, actions, and suggestions.
        """
        signals = extract_signals(html)
        user_message = self._build_user_message(subject, from_name, signals)

        raw_response = await self._call_llm(
            sanitize_prompt(user_message),
            PREDICTION_SYSTEM_PROMPT,
        )

        return self._parse_prediction(raw_response, signals)

    @staticmethod
    def _build_user_message(
        subject: str,
        from_name: str,
        signals: EmailSignals,
    ) -> str:
        """Build the user message with email details and extracted signals."""
        parts = [
            f"Subject: {subject}",
            f"From: {from_name}",
        ]
        if signals.preview_text:
            parts.append(f"Preview text: {signals.preview_text}")

        parts.append(f"\nEmail body text:\n{signals.plain_text[:6000]}")

        # Include signal metadata for better category prediction
        signal_parts = [
            f"Unsubscribe link: {'yes' if signals.has_unsubscribe else 'no'}",
            f"Schema.org markup: {'yes' if signals.has_schema_org else 'no'}",
            f"CTA count: {signals.cta_count}",
            f"Price mentions: {signals.price_mentions}",
            f"Urgency words: {signals.urgency_words}",
            f"Link count: {signals.link_count}",
        ]
        parts.append("\nExtracted signals:\n" + "\n".join(signal_parts))

        return "\n".join(parts)

    @staticmethod
    async def _call_llm(user_message: str, system_prompt: str) -> str:
        """Make LLM API call via OpenAI-compatible endpoint."""
        settings = get_settings()
        config = settings.qa_gmail_predictor

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(
                    f"{config.api_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    logger.warning("gmail_intelligence.llm.empty_choices")
                    return "{}"
                return str(choices[0].get("message", {}).get("content", "{}")).strip()
        except httpx.TimeoutException:
            logger.warning("gmail_intelligence.llm.timeout", timeout=config.timeout_seconds)
            return "{}"
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "gmail_intelligence.llm.http_error",
                status_code=exc.response.status_code,
            )
            return "{}"
        except httpx.ConnectError:
            logger.warning("gmail_intelligence.llm.connect_error")
            return "{}"

    @staticmethod
    def _parse_prediction(raw: str, signals: EmailSignals) -> GmailPrediction:
        """Parse LLM JSON response into GmailPrediction."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("gmail_intelligence.predict.parse_failed", raw_length=len(raw))
            # Fallback: deterministic category guess from signals
            category = _guess_category(signals)
            return GmailPrediction(
                summary_text="Unable to generate prediction",
                predicted_category=category,
                confidence=0.0,
            )

        category = data.get("predicted_category", "Primary")
        if category not in _VALID_CATEGORIES:
            category = "Primary"

        confidence = data.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        return GmailPrediction(
            summary_text=str(data.get("summary_text", "")),
            predicted_category=category,
            key_actions=[str(a) for a in data.get("key_actions", [])],
            promotion_signals=[str(s) for s in data.get("promotion_signals", [])],
            improvement_suggestions=[str(s) for s in data.get("improvement_suggestions", [])],
            confidence=confidence,
        )


def _guess_category(signals: EmailSignals) -> str:
    """Deterministic category fallback from signals."""
    if signals.has_unsubscribe and (signals.price_mentions > 0 or signals.cta_count >= 3):
        return "Promotions"
    if signals.has_schema_org:
        return "Updates"
    if signals.has_unsubscribe:
        return "Promotions"
    return "Primary"
