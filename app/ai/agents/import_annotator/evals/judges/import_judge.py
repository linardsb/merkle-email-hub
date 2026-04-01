"""Import annotator evaluation judge — 5 criteria."""

from app.ai.agents.evals.judges.base import (
    build_system_prompt,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

IMPORT_ANNOTATOR_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="section_boundary_accuracy",
        description=(
            "PASS if the AI correctly identified the major visual section boundaries "
            "(header, hero, content blocks, CTA, footer). Each boundary should align with "
            "a visually distinct horizontal band. Minor boundary disagreements (e.g., "
            "spacer included in adjacent section) are acceptable. "
            "FAIL if major sections are missed or split incorrectly."
        ),
    ),
    JudgeCriteria(
        name="annotation_completeness",
        description=(
            "PASS if every visually distinct section in the email has a data-section-id attribute. "
            "FAIL if any visible content section lacks annotation."
        ),
    ),
    JudgeCriteria(
        name="html_preservation",
        description=(
            "PASS if the annotated HTML is identical to the input HTML except for the addition "
            "of data-section-id, data-component-name, and data-section-layout attributes. "
            "No content, attributes, classes, IDs, inline styles, or comments were modified. "
            "FAIL if any non-annotation change was made."
        ),
    ),
    JudgeCriteria(
        name="esp_token_integrity",
        description=(
            "PASS if all ESP tokens ({{ }}, {% %}, {{{ }}}, %%[...]%%, %%...%%, <% %>) "
            "in the input HTML are present and identical in the output HTML. "
            "FAIL if any token was modified, removed, or corrupted."
        ),
    ),
    JudgeCriteria(
        name="column_detection",
        description=(
            "PASS if multi-column layouts are annotated as a single section with "
            "data-section-layout='columns' on the parent element, NOT individual columns. "
            "Also PASS if no column layouts exist in the input. "
            "FAIL if individual columns are annotated as separate sections."
        ),
    ),
]


class ImportAnnotatorJudge:
    agent_name: str = "import_annotator"
    criteria: list[JudgeCriteria] = IMPORT_ANNOTATOR_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        system = build_system_prompt(self.criteria, self.agent_name)
        input_html = str(judge_input.input_data.get("html", ""))
        output_html = str((judge_input.output_data or {}).get("annotated_html", ""))
        user_content = (
            f"## AGENT INPUT (Original HTML)\n```html\n{input_html}\n```\n\n"
            f"## AGENT OUTPUT (Annotated HTML)\n```html\n{output_html}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        return parse_judge_response(raw, judge_input, self.agent_name)
