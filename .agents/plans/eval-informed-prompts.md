# Plan: 7.2 Eval-Informed Agent Prompts — COMPLETE (2026-03-09)

## Context

Agent eval data shows recurring failure patterns (e.g., scaffolder MSO conditionals at 58%, dark mode meta tags at 50%). This data currently sits in `traces/analysis.json` but doesn't feed back into agent prompts. Task 7.2 closes the feedback loop: read failure clusters from error analysis, generate per-agent warning fragments, and inject them into system prompts at runtime.

**Key design constraint:** All 9 agents already have a uniform `build_system_prompt(relevant_skills) -> str` function in their `prompt.py`. The injection point is inside this function — after L1+L2 SKILL.md content, before L3 reference files.

## Files to Create

- `app/ai/agents/evals/failure_warnings.py` — Core module: loads analysis.json, filters per agent, formats prompt fragments
- `app/ai/agents/evals/tests/test_failure_warnings.py` — Unit tests

## Files to Modify

- `app/ai/agents/scaffolder/prompt.py` — Inject failure warnings into `build_system_prompt()`
- `app/ai/agents/dark_mode/prompt.py` — Same
- `app/ai/agents/content/prompt.py` — Same
- `app/ai/agents/outlook_fixer/prompt.py` — Same
- `app/ai/agents/accessibility/prompt.py` — Same
- `app/ai/agents/personalisation/prompt.py` — Same
- `app/ai/agents/code_reviewer/prompt.py` — Same
- `app/ai/agents/knowledge/prompt.py` — Same
- `app/ai/agents/innovation/prompt.py` — Same

## Implementation Steps

### Step 1: Create `app/ai/agents/evals/failure_warnings.py`

This module reads `traces/analysis.json` (output of `make eval-analysis`) and generates per-agent prompt fragments highlighting failure patterns.

