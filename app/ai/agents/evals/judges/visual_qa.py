# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Visual QA agent."""

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

VISUAL_QA_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="defect_detection_accuracy",
        description=(
            "Are real rendering defects correctly identified? Each reported defect must "
            "correspond to a genuine visual issue visible in the screenshots. Hallucinated "
            "defects (reporting issues that don't exist) are failures. Missing obvious "
            "defects (layout collapse, missing elements, broken images) are also failures. "
            "The agent should detect all defects listed in expected_challenges."
        ),
    ),
    JudgeCriteria(
        name="fix_correctness",
        description=(
            "Are the suggested fixes technically correct for email HTML? Fixes must be "
            "implementable in email context — e.g., suggesting flexbox replacement with "
            "table layout for Outlook, inline styles for Gmail style stripping, VML roundrect "
            "for border-radius in Outlook. Suggesting modern CSS features that don't work "
            "in email clients is a failure. Fixes should reference specific CSS properties "
            "or HTML patterns."
        ),
    ),
    JudgeCriteria(
        name="false_positive_rate",
        description=(
            "Does the agent avoid flagging acceptable cross-client variations as defects? "
            "Minor font rendering differences, slight spacing variations, and expected "
            "platform-specific styling (e.g., iOS blue link color) should NOT be flagged "
            "as defects. Anti-aliasing differences and sub-pixel rendering are acceptable. "
            "For 'perfect rendering' test cases, zero defects should be reported."
        ),
    ),
    JudgeCriteria(
        name="client_coverage",
        description=(
            "Are all screenshotted clients analyzed? The agent must not skip any client "
            "that was provided in the screenshots. Each defect must correctly attribute "
            "which clients are affected. Client names in affected_clients must match the "
            "input screenshot client names exactly."
        ),
    ),
    JudgeCriteria(
        name="severity_calibration",
        description=(
            "Is severity correctly assigned to each defect? Critical = content missing, "
            "unreadable, or layout broken. Warning = visual degradation but content usable. "
            "Info = minor cosmetic differences. Over-classifying info issues as critical is "
            "a failure. Under-classifying critical issues (broken layout as info) is also "
            "a failure. The overall_rendering_score should be consistent with the number "
            "and severity of reported defects."
        ),
    ),
]


class VisualQAJudge:
    """Binary judge for Visual QA agent outputs."""

    agent_name: str = "visual_qa"
    criteria: list[JudgeCriteria] = VISUAL_QA_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with screenshots info and analysis output."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        # Extract input context
        clients = ""
        html_preview = ""
        if judge_input.input_data:
            clients = str(judge_input.input_data.get("clients", ""))
            html_preview = str(judge_input.input_data.get("html_preview", ""))

        # Extract output
        analysis_output = ""
        if judge_input.output_data:
            defects = judge_input.output_data.get("defects", [])
            summary = judge_input.output_data.get("summary", "")
            score = judge_input.output_data.get("overall_rendering_score", "?")
            analysis_output = f"Summary: {summary}\nRendering score: {score}\n\nDefects:\n"
            for defect in defects:  # type: ignore[attr-defined]
                if isinstance(defect, dict):
                    analysis_output += (
                        f"- [{defect.get('severity', '?')}] {defect.get('region', '?')}: "
                        f"{defect.get('description', '')} "
                        f"(fix: {defect.get('suggested_fix', 'none')}, "
                        f"css: {defect.get('css_property', 'none')}, "
                        f"clients: {defect.get('affected_clients', [])})\n"
                    )

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## SCREENSHOTTED CLIENTS\n{clients}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT INPUT (Email HTML preview)\n```html\n{html_preview}\n```\n\n"
            f"## AGENT OUTPUT (Visual QA Analysis)\n{analysis_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
