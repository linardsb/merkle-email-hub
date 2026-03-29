"""Binary pass/fail judge for the Accessibility Auditor agent."""

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

ACCESSIBILITY_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="wcag_aa_compliance",
        description=(
            "Does the output HTML meet WCAG 2.1 AA standards for email? "
            "Check: <html> has lang attribute; all layout tables have role='presentation'; "
            "<title> element present in <head>; role='article' on outer wrapper; "
            "<meta charset='utf-8'> present. Missing any of these is a failure."
        ),
    ),
    JudgeCriteria(
        name="alt_text_quality",
        description=(
            "Do all images have appropriate alt text? Informative images must have "
            "descriptive alt text (max ~125 chars, no 'image of' prefix). Decorative "
            "images must have alt='' (empty string, not missing). Functional images "
            "(inside links) must describe the action/destination. Missing alt attributes "
            "or generic alt text like 'image' or 'photo' is a failure."
        ),
    ),
    JudgeCriteria(
        name="contrast_ratio_accuracy",
        description=(
            "Are color contrast issues identified and fixed? Normal text requires "
            "minimum 4.5:1 contrast ratio against its background. Large text (>=18px or "
            ">=14px bold) requires minimum 3:1. If the input has low-contrast text, the "
            "output must either fix the colors or flag them. Introducing new low-contrast "
            "text is a failure."
        ),
    ),
    JudgeCriteria(
        name="semantic_structure",
        description=(
            "Is the heading hierarchy sequential with no skipped levels? There should "
            "be at most one <h1>, and headings must proceed h1→h2→h3 without gaps. "
            "Link text must be descriptive (never 'click here', 'read more', 'here' "
            "alone). Layout tables must not use <th>, <caption>, or <thead> (those are "
            "for data tables only)."
        ),
    ),
    JudgeCriteria(
        name="screen_reader_compatibility",
        description=(
            "Is the output compatible with major screen readers in email clients? "
            "Layout tables must have role='presentation' (prevents column/row announcement). "
            "VML elements must be inside MSO conditionals (screen readers should skip them). "
            "Reading order must follow DOM order. ARIA attributes must be valid and not "
            "conflict with native semantics. Original content must be preserved — the "
            "agent must not remove or alter text, links, or images."
        ),
    ),
]


class AccessibilityJudge:
    """Binary judge for Accessibility Auditor agent outputs."""

    agent_name: str = "accessibility"
    criteria: list[JudgeCriteria] = ACCESSIBILITY_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML and fixed output HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))

        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        golden = format_golden_section(
            [
                "wcag_aa_compliance",
                "alt_text_quality",
                "semantic_structure",
                "screen_reader_compatibility",
            ]
        )
        golden_block = f"\n\n{golden}" if golden else ""

        user_content = (
            f"## AGENT INPUT (Email HTML with accessibility issues)\n```html\n{html_input}\n```"
            f"{golden_block}\n\n"
            f"## AGENT OUTPUT (Fixed HTML with accessibility improvements)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
