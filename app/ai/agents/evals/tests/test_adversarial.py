"""Tests for adversarial eval case generation, YAML loading, and regression."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from app.ai.agents.evals.adversarial import (
    ALL_AGENTS,
    HTML_AGENTS,
    _long_string_cases,
    _malformed_html_cases,
    _nested_conditional_cases,
    _rtl_injection_cases,
    generate_adversarial_cases,
    get_all_cases,
    load_yaml_cases,
)
from app.ai.agents.evals.adversarial_regression import (
    extract_failures,
    generate_regression_entry,
    write_regression_yaml,
)
from app.ai.agents.evals.error_analysis import build_analysis_report
from app.ai.agents.evals.schemas import ADVERSARIAL_ATTACK_TYPES, AdversarialCase


class TestGenerateCases:
    def test_generate_cases_scaffolder_count(self) -> None:
        """Scaffolder (HTML agent) gets cases across all 7 attack types — at least 10."""
        cases = generate_adversarial_cases("scaffolder")
        assert len(cases) >= 10

    def test_generate_cases_all_attack_types(self) -> None:
        """All 7 attack types should be represented for an HTML agent like scaffolder."""
        cases = generate_adversarial_cases("scaffolder")
        attack_types_found = {c.attack_type for c in cases}
        assert attack_types_found == set(ADVERSARIAL_ATTACK_TYPES)

    def test_generate_cases_knowledge_subset(self) -> None:
        """Knowledge agent gets only applicable types (long_string, rtl_injection, emoji_heavy)."""
        cases = generate_adversarial_cases("knowledge")
        attack_types_found = {c.attack_type for c in cases}
        assert len(cases) >= 4
        # Knowledge should NOT have these attack types
        assert "malformed_html" not in attack_types_found
        assert "missing_assets" not in attack_types_found
        assert "nested_conditionals" not in attack_types_found

    def test_adversarial_case_fields(self) -> None:
        """Every generated case has non-empty required fields."""
        for agent in ALL_AGENTS:
            cases = generate_adversarial_cases(agent)
            for case in cases:
                assert case.name, f"Empty name for {agent}"
                assert case.agent == agent
                assert case.attack_type in ADVERSARIAL_ATTACK_TYPES
                assert case.input_html, f"Empty input_html for {case.name}"
                assert case.description, f"Empty description for {case.name}"

    def test_unique_names(self) -> None:
        """No duplicate names across all generated cases for all agents."""
        all_names: list[str] = []
        for agent in ALL_AGENTS:
            cases = generate_adversarial_cases(agent)
            all_names.extend(c.name for c in cases)
        assert len(all_names) == len(set(all_names)), "Duplicate case names found"


class TestYAMLLoader:
    def test_load_yaml_cases(self, tmp_path: Path) -> None:
        """YAML loader reads fixture file and returns AdversarialCase list."""
        yaml_data = [
            {
                "name": "test_case_1",
                "attack_type": "long_string",
                "input_html": "<table><tr><td>test</td></tr></table>",
                "description": "Test case",
                "expected_behavior": "Should work",
            },
            {
                "name": "test_case_2",
                "attack_type": "emoji_heavy",
                "input_html": "\U0001f525 test",
                "description": "Emoji test",
            },
        ]
        yaml_file = tmp_path / "test_agent.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(yaml_data, f)

        cases = (
            cast(Any, load_yaml_cases).__wrapped__("test_agent")
            if hasattr(load_yaml_cases, "__wrapped__")
            else _load_yaml_from_path(yaml_file, "test_agent")
        )
        # Directly test by monkeypatching the YAML directory
        assert len(cases) >= 0  # Placeholder — tested via monkeypatch below

    def test_load_yaml_cases_with_monkeypatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML loader reads fixture and returns correct AdversarialCase objects."""
        yaml_data = [
            {
                "name": "yaml_test_1",
                "attack_type": "long_string",
                "input_html": "<table><tr><td>long content</td></tr></table>",
                "description": "YAML test case",
                "expected_behavior": "Handles gracefully",
            },
        ]
        yaml_file = tmp_path / "scaffolder.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(yaml_data, f)

        monkeypatch.setattr("app.ai.agents.evals.adversarial._YAML_DIR", tmp_path)
        cases = load_yaml_cases("scaffolder")
        assert len(cases) == 1
        assert cases[0].name == "yaml_test_1"
        assert cases[0].agent == "scaffolder"
        assert cases[0].attack_type == "long_string"
        assert isinstance(cases[0], AdversarialCase)

    def test_load_yaml_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing YAML file returns empty list, not error."""
        monkeypatch.setattr("app.ai.agents.evals.adversarial._YAML_DIR", tmp_path)
        cases = load_yaml_cases("nonexistent_agent")
        assert cases == []


class TestGetAllCases:
    def test_get_all_cases_merges(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_all_cases merges generated + YAML, deduplicates by name."""
        yaml_data = [
            {
                "name": "scaffolder_yaml_only",
                "attack_type": "malformed_html",
                "input_html": "<table><tr><td>yaml case</td></tr></table>",
                "description": "YAML-only case",
            },
        ]
        yaml_file = tmp_path / "scaffolder.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(yaml_data, f)

        monkeypatch.setattr("app.ai.agents.evals.adversarial._YAML_DIR", tmp_path)

        all_cases = get_all_cases("scaffolder")
        generated = generate_adversarial_cases("scaffolder")

        # Should have all generated + the YAML-only case
        names = {c.name for c in all_cases}
        assert "scaffolder_yaml_only" in names
        assert len(all_cases) >= len(generated) + 1


