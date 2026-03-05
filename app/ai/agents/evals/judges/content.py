"""Binary pass/fail judge for the Content agent."""

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

CONTENT_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="copy_quality",
        description=(
            "Is the generated copy compelling, clear, and well-crafted? "
            "For subject lines: front-loaded value, 40-60 chars, curiosity or urgency. "
            "For CTAs: action verb, 2-5 words, benefit-focused. "
            "For body copy: scannable, short paragraphs, clear value proposition. "
            "For rewrites/transforms: meaning preserved, clarity improved."
        ),
    ),
    JudgeCriteria(
        name="tone_accuracy",
        description=(
            "Does the output match the requested tone? "
            "If 'professional_formal' — no slang, structured sentences. "
            "If 'casual_friendly' — conversational, approachable. "
            "If 'urgent_fomo' — time pressure without desperation. "
            "If 'luxury_aspirational' — refined, exclusive language. "
            "If brand_voice was provided, it must override default tone guidance."
        ),
    ),
    JudgeCriteria(
        name="spam_avoidance",
        description=(
            "Is the output free of common email spam triggers while remaining persuasive? "
            "Must not contain: ALL CAPS words, excessive punctuation (!!!, ???), "
            "'click here', 'buy now', 'act now', 'limited time', '100% free', "
            "'no obligation', 'guaranteed', 'winner', 'congratulations' as standalone phrases. "
            "A single 'free' in natural context (e.g., 'free shipping') is acceptable."
        ),
    ),
    JudgeCriteria(
        name="operation_compliance",
        description=(
            "Does the output correctly follow the requested operation? "
            "subject_line: within char limits. preheader: complements not repeats subject. "
            "shorten: actually shorter (30-50% reduction). expand: adds substance, not filler. "
            "tone_adjust: factual content preserved, only style changed. "
            "rewrite: improved clarity while preserving core message."
        ),
    ),
    JudgeCriteria(
        name="security_and_pii",
        description=(
            "Does the output contain NO real PII (names, emails, SSNs, phone numbers)? "
            "Placeholders like [NAME], [EMAIL], [COMPANY] should be used instead. "
            "No HTML tags, no JavaScript, no URLs unless present in the source text. "
            "Output must be plain text only."
        ),
    ),
]


class ContentJudge:
    """Binary judge for Content agent outputs."""

    agent_name: str = "content"
    criteria: list[JudgeCriteria] = CONTENT_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with operation context and generated content."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        input_data = judge_input.input_data
        operation = str(input_data.get("operation", ""))
        text = str(input_data.get("text", ""))
        tone = str(input_data.get("tone", "not specified"))
        brand_voice = input_data.get("brand_voice")

        output_data = judge_input.output_data or {}
        raw_content = output_data.get("content", [])
        content_items: list[str]
        if isinstance(raw_content, list):
            content_items = [str(x) for x in raw_content]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
        else:
            content_items = [str(raw_content)]
        formatted_output = "\n---\n".join(content_items)

        constraints = f"Operation: {operation}\nTone: {tone}"
        if brand_voice:
            constraints += f"\nBrand voice: {brand_voice}"

        user_content = (
            f"## AGENT INPUT\n{constraints}\n\nOriginal text:\n{text}\n\n"
            f"## AGENT OUTPUT\n```text\n{formatted_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
