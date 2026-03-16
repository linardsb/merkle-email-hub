# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401
"""Base agent service — shared pipeline for HTML transformer agents.

Eliminates ~80% code duplication across scaffolder, dark_mode, outlook_fixer,
accessibility, and personalisation agents.  Each subclass overrides only
what's unique: model tier, user message construction, skill detection,
and post-processing.

Uses ``Any`` for request/response types because each agent has its own
Pydantic schema.  Concrete subclasses narrow the types in their overrides.
"""

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.ai.blueprints.protocols import AgentHandoff, HandoffStatus
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import TaskTier, resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

# Confidence scoring instruction appended to system prompts
CONFIDENCE_INSTRUCTION = (
    "\n\nEnd your response with <!-- CONFIDENCE: X.XX --> where X.XX is your "
    "confidence (0.00-1.00) in the output quality."
)


class BaseAgentService:
    """Shared agent pipeline: prompt → LLM → post-process → QA.

    Subclasses MUST set ``agent_name`` and implement ``_build_user_message``
    and ``detect_relevant_skills``.  Optionally override ``_post_process``,
    ``_run_qa``, ``_build_response``, and class-level config attributes.
    """

    # ── Class-level config (override in subclass) ──
    agent_name: str = ""
    model_tier: TaskTier = "standard"
    max_tokens: int = 8192
    run_qa_default: bool = True
    stream_prefix: str = "agent"
    output_mode_default: str = "html"
    _output_mode_supported: bool = False

    # ── Output mode ──

    def _get_output_mode(self, request: Any) -> str:
        """Extract output_mode from request, with fallback to class default."""
        return str(getattr(request, "output_mode", self.output_mode_default))

    # ── Subclass hooks ──

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        """Build the system prompt from skill files.

        Every agent has its own ``prompt.py`` with ``build_system_prompt()``.
        Override this method to call the agent-specific version.
        """
        raise NotImplementedError

    def detect_relevant_skills(self, request: Any) -> list[str]:  # noqa: ARG002
        """Detect which L3 skill files to load for this request.

        Override with agent-specific keyword detection.
        """
        return []

    def _build_user_message(self, request: Any) -> str:
        """Build the user message from the request.

        MUST be overridden by every subclass.
        """
        raise NotImplementedError

    # ── Pipeline hooks (override when behaviour differs) ──

    def _post_process(self, raw_content: str) -> str:
        """Post-process raw LLM output into clean HTML.

        Default: extract_html + sanitize_html_xss.
        Override for non-HTML agents (e.g., content → extract_content).
        """
        html = extract_html(raw_content)
        return sanitize_html_xss(html)

    async def _run_qa(self, html: str) -> tuple[list[QACheckResult], bool]:
        """Run QA checks on the output.

        Override for agents that need custom QA ordering (e.g., dark_mode)
        or QA on input rather than output (e.g., code_reviewer).
        """
        qa_results: list[QACheckResult] = []
        for check in ALL_CHECKS:
            check_result = await check.run(html)
            qa_results.append(check_result)
        qa_passed = all(r.passed for r in qa_results)
        return qa_results, qa_passed

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
    ) -> Any:
        """Construct the final response object.

        MUST be overridden — each agent has its own response schema.
        The ``request`` is passed through so agents can include request
        fields in the response (e.g., personalisation.platform).
        """
        raise NotImplementedError

    def _get_model_tier(self, request: Any) -> TaskTier:  # noqa: ARG002
        """Return the model tier for this request.

        Override to vary tier per-request (e.g., content agent uses
        different tiers per operation) without mutating instance state.
        """
        return self.model_tier

    def _should_run_qa(self, request: Any) -> bool:
        """Whether to run QA checks for this request.

        Override to suppress QA in the base pipeline (e.g., code_reviewer
        runs QA on input HTML, not output).
        """
        return bool(getattr(request, "run_qa", self.run_qa_default))

    # ── Shared pipeline ──

    async def _process_structured(self, request: Any) -> Any:
        """New pipeline: LLM -> structured JSON -> deterministic assembly.

        Override in subclass when implementing structured mode.
        """
        raise NotImplementedError(f"{self.agent_name} does not support structured output mode")

    async def process(self, request: Any) -> Any:
        """Execute the full agent pipeline (non-streaming).

        Routes to structured pipeline when output_mode="structured" and supported.

        Steps:
        1. Resolve model from tier
        2. Detect skills + build system prompt
        3. Build user message + sanitize
        4. Call LLM
        5. Post-process output
        6. Extract confidence
        7. Run QA checks (if enabled)
        8. Build and return response
        """
        output_mode = self._get_output_mode(request)
        if output_mode == "structured" and self._output_mode_supported:
            return await self._process_structured(request)

        settings = get_settings()
        provider_name = settings.ai.provider
        base_tier = self._get_model_tier(request)
        effective_tier = getattr(request, "effective_tier", None) or base_tier
        model = resolve_model(effective_tier)
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure — load only relevant skill files
        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode=output_mode)
        system_prompt += CONFIDENCE_INSTRUCTION

        # Build messages
        user_message = self._build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            f"agents.{self.agent_name}.process_started",
            provider=provider_name,
            model=model,
            skills_loaded=relevant_skills,
        )

        # Call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(
                messages, model_override=model, max_tokens=self.max_tokens
            )
        except Exception as e:
            logger.error(
                f"agents.{self.agent_name}.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"{self.agent_name} processing failed") from e

        # Post-process output
        raw_content = validate_output(result.content)
        confidence = extract_confidence(raw_content)
        html = self._post_process(raw_content)

        logger.info(
            f"agents.{self.agent_name}.process_completed",
            model=model_id,
            html_length=len(html),
            confidence=confidence,
            usage=result.usage,
        )

        # CRAG validation loop (if mixin present and enabled)
        from app.ai.agents.validation_loop import CRAGMixin

        if isinstance(self, CRAGMixin) and settings.knowledge.crag_enabled:
            html, crag_corrections = await self._crag_validate_and_correct(
                html, system_prompt, model
            )
            if crag_corrections:
                logger.info(
                    f"agents.{self.agent_name}.crag_applied",
                    corrections=crag_corrections,
                )

        # Optional QA checks
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None
        should_run_qa = self._should_run_qa(request)

        if should_run_qa:
            qa_results_list, qa_passed = await self._run_qa(html)
            qa_results = qa_results_list

            logger.info(
                f"agents.{self.agent_name}.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return self._build_response(
            request=request,
            html=html,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model_id=model_id,
            confidence=confidence,
            skills_loaded=relevant_skills,
            raw_content=raw_content,
        )

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        """Stream agent output as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete output).
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self._get_model_tier(request))
        model_id = f"{provider_name}:{model}"
        response_id = f"{self.stream_prefix}-{uuid.uuid4().hex[:12]}"

        relevant_skills = self._detect_skills_from_request(request)
        output_mode = self._get_output_mode(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode=output_mode)
        system_prompt += CONFIDENCE_INSTRUCTION

        user_message = self._build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            f"agents.{self.agent_name}.stream_started",
            provider=provider_name,
            model=model,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            async for chunk in provider.stream(
                messages, model_override=model, max_tokens=self.max_tokens
            ):  # type: ignore[attr-defined]
                sse_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

        except Exception as e:
            logger.error(
                f"agents.{self.agent_name}.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"{self.agent_name} streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            f"agents.{self.agent_name}.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )

    # ── Handoff helpers ──

    def to_handoff(
        self,
        *,
        html: str,
        confidence: float | None = None,
        qa_passed: bool | None = None,
        decisions: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        component_refs: tuple[str, ...] = (),
    ) -> AgentHandoff:
        """Build a standardised AgentHandoff from agent output.

        Blueprint nodes can call this instead of manually constructing
        AgentHandoff, ensuring consistent field population across all agents.
        """
        if qa_passed is False:
            status = HandoffStatus.WARNING
        else:
            status = HandoffStatus.OK

        return AgentHandoff(
            status=status,
            agent_name=self.agent_name,
            artifact=html,
            decisions=decisions,
            warnings=warnings,
            component_refs=component_refs,
            confidence=confidence,
        )

    # ── Internal helpers ──

    def _detect_skills_from_request(self, request: Any) -> list[str]:
        """Adapter that calls detect_relevant_skills with the right args.

        Override if your skill detection signature differs from the default.
        """
        return self.detect_relevant_skills(request)
