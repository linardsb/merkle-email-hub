# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Knowledge agent."""

from app.ai.agents.evals.judges.base import (
    build_system_prompt,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

KNOWLEDGE_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="answer_accuracy",
        description=(
            "Is the answer factually correct based on the retrieved context? "
            "Claims about CSS support, email client behavior, or rendering engines "
            "must match the source documents. Fabricated or hallucinated claims "
            "not grounded in the retrieved context are a failure."
        ),
    ),
    JudgeCriteria(
        name="citation_grounding",
        description=(
            "Does the answer cite specific source documents? Every factual claim "
            "should reference the document it came from (by filename or domain). "
            "An answer that states facts without any citation is a failure. "
            "Citations to non-existent documents are also a failure."
        ),
    ),
    JudgeCriteria(
        name="code_example_quality",
        description=(
            "When the question calls for code, does the answer include a working "
            "email-safe HTML/CSS example? Code must use table-based layouts (not "
            "div/flex/grid for layout), inline styles, and placeholder URLs "
            "(placehold.co or example.com). Must NOT contain <script>, on* handlers, "
            "or javascript: protocol. If no code is needed, this criterion passes."
        ),
    ),
    JudgeCriteria(
        name="source_relevance",
        description=(
            "Are the retrieved sources relevant to the question? The top sources "
            "should come from the expected domain(s). If the question is about CSS "
            "support, sources should be from css_support domain. If sources are "
            "irrelevant or no sources were retrieved for a well-covered topic, "
            "this criterion fails."
        ),
    ),
    JudgeCriteria(
        name="completeness",
        description=(
            "Does the answer address all aspects of the question? Compare against "
            "the expected_challenges list. Missing a major aspect (e.g., not "
            "mentioning Outlook fallback when discussing a CSS property) is a "
            "failure. The answer should also include a confidence indicator "
            "appropriate to the source coverage level."
        ),
    ),
]


class KnowledgeJudge:
    """Binary judge for Knowledge agent outputs."""

    agent_name: str = "knowledge"
    criteria: list[JudgeCriteria] = KNOWLEDGE_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with question, sources, and answer."""
        system = build_system_prompt(self.criteria, self.agent_name)

        question = ""
        domain = "any"
        if judge_input.input_data:
            question = str(judge_input.input_data.get("question", ""))
            domain = str(judge_input.input_data.get("domain", "any"))

        answer_output = ""
        sources_output = ""
        if judge_input.output_data:
            answer_output = str(judge_input.output_data.get("answer", ""))
            sources = judge_input.output_data.get("sources", [])
            if isinstance(sources, list):
                for src in sources:
                    if isinstance(src, dict):
                        sources_output += (
                            f"- {src.get('filename', '?')} "
                            f"(domain: {src.get('domain', '?')}, "
                            f"score: {src.get('relevance_score', '?')})\n"
                        )

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## QUESTION\n{question}\n\n"
            f"## DOMAIN FILTER\n{domain}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT OUTPUT (Answer)\n{answer_output}\n\n"
            f"## RETRIEVED SOURCES\n{sources_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
