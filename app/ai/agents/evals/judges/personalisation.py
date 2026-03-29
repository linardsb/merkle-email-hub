"""Binary pass/fail judge for the Personalisation agent."""

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

PERSONALISATION_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="syntax_correctness",
        description=(
            "Is the ESP-specific syntax valid? For Braze: all {{ }} and {% %} tags are "
            "properly opened and closed, filters use | pipe syntax, connected_content uses "
            "correct :save parameter. For SFMC: %%[...]%% blocks are matched, %%=...=%% "
            "inline output is well-formed, functions use correct case (Lookup not lookup). "
            "For Adobe Campaign: <%= %> output tags and <% %> logic blocks are matched, "
            "recipient fields use correct dot notation. No mixed platform syntax."
        ),
    ),
    JudgeCriteria(
        name="fallback_completeness",
        description=(
            "Does every dynamic variable have a fallback/default value? For Braze: "
            "{{ variable | default: 'value' }} pattern. For SFMC: IIF or IF/ELSE around "
            "every variable reference. For Adobe Campaign: ternary or if-block fallback. "
            "Section-level hiding (conditional wrapping of entire content blocks) counts as "
            "valid fallback. Variables without any fallback mechanism fail this criterion."
        ),
    ),
    JudgeCriteria(
        name="html_preservation",
        description=(
            "Is the original HTML structure, content, and styling preserved? All existing "
            "elements (tables, images, links, text), inline styles, CSS, MSO conditionals, "
            "VML, dark mode support, and accessibility attributes must remain intact. Only "
            "personalisation tag insertions are acceptable changes. No removal of existing "
            "content, no structural modifications, no style alterations."
        ),
    ),
    JudgeCriteria(
        name="platform_accuracy",
        description=(
            "Is the output using the correct ESP platform's syntax exclusively? If the "
            "target platform is Braze, there must be zero AMPscript or Adobe JSSP tags. "
            "If SFMC, there must be zero Liquid or JSSP tags. If Adobe Campaign, there "
            "must be zero Liquid or AMPscript tags. Platform-specific best practices must "
            "be followed (e.g., Braze content blocks via content_blocks syntax, "
            "SFMC data extension via Lookup(), Adobe via recipient.field notation)."
        ),
    ),
    JudgeCriteria(
        name="logic_match",
        description=(
            "Does the personalisation logic match the natural language requirements? "
            "If requirements say 'show VIP section only for premium users', the output "
            "must contain a conditional that checks user tier/status and wraps the VIP "
            "section. If requirements say 'loop through products', the output must contain "
            "an iteration construct. The logic structure must faithfully implement the "
            "stated intent -- not just add surface-level variable substitution."
        ),
    ),
]


class PersonalisationJudge:
    """Binary judge for Personalisation agent outputs."""

    agent_name: str = "personalisation"
    criteria: list[JudgeCriteria] = PERSONALISATION_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML, requirements, and output HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        requirements = ""
        platform = ""
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))
            requirements = str(judge_input.input_data.get("requirements", ""))
            platform = str(judge_input.input_data.get("platform", ""))

        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        golden = format_golden_section(
            ["syntax_correctness", "fallback_completeness", "platform_accuracy"],
            name_filter=platform or None,
        )
        golden_block = f"\n\n{golden}" if golden else ""

        user_content = (
            f"## TARGET PLATFORM\n{platform}\n\n"
            f"## PERSONALISATION REQUIREMENTS\n{requirements}\n\n"
            f"## AGENT INPUT (Original HTML)\n```html\n{html_input}\n```"
            f"{golden_block}\n\n"
            f"## AGENT OUTPUT (Personalised HTML)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
