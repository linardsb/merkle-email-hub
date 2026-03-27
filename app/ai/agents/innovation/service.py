"""Innovation agent service — prototype experimental email techniques."""

from __future__ import annotations

import re

from app.ai.agents.innovation.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.innovation.schemas import InnovationRequest, InnovationResponse
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


class InnovationService:
    """Orchestrates technique prototyping with feasibility assessment."""

    async def process(
        self,
        request: InnovationRequest,
        competitive_context: str = "",
    ) -> InnovationResponse:
        """Process an innovation technique request.

        Args:
            request: The technique description and optional filters.

        Returns:
            Prototype with feasibility assessment and fallback.
        """
        logger.info(
            "agents.innovation.process_started",
            technique_length=len(request.technique),
            category=request.category,
        )

        # 1. Detect skills and build prompt
        relevant_skills = detect_relevant_skills(request.technique)
        client_id: str | None = getattr(request, "client_id", None)
        system_prompt = build_system_prompt(relevant_skills, client_id=client_id)

        # 2. Build user message
        user_message = _build_user_message(request, competitive_context)

        # 3. Call LLM (use complex model for creative/experimental work)
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("complex")

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(
                messages, model_override=model, max_tokens=8192
            )
        except Exception as exc:
            logger.error("agents.innovation.llm_failed", error=str(exc))
            raise ServiceUnavailableError("Innovation service temporarily unavailable") from exc

        # 4. Validate and extract confidence
        raw_output = validate_output(response.content)
        confidence = extract_confidence(raw_output)
        clean_output = strip_confidence_comment(raw_output)

        # 5. Parse structured sections from output
        prototype, feasibility, coverage, risk, recommendation, fallback = _parse_innovation_output(
            clean_output
        )

        logger.info(
            "agents.innovation.process_completed",
            confidence=confidence,
            risk_level=risk,
            client_coverage=coverage,
            model=response.model,
        )

        return InnovationResponse(
            prototype=prototype,
            feasibility=feasibility,
            client_coverage=coverage,
            risk_level=risk,
            recommendation=recommendation,
            fallback_html=fallback,
            confidence=confidence or 0.5,
            skills_loaded=relevant_skills,
            model=response.model,
        )


def _build_user_message(request: InnovationRequest, competitive_context: str = "") -> str:
    """Build the user message with technique request and constraints."""
    parts = [f"## TECHNIQUE REQUEST\n{request.technique}"]

    if request.category:
        parts.append(f"\n## CATEGORY\n{request.category}")

    if request.target_clients:
        clients = ", ".join(request.target_clients)
        parts.append(f"\n## TARGET CLIENTS\n{clients}")

    if competitive_context:
        parts.append(f"\n{competitive_context}")

    parts.append(
        "\n## INSTRUCTIONS\n"
        "Provide your response with these clearly labelled sections:\n"
        "### 1. Prototype\nComplete working HTML/CSS code.\n"
        "### 2. Feasibility Assessment\nClient coverage %, risk level, "
        "file size impact, complexity, recommendation.\n"
        "### 3. Fallback Strategy\nStatic fallback HTML for unsupported clients.\n"
        "### 4. Known Limitations\nClient-specific issues and caveats.\n\n"
        "End with a confidence comment: <!-- CONFIDENCE: 0.XX -->"
    )

    return "\n".join(parts)


def _parse_innovation_output(
    output: str,
) -> tuple[str, str, float, str, str, str]:
    """Parse structured sections from Innovation agent output.

    Returns:
        Tuple of (prototype, feasibility, coverage, risk, recommendation, fallback).
    """
    prototype = ""
    feasibility = ""
    coverage = 0.5
    risk = "medium"
    recommendation = "test_further"
    fallback = ""

    sections = output.split("### ")
    for section in sections:
        lower = section.lower()
        if lower.startswith("1.") or lower.startswith("prototype"):
            prototype = section.split("\n", 1)[-1].strip() if "\n" in section else ""
        elif lower.startswith("2.") or lower.startswith("feasibility"):
            feasibility = section.split("\n", 1)[-1].strip() if "\n" in section else ""
            # Extract coverage percentage
            coverage = _extract_percentage(feasibility)
            # Extract risk level
            risk = _extract_risk(feasibility)
            # Extract recommendation
            recommendation = _extract_recommendation(feasibility)
        elif lower.startswith("3.") or lower.startswith("fallback"):
            fallback = section.split("\n", 1)[-1].strip() if "\n" in section else ""

    return prototype, feasibility, coverage, risk, recommendation, fallback


def _extract_percentage(text: str) -> float:
    """Extract a percentage from text, return as 0.0-1.0."""
    match = re.search(r"(\d{1,3})%", text)
    if match:
        return min(int(match.group(1)) / 100.0, 1.0)
    return 0.5


def _extract_risk(text: str) -> str:
    """Extract risk level from feasibility text."""
    lower = text.lower()
    if "high risk" in lower or "risk: high" in lower or "risk level: high" in lower:
        return "high"
    if "low risk" in lower or "risk: low" in lower or "risk level: low" in lower:
        return "low"
    return "medium"


def _extract_recommendation(text: str) -> str:
    """Extract recommendation from feasibility text."""
    lower = text.lower()
    if "avoid" in lower:
        return "avoid"
    if "ship" in lower and "test" not in lower:
        return "ship"
    return "test_further"


def get_innovation_service() -> InnovationService:
    """Get singleton Innovation agent service."""
    return InnovationService()
