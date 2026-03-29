"""Tests for golden reference injection into judge prompts (Phase 37.3)."""

from __future__ import annotations

import pytest

from app.ai.agents.evals.golden_references import load_golden_references
from app.ai.agents.evals.judges.accessibility import AccessibilityJudge
from app.ai.agents.evals.judges.base import _GOLDEN_TOKEN_BUDGET, format_golden_section
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.innovation import InnovationJudge
from app.ai.agents.evals.judges.outlook_fixer import OutlookFixerJudge
from app.ai.agents.evals.judges.personalisation import PersonalisationJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import JudgeInput


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear lru_cache between tests."""
    load_golden_references.cache_clear()


def _make_input(
    agent: str,
    *,
    input_data: dict[str, object] | None = None,
    output_data: dict[str, object] | None = None,
) -> JudgeInput:
    return JudgeInput(
        trace_id="test-golden-001",
        agent=agent,
        input_data=input_data or {},
        output_data=output_data or {"html": "<table></table>"},
        expected_challenges=[],
    )


# --- Per-Judge Injection Tests ---


class TestScaffolderGoldenInjection:
    def test_prompt_contains_golden_refs(self) -> None:
        judge = ScaffolderJudge()
        ji = _make_input("scaffolder", input_data={"brief": "Test brief"})
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        assert "verified-correct email HTML patterns" in prompt

    def test_prompt_contains_relevant_snippets(self) -> None:
        judge = ScaffolderJudge()
        ji = _make_input("scaffolder", input_data={"brief": "Test brief"})
        prompt = judge.build_prompt(ji)

        # Scaffolder criteria include mso_conditional_correctness → VML refs
        assert "```html" in prompt


class TestDarkModeGoldenInjection:
    def test_prompt_contains_golden_refs(self) -> None:
        judge = DarkModeJudge()
        ji = _make_input(
            "dark_mode",
            input_data={"html_input": "<html></html>"},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt

    def test_golden_between_input_and_output(self) -> None:
        judge = DarkModeJudge()
        ji = _make_input(
            "dark_mode",
            input_data={"html_input": "<html></html>"},
        )
        prompt = judge.build_prompt(ji)

        golden_pos = prompt.index("GOLDEN REFERENCE EXAMPLES")
        input_pos = prompt.index("ORIGINAL HTML")
        output_pos = prompt.index("DARK MODE HTML")
        assert input_pos < golden_pos < output_pos


class TestOutlookFixerGoldenInjection:
    def test_prompt_contains_golden_refs(self) -> None:
        judge = OutlookFixerJudge()
        ji = _make_input("outlook_fixer", input_data={"html_input": "<html></html>"})
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        # Should have VML/MSO references
        assert "```html" in prompt


class TestAccessibilityGoldenInjection:
    def test_prompt_contains_golden_refs(self) -> None:
        judge = AccessibilityJudge()
        ji = _make_input("accessibility", input_data={"html_input": "<html></html>"})
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt


class TestPersonalisationPlatformFiltering:
    def test_braze_only_gets_braze_ref(self) -> None:
        judge = PersonalisationJudge()
        ji = _make_input(
            "personalisation",
            input_data={"html_input": "<html></html>", "platform": "braze", "requirements": ""},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        assert "Braze" in prompt
        assert "SFMC" not in prompt.split("GOLDEN REFERENCE EXAMPLES")[1].split("AGENT OUTPUT")[0]

    def test_sfmc_only_gets_sfmc_ref(self) -> None:
        judge = PersonalisationJudge()
        ji = _make_input(
            "personalisation",
            input_data={"html_input": "<html></html>", "platform": "sfmc", "requirements": ""},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        golden_section = prompt.split("GOLDEN REFERENCE EXAMPLES")[1].split("AGENT OUTPUT")[0]
        assert "SFMC" in golden_section

    def test_unknown_platform_no_golden_section(self) -> None:
        judge = PersonalisationJudge()
        ji = _make_input(
            "personalisation",
            input_data={
                "html_input": "<html></html>",
                "platform": "unknown_esp",
                "requirements": "",
            },
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" not in prompt


class TestCodeReviewerInvertedFraming:
    def test_inverted_framing_present(self) -> None:
        judge = CodeReviewerJudge()
        ji = _make_input(
            "code_reviewer",
            input_data={"html_input": "<html></html>", "focus": "all"},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        assert "do NOT flag them as issues" in prompt

    def test_standard_framing_absent(self) -> None:
        judge = CodeReviewerJudge()
        ji = _make_input(
            "code_reviewer",
            input_data={"html_input": "<html></html>", "focus": "all"},
        )
        prompt = judge.build_prompt(ji)

        # Should NOT have the standard framing
        assert 'what "correct" looks like' not in prompt


class TestInnovationCategoryFiltering:
    def test_carousel_only_gets_carousel_ref(self) -> None:
        judge = InnovationJudge()
        ji = _make_input(
            "innovation",
            input_data={"technique": "CSS carousel", "category": "carousel"},
            output_data={"prototype": "<div></div>", "feasibility": "ok", "fallback_html": ""},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        golden_section = prompt.split("GOLDEN REFERENCE EXAMPLES")[1].split("AGENT OUTPUT")[0]
        assert "Carousel" in golden_section

    def test_accordion_only_gets_accordion_ref(self) -> None:
        judge = InnovationJudge()
        ji = _make_input(
            "innovation",
            input_data={"technique": "Accordion", "category": "accordion"},
            output_data={"prototype": "<div></div>", "feasibility": "ok", "fallback_html": ""},
        )
        prompt = judge.build_prompt(ji)

        assert "GOLDEN REFERENCE EXAMPLES" in prompt
        golden_section = prompt.split("GOLDEN REFERENCE EXAMPLES")[1].split("AGENT OUTPUT")[0]
        assert "Accordion" in golden_section

    def test_any_category_gets_all_refs(self) -> None:
        judge = InnovationJudge()
        ji = _make_input(
            "innovation",
            input_data={"technique": "Something", "category": "any"},
            output_data={"prototype": "<div></div>", "feasibility": "ok", "fallback_html": ""},
        )
        prompt = judge.build_prompt(ji)

        # category="any" → no name_filter → all technique_correctness/fallback_quality refs
        assert "GOLDEN REFERENCE EXAMPLES" in prompt


# --- format_golden_section Unit Tests ---


class TestFormatGoldenSection:
    def test_empty_criteria_returns_empty(self) -> None:
        result = format_golden_section([])
        assert result == ""

    def test_unknown_criterion_returns_empty(self) -> None:
        result = format_golden_section(["nonexistent_criterion_xyz"])
        assert result == ""

    def test_name_filter_excludes_non_matching(self) -> None:
        result = format_golden_section(
            ["syntax_correctness", "fallback_completeness", "platform_accuracy"],
            name_filter="braze",
        )
        assert result != ""
        assert "Braze" in result

    def test_name_filter_no_match_returns_empty(self) -> None:
        result = format_golden_section(
            ["syntax_correctness"],
            name_filter="nonexistent_platform",
        )
        assert result == ""

    def test_inverted_framing_text(self) -> None:
        result = format_golden_section(
            ["issue_genuineness"],
            framing="inverted",
        )
        assert "do NOT flag them as issues" in result
        assert 'what "correct" looks like' not in result

    def test_standard_framing_text(self) -> None:
        result = format_golden_section(["mso_conditional_correctness"])
        assert 'what "correct" looks like' in result
        assert "do NOT flag" not in result

    def test_dedup_across_criteria(self) -> None:
        # mso_conditional_correctness and vml_wellformedness share some refs
        result = format_golden_section(["mso_conditional_correctness", "vml_wellformedness"])
        # Count "### Example" occurrences — should be deduplicated
        example_count = result.count("### Example")
        # VML Background Image + Nested MSO + VML Rounded Button = 3 unique refs
        # (some appear under both criteria but should only show once)
        assert example_count >= 2
        assert example_count <= 5  # capped at unique count

    def test_token_budget_cap(self) -> None:
        result = format_golden_section(["mso_conditional_correctness", "vml_wellformedness"])
        # Budget: ~8000 chars for golden section content
        char_budget = _GOLDEN_TOKEN_BUDGET * 4
        # The actual content (excluding header) should be within budget
        assert len(result) < char_budget + 500  # small header overhead allowance