```python
"""Generate agent prompt fragments from eval failure analysis.

Reads traces/analysis.json (output of `make eval-analysis`) and produces
per-agent warning text that gets injected into system prompts. This closes
the eval → prompt feedback loop described in TODO.md task 7.2.

Usage in agent prompt.py:
    from app.ai.agents.evals.failure_warnings import get_failure_warnings
    warnings = get_failure_warnings("scaffolder")
    if warnings:
        parts.append(warnings)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default analysis file location (output of `make eval-analysis`)
_DEFAULT_ANALYSIS_PATH = Path("traces/analysis.json")

# Cache: (mtime, agent_name) -> formatted warnings
_cache: dict[tuple[float, str], str | None] = {}
_cached_mtime: float = 0.0
_cached_data: dict[str, Any] | None = None

# Only include failure clusters where pass rate is below this threshold
_PASS_RATE_THRESHOLD = 0.85

# Maximum number of failure warnings per agent (avoid prompt bloat)
_MAX_WARNINGS_PER_AGENT = 5


def _load_analysis(path: Path) -> dict[str, Any] | None:
    """Load analysis.json, returning None if missing or invalid."""
    global _cached_mtime, _cached_data  # noqa: PLW0603

    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    if mtime == _cached_mtime and _cached_data is not None:
        return _cached_data

    try:
        with path.open() as f:
            data = json.load(f)
        _cached_mtime = mtime
        _cached_data = data
        _cache.clear()  # Invalidate per-agent cache on new data
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("evals.failure_warnings.load_failed", error=str(exc))
        return None


def _format_criterion_name(criterion: str) -> str:
    """Convert snake_case criterion to readable title.

    Examples:
        mso_conditional_correctness -> MSO Conditional Correctness
        html_preservation -> HTML Preservation
        alt_text_quality -> Alt Text Quality
    """
    words = criterion.split("_")
    # Uppercase known abbreviations
    abbreviations = {"mso", "html", "css", "vml", "wcag", "aa", "cta", "rag", "amp"}
    return " ".join(
        w.upper() if w.lower() in abbreviations else w.capitalize()
        for w in words
    )


def _build_warnings_for_agent(
    agent: str,
    pass_rates: dict[str, dict[str, float]],
    failure_clusters: list[dict[str, Any]],
) -> str | None:
    """Build formatted warning text for a single agent.

    Args:
        agent: Agent name (e.g., "scaffolder").
        pass_rates: Per-agent per-criterion pass rates from analysis.json.
        failure_clusters: All failure clusters from analysis.json.

    Returns:
        Formatted warning text, or None if no actionable warnings.
    """
    agent_rates = pass_rates.get(agent, {})
    if not agent_rates:
        return None

    # Filter to criteria below threshold, sorted by pass rate ascending (worst first)
    weak_criteria = sorted(
        [(criterion, rate) for criterion, rate in agent_rates.items() if rate < _PASS_RATE_THRESHOLD],
        key=lambda x: x[1],
    )

    if not weak_criteria:
        return None

    # Build a lookup of failure clusters for this agent
    cluster_lookup: dict[str, dict[str, Any]] = {}
    for cluster in failure_clusters:
        if cluster["agent"] == agent:
            cluster_lookup[cluster["criterion"]] = cluster

    lines: list[str] = [
        "## KNOWN FAILURE PATTERNS (from recent evaluations)",
        "",
        "The following quality criteria have low pass rates in recent eval runs.",
        "Pay extra attention to these areas:",
        "",
    ]

    for criterion, rate in weak_criteria[:_MAX_WARNINGS_PER_AGENT]:
        pct = f"{rate:.0%}"
        name = _format_criterion_name(criterion)
        cluster = cluster_lookup.get(criterion)
        count = cluster["count"] if cluster else 0

        lines.append(f"**{name} ({pct} pass rate, {count} failures):**")

        # Add sample reasonings as actionable hints if available
        if cluster and cluster.get("sample_reasonings"):
            for reasoning in cluster["sample_reasonings"][:2]:
                # Clean up mock prefixes from dry-run data
                cleaned = reasoning
                if cleaned.startswith("Fail: mock evaluation of"):
                    cleaned = f"Check {_format_criterion_name(criterion).lower()} thoroughly"
                lines.append(f"- {cleaned}")
        else:
            lines.append(f"- Review {criterion.replace('_', ' ')} carefully before finalising output")

        lines.append("")

    return "\n".join(lines)


def get_failure_warnings(
    agent: str,
    analysis_path: Path | None = None,
) -> str | None:
    """Get formatted failure warning text for an agent's system prompt.

    Reads the latest analysis.json (cached by mtime) and returns a formatted
    prompt fragment highlighting the agent's weakest eval criteria. Returns
    None if no analysis file exists or the agent has no failures below threshold.

    Args:
        agent: Agent name (e.g., "scaffolder", "dark_mode").
        analysis_path: Override path to analysis.json (for testing).

    Returns:
        Formatted warning text to append to system prompt, or None.
    """
    path = analysis_path or _DEFAULT_ANALYSIS_PATH
    data = _load_analysis(path)
    if data is None:
        return None

    # Check per-agent cache
    mtime = _cached_mtime
    cache_key = (mtime, agent)
    if cache_key in _cache:
        return _cache[cache_key]

    pass_rates = data.get("pass_rates", {})
    failure_clusters = data.get("failure_clusters", [])

    result = _build_warnings_for_agent(agent, pass_rates, failure_clusters)
    _cache[cache_key] = result

    if result:
        logger.info(
            "evals.failure_warnings.loaded",
            agent=agent,
            warning_count=result.count("**"),
        )

    return result


def clear_cache() -> None:
    """Clear the analysis cache. Useful for testing."""
    global _cached_mtime, _cached_data  # noqa: PLW0603
    _cache.clear()
    _cached_mtime = 0.0
    _cached_data = None
```

### Step 2: Create `app/ai/agents/evals/tests/test_failure_warnings.py`

