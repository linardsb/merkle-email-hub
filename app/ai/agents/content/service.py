# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Content agent service — orchestrates LLM → extract → spam check."""

import re
from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.content.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.content.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.content.schemas import ContentRequest, ContentResponse, SpamWarning
from app.ai.routing import TaskTier
from app.ai.sanitize import validate_output
from app.qa_engine.checks.spam_score import SPAM_TRIGGERS
from app.qa_engine.schemas import QACheckResult

# ── Regex patterns for content extraction ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:text|TEXT)?\s*\n(.*?)```",
    re.DOTALL,
)

_ALT_DELIMITER = "---"

# ── Operation-to-tier mapping ──

_OPERATION_TIERS: dict[str, TaskTier] = {
    "subject_line": "standard",
    "preheader": "standard",
    "cta": "standard",
    "body_copy": "standard",
    "rewrite": "standard",
    "shorten": "lightweight",
    "expand": "lightweight",
    "tone_adjust": "standard",
}


def extract_content(raw: str) -> list[str]:
    """Extract text alternatives from LLM response.

    Looks for ```text ... ``` code blocks. Falls back to raw content
    if no code block is found. Splits by --- delimiter for multiple
    alternatives.
    """
    match = _CODE_BLOCK_RE.search(raw)
    inner = match.group(1) if match else raw

    parts = inner.split(_ALT_DELIMITER)
    results = [part.strip() for part in parts if part.strip()]
    return results


def check_spam_triggers(texts: list[str]) -> list[SpamWarning]:
    """Scan generated text for known spam trigger words/phrases."""
    warnings: list[SpamWarning] = []
    for text in texts:
        text_lower = text.lower()
        for trigger in SPAM_TRIGGERS:
            pos = text_lower.find(trigger)
            if pos == -1:
                continue
            start = max(0, pos - 15)
            end = min(len(text), pos + len(trigger) + 15)
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."
            warnings.append(SpamWarning(trigger=trigger, context=context))
    return warnings


class ContentService(BaseAgentService):
    """Orchestrates the content agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract content → spam check.
    """

    agent_name = "content"
    model_tier = "standard"
    max_tokens = 2048
    run_qa_default = False
    stream_prefix = "content"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: ContentRequest = request
        return _detect_relevant_skills(req.operation, req.brand_voice, req.text)

    def _build_user_message(self, request: Any) -> str:
        req: ContentRequest = request
        parts: list[str] = [
            f"Operation: {req.operation}",
            f"\nSource text:\n{req.text}",
        ]
        if req.tone:
            parts.append(f"\nTarget tone: {req.tone}")
        if req.brand_voice:
            parts.append(f"\nBrand voice guidelines:\n{req.brand_voice}")

        # Auto-generate 5 subject line alternatives when user doesn't specify
        effective_alternatives = req.num_alternatives
        if req.operation == "subject_line" and req.num_alternatives == 1:
            effective_alternatives = 5

        if effective_alternatives > 1:
            parts.append(
                f"\nGenerate {effective_alternatives} distinct alternatives, "
                "separated by --- on its own line."
            )
        return "\n".join(parts)

    def _post_process(self, raw_content: str) -> str:
        """Content agent returns text, not HTML. Return validated raw content."""
        return validate_output(raw_content)

    def _build_response(
        self,
        *,
        request: Any,
        html: str,
        qa_results: list[QACheckResult] | None,
        qa_passed: bool | None,
        model_id: str,
        confidence: float | None,
        skills_loaded: list[str],
        raw_content: str,
    ) -> ContentResponse:
        req: ContentRequest = request
        # For content agent, "html" is actually raw text (via overridden _post_process)
        alternatives = extract_content(html)
        warnings = check_spam_triggers(alternatives)
        return ContentResponse(
            content=alternatives,
            operation=req.operation,
            spam_warnings=warnings,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    def _get_model_tier(self, request: Any) -> TaskTier:
        """Return operation-specific model tier (thread-safe, no state mutation)."""
        req: ContentRequest = request
        return _OPERATION_TIERS.get(req.operation, "standard")

    # Content uses generate/stream_generate names for backward compat with routes
    async def generate(self, request: ContentRequest) -> ContentResponse:
        """Generate content via LLM with spam detection."""
        return await self.process(request)  # type: ignore[no-any-return]

    async def stream_generate(self, request: ContentRequest) -> AsyncIterator[str]:
        """Stream content generation via SSE."""
        async for chunk in self.stream_process(request):
            yield chunk


# ── Module-level singleton ──

_content_service: ContentService | None = None


def get_content_service() -> ContentService:
    """Get or create the content service singleton."""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service
