"""Unit tests for LLM judge modules — prompt building and response parsing only."""

import json

from app.ai.agents.evals.judges import JUDGE_REGISTRY
from app.ai.agents.evals.judges.content import ContentJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import JudgeInput


def _make_scaffolder_input() -> JudgeInput:
    return JudgeInput(
        trace_id="scaff-001",
        agent="scaffolder",
        input_data={"brief": "Create a single-column promotional email"},
        output_data={"html": "<html><body><table></table></body></html>"},
        expected_challenges=["table layout", "MSO conditionals"],
    )


def _make_dark_mode_input() -> JudgeInput:
    return JudgeInput(
        trace_id="dark-001",
        agent="dark_mode",
        input_data={
            "html_input": "<html><body style='background:#fff'></body></html>",
            "color_overrides": {"#fff": "#1a1a2e"},
            "preserve_colors": ["#E85D04"],
        },
        output_data={"html": "<html><body style='background:#1a1a2e'></body></html>"},
        expected_challenges=["color remapping"],
    )


def _make_content_input() -> JudgeInput:
    return JudgeInput(
        trace_id="content-001",
        agent="content",
        input_data={
            "operation": "subject_line",
            "text": "We have new arrivals in our spring collection",
            "tone": "luxury_aspirational",
            "brand_voice": "Refined and exclusive",
            "num_alternatives": 3,
        },
        output_data={
            "content": ["Spring Awaits: New Arrivals", "Discover Spring", "Unveil the Season"]
        },
        expected_challenges=["char limit", "tone match"],
    )


def _make_valid_response(criteria_names: list[str], all_pass: bool = True) -> str:
    return json.dumps(
        {
            "overall_pass": all_pass,
            "criteria_results": [
                {"criterion": name, "passed": all_pass, "reasoning": f"{name} evaluated."}
                for name in criteria_names
            ],
        }
    )


SCAFFOLDER_CRITERIA_NAMES = [
    "brief_fidelity",
    "email_layout_patterns",
    "mso_conditional_correctness",
    "dark_mode_readiness",
    "accessibility_baseline",
]

DARK_MODE_CRITERIA_NAMES = [
    "color_coherence",
    "html_preservation",
    "outlook_selector_completeness",
    "meta_and_media_query",
    "contrast_preservation",
]

CONTENT_CRITERIA_NAMES = [
    "copy_quality",
    "tone_accuracy",
    "spam_avoidance",
    "operation_compliance",
    "security_and_pii",
]


# --- Scaffolder Judge Tests ---


