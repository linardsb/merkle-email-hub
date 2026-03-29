# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Innovation agent."""

from app.ai.agents.evals.judges.base import (
    SYSTEM_PROMPT_TEMPLATE,
    build_criteria_block,
    format_golden_section,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

INNOVATION_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="technique_correctness",
        description=(
            "Is the prototype code technically correct for the requested technique? "
            "CSS checkbox hacks must use the hidden-input + label + sibling-selector "
            "pattern. AMP components must include proper boilerplate. Animations must "
            "use valid @keyframes. Code must be HTML/CSS only (no JavaScript). "
            "Prototype with syntax errors or wrong patterns is a failure."
        ),
    ),
    JudgeCriteria(
        name="fallback_quality",
        description=(
            "Does the response include a production-quality fallback for unsupported "
            "clients? The fallback must be static HTML that displays meaningful content "
            "(not blank or broken). AMP techniques need MIME fallback mention. "
            "Missing fallback or a fallback that renders broken is a failure."
        ),
    ),
    JudgeCriteria(
        name="client_coverage_accuracy",
        description=(
            "Is the stated client coverage percentage realistic? Apple Mail/iOS support "
            "most CSS; Gmail strips most advanced CSS; Outlook uses Word renderer. "
            "Overstating coverage (e.g., claiming 80% for checkbox hacks) is a failure. "
            "Understating by >20 percentage points is also a failure."
        ),
    ),
    JudgeCriteria(
        name="feasibility_assessment",
        description=(
            "Does the feasibility assessment include risk level, file size impact, "
            "and a clear recommendation (ship/test_further/avoid)? The recommendation "
            "must be appropriate — bleeding-edge techniques should not recommend 'ship'. "
            "Well-proven patterns should not recommend 'avoid'. Missing any of "
            "risk/recommendation/coverage is a failure."
        ),
    ),
    JudgeCriteria(
        name="innovation_value",
        description=(
            "Does the response demonstrate genuine knowledge of the technique's "
            "trade-offs and provide actionable guidance? A response that only shows "
            "generic code without email-specific context (client quirks, limitations, "
            "workarounds) is a failure. The response should help a developer make an "
            "informed decision about whether to use this technique."
        ),
    ),
]


class InnovationJudge:
    """Binary judge for Innovation agent outputs."""

    agent_name: str = "innovation"
    criteria: list[JudgeCriteria] = INNOVATION_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with technique request and prototype output."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        technique = ""
        category = "any"
        if judge_input.input_data:
            technique = str(judge_input.input_data.get("technique", ""))
            category = str(judge_input.input_data.get("category", "any"))

        prototype_output = ""
        feasibility_output = ""
        fallback_output = ""
        if judge_input.output_data:
            prototype_output = str(judge_input.output_data.get("prototype", ""))
            feasibility_output = str(judge_input.output_data.get("feasibility", ""))
            fallback_output = str(judge_input.output_data.get("fallback_html", ""))

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        golden = format_golden_section(
            ["technique_correctness", "fallback_quality"],
            name_filter=category if category != "any" else None,
        )
        golden_block = f"\n\n{golden}" if golden else ""

        user_content = (
            f"## TECHNIQUE REQUEST\n{technique}\n\n"
            f"## CATEGORY\n{category}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}"
            f"{golden_block}\n\n"
            f"## AGENT OUTPUT (Prototype)\n{prototype_output}\n\n"
            f"## AGENT OUTPUT (Feasibility)\n{feasibility_output}\n\n"
            f"## AGENT OUTPUT (Fallback)\n{fallback_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
