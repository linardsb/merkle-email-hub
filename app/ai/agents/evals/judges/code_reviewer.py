# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Code Reviewer agent."""

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

CODE_REVIEWER_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="issue_genuineness",
        description=(
            "Are all flagged issues real problems? Each reported issue must be a "
            "genuine code quality problem in email HTML context. Standard email patterns "
            "(table layouts, inline styles, MSO conditionals, VML, mso-* CSS properties, "
            "cellpadding/cellspacing/border attributes) must NOT be flagged as issues. "
            "A false positive is any issue that flags normal, expected email HTML patterns."
        ),
    ),
    JudgeCriteria(
        name="suggestion_actionability",
        description=(
            "Does every issue include a concrete, actionable fix suggestion? Generic "
            "advice like 'consider improving' or 'review this code' is insufficient. "
            "Suggestions must specify what to change (e.g., 'Replace display:flex with "
            "table-based layout', 'Move repeated font-family to <style> class', "
            "'Host image externally instead of base64 encoding'). Severity:info issues "
            "may have lighter suggestions but must still be specific."
        ),
    ),
    JudgeCriteria(
        name="severity_accuracy",
        description=(
            "Is the severity classification correct for each issue? Critical = breaks "
            "rendering in major email clients (Outlook, Gmail). Warning = degrades "
            "experience or poor practice. Info = optimisation opportunity. Examples: "
            "display:flex should be critical (breaks Outlook). Redundant styles should "
            "be warning or info. Unused CSS class should be info. File size >102KB "
            "should be critical. Over-classifying info issues as critical is a failure."
        ),
    ),
    JudgeCriteria(
        name="coverage_completeness",
        description=(
            "Does the review catch all significant issues in the HTML? Compare the "
            "expected_challenges from the test case against the reported issues. "
            "Missing a critical issue (unsupported CSS, invalid nesting, size threshold) "
            "is a coverage failure. Missing an info-level optimisation is acceptable "
            "if the major issues are caught."
        ),
    ),
    JudgeCriteria(
        name="output_format",
        description=(
            "Is the output valid JSON with the expected structure? Must contain an "
            "'issues' array where each issue has 'rule' (string), 'severity' "
            "(critical/warning/info), 'message' (string), and optionally 'line_hint' "
            "(integer) and 'suggestion' (string). Must also contain a 'summary' string. "
            "If the output is not parseable JSON or is missing required fields, this "
            "criterion fails."
        ),
    ),
]


class CodeReviewerJudge:
    """Binary judge for Code Reviewer agent outputs."""

    agent_name: str = "code_reviewer"
    criteria: list[JudgeCriteria] = CODE_REVIEWER_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML and review output."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        focus = "all"
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))
            focus = str(judge_input.input_data.get("focus", "all"))

        review_output = ""
        if judge_input.output_data:
            # Output includes issues and summary
            issues = judge_input.output_data.get("issues", [])
            summary = judge_input.output_data.get("summary", "")
            review_output = f"Summary: {summary}\n\nIssues:\n"
            for issue in issues:
                if isinstance(issue, dict):
                    review_output += (
                        f"- [{issue.get('severity', '?')}] {issue.get('rule', '?')}: "
                        f"{issue.get('message', '')} "
                        f"(suggestion: {issue.get('suggestion', 'none')})\n"
                    )

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## REVIEW FOCUS\n{focus}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT INPUT (Email HTML)\n```html\n{html_input}\n```\n\n"
            f"## AGENT OUTPUT (Code Review)\n{review_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
