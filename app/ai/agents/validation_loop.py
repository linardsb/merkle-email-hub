"""CRAG (Corrective RAG) validation loop for agent HTML output."""

from __future__ import annotations

from typing import Any

from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.query import unsupported_css_in_html
from app.knowledge.ontology.registry import load_ontology

logger = get_logger(__name__)

CRAG_SYSTEM_PROMPT = "You are an email HTML developer. Fix CSS compatibility issues."


class CRAGMixin:
    """Mixin providing CRAG validation for agent services.

    Stateless — no __init__. Call _crag_validate_and_correct() on
    post-processed HTML to detect unsupported CSS and re-generate
    with ontology fallbacks.
    """

    async def _crag_validate_and_correct(
        self,
        html: str,
        system_prompt: str,
        model: str,
    ) -> tuple[str, list[str]]:
        """Validate HTML against compatibility matrix; correct if needed.

        Returns:
            Tuple of (corrected_html, list_of_corrections_applied).
            If no issues found, returns (html, []) with zero LLM cost.
        """
        settings = get_settings()
        min_severity = settings.knowledge.crag_min_severity

        # Step 1: Detect unsupported CSS
        issues = unsupported_css_in_html(html)

        # Step 2: Filter by severity threshold
        severity_order = {"error": 0, "warning": 1, "info": 2}
        threshold = severity_order.get(min_severity, 0)
        qualifying = [
            issue for issue in issues if severity_order.get(str(issue["severity"]), 2) <= threshold
        ]

        if not qualifying:
            return html, []

        logger.info(
            "agents.crag.issues_detected",
            total_issues=len(issues),
            qualifying_issues=len(qualifying),
            min_severity=min_severity,
        )

        # Step 3: Retrieve fallbacks from ontology
        onto = load_ontology()
        correction_instructions: list[str] = []

        for issue in qualifying:
            prop_id = str(issue["property_id"])
            prop_name = str(issue["property_name"])
            value = issue.get("value", "")
            raw_clients = issue.get("unsupported_clients", [])
            clients_list: list[Any] = raw_clients if isinstance(raw_clients, list) else []  # pyright: ignore[reportUnknownVariableType]
            clients_str = ", ".join(str(c) for c in clients_list)
            fallbacks = onto.fallbacks_for(prop_id)

            if fallbacks:
                fb = fallbacks[0]  # Use first (best) fallback
                instruction = (
                    f"- `{prop_name}"
                    + (f": {value}" if value else "")
                    + f"` is unsupported in: {clients_str}.\n"
                    f"  Technique: {fb.technique}\n"
                    f"  Replacement code:\n```\n{fb.code_example}\n```"
                )
            else:
                instruction = (
                    f"- `{prop_name}"
                    + (f": {value}" if value else "")
                    + f"` is unsupported in: {clients_str}.\n"
                    f"  Remove or replace with a universally supported alternative."
                )
            correction_instructions.append(instruction)

        # Step 4: Build correction prompt (cap HTML at 100K chars to avoid token exhaustion)
        capped_html = html[:100_000] if len(html) > 100_000 else html
        correction_prompt = (
            "The following CSS compatibility issues were detected in this HTML email. "
            "Replace each unsupported property with the provided fallback technique. "
            "Preserve all other HTML exactly as-is. Return ONLY the corrected HTML.\n\n"
            + "\n\n".join(correction_instructions)
            + "\n\nOriginal HTML:\n```html\n"
            + capped_html
            + "\n```"
        )

        # Step 5: Call LLM
        from app.ai.protocols import Message
        from app.ai.registry import get_registry

        provider_name = settings.ai.provider
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        messages = [
            Message(role="system", content=sanitize_prompt(system_prompt)),
            Message(role="user", content=sanitize_prompt(correction_prompt)),
        ]

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=16_384)
        except Exception:
            logger.warning("agents.crag.llm_call_failed", exc_info=True)
            return html, []  # Failure-safe: return original

        # Step 6: Validate and sanitize output
        raw = validate_output(result.content)
        corrected = extract_html(raw)
        corrected = sanitize_html_xss(corrected)

        if not corrected or len(corrected) < 50:
            logger.warning("agents.crag.output_too_short", length=len(corrected))
            return html, []  # Failure-safe: return original

        corrections = [str(issue["property_id"]) for issue in qualifying]
        logger.info(
            "agents.crag.correction_applied",
            corrections=corrections,
            original_length=len(html),
            corrected_length=len(corrected),
        )

        return corrected, corrections
