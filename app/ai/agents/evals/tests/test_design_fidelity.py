"""Tests for design fidelity scoring — schemas, prompt formatting, trace round-trip."""

from __future__ import annotations

import json

import pytest

from app.ai.agents.evals.judges.base import format_design_context_section
from app.ai.agents.evals.judges.schemas import (
    DesignContext,
    DesignTokenSummary,
    JudgeInput,
    SectionDesignMapping,
)

# ── DesignContext Schema ───────────────────────────────────────────────


class TestDesignContextSchema:
    """Verify DesignContext and sub-schemas accept valid data."""

    def test_empty_context(self) -> None:
        ctx = DesignContext()
        assert ctx.figma_url is None
        assert ctx.design_tokens is None
        assert ctx.section_mapping == []

    def test_full_context(self) -> None:
        ctx = DesignContext(
            figma_url="https://www.figma.com/design/abc123?node-id=1-2",
            node_id="1-2",
            file_id="abc123",
            design_tokens=DesignTokenSummary(
                colors={"primary": "#FF0000"},
                fonts={"heading": "Arial"},
            ),
            section_mapping=[
                SectionDesignMapping(
                    section_index=0,
                    component_slug="hero-block",
                    figma_frame_name="Hero",
                    style_overrides={"bgcolor": "#FF0000"},
                ),
            ],
        )
        assert ctx.node_id == "1-2"
        assert ctx.design_tokens is not None
        assert ctx.design_tokens.colors["primary"] == "#FF0000"
        assert len(ctx.section_mapping) == 1
        assert ctx.section_mapping[0].component_slug == "hero-block"

    def test_partial_tokens(self) -> None:
        tokens = DesignTokenSummary(colors={"bg": "#FFF"})
        assert tokens.fonts == {}
        assert tokens.font_sizes == {}
        assert tokens.spacing == {}

    def test_section_mapping_minimal(self) -> None:
        mapping = SectionDesignMapping(section_index=0, component_slug="heading")
        assert mapping.figma_frame_name is None
        assert mapping.slot_fills == {}
        assert mapping.style_overrides == {}


# ── JudgeInput Backward Compatibility ─────────────────────────────────


class TestJudgeInputBackwardCompat:
    """JudgeInput must work with and without design_context."""

    def test_without_design_context(self) -> None:
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={"brief": "test"},
            output_data={"html": "<table></table>"},
            expected_challenges=["layout"],
        )
        assert ji.design_context is None

    def test_with_design_context(self) -> None:
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={"brief": "test"},
            output_data={"html": "<table></table>"},
            expected_challenges=[],
            design_context=DesignContext(node_id="2833-1424"),
        )
        assert ji.design_context is not None
        assert ji.design_context.node_id == "2833-1424"

    def test_model_dump_includes_design_context(self) -> None:
        ctx = DesignContext(
            figma_url="https://figma.com/design/abc",
            design_tokens=DesignTokenSummary(colors={"primary": "#000"}),
        )
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={},
            output_data=None,
            expected_challenges=[],
            design_context=ctx,
        )
        dump = ji.model_dump()
        assert dump["design_context"]["figma_url"] == "https://figma.com/design/abc"
        assert dump["design_context"]["design_tokens"]["colors"]["primary"] == "#000"

    def test_model_dump_none_context(self) -> None:
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={},
            output_data=None,
            expected_challenges=[],
        )
        dump = ji.model_dump()
        assert dump["design_context"] is None


# ── Trace Round-Trip ──────────────────────────────────────────────────


class TestTraceRoundTrip:
    """design_context survives JSONL serialize → deserialize → JudgeInput."""

    def test_trace_with_design_context_round_trip(self) -> None:
        from app.ai.agents.evals.judge_runner import trace_to_judge_input

        trace = {
            "id": "scaff-023",
            "agent": "scaffolder",
            "input": {"brief": "Starbucks test"},
            "output": {"html": "<table></table>"},
            "expected_challenges": ["color_fidelity"],
            "design_context": {
                "figma_url": "https://figma.com/design/abc?node-id=2833-1424",
                "node_id": "2833-1424",
                "file_id": "abc",
                "design_tokens": {
                    "colors": {"primary": "#1e3932"},
                    "fonts": {"heading": "SoDo Sans"},
                    "font_sizes": {},
                    "spacing": {},
                },
                "section_mapping": [
                    {
                        "section_index": 0,
                        "component_slug": "full-width-image",
                        "figma_frame_name": "Hero",
                        "slot_fills": {},
                        "style_overrides": {},
                    },
                ],
            },
        }

        # Simulate JSONL round-trip
        serialized = json.dumps(trace)
        deserialized = json.loads(serialized)

        ji = trace_to_judge_input(deserialized)
        assert ji.design_context is not None
        assert ji.design_context.node_id == "2833-1424"
        assert ji.design_context.design_tokens is not None
        assert ji.design_context.design_tokens.colors["primary"] == "#1e3932"
        assert len(ji.design_context.section_mapping) == 1

    def test_trace_without_design_context(self) -> None:
        from app.ai.agents.evals.judge_runner import trace_to_judge_input

        trace = {
            "id": "scaff-001",
            "agent": "scaffolder",
            "input": {"brief": "Simple test"},
            "output": {"html": "<table></table>"},
            "expected_challenges": [],
        }
        ji = trace_to_judge_input(trace)
        assert ji.design_context is None


# ── format_design_context_section ─────────────────────────────────────


