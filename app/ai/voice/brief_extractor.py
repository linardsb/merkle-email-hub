"""LLM-based structured email brief extraction from transcript."""

from __future__ import annotations

import json
from typing import Any, cast

from app.ai.protocols import CompletionResponse, Message
from app.ai.voice.exceptions import BriefExtractionError
from app.ai.voice.schemas import EmailBrief, SectionBrief, Transcript
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_EXTRACTION_PROMPT = """\
You are an email campaign brief extractor. Given a transcript of someone describing \
an email campaign, extract a structured brief.

Return ONLY valid JSON with this schema:
{
  "topic": "string — main email campaign topic/subject",
  "sections": [
    {
      "type": "hero|content_block|cta|product_card|countdown|footer|testimonial|social",
      "description": "what this section should contain",
      "content_hints": ["specific details mentioned"]
    }
  ],
  "tone": "string — overall tone (professional, casual, urgent, playful, etc.)",
  "cta_text": "string or null — specific call-to-action text if mentioned",
  "audience": "string or null — target audience if mentioned",
  "constraints": ["any specific constraints, deadlines, or requirements mentioned"],
  "confidence": 0.0-1.0
}

Ignore filler words, self-corrections, and off-topic tangents. Focus on the email \
campaign intent. If the transcript is unclear or too short, set confidence below 0.7."""


class VoiceBriefExtractor:
    """Extracts structured email brief from transcript via LLM."""

    async def extract(self, transcript: Transcript) -> tuple[EmailBrief, float]:
        """Extract structured brief from transcript.

        Returns:
            Tuple of (EmailBrief, confidence). If confidence < threshold,
            the brief contains only raw_transcript with minimal structure.
        """
        from app.ai.sanitize import sanitize_prompt

        sanitized_text = sanitize_prompt(transcript.text)

        settings = get_settings()

        # Get LLM provider
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model

        registry = get_registry()
        provider_name = settings.ai.provider

        # Use configured extraction model or default
        model = settings.voice.extraction_model or resolve_model("standard")
        provider = registry.get_llm(provider_name)

        messages = [
            Message(role="system", content=_EXTRACTION_PROMPT),
            Message(role="user", content=f"Transcript:\n\n{sanitized_text}"),
        ]

        try:
            result: CompletionResponse = await provider.complete(
                messages, model_override=model, max_tokens=2048, temperature=0.1
            )
        except Exception as exc:
            logger.error("voice.extract.llm_failed", error=str(exc))
            raise BriefExtractionError(f"Brief extraction LLM call failed: {exc}") from exc

        # Validate response is a string
        if not isinstance(result.content, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise BriefExtractionError("LLM returned non-text response")

        # Parse JSON response
        try:
            # Strip markdown code fences if present
            content = result.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.removesuffix("```")
                content = content.strip()

            data: dict[str, Any] = json.loads(content)
        except (json.JSONDecodeError, IndexError) as exc:
            logger.warning("voice.extract.json_parse_failed", content=result.content[:200])
            raise BriefExtractionError(f"Failed to parse extraction response: {exc}") from exc

        raw_confidence = data.get("confidence", 0.5)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            logger.warning("voice.extract.invalid_confidence", value=str(raw_confidence))
            confidence = 0.5

        # If low confidence, return minimal brief with raw transcript
        if confidence < settings.voice.confidence_threshold:
            logger.info("voice.extract.low_confidence", confidence=confidence)
            return (
                EmailBrief(
                    topic=data.get("topic", "Voice brief"),
                    sections=[],
                    tone=data.get("tone", "professional"),
                    raw_transcript=sanitized_text,
                ),
                confidence,
            )

        raw_sections: list[Any] = data.get("sections", [])
        typed_sections = cast(
            list[dict[str, Any]],
            [s for s in raw_sections if isinstance(s, dict)],
        )
        sections = [
            SectionBrief(
                type=s.get("type", "content_block"),
                description=s.get("description", ""),
                content_hints=s.get("content_hints", []),
            )
            for s in typed_sections
        ]

        brief = EmailBrief(
            topic=data.get("topic", ""),
            sections=sections,
            tone=data.get("tone", "professional"),
            cta_text=data.get("cta_text"),
            audience=data.get("audience"),
            constraints=data.get("constraints", []),
            raw_transcript=sanitized_text,
        )

        logger.info(
            "voice.extract.completed",
            topic=brief.topic,
            section_count=len(sections),
            confidence=confidence,
        )

        return brief, confidence
