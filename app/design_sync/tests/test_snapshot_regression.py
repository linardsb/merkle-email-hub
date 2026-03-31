"""Snapshot regression tests for design-to-HTML conversion.

Loads real design inputs (structure.json + tokens.json) from data/debug/{case}/,
runs the full converter pipeline, and compares output against visually verified
expected.html files.

This is the ground truth — every converter fix must pass all snapshot cases.

To add a new case:
    1. Capture design data:  python -m app.design_sync.diagnose.extract --connection-id <N>
    2. Generate current output:  python scripts/snapshot-capture.py <case_id>
    3. Open data/debug/<case_id>/expected.html in a browser, verify visually
    4. Add the case to data/debug/manifest.yaml with status: active
    5. Run:  make snapshot-test
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.design_sync.converter_service import ConversionResult, DesignConverterService
from app.design_sync.diagnose.report import load_structure_from_json, load_tokens_from_json

_DEBUG_DIR = Path(__file__).resolve().parents[3] / "data" / "debug"
_MANIFEST = _DEBUG_DIR / "manifest.yaml"


def _load_manifest() -> list[dict[str, Any]]:
    """Load active snapshot cases from manifest."""
    if not _MANIFEST.exists():
        return []
    data = yaml.safe_load(_MANIFEST.read_text())
    cases: list[dict[str, Any]] = data.get("cases", [])
    return [c for c in cases if c.get("status") == "active"]


def _get_active_case_ids() -> list[str]:
    """Return case IDs for parametrize."""
    return [c["id"] for c in _load_manifest()]


def _normalize_html(html: str) -> str:
    """Normalize HTML for comparison.

    - Collapse whitespace runs to single space
    - Strip leading/trailing whitespace per line
    - Remove blank lines
    - Normalize self-closing tags

    This allows the snapshot to survive whitespace-only reformatting
    while catching any real content/structure changes.
    """
    # Collapse runs of whitespace (including newlines) to single space
    html = re.sub(r"\s+", " ", html)
    # Normalize self-closing tags: <br /> → <br>
    html = re.sub(r"\s*/>", ">", html)
    # Split on > to get roughly one tag per line for readable diffs
    parts = html.split(">")
    lines = [p.strip() + ">" for p in parts if p.strip()]
    return "\n".join(lines)


def _html_diff(expected: str, actual: str) -> str:
    """Generate a readable unified diff between normalized HTML."""
    expected_lines = _normalize_html(expected).splitlines(keepends=True)
    actual_lines = _normalize_html(actual).splitlines(keepends=True)
    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile="expected.html",
        tofile="actual.html",
        n=3,
    )
    return "".join(list(diff)[:100])  # Cap at 100 lines for readability


def _run_conversion(case_dir: Path) -> ConversionResult:
    """Load real inputs and run the full converter pipeline."""
    structure = load_structure_from_json(case_dir / "structure.json")
    tokens = load_tokens_from_json(case_dir / "tokens.json")
    converter = DesignConverterService()
    return converter.convert(structure, tokens)


# ── Snapshot tests ────────────────────────────────────────────────


class TestSnapshotRegression:
    """Each active case in manifest.yaml must produce output matching expected.html."""

    @pytest.mark.parametrize("case_id", _get_active_case_ids())
    def test_snapshot_matches(self, case_id: str) -> None:
        case_dir = _DEBUG_DIR / case_id

        expected_path = case_dir / "expected.html"
        assert expected_path.exists(), (
            f"Missing expected.html for case {case_id}. "
            f"Run: python scripts/snapshot-capture.py {case_id}"
        )

        expected_html = expected_path.read_text()
        assert "PLACEHOLDER" not in expected_html, (
            f"expected.html for case {case_id} still has placeholder content. "
            f"Run: python scripts/snapshot-capture.py {case_id} "
            f"then verify visually and remove the placeholder comment."
        )

        result = _run_conversion(case_dir)

        assert result.html, f"Converter produced empty HTML for case {case_id}"
        assert result.sections_count > 0, f"Converter found 0 sections for case {case_id}"

        expected_norm = _normalize_html(expected_html)
        actual_norm = _normalize_html(result.html)

        if expected_norm != actual_norm:
            diff = _html_diff(expected_html, result.html)
            # Also save the actual output for easy comparison
            actual_path = case_dir / "actual.html"
            actual_path.write_text(result.html)
            pytest.fail(
                f"Snapshot mismatch for case {case_id}.\n"
                f"Actual output saved to: {actual_path}\n"
                f"Open both files in a browser to compare visually.\n\n"
                f"If the new output is correct, update expected.html:\n"
                f"  cp {actual_path} {expected_path}\n\n"
                f"Diff (first 100 lines):\n{diff}"
            )


class TestSnapshotSanity:
    """Basic sanity checks on all cases (including pending)."""

    @pytest.mark.parametrize(
        "case_id",
        [
            c["id"]
            for c in (yaml.safe_load((_DEBUG_DIR / "manifest.yaml").read_text()) or {}).get(
                "cases", []
            )
        ],
    )
    def test_case_loads(self, case_id: str) -> None:
        """Every case in the manifest must have loadable structure + tokens."""
        case_dir = _DEBUG_DIR / case_id
        assert (case_dir / "structure.json").exists(), f"Missing structure.json for case {case_id}"
        assert (case_dir / "tokens.json").exists(), f"Missing tokens.json for case {case_id}"

        structure = load_structure_from_json(case_dir / "structure.json")
        load_tokens_from_json(case_dir / "tokens.json")

        assert len(structure.pages) > 0, f"Empty pages in case {case_id}"
        assert structure.file_name, f"Empty file_name in case {case_id}"


class TestSnapshotSectionCount:
    """Section count must match manifest expectation (catches layout analysis regressions)."""

    @pytest.mark.parametrize("case_id", _get_active_case_ids())
    def test_section_count(self, case_id: str) -> None:
        cases = {c["id"]: c for c in _load_manifest()}
        case = cases[case_id]
        expected_sections = case.get("sections")
        if expected_sections is None:
            pytest.skip("No expected section count in manifest")

        case_dir = _DEBUG_DIR / case_id
        result = _run_conversion(case_dir)
        assert result.sections_count == expected_sections, (
            f"Case {case_id}: expected {expected_sections} sections, got {result.sections_count}"
        )
