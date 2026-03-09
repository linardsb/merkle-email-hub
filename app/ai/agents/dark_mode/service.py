# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
# ruff: noqa: ANN401, ARG002
"""Dark Mode agent service — orchestrates LLM → extract → sanitize → QA."""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.agents.base import BaseAgentService
from app.ai.agents.dark_mode.prompt import (
    build_system_prompt as _build_system_prompt,
)
from app.ai.agents.dark_mode.prompt import (
    detect_relevant_skills as _detect_relevant_skills,
)
from app.ai.agents.dark_mode.schemas import DarkModeRequest, DarkModeResponse
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.checks.dark_mode import DarkModeCheck
from app.qa_engine.schemas import QACheckResult


class DarkModeService(BaseAgentService):
    """Orchestrates the dark mode agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    agent_name = "dark_mode"
    model_tier = "standard"
    stream_prefix = "darkmode"

    def build_system_prompt(self, relevant_skills: list[str]) -> str:
        return _build_system_prompt(relevant_skills)

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