```python
"""Tests for eval-informed failure warnings module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.ai.agents.evals.failure_warnings import (
    _build_warnings_for_agent,
    _format_criterion_name,
    clear_cache,
    get_failure_warnings,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear module-level cache before each test."""
    clear_cache()


def _make_analysis(
    pass_rates: dict[str, dict[str, float]] | None = None,
    failure_clusters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal analysis.json structure."""
    return {
        "summary": {"total_traces": 10, "passed": 5, "failed": 5, "errors": 0, "overall_pass_rate": 0.5},
        "pass_rates": pass_rates or {},
        "failure_clusters": failure_clusters or [],
        "top_failures": [],
    }


class TestFormatCriterionName:
    def test_simple(self) -> None:
        assert _format_criterion_name("brief_fidelity") == "Brief Fidelity"

    def test_abbreviations(self) -> None:
        assert _format_criterion_name("mso_conditional_correctness") == "MSO Conditional Correctness"
        assert _format_criterion_name("html_preservation") == "HTML Preservation"
        assert _format_criterion_name("css_support") == "CSS Support"
        assert _format_criterion_name("vml_wellformedness") == "VML Wellformedness"

    def test_single_word(self) -> None:
        assert _format_criterion_name("grammar") == "Grammar"


class TestBuildWarningsForAgent:
    def test_no_rates_returns_none(self) -> None:
        assert _build_warnings_for_agent("scaffolder", {}, []) is None

    def test_all_above_threshold_returns_none(self) -> None:
        rates = {"scaffolder": {"brief_fidelity": 0.9, "code_quality": 0.95}}
        assert _build_warnings_for_agent("scaffolder", rates, []) is None

    def test_below_threshold_included(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5, "brief_fidelity": 0.9}}
        clusters = [
            {
                "agent": "scaffolder",
                "criterion": "mso_conditionals",
                "count": 5,
                "sample_reasonings": ["Missing <!--[if mso]> wrappers"],
            },
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "MSO Conditionals" in result
        assert "50%" in result
        assert "5 failures" in result
        assert "Missing <!--[if mso]> wrappers" in result

    def test_sorted_worst_first(self) -> None:
        rates = {"scaffolder": {"criterion_a": 0.3, "criterion_b": 0.6}}
        result = _build_warnings_for_agent("scaffolder", rates, [])
        assert result is not None
        # criterion_a (30%) should appear before criterion_b (60%)
        idx_a = result.index("Criterion A")
        idx_b = result.index("Criterion B")
        assert idx_a < idx_b

    def test_max_warnings_cap(self) -> None:
        rates = {"scaffolder": {f"criterion_{i}": 0.1 * i for i in range(8)}}
        result = _build_warnings_for_agent("scaffolder", rates, [])
        assert result is not None
        # Should cap at 5 warnings
        assert result.count("pass rate") == 5

    def test_other_agent_clusters_excluded(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5}}
        clusters = [
            {"agent": "dark_mode", "criterion": "meta_tags", "count": 5, "sample_reasonings": ["Missing meta"]},
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "meta_tags" not in result.lower()

    def test_mock_reasoning_cleaned(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5}}
        clusters = [
            {
                "agent": "scaffolder",
                "criterion": "mso_conditionals",
                "count": 3,
                "sample_reasonings": ["Fail: mock evaluation of mso_conditionals for scaff-001"],
            },
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "mock evaluation" not in result


class TestGetFailureWarnings:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        result = get_failure_warnings("scaffolder", analysis_path=tmp_path / "nonexistent.json")
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "analysis.json"
        bad_file.write_text("not json{{{")
        result = get_failure_warnings("scaffolder", analysis_path=bad_file)
        assert result is None

    def test_loads_real_format(self, tmp_path: Path) -> None:
        analysis = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.58, "brief_fidelity": 0.83}},
            failure_clusters=[
                {
                    "cluster_id": "scaffolder:mso_conditionals",
                    "agent": "scaffolder",
                    "criterion": "mso_conditionals",
                    "pattern": "Missing MSO conditional comments",
                    "count": 5,
                    "trace_ids": ["s1", "s2", "s3", "s4", "s5"],
                    "sample_reasonings": ["MSO wrappers missing around table elements"],
                },
            ],
        )
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result is not None
        assert "MSO Conditionals" in result
        assert "58%" in result

    def test_caching_by_mtime(self, tmp_path: Path) -> None:
        analysis = _make_analysis(pass_rates={"scaffolder": {"criterion_a": 0.5}})
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result1 = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        result2 = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result1 == result2  # Same object from cache

    def test_unknown_agent_returns_none(self, tmp_path: Path) -> None:
        analysis = _make_analysis(pass_rates={"scaffolder": {"criterion_a": 0.5}})
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("nonexistent_agent", analysis_path=analysis_file)
        assert result is None

    def test_agent_all_passing_returns_none(self, tmp_path: Path) -> None:
        analysis = _make_analysis(pass_rates={"scaffolder": {"brief_fidelity": 0.95, "code_quality": 0.90}})
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result is None
```

### Step 3: Integrate into all 9 agent `prompt.py` files

The integration follows the same pattern for all agents. Add the failure warnings call inside `build_system_prompt()`, after the base prompt and before L3 skill references.

**Pattern A — Agents using string concatenation (scaffolder, dark_mode):**

In `app/ai/agents/scaffolder/prompt.py`, modify `build_system_prompt()`:

```python
# Add import at top of file
from app.ai.agents.evals.failure_warnings import get_failure_warnings

def build_system_prompt(relevant_skills: list[str]) -> str:
    parts = [SCAFFOLDER_SYSTEM_PROMPT]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("scaffolder")
    if failure_warnings:
        parts.append(f"\n\n{failure_warnings}")

    for skill_key in relevant_skills:
        # ... existing L3 loading unchanged ...
```

