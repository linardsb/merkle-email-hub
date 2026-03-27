"""Progressive disclosure prompt builder for the Knowledge agent."""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_loader import parse_skill_meta, should_load_skill
from app.ai.agents.skill_override import get_override
from app.core.logging import get_logger

logger = get_logger(__name__)

_AGENT_DIR = Path(__file__).parent

# L3 skill files loaded on-demand
SKILL_FILES: dict[str, str] = {
    "rag_strategies": "rag_strategies.md",
    "email_client_engines": "email_client_engines.md",
    "can_i_email_reference": "can_i_email_reference.md",
    "citation_rules": "citation_rules.md",
}


def detect_relevant_skills(question: str) -> list[str]:
    """Detect which L3 skills are relevant to the question."""
    q = question.lower()
    relevant: list[str] = []

    # Always load citation rules (core to Knowledge agent)
    relevant.append("citation_rules")

    # Client/engine questions
    engine_keywords = [
        "outlook",
        "gmail",
        "apple mail",
        "yahoo",
        "samsung",
        "rendering engine",
        "webkit",
        "word",
        "blink",
        "thunderbird",
    ]
    if any(kw in q for kw in engine_keywords):
        relevant.append("email_client_engines")

    # CSS support / Can I Email questions
    css_keywords = [
        "css",
        "support",
        "can i email",
        "property",
        "display",
        "flex",
        "grid",
        "margin",
        "padding",
        "background",
        "border-radius",
        "box-shadow",
        "variable",
        "var(",
    ]
    if any(kw in q for kw in css_keywords):
        relevant.append("can_i_email_reference")

    # RAG strategy questions (meta — how to search better)
    rag_keywords = ["search", "find", "knowledge base", "document"]
    if any(kw in q for kw in rag_keywords):
        relevant.append("rag_strategies")

    return relevant


def build_system_prompt(
    relevant_skills: list[str],
    *,
    remaining_budget: int | None = None,
    client_id: str | None = None,
) -> str:
    """Build system prompt from SKILL.md + relevant L3 files."""
    override = get_override("knowledge")
    if override is not None:
        base_prompt = override
    else:
        skill_path = _AGENT_DIR / "SKILL.md"
        base_prompt = skill_path.read_text()

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("knowledge")
    if failure_warnings:
        base_prompt += f"\n\n{failure_warnings}"

    cumulative_cost = 0
    for skill_name in relevant_skills:
        filename = SKILL_FILES.get(skill_name)
        if not filename:
            continue
        skill_file = _AGENT_DIR / "skills" / filename
        if skill_file.exists():
            raw_content = skill_file.read_text()
            meta, body = parse_skill_meta(raw_content)
            if remaining_budget is not None and not should_load_skill(
                meta, cumulative_cost, remaining_budget, remaining_budget
            ):
                continue
            cumulative_cost += meta.token_cost
            base_prompt += f"\n\n---\n## Reference: {skill_name}\n\n{body}"
            logger.info(
                "agents.knowledge.skill_loaded",
                skill=skill_name,
            )

    # Per-client skill overlays (Phase 32.11)
    if client_id:
        from app.ai.agents.skill_loader import apply_overlays, discover_overlays

        overlays = discover_overlays("knowledge", client_id)
        if overlays:
            budget = remaining_budget or 2000
            parts = [base_prompt]
            parts, cumulative_cost, _overlay_names = apply_overlays(
                parts, set(relevant_skills), overlays, cumulative_cost, budget, budget
            )
            base_prompt = "\n".join(parts)

    return base_prompt
