# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Content agent service — orchestrates LLM → extract → spam check → length validate."""

import contextvars
import json
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.multimodal import ContentBlock

from app.ai.agents.base import CONFIDENCE_INSTRUCTION, BaseAgentService
from app.ai.agents.content.length_guardrail import (
    build_retry_constraint,
    validate_alternatives,
)
from app.ai.agents.content.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.content.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.content.schemas import ContentRequest, ContentResponse, SpamWarning
from app.ai.agents.schemas.content_decisions import ContentDecisions, SlotContentRefinement
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import TaskTier, resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks.spam_score import SPAM_TRIGGERS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

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

# Per-request storage for length warnings (avoids race on singleton instance)
_length_warnings_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "content_length_warnings", default=None
)


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
    extract content → spam check → length validate → optional retry.
    """

    agent_name = "content"
    model_tier = "standard"
    max_tokens = 2048
    run_qa_default = False
    stream_prefix = "content"
    _output_mode_supported: bool = True

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

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
        """Content agent returns text, not HTML. Return validated raw content.

        Punctuation cleanup is NOT applied here — it runs per-alternative
        in validate_alternatives() after extraction, where it targets actual
        content rather than raw LLM output (which includes code fences).
        """
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
        length_warns = _length_warnings_var.get(None) or []
        return ContentResponse(
            content=alternatives,
            operation=req.operation,
            spam_warnings=warnings,
            length_warnings=length_warns,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
        )

    def _get_model_tier(self, request: Any) -> TaskTier:
        """Return operation-specific model tier (thread-safe, no state mutation)."""
        req: ContentRequest = request
        return _OPERATION_TIERS.get(req.operation, "standard")

    async def _process_structured(self, request: Any) -> ContentResponse:
        """Structured mode: refine slot content and return decisions."""
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: ContentRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self._get_model_tier(request))
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode="structured")

        plan_data = req.build_plan or {}
        user_message = (
            f"Refine content in the following EmailBuildPlan. Operation: {req.operation}\n\n"
            f"Plan: {json.dumps(plan_data, default=str)}\n\n"
            f"Source text: {req.text}\n\n"
            "Return a JSON object with:\n"
            "- subject_line: refined subject line (empty string if not changing)\n"
            "- preheader: refined preheader (empty string if not changing)\n"
            "- slot_refinements: array of {slot_id, refined_content, reasoning}\n"
            "- cta_text: CTA button text (empty string if not changing)\n"
            "- confidence: float 0-1\n"
            "- reasoning: string"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        registry = get_registry()
        provider = registry.get_llm(provider_name)
        result = await provider.complete(messages, model_override=model, max_tokens=self.max_tokens)

        decisions = self._parse_content_decisions(result.content)

        logger.info(
            "agents.content.structured_completed",
            refinements=len(decisions.slot_refinements),
            confidence=decisions.confidence,
        )

        return ContentResponse(
            content=[],
            operation=req.operation,
            model=model_id,
            confidence=decisions.confidence,
            skills_loaded=relevant_skills,
            decisions=decisions,
        )

    def _parse_content_decisions(self, raw_content: str) -> ContentDecisions:
        """Parse LLM response into ContentDecisions."""
        import json

        content = raw_content.strip()
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("agents.content.structured_parse_failed")
            return ContentDecisions(confidence=0.0, reasoning="Failed to parse")

        refinements = tuple(
            SlotContentRefinement(
                slot_id=str(r.get("slot_id", "")),
                refined_content=str(r.get("refined_content", "")),
                reasoning=str(r.get("reasoning", "")),
            )
            for r in data.get("slot_refinements", [])
            if isinstance(r, dict)
        )

        return ContentDecisions(
            subject_line=str(data.get("subject_line", "")),
            preheader=str(data.get("preheader", "")),
            slot_refinements=refinements,
            cta_text=str(data.get("cta_text", "")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    async def process(self, request: Any, context_blocks: list[ContentBlock] | None = None) -> Any:
        """Execute pipeline with post-generation length validation.

        Flow: LLM call → extract → spam check → length validate →
        (optional) retry with constraint → return.
        Max 1 retry for length violations.
        """
        _length_warnings_var.set(None)
        response: ContentResponse = await super().process(request, context_blocks)
        req: ContentRequest = request

        # Validate lengths of all alternatives
        cleaned, warnings = validate_alternatives(response.content, req.operation, req.text)
        response.content = cleaned

        if not warnings:
            _length_warnings_var.set([])
            return response

        # Check if retry is warranted (only for "too long" violations)
        constraint = build_retry_constraint(req.operation, warnings)

        if constraint is None:
            # Min violations only — warn but don't retry
            response.length_warnings = warnings
            _length_warnings_var.set(warnings)
            logger.info(
                "agents.content.length_warnings",
                warning_count=len(warnings),
                warnings=warnings[:5],
            )
            return response

        # Retry once with explicit length constraint
        logger.warning(
            "agents.content.length_violation_retrying",
            warnings=warnings[:5],
            constraint=constraint,
        )

        retry_response = await self._retry_with_length_constraint(request, constraint)

        if retry_response is not None:
            return retry_response

        # Retry didn't help — return original with warnings
        response.length_warnings = warnings
        _length_warnings_var.set(warnings)
        return response

    async def _retry_with_length_constraint(
        self,
        request: Any,
        constraint: str,
    ) -> ContentResponse | None:
        """Retry LLM call with explicit length constraint injected.

        Returns improved response if retry passes length check, None otherwise.
        """
        req: ContentRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self._get_model_tier(request))
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills)
        system_prompt += CONFIDENCE_INSTRUCTION

        # Build retry message with constraint injected
        user_message = self._build_user_message(request)
        retry_message = f"{user_message}\n\n{constraint}"

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(retry_message)),
        ]

        try:
            registry = get_registry()
            provider = registry.get_llm(provider_name)
            result = await provider.complete(
                messages, model_override=model, max_tokens=self.max_tokens
            )
        except Exception as e:
            logger.error(
                "agents.content.length_retry_failed",
                error=str(e),
            )
            return None

        raw_content = validate_output(result.content)
        confidence = extract_confidence(raw_content)
        processed = self._post_process(raw_content)

        # Extract and validate retry output
        alternatives = extract_content(processed)
        cleaned, retry_warnings = validate_alternatives(alternatives, req.operation, req.text)
        spam_warnings = check_spam_triggers(cleaned)

        # Accept retry only if no max violations remain
        max_violations = [w for w in retry_warnings if "exceeds max" in w or "max allowed" in w]
        if max_violations:
            logger.warning("agents.content.length_retry_no_improvement")
            return None

        logger.info(
            "agents.content.length_retry_improved",
            remaining_warnings=len(retry_warnings),
        )

        _length_warnings_var.set(retry_warnings)

        return ContentResponse(
            content=cleaned,
            operation=req.operation,
            spam_warnings=spam_warnings,
            length_warnings=retry_warnings,
            model=model_id,
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

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
