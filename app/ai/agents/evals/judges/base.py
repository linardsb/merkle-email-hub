"""Base judge protocol and shared prompt template."""

from __future__ import annotations

import json
from typing import Protocol

from app.ai.agents.evals.judges.schemas import (
    CriterionResult,
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

_GOLDEN_TOKEN_BUDGET = 2000  # ~8000 chars at ~4 chars/token


class Judge(Protocol):
    """Protocol for all agent judges."""

    agent_name: str
    criteria: list[JudgeCriteria]

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build the full prompt for the LLM judge call."""
        ...

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM response into structured verdict."""
        ...


SYSTEM_PROMPT_TEMPLATE = """\
You are a strict quality evaluator for email development AI agents.

You will receive an agent's input and output. Evaluate the output against each criterion below.

For EACH criterion, respond with:
- "passed": true or false
- "reasoning": 1-2 sentences explaining your judgment

Then give an overall "overall_pass" which is true ONLY if ALL criteria pass.

Respond with ONLY valid JSON in this exact format:
{{
  "overall_pass": true/false,
  "criteria_results": [
    {{
      "criterion": "<name>",
      "passed": true/false,
      "reasoning": "<explanation>"
    }}
  ]
}}

CRITERIA:
{criteria_block}

IMPORTANT:
- Be strict. If in doubt, fail.
- Judge the OUTPUT only. Do not judge the input quality.
- Output ONLY the JSON object. No markdown, no explanation outside JSON.
"""


def build_criteria_block(criteria: list[JudgeCriteria]) -> str:
    """Format criteria list into numbered prompt block."""
    lines: list[str] = []
    for i, c in enumerate(criteria, 1):
        lines.append(f"{i}. **{c.name}**: {c.description}")
    return "\n".join(lines)


def format_golden_section(
    criteria_names: list[str],
    *,
    framing: str = "standard",
    name_filter: str | None = None,
) -> str:
    """Build golden reference prompt section for given criteria.

    Args:
        criteria_names: Criterion names to fetch references for.
        framing: "standard" | "inverted". Inverted adds "do NOT flag" clause.
        name_filter: If set, only include refs whose name contains this substring
                     (case-insensitive). Used for platform/category filtering.

    Returns:
        Formatted section string, or empty string if no references found.
    """
    from app.ai.agents.evals.golden_references import get_references_for_criterion

    snippets: list[tuple[str, str]] = []
    for name in criteria_names:
        snippets.extend(get_references_for_criterion(name))

    if not snippets:
        return ""

    # Deduplicate by name (same ref may appear for multiple criteria)
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for ref_name, html in snippets:
        if ref_name not in seen:
            seen.add(ref_name)
            unique.append((ref_name, html))

    # Apply name filter (platform/category conditional)
    if name_filter:
        filter_lower = name_filter.lower()
        unique = [(n, h) for n, h in unique if filter_lower in n.lower()]

    if not unique:
        return ""

    # Enforce token budget (~4 chars per token)
    char_budget = _GOLDEN_TOKEN_BUDGET * 4
    parts: list[str] = []
    used = 0
    for i, (ref_name, html) in enumerate(unique, 1):
        entry = f"### Example {i}: {ref_name}\n```html\n{html}\n```"
        if used + len(entry) > char_budget:
            break
        parts.append(entry)
        used += len(entry)

    if not parts:
        return ""

    if framing == "inverted":
        header = (
            "## GOLDEN REFERENCE EXAMPLES\n"
            "The following are verified-correct email HTML patterns. "
            "These patterns are CORRECT — do NOT flag them as issues.\n"
        )
    else:
        header = (
            "## GOLDEN REFERENCE EXAMPLES\n"
            "The following are verified-correct email HTML patterns. "
            'Use them as your standard for what "correct" looks like '
            "when evaluating the criteria above.\n"
        )

    return header + "\n" + "\n\n".join(parts)


def parse_judge_response(raw: str, judge_input: JudgeInput, agent_name: str) -> JudgeVerdict:
    """Parse LLM JSON response into JudgeVerdict.

    Handles markdown code fences and returns error verdict on parse failure.
    """
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        data = json.loads(cleaned)

        criteria_results = [
            CriterionResult(
                criterion=cr["criterion"],
                passed=cr["passed"],
                reasoning=cr["reasoning"],
            )
            for cr in data["criteria_results"]
        ]

        return JudgeVerdict(
            trace_id=judge_input.trace_id,
            agent=agent_name,
            overall_pass=data["overall_pass"],
            criteria_results=criteria_results,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return JudgeVerdict(
            trace_id=judge_input.trace_id,
            agent=agent_name,
            overall_pass=False,
            criteria_results=[],
            error=f"Failed to parse judge response: {e}",
        )