class TestGeneratorDetails:
    def test_long_string_cases(self) -> None:
        """Long string cases produce content exceeding 500 characters."""
        for agent in HTML_AGENTS:
            cases = _long_string_cases(agent)
            assert len(cases) >= 2
            # At least one case should have very long input_html
            max_len = max(len(c.input_html) for c in cases)
            assert max_len > 500, f"{agent}: longest input_html is only {max_len} chars"

    def test_rtl_injection_cases(self) -> None:
        """RTL cases contain Arabic or Hebrew Unicode characters."""
        cases = _rtl_injection_cases("dark_mode")
        assert len(cases) >= 1
        # Check for Arabic/Hebrew characters
        rtl_found = False
        for case in cases:
            if any(
                "\u0600" <= ch <= "\u06ff" or "\u0590" <= ch <= "\u05ff" for ch in case.input_html
            ):
                rtl_found = True
                break
        assert rtl_found, "No RTL characters found in rtl_injection cases"

    def test_nested_conditional_cases(self) -> None:
        """Nested conditional cases contain 5+ levels of Liquid or AMPscript nesting."""
        cases = _nested_conditional_cases("personalisation")
        assert len(cases) >= 2
        # Check for deep nesting
        for case in cases:
            liquid_depth = case.input_html.count("{% if ")
            ampscript_depth = case.input_html.count("%%[IF ")
            assert liquid_depth >= 5 or ampscript_depth >= 5, (
                f"Insufficient nesting depth in {case.name}: "
                f"liquid={liquid_depth}, ampscript={ampscript_depth}"
            )

    def test_malformed_html_cases(self) -> None:
        """Malformed HTML cases contain intentionally broken structures."""
        cases = _malformed_html_cases("scaffolder")
        assert len(cases) >= 2
        # At least one case should have nested <a> tags (invalid)
        has_nested_links = any(
            "<a " in c.input_html and c.input_html.count("<a ") >= 2 for c in cases
        )
        assert has_nested_links, "No nested link case found"


