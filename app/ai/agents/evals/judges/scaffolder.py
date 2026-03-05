"""Binary pass/fail judge for the Scaffolder agent."""

from app.ai.agents.evals.judges.base import (
    SYSTEM_PROMPT_TEMPLATE,
    build_criteria_block,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

SCAFFOLDER_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="brief_fidelity",
        description=(
            "Does the generated HTML faithfully implement all key elements from the brief? "
            "Check that layout type, sections, content areas, and specific requirements "
            "mentioned in the brief are present in the output. Minor creative additions "
            "are acceptable; missing requested sections are not."
        ),
    ),
    JudgeCriteria(
        name="email_layout_patterns",
        description=(
            "Does the HTML use email-appropriate layout patterns exclusively? "
            "Must use nested <table> with role='presentation' for layout — no flexbox, "
            "no CSS grid, no float-based layouts. Tables must have cellpadding='0' "
            "and cellspacing='0'. Content width must not exceed 600px."
        ),
    ),
    JudgeCriteria(
        name="mso_conditional_correctness",
        description=(
            "Are MSO conditional comments (<!--[if mso]>, <!--[if !mso]>) present "
            "and correctly structured? Must include xmlns:v and xmlns:o namespace "
            "declarations. VML elements (if used for buttons/backgrounds) must be "
            "inside MSO conditionals. Conditional blocks must be properly closed."
        ),
    ),
    JudgeCriteria(
        name="dark_mode_readiness",
        description=(
            "Does the output include dark mode meta tags (color-scheme, "
            "supported-color-schemes), @media (prefers-color-scheme: dark) rules, "
            "and [data-ogsc]/[data-ogsb] Outlook dark mode selectors? "
            "Colors must maintain 4.5:1 contrast ratio in both modes."
        ),
    ),
    JudgeCriteria(
        name="accessibility_baseline",
        description=(
            "Does the HTML include lang attribute on <html>, role='article' on "
            "wrapper, role='presentation' on layout tables, semantic heading "
            "hierarchy, and meaningful alt text on all <img> tags? "
            "Images must have explicit width/height and style='display:block;border:0'."
        ),
    ),
]


class ScaffolderJudge:
    """Binary judge for Scaffolder agent outputs."""

    agent_name: str = "scaffolder"
    criteria: list[JudgeCriteria] = SCAFFOLDER_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with brief and generated HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        brief = str(judge_input.input_data.get("brief", ""))
        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        user_content = (
            f"## AGENT INPUT (Brief)\n{brief}\n\n"
            f"## AGENT OUTPUT (HTML)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
