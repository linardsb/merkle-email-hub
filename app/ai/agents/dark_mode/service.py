# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401, ARG002
"""Dark Mode agent service — orchestrates LLM → extract → sanitize → QA."""

import contextvars
import json
from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.dark_mode.meta_injector import inject_missing_meta_tags
from app.ai.agents.dark_mode.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.dark_mode.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.dark_mode.schemas import DarkModeRequest, DarkModeResponse
from app.ai.agents.schemas.dark_mode_decisions import DarkColorOverride, DarkModeDecisions
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.schemas import QACheckResult

# Per-request storage for injected tag names (avoids race on singleton instance)
logger = get_logger(__name__)

_injected_tags_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "dm_injected_tags", default=None
)


class DarkModeService(BaseAgentService):
    """Orchestrates the dark mode agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract HTML → XSS sanitize → inject meta tags → optional QA checks.
    """

    agent_name = "dark_mode"
    model_tier = "standard"
    stream_prefix = "darkmode"
    _output_mode_supported: bool = True

    def _post_process(self, raw_content: str) -> str:
        """Post-process LLM output: extract HTML, sanitize, then inject missing meta tags."""
        html = super()._post_process(raw_content)
        result = inject_missing_meta_tags(html)
        _injected_tags_var.set(list(result.injected_tags))
        return result.html

    def build_system_prompt(self, relevant_skills: list[str], output_mode: str = "html") -> str:
        return _build_system_prompt(relevant_skills, output_mode=output_mode)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        req: DarkModeRequest = request
        return _detect_relevant_skills(req.html, req.color_overrides)

    def _build_user_message(self, request: Any) -> str:
        req: DarkModeRequest = request
        parts: list[str] = [
            "Enhance the following email HTML with comprehensive dark mode support:\n",
            req.html,
        ]
        if req.color_overrides:
            overrides = ", ".join(f"{k} → {v}" for k, v in req.color_overrides.items())
            parts.append(f"\n\nUse these specific colour mappings: {overrides}")
        if req.preserve_colors:
            preserved = ", ".join(req.preserve_colors)
            parts.append(f"\n\nDo NOT remap these colours (keep them unchanged): {preserved}")
        return "\n".join(parts)

    async def _run_qa(self, html: str) -> tuple[list[QACheckResult], bool]:
        """Run QA checks with dark mode check first for primary signal."""
        qa_results: list[QACheckResult] = []

        # Dark mode check first (primary signal)
        dm_check = DarkModeCheck()
        dm_result = await dm_check.run(html)
        qa_results.append(dm_result)

        # Remaining checks (skip duplicate dark mode check)
        for check in ALL_CHECKS:
            if isinstance(check, DarkModeCheck):
                continue
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
    ) -> DarkModeResponse:
        return DarkModeResponse(
            html=html,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
            confidence=confidence,
            skills_loaded=skills_loaded,
            meta_tags_injected=_injected_tags_var.get(None) or [],
        )

    async def _process_structured(self, request: Any) -> DarkModeResponse:
        """Structured mode: analyze plan and return dark mode color decisions."""
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model
        from app.ai.sanitize import sanitize_prompt
        from app.core.config import get_settings

        req: DarkModeRequest = request
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model(self.model_tier)
        model_id = f"{provider_name}:{model}"

        relevant_skills = self._detect_skills_from_request(request)
        system_prompt = self.build_system_prompt(relevant_skills, output_mode="structured")

        # Build plan context for LLM
        plan_data = req.build_plan or {}
        user_message = (
            "Analyze the following EmailBuildPlan and return dark mode color decisions as JSON.\n\n"
            f"Plan: {json.dumps(plan_data, default=str)}\n\n"
            "Return a JSON object with these fields:\n"
            "- color_overrides: array of {token_name, light_value, dark_value, reasoning}\n"
            "- background_dark: hex color for dark mode background\n"
            "- text_dark: hex color for dark mode text\n"
            "- enable_prefers_color_scheme: boolean\n"
            "- confidence: float 0-1\n"
            "- reasoning: string explaining strategy"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        registry = get_registry()
        provider = registry.get_llm(provider_name)
        result = await provider.complete(messages, model_override=model, max_tokens=self.max_tokens)

        # Parse structured response
        decisions = self._parse_dark_mode_decisions(result.content)

        logger.info(
            "agents.dark_mode.structured_completed",
            overrides=len(decisions.color_overrides),
            confidence=decisions.confidence,
        )

        return DarkModeResponse(
            html="",  # No HTML in structured mode
            model=model_id,
            confidence=decisions.confidence,
            skills_loaded=relevant_skills,
            meta_tags_injected=[],
            decisions=decisions,
        )

    def _parse_dark_mode_decisions(self, raw_content: str) -> DarkModeDecisions:
        """Parse LLM response into DarkModeDecisions."""
        content = raw_content.strip()
        # Extract JSON from code fence if present
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
            logger.warning("agents.dark_mode.structured_parse_failed")
            return DarkModeDecisions(confidence=0.0, reasoning="Failed to parse LLM response")

        overrides = tuple(
            DarkColorOverride(
                token_name=str(o.get("token_name", "")),
                light_value=str(o.get("light_value", "")),
                dark_value=str(o.get("dark_value", "")),
                reasoning=str(o.get("reasoning", "")),
            )
            for o in data.get("color_overrides", [])
            if isinstance(o, dict)
        )

        return DarkModeDecisions(
            color_overrides=overrides,
            background_dark=str(data.get("background_dark", "#1a1a2e")),
            text_dark=str(data.get("text_dark", "#e0e0e0")),
            enable_prefers_color_scheme=bool(data.get("enable_prefers_color_scheme", True)),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        async for chunk in super().stream_process(request):
            yield chunk


# ── Module-level singleton ──

_dark_mode_service: DarkModeService | None = None


def get_dark_mode_service() -> DarkModeService:
    """Get or create the dark mode service singleton."""
    global _dark_mode_service
    if _dark_mode_service is None:
        _dark_mode_service = DarkModeService()
    return _dark_mode_service