class TestScaffolderJudge:
    def test_build_prompt_contains_criteria_and_input(self) -> None:
        judge = ScaffolderJudge()
        prompt = judge.build_prompt(_make_scaffolder_input())

        assert "brief_fidelity" in prompt
        assert "email_layout_patterns" in prompt
        assert "mso_conditional_correctness" in prompt
        assert "Create a single-column promotional email" in prompt
        assert "<table></table>" in prompt

    def test_parse_valid_response(self) -> None:
        judge = ScaffolderJudge()
        raw = _make_valid_response(SCAFFOLDER_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_scaffolder_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.error is None
        assert verdict.trace_id == "scaff-001"
        assert verdict.agent == "scaffolder"

    def test_parse_markdown_wrapped_response(self) -> None:
        judge = ScaffolderJudge()
        inner = _make_valid_response(SCAFFOLDER_CRITERIA_NAMES)
        raw = f"```json\n{inner}\n```"
        verdict = judge.parse_response(raw, _make_scaffolder_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.error is None

    def test_parse_invalid_json_returns_error(self) -> None:
        judge = ScaffolderJudge()
        verdict = judge.parse_response("not valid json {{{", _make_scaffolder_input())

        assert verdict.overall_pass is False
        assert verdict.criteria_results == []
        assert verdict.error is not None
        assert "Failed to parse" in verdict.error


# --- Dark Mode Judge Tests ---


class TestDarkModeJudge:
    def test_build_prompt_includes_constraints(self) -> None:
        judge = DarkModeJudge()
        prompt = judge.build_prompt(_make_dark_mode_input())

        assert "Color overrides requested" in prompt
        assert "#E85D04" in prompt
        assert "Colors to preserve" in prompt

    def test_build_prompt_includes_both_htmls(self) -> None:
        judge = DarkModeJudge()
        prompt = judge.build_prompt(_make_dark_mode_input())

        assert "ORIGINAL HTML" in prompt
        assert "background:#fff" in prompt
        assert "DARK MODE HTML" in prompt
        assert "background:#1a1a2e" in prompt

    def test_parse_valid_response(self) -> None:
        judge = DarkModeJudge()
        raw = _make_valid_response(DARK_MODE_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_dark_mode_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.agent == "dark_mode"

    def test_build_prompt_without_constraints(self) -> None:
        """Prompt should work when no color overrides/preserve specified."""
        judge = DarkModeJudge()
        judge_input = JudgeInput(
            trace_id="dark-simple",
            agent="dark_mode",
            input_data={"html_input": "<html></html>"},
            output_data={"html": "<html></html>"},
            expected_challenges=[],
        )
        prompt = judge.build_prompt(judge_input)

        assert "Color overrides" not in prompt
        assert "Colors to preserve" not in prompt


# --- Content Judge Tests ---


class TestContentJudge:
    def test_build_prompt_includes_operation_and_tone(self) -> None:
        judge = ContentJudge()
        prompt = judge.build_prompt(_make_content_input())

        assert "Operation: subject_line" in prompt
        assert "Tone: luxury_aspirational" in prompt
        assert "Brand voice: Refined and exclusive" in prompt

    def test_parse_valid_response(self) -> None:
        judge = ContentJudge()
        raw = _make_valid_response(CONTENT_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_content_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.agent == "content"

    def test_build_prompt_formats_alternatives(self) -> None:
        judge = ContentJudge()
        prompt = judge.build_prompt(_make_content_input())

        assert "Spring Awaits: New Arrivals" in prompt
        assert "Discover Spring" in prompt
        assert "Unveil the Season" in prompt


# --- Registry & Cross-Cutting Tests ---


class TestJudgeRegistry:
    def test_registry_has_all_agents(self) -> None:
        assert "scaffolder" in JUDGE_REGISTRY
        assert "dark_mode" in JUDGE_REGISTRY
        assert "content" in JUDGE_REGISTRY
        assert "outlook_fixer" in JUDGE_REGISTRY
        assert len(JUDGE_REGISTRY) == 4

    def test_registry_instantiation(self) -> None:
        for name, cls in JUDGE_REGISTRY.items():
            judge = cls()
            assert judge.agent_name == name


class TestVerdictOverallPass:
    def test_overall_false_when_criterion_fails(self) -> None:
        """Verify parse correctly reads overall_pass=false from response."""
        judge = ScaffolderJudge()
        data = {
            "overall_pass": False,
            "criteria_results": [
                {"criterion": "brief_fidelity", "passed": True, "reasoning": "OK"},
                {
                    "criterion": "email_layout_patterns",
                    "passed": False,
                    "reasoning": "Uses flexbox",
                },
                {"criterion": "mso_conditional_correctness", "passed": True, "reasoning": "OK"},
                {"criterion": "dark_mode_readiness", "passed": True, "reasoning": "OK"},
                {"criterion": "accessibility_baseline", "passed": True, "reasoning": "OK"},
            ],
        }
        verdict = judge.parse_response(json.dumps(data), _make_scaffolder_input())

        assert verdict.overall_pass is False
        failed = [cr for cr in verdict.criteria_results if not cr.passed]
        assert len(failed) == 1
        assert failed[0].criterion == "email_layout_patterns"