class TestFormatDesignContextSection:
    """Prompt formatting helper for design context."""

    def test_empty_context_returns_empty(self) -> None:
        ctx = DesignContext()
        assert format_design_context_section(ctx) == ""

    def test_url_only(self) -> None:
        ctx = DesignContext(figma_url="https://figma.com/design/abc")
        result = format_design_context_section(ctx)
        assert "https://figma.com/design/abc" in result
        assert "## DESIGN REFERENCE" in result

    def test_full_context_format(self) -> None:
        ctx = DesignContext(
            figma_url="https://figma.com/design/abc?node-id=1-2",
            node_id="1-2",
            design_tokens=DesignTokenSummary(
                colors={"primary": "#FF0000", "bg": "#FFFFFF"},
                fonts={"heading": "Arial"},
                font_sizes={"heading": "40px"},
                spacing={"top": "20px"},
            ),
            section_mapping=[
                SectionDesignMapping(
                    section_index=0,
                    component_slug="hero-block",
                    figma_frame_name="Hero",
                    style_overrides={"bgcolor": "#FF0000"},
                ),
                SectionDesignMapping(
                    section_index=1,
                    component_slug="heading",
                ),
            ],
        )
        result = format_design_context_section(ctx)
        assert "primary=#FF0000" in result
        assert "heading=Arial" in result
        assert "heading=40px" in result
        assert "top=20px" in result
        assert "Section 0: hero-block (frame: Hero)" in result
        assert "Overrides: bgcolor=#FF0000" in result
        assert "Section 1: heading" in result

    def test_char_budget_enforced(self) -> None:
        """Output must not exceed the char budget (1500 chars)."""
        ctx = DesignContext(
            figma_url="https://figma.com/design/abc",
            design_tokens=DesignTokenSummary(
                colors={f"color_{i}": f"#{i:06d}" for i in range(100)},
            ),
            section_mapping=[
                SectionDesignMapping(
                    section_index=i,
                    component_slug=f"component-{i}",
                    figma_frame_name=f"Frame {i}",
                    style_overrides={f"prop-{j}": f"val-{j}" for j in range(5)},
                )
                for i in range(50)
            ],
        )
        result = format_design_context_section(ctx)
        # 1500 + len("[truncated]") + newline
        assert len(result) <= 1520


# ── Scaffolder Judge Design Block ─────────────────────────────────────


class TestScaffolderJudgeDesignBlock:
    """ScaffolderJudge includes design context in prompt when available."""

    def test_prompt_without_design_context(self) -> None:
        from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge

        judge = ScaffolderJudge()
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={"brief": "test brief"},
            output_data={"html": "<table></table>"},
            expected_challenges=[],
        )
        prompt = judge.build_prompt(ji)
        assert "DESIGN REFERENCE (from Figma)" not in prompt
        assert "design_fidelity" in prompt  # criterion is always listed

    def test_prompt_with_design_context(self) -> None:
        from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge

        judge = ScaffolderJudge()
        ji = JudgeInput(
            trace_id="t1",
            agent="scaffolder",
            input_data={"brief": "test brief"},
            output_data={"html": "<table></table>"},
            expected_challenges=[],
            design_context=DesignContext(
                figma_url="https://figma.com/design/abc",
                node_id="2833-1424",
                design_tokens=DesignTokenSummary(
                    colors={"primary": "#1e3932"},
                ),
            ),
        )
        prompt = judge.build_prompt(ji)
        assert "## DESIGN REFERENCE" in prompt
        assert "primary=#1e3932" in prompt
        assert "design_fidelity" in prompt

    def test_design_fidelity_criterion_exists(self) -> None:
        from app.ai.agents.evals.judges.scaffolder import SCAFFOLDER_CRITERIA

        names = [c.name for c in SCAFFOLDER_CRITERIA]
        assert "design_fidelity" in names
        assert len(names) == 6


# ── Synthetic Test Cases ──────────────────────────────────────────────


class TestDesignFidelitySyntheticCases:
    """Verify the 3 design-fidelity synthetic cases are well-formed."""

    def test_design_fidelity_cases_exist(self) -> None:
        from app.ai.agents.evals.synthetic_data_scaffolder import SCAFFOLDER_TEST_CASES

        fidelity_cases = [c for c in SCAFFOLDER_TEST_CASES if c.get("design_context")]
        assert len(fidelity_cases) == 3

    def test_design_fidelity_cases_have_valid_context(self) -> None:
        from typing import Any, cast

        from app.ai.agents.evals.synthetic_data_scaffolder import SCAFFOLDER_TEST_CASES

        for case in SCAFFOLDER_TEST_CASES:
            dc = case.get("design_context")
            if dc is None:
                continue
            # Verify it can be parsed into DesignContext
            ctx = DesignContext(**cast(dict[str, Any], dc))
            assert ctx.figma_url is not None
            assert ctx.node_id is not None
            assert ctx.file_id is not None
            assert ctx.design_tokens is not None
            assert len(ctx.section_mapping) > 0

    @pytest.mark.parametrize("case_id", ["scaff-023", "scaff-024", "scaff-025"])
    def test_design_fidelity_case_ids(self, case_id: str) -> None:
        from app.ai.agents.evals.synthetic_data_scaffolder import SCAFFOLDER_TEST_CASES

        ids = [c["id"] for c in SCAFFOLDER_TEST_CASES]
        assert case_id in ids

    def test_all_cases_reference_same_figma_file(self) -> None:
        from typing import Any, cast

        from app.ai.agents.evals.synthetic_data_scaffolder import SCAFFOLDER_TEST_CASES

        fidelity_cases = [c for c in SCAFFOLDER_TEST_CASES if c.get("design_context")]
        file_ids = {cast(dict[str, Any], c["design_context"])["file_id"] for c in fidelity_cases}
        assert file_ids == {"VUlWjZGAEVZr3mK1EawsYR"}
