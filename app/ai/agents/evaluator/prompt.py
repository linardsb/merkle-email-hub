"""System prompt and skill detection for the Evaluator agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CRITERIA_DIR = Path(__file__).parent / "criteria"

_SYSTEM_PROMPT_TEMPLATE = """\
You are an adversarial quality evaluator for email HTML. You did NOT generate \
this HTML. Your role is to find defects the generator missed.

You will receive:
1. The original campaign brief
2. The agent's HTML output
3. Quality criteria to evaluate against

## Evaluation Rules

- Be thorough and critical — assume the generator made mistakes
- Check every criterion independently
- Score 0.0-1.0 based on overall quality
- Verdict: "accept" (score >= 0.8, no critical issues), \
"revise" (fixable issues found), "reject" (fundamental failures)

## Response Format

Return ONLY valid JSON matching this schema:
```json
{{
  "verdict": "accept" | "revise" | "reject",
  "score": 0.0-1.0,
  "issues": [
    {{
      "severity": "critical" | "major" | "minor",
      "category": "string",
      "description": "string",
      "location": "string or null"
    }}
  ],
  "feedback": "Overall assessment string",
  "suggested_corrections": ["correction 1", "correction 2"]
}}
```

{criteria_section}
"""

# Agent name → criteria YAML file mapping
_AGENT_CRITERIA_MAP: dict[str, str] = {
    "scaffolder": "scaffolder.yaml",
    "dark_mode": "dark_mode.yaml",
    "accessibility": "accessibility.yaml",
}


def _load_criteria(agent_name: str) -> list[dict[str, Any]]:
    """Load evaluation criteria for a given agent from YAML.

    Falls back to generic.yaml for unknown agents.
    """
    settings = get_settings()
    criteria_dir = Path(settings.ai.evaluator.criteria_dir)

    filename = _AGENT_CRITERIA_MAP.get(agent_name, "generic.yaml")
    criteria_path = criteria_dir / filename

    if not criteria_path.exists():
        # Try module-relative fallback
        criteria_path = _CRITERIA_DIR / filename
    if not criteria_path.exists():
        criteria_path = _CRITERIA_DIR / "generic.yaml"
    if not criteria_path.exists():
        logger.warning("evaluator.criteria_not_found", agent=agent_name, path=str(criteria_path))
        return []

    try:
        data = yaml.safe_load(criteria_path.read_text(encoding="utf-8"))
        return list(data.get("criteria", []))
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("evaluator.criteria_load_failed", agent=agent_name, error=str(exc))
        return []


def _format_criteria_section(criteria: list[dict[str, Any]]) -> str:
    """Format criteria list into a prompt section."""
    if not criteria:
        return ""
    lines = ["## Quality Criteria\n"]
    for c in criteria:
        weight = c.get("weight", 1.0)
        lines.append(f"- **{c['name']}** (weight={weight}): {c['description']}")
    return "\n".join(lines)


def build_system_prompt(agent_name: str) -> str:
    """Build the evaluator system prompt with agent-specific criteria."""
    criteria = _load_criteria(agent_name)
    criteria_section = _format_criteria_section(criteria)
    return _SYSTEM_PROMPT_TEMPLATE.format(criteria_section=criteria_section)


def detect_relevant_skills(agent_name: str) -> list[str]:
    """Return criteria file names loaded for the given agent."""
    filename = _AGENT_CRITERIA_MAP.get(agent_name, "generic.yaml")
    return [filename.removesuffix(".yaml")]