**Pattern B — Agents using string concatenation with += (knowledge, innovation):**

In `app/ai/agents/knowledge/prompt.py`, modify `build_system_prompt()`:

```python
from app.ai.agents.evals.failure_warnings import get_failure_warnings

def build_system_prompt(relevant_skills: list[str]) -> str:
    skill_path = _AGENT_DIR / "SKILL.md"
    base_prompt = skill_path.read_text()

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("knowledge")
    if failure_warnings:
        base_prompt += f"\n\n{failure_warnings}"

    for skill_name in relevant_skills:
        # ... existing L3 loading unchanged ...
```

**All 9 agents get the same treatment:**

| Agent | File | Function | Agent name string |
|-------|------|----------|-------------------|
| Scaffolder | `app/ai/agents/scaffolder/prompt.py` | `build_system_prompt()` | `"scaffolder"` |
| Dark Mode | `app/ai/agents/dark_mode/prompt.py` | `build_system_prompt()` | `"dark_mode"` |
| Content | `app/ai/agents/content/prompt.py` | `build_system_prompt()` | `"content"` |
| Outlook Fixer | `app/ai/agents/outlook_fixer/prompt.py` | `build_system_prompt()` | `"outlook_fixer"` |
| Accessibility | `app/ai/agents/accessibility/prompt.py` | `build_system_prompt()` | `"accessibility"` |
| Personalisation | `app/ai/agents/personalisation/prompt.py` | `build_system_prompt()` | `"personalisation"` |
| Code Reviewer | `app/ai/agents/code_reviewer/prompt.py` | `build_system_prompt()` | `"code_reviewer"` |
| Knowledge | `app/ai/agents/knowledge/prompt.py` | `build_system_prompt()` | `"knowledge"` |
| Innovation | `app/ai/agents/innovation/prompt.py` | `build_system_prompt()` | `"innovation"` |

### Step 4: Verify with `make check`

Run full quality checks to ensure:
- Type annotations pass mypy + pyright
- Ruff lint passes
- All existing tests pass (544+)
- New tests pass (13+ new tests)
- Security check passes

## Design Decisions

1. **File-based, not DB-based:** Reads `traces/analysis.json` directly. No new database tables, migrations, or API endpoints. Analysis file is generated by `make eval-analysis` which already exists.

2. **Mtime-based caching:** Avoids re-reading the JSON on every agent call. Cache invalidates automatically when the analysis file is updated (after a new `make eval-analysis` run).

3. **Graceful degradation:** If `traces/analysis.json` doesn't exist (fresh clone, CI, no evals run yet), `get_failure_warnings()` returns `None` and the agent prompt is unchanged. Zero impact on existing functionality.

4. **Threshold filtering (< 85%):** Only criteria with pass rates below 85% generate warnings. Agents with all criteria above threshold get no warnings — avoids noise.

5. **Max 5 warnings per agent:** Prevents prompt bloat. Sorted worst-first so the most impactful warnings always appear.

6. **Mock reasoning cleanup:** Current analysis.json has mock dry-run reasonings (`"Fail: mock evaluation of..."`). The formatter detects and replaces these with generic actionable guidance.

7. **Injection point — after L2, before L3:** Failure warnings appear between the core SKILL.md instructions and the on-demand skill reference files. This ensures warnings are always visible but don't interfere with skill content.

## Security Checklist

No new endpoints, routes, or API surface. This is an internal prompt-engineering feature.

- [x] No new routes (no auth/rate-limit needed)
- [x] No user input flows into failure warnings (data comes from eval analysis only)
- [x] No secrets/credentials in analysis data or generated prompt fragments
- [x] Failure patterns contain no user data (only aggregated error categories)
- [x] Analysis file path is hardcoded default, not user-controllable
- [x] Error responses use structured logging, no class name leakage

## Verification

- [x] `make check` passes (lint, types, tests, security) — 560 tests pass
- [x] New unit tests cover: missing file, invalid JSON, cache behavior, threshold filtering, per-agent isolation, mock cleanup, max warnings cap, abbreviation formatting (16 tests)
- [x] With `traces/analysis.json` present: agent prompts include failure warnings for criteria below 85%
- [x] Without `traces/analysis.json`: agent prompts are unchanged (graceful degradation)
- [x] After `make eval-analysis` updates the file: next agent call picks up new data (mtime cache invalidation)