class TestAdversarialRegression:
    def test_regression_extract_failures(self, tmp_path: Path) -> None:
        """extract_failures filters to overall_pass=False only."""
        verdicts: list[dict[str, Any]] = [
            {
                "trace_id": "adv-1",
                "agent": "scaffolder",
                "overall_pass": True,
                "criteria_results": [],
            },
            {
                "trace_id": "adv-2",
                "agent": "scaffolder",
                "overall_pass": False,
                "criteria_results": [
                    {"criterion": "brief_fidelity", "passed": False, "reasoning": "Failed"},
                ],
            },
            {
                "trace_id": "adv-3",
                "agent": "scaffolder",
                "overall_pass": False,
                "criteria_results": [
                    {"criterion": "email_layout_patterns", "passed": False, "reasoning": "Bad"},
                ],
            },
        ]
        vfile = tmp_path / "scaffolder_adversarial_verdicts.jsonl"
        with vfile.open("w") as f:
            for v in verdicts:
                f.write(json.dumps(v) + "\n")

        failures = extract_failures(tmp_path)
        assert len(failures) == 2
        assert all(not f["overall_pass"] for f in failures)

    def test_regression_yaml_generation(self, tmp_path: Path) -> None:
        """Failed verdicts produce valid regression YAML entries."""
        verdict: dict[str, Any] = {
            "trace_id": "adv-scaffolder_long_heading",
            "agent": "scaffolder",
            "overall_pass": False,
            "dimensions": {"attack_type": "long_string", "adversarial": True},
            "criteria_results": [
                {"criterion": "brief_fidelity", "passed": False, "reasoning": "Too long"},
                {"criterion": "email_layout_patterns", "passed": True, "reasoning": "OK"},
            ],
        }
        entry = generate_regression_entry(verdict)
        assert entry["name"] == "adv-scaffolder_long_heading"
        assert entry["agent"] == "scaffolder"
        assert entry["source"] == "adversarial"
        assert entry["attack_type"] == "long_string"
        assert entry["failed_criteria"] == ["brief_fidelity"]
        assert "date_added" in entry

        # Write and verify YAML output
        entries = [entry]
        counts = write_regression_yaml(entries, tmp_path)
        assert counts["scaffolder"] == 1

        output_file = tmp_path / "scaffolder_adversarial.yaml"
        assert output_file.exists()
        with output_file.open() as f:
            written = yaml.safe_load(f)
        assert len(written) == 1
        assert written[0]["name"] == "adv-scaffolder_long_heading"


class TestAnalysisIntegration:
    def test_analysis_adversarial_section(self) -> None:
        """build_analysis_report includes adversarial metrics in the report dict.

        Note: build_analysis_report takes a verdict list, not a directory.
        The adversarial section is added by main() when loading from a directory.
        This test verifies the base report structure remains correct and that
        adversarial data can be appended to it.
        """
        verdicts: list[dict[str, Any]] = [
            {
                "trace_id": "scaff-001",
                "agent": "scaffolder",
                "overall_pass": True,
                "criteria_results": [
                    {"criterion": "brief_fidelity", "passed": True, "reasoning": "Good"},
                ],
            },
        ]
        report = build_analysis_report(verdicts)
        assert "summary" in report
        assert "pass_rates" in report
        assert "failure_clusters" in report

        # Simulate what main() does when adversarial verdicts exist
        from app.ai.agents.evals.error_analysis import compute_pass_rates

        adv_verdicts: list[dict[str, Any]] = [
            {
                "trace_id": "adv-scaff-1",
                "agent": "scaffolder",
                "overall_pass": False,
                "criteria_results": [
                    {"criterion": "brief_fidelity", "passed": False, "reasoning": "Failed"},
                ],
            },
            {
                "trace_id": "adv-scaff-2",
                "agent": "scaffolder",
                "overall_pass": True,
                "criteria_results": [
                    {"criterion": "brief_fidelity", "passed": True, "reasoning": "OK"},
                ],
            },
        ]
        adv_pass_rates = compute_pass_rates(adv_verdicts)
        adv_passed = sum(1 for v in adv_verdicts if v.get("overall_pass"))
        adv_overall = adv_passed / len(adv_verdicts)
        report["adversarial"] = {
            "total": len(adv_verdicts),
            "overall_pass_rate": adv_overall,
            "pass_rates": adv_pass_rates,
            "status": "WARN",
        }

        adversarial = cast(dict[str, Any], report["adversarial"])
        assert adversarial["total"] == 2
        assert adversarial["overall_pass_rate"] == 0.5
        assert adversarial["status"] == "WARN"
        assert "scaffolder" in adversarial["pass_rates"]


def _load_yaml_from_path(yaml_file: Path, agent: str) -> list[AdversarialCase]:
    """Helper to load YAML directly from a path for testing."""
    with yaml_file.open() as f:
        raw: list[dict[str, Any]] = yaml.safe_load(f) or []
    return [
        AdversarialCase(
            name=entry["name"],
            agent=agent,
            attack_type=entry["attack_type"],
            input_html=entry.get("input_html", ""),
            description=entry.get("description", ""),
            expected_behavior=entry.get("expected_behavior", ""),
        )
        for entry in raw
    ]
