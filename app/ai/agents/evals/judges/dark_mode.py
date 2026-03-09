"""Binary pass/fail judge for the Dark Mode agent."""

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

DARK_MODE_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="color_coherence",
        description=(
            "Are the dark mode colors visually coherent — not just technically present? "
            "Background colors should be dark (not just inverted), text should be light "
            "and readable. Brand colors should be adjusted to darker variants, not left "
            "as-is on dark backgrounds. No white-on-light or dark-on-dark combinations."
        ),
    ),
    JudgeCriteria(
        name="html_preservation",
        description=(
            "Is the original HTML structure fully preserved? No elements removed, "
            "no attributes deleted, no inline styles stripped. Layout tables must be "
            "identical. Element ordering unchanged. MSO conditionals untouched. "
            "VML namespaces and Outlook markup preserved exactly. "
            "Compare: only CSS additions and class attribute extensions are allowed."
        ),
    ),
    JudgeCriteria(
        name="outlook_selector_completeness",
        description=(
            "Are [data-ogsc] (text color) and [data-ogsb] (background color) selectors "
            "present for all elements that have dark mode color overrides? "
            "Outlook dark mode requires these attribute selectors because it ignores "
            "@media queries. Every dark mode color change must have a corresponding "
            "Outlook selector."
        ),
    ),
    JudgeCriteria(
        name="meta_and_media_query",
        description=(
            "Does the output include <meta name='color-scheme' content='light dark'> "
            "and <meta name='supported-color-schemes' content='light dark'>? "
            "Is there a @media (prefers-color-scheme: dark) block with !important "
            "overrides? Dark mode utility classes (.dark-bg, .dark-text) should be defined."
        ),
    ),
    JudgeCriteria(
        name="contrast_preservation",
        description=(
            "Do all text-background combinations in dark mode maintain at least "
            "4.5:1 contrast ratio (WCAG AA)? Links must remain distinguishable. "
            "If color_overrides or preserve_colors were specified in the input, "
            "those constraints must be respected in the output."
        ),
    ),
]


class DarkModeJudge:
    """Binary judge for Dark Mode agent outputs."""

    agent_name: str = "dark_mode"
    criteria: list[JudgeCriteria] = DARK_MODE_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with original and dark-mode HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = str(judge_input.input_data.get("html_input", ""))
        color_overrides = judge_input.input_data.get("color_overrides")
        preserve_colors = judge_input.input_data.get("preserve_colors")

        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        constraints = ""
        if color_overrides:
            constraints += f"\nColor overrides requested: {color_overrides}"
        if preserve_colors:
            constraints += f"\nColors to preserve: {preserve_colors}"

        # If input HTML is missing (old traces), warn the judge to skip html_preservation
        input_section = f"## ORIGINAL HTML (Input)\n```html\n{html_input}\n```"
        if not html_input.strip():
            input_section = (
                "## ORIGINAL HTML (Input)\n"
                "**Not available in trace data.** "
                "For html_preservation, mark as PASS (cannot evaluate without input)."
            )

        user_content = (
            f"{input_section}\n"
            f"{constraints}\n\n"
            f"## DARK MODE HTML (Output)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
