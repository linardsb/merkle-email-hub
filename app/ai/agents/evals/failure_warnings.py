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
    global _cached_mtime, _cached_data

    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    if mtime == _cached_mtime and _cached_data is not None:
        return _cached_data

    try:
        with path.open() as f:
            data: dict[str, Any] = json.load(f)
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
    return " ".join(w.upper() if w.lower() in abbreviations else w.capitalize() for w in words)


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
        [
            (criterion, rate)
            for criterion, rate in agent_rates.items()
            if rate < _PASS_RATE_THRESHOLD
        ],
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
        matched = cluster_lookup.get(criterion)
        count = matched["count"] if matched else 0

        lines.append(f"**{name} ({pct} pass rate, {count} failures):**")

        # Add sample reasonings as actionable hints if available
        if matched and matched.get("sample_reasonings"):
            for reasoning in matched["sample_reasonings"][:2]:
                # Clean up mock prefixes from dry-run data
                cleaned = reasoning
                if cleaned.startswith("Fail: mock evaluation of"):
                    cleaned = f"Check {_format_criterion_name(criterion).lower()} thoroughly"
                lines.append(f"- {cleaned}")
        else:
            lines.append(
                f"- Review {criterion.replace('_', ' ')} carefully before finalising output"
            )

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

    pass_rates: dict[str, dict[str, float]] = data.get("pass_rates", {})
    failure_clusters: list[dict[str, Any]] = data.get("failure_clusters", [])

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
    global _cached_mtime, _cached_data
    _cache.clear()
    _cached_mtime = 0.0
    _cached_data = None
