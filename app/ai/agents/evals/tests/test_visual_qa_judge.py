# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
"""Unit tests for the Visual QA judge — prompt building and response parsing."""

import json

from app.ai.agents.evals.judges.schemas import JudgeInput
from app.ai.agents.evals.judges.visual_qa import (
    VISUAL_QA_CRITERIA,
    VisualQAJudge,
)

VISUAL_QA_CRITERIA_NAMES = [
    "defect_detection_accuracy",
    "fix_correctness",
    "false_positive_rate",
    "client_coverage",
    "severity_calibration",
]


def _make_visual_qa_input() -> JudgeInput:
    return JudgeInput(
        trace_id="vqa-001",
        agent="visual_qa",
        input_data={
            "clients": ["gmail_web", "outlook_2019", "apple_mail"],
            "html_preview": "<html><body><table><tr><td>Email content</td></tr></table></body></html>",
        },
        output_data={
            "summary": "Found 2 rendering defects across 3 clients",
            "overall_rendering_score": 7.5,
            "defects": [
                {
                    "severity": "warning",
                    "region": "header",
                    "description": "Border-radius not rendered in Outlook",
                    "suggested_fix": "Use VML roundrect for Outlook",
                    "css_property": "border-radius",
                    "affected_clients": ["outlook_2019"],
                },
                {
                    "severity": "info",
                    "region": "footer",
                    "description": "Slight font size difference",
                    "suggested_fix": "Explicitly set font-size in inline styles",
                    "css_property": "font-size",
                    "affected_clients": ["gmail_web"],
                },
            ],
        },
        expected_challenges=["border-radius in Outlook", "style stripping in Gmail"],
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


# ── A. Judge criteria ──


class TestVisualQACriteria:
    def test_criteria_count(self) -> None:
        assert len(VISUAL_QA_CRITERIA) == 5

    def test_criteria_names(self) -> None:
        names = {c.name for c in VISUAL_QA_CRITERIA}
        assert names == set(VISUAL_QA_CRITERIA_NAMES)

    def test_agent_name(self) -> None:
        judge = VisualQAJudge()
        assert judge.agent_name == "visual_qa"


# ── B. Prompt building ──


class TestVisualQAPromptBuilding:
    def test_build_prompt_includes_clients(self) -> None:
        judge = VisualQAJudge()
        prompt = judge.build_prompt(_make_visual_qa_input())

        assert "gmail_web" in prompt
        assert "outlook_2019" in prompt
        assert "apple_mail" in prompt

    def test_build_prompt_includes_html_preview(self) -> None:
        judge = VisualQAJudge()
        prompt = judge.build_prompt(_make_visual_qa_input())

        assert "<table>" in prompt
        assert "Email content" in prompt

    def test_build_prompt_includes_expected_challenges(self) -> None:
        judge = VisualQAJudge()
        prompt = judge.build_prompt(_make_visual_qa_input())

        assert "border-radius in Outlook" in prompt
        assert "style stripping in Gmail" in prompt

    def test_build_prompt_includes_vlm_output(self) -> None:
        judge = VisualQAJudge()
        prompt = judge.build_prompt(_make_visual_qa_input())

        assert "Border-radius not rendered in Outlook" in prompt
        assert "VML roundrect" in prompt
        assert "Rendering score: 7.5" in prompt
        assert "[warning]" in prompt
        assert "[info]" in prompt


# ── C. Response parsing ──


class TestVisualQAResponseParsing:
    def test_parse_valid_response(self) -> None:
        judge = VisualQAJudge()
        raw = _make_valid_response(VISUAL_QA_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_visual_qa_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.error is None
        assert verdict.trace_id == "vqa-001"
        assert verdict.agent == "visual_qa"

    def test_parse_all_pass(self) -> None:
        judge = VisualQAJudge()
        raw = _make_valid_response(VISUAL_QA_CRITERIA_NAMES, all_pass=True)
        verdict = judge.parse_response(raw, _make_visual_qa_input())

        assert verdict.overall_pass is True
        assert all(cr.passed for cr in verdict.criteria_results)

    def test_parse_partial_fail(self) -> None:
        judge = VisualQAJudge()
        data = {
            "overall_pass": False,
            "criteria_results": [
                {"criterion": "defect_detection_accuracy", "passed": True, "reasoning": "OK"},
                {"criterion": "fix_correctness", "passed": True, "reasoning": "OK"},
                {"criterion": "false_positive_rate", "passed": False, "reasoning": "Too many FPs"},
                {"criterion": "client_coverage", "passed": True, "reasoning": "OK"},
                {
                    "criterion": "severity_calibration",
                    "passed": False,
                    "reasoning": "Miscalibrated",
                },
            ],
        }
        verdict = judge.parse_response(json.dumps(data), _make_visual_qa_input())

        assert verdict.overall_pass is False
        failed = [cr for cr in verdict.criteria_results if not cr.passed]
        assert len(failed) == 2
        assert {cr.criterion for cr in failed} == {"false_positive_rate", "severity_calibration"}

    def test_parse_malformed_json(self) -> None:
        judge = VisualQAJudge()
        verdict = judge.parse_response("not valid json {{{", _make_visual_qa_input())

        assert verdict.overall_pass is False
        assert verdict.criteria_results == []
        assert verdict.error is not None
        assert "Failed to parse" in verdict.error

    def test_parse_missing_criteria(self) -> None:
        judge = VisualQAJudge()
        # Missing criteria_results key entirely
        data = {"overall_pass": True}
        verdict = judge.parse_response(json.dumps(data), _make_visual_qa_input())

        assert verdict.overall_pass is False
        assert verdict.error is not None
        assert "Failed to parse" in verdict.error
