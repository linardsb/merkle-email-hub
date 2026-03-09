"""Binary pass/fail judge for the Outlook Fixer agent."""

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

OUTLOOK_FIXER_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="mso_conditional_correctness",
        description=(
            "Are MSO conditional comments (<!--[if mso]>, <!--[if !mso]>) present "
            "and correctly structured? Every opening <!--[if must have a matching "
            "<![endif]-->. The non-MSO pattern must use <!--[if !mso]><!--> with "
            "<!--<![endif]--> (note the extra comment markers). VML elements must "
            "be inside MSO conditionals. Conditional blocks must not be nested."
        ),
    ),
    JudgeCriteria(
        name="vml_wellformedness",
        description=(
            "Are VML elements properly structured? Check: xmlns:v namespace exists "
            "on <html> tag when VML is used; all <v:*> elements are properly closed; "
            "<v:roundrect> has required attributes (arcsize, style with width/height, "
            "fillcolor); <v:fill> uses correct type attribute (frame for images); "
            "<v:textbox> uses inset attribute for padding (not CSS padding). "
            "If no VML is needed (no buttons/backgrounds), this criterion passes."
        ),
    ),
    JudgeCriteria(
        name="html_preservation",
        description=(
            "Is the original HTML structure, content, and non-Outlook styles preserved? "
            "Text content, headings, links, images, alt text must be unchanged. "
            "Dark mode CSS (@media prefers-color-scheme, [data-ogsc], [data-ogsb]) "
            "must not be removed. Accessibility attributes (role, aria-*, lang) must "
            "remain intact. Only additions and Outlook-specific modifications are acceptable."
        ),
    ),
    JudgeCriteria(
        name="fix_completeness",
        description=(
            "Are all identified Outlook rendering issues addressed? If the input has "
            "multi-column layout without ghost tables, ghost tables must be added. "
            "If CSS background-image is used, VML fallback must be provided. "
            "If buttons use border-radius, VML roundrect must be added. "
            "Missing fixes count as failures. Partial fixes (e.g., ghost table for "
            "2 of 3 columns) also count as failures."
        ),
    ),
    JudgeCriteria(
        name="outlook_version_targeting",
        description=(
            "Are fixes correctly scoped to affected Outlook versions? MSO conditionals "
            "should target the appropriate version range (e.g., <!--[if gte mso 9]> for "
            "all Outlook, <!--[if mso 16]> for 2016+). Fixes should not break rendering "
            "in non-Outlook clients — non-MSO content must use <!--[if !mso]><!--> pattern "
            "correctly. DPI fix should include <o:PixelsPerInch>96</o:PixelsPerInch> when "
            "images are present."
        ),
    ),
]


class OutlookFixerJudge:
    """Binary judge for Outlook Fixer agent outputs."""

    agent_name: str = "outlook_fixer"
    criteria: list[JudgeCriteria] = OUTLOOK_FIXER_CRITERIA

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

        user_content = (
            f"## AGENT INPUT (Email HTML with Outlook issues)\n```html\n{html_input}\n```\n\n"
            f"## AGENT OUTPUT (Fixed HTML)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
