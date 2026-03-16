"""Auto-surface SKILL.md amendment suggestions from eval failure clusters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_ANALYSIS_PATH = Path("traces/analysis.json")
_DEFAULT_SUGGESTIONS_DIR = Path("traces/suggestions")
_SKILL_BASE = Path("app/ai/agents")

# Minimum failures in a cluster to trigger a suggestion
_MIN_CLUSTER_SIZE = 3


def _load_analysis(path: Path) -> dict[str, Any] | None:
    """Load analysis.json, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        logger.warning("amendment_suggester.load_failed", path=str(path))
        return None


def _load_skill_md(agent: str) -> str | None:
    """Load SKILL.md for an agent, return None if not found."""
    path = _SKILL_BASE / agent / "SKILL.md"
    if not path.exists():
        return None
    return path.read_text()


def _filter_actionable_clusters(
    clusters: list[dict[str, Any]],
    min_size: int = _MIN_CLUSTER_SIZE,
) -> dict[str, list[dict[str, Any]]]:
    """Group clusters by agent, keeping only those with >= min_size failures."""
    by_agent: dict[str, list[dict[str, Any]]] = {}
    for cluster in clusters:
        if cluster.get("count", 0) >= min_size:
            agent = cluster["agent"]
            by_agent.setdefault(agent, []).append(cluster)
    return by_agent


def _build_suggestion_prompt(
    agent: str,
    skill_md: str,
    clusters: list[dict[str, Any]],
) -> str:
    """Build the LLM prompt for generating a SKILL.md amendment suggestion."""
    cluster_text = ""
    for c in clusters:
        cluster_text += f"\n### {c['criterion']} ({c['count']} failures)\n"
        cluster_text += f"Pattern: {c.get('pattern', 'unknown')}\n"
        for i, reasoning in enumerate(c.get("sample_reasonings", [])[:3], 1):
            cluster_text += f"  Example {i}: {reasoning}\n"

    return f"""You are an expert email development AI engineer reviewing evaluation results for the "{agent}" agent.

## Task
Analyze the recurring failure patterns below and suggest specific amendments to the agent's SKILL.md file that would address these failures. The amendments should be concrete, actionable instructions that the agent can follow to avoid these failure patterns.

## Current SKILL.md
```
{skill_md}
```

## Recurring Failure Patterns
{cluster_text}

## Output Format
Respond with EXACTLY this structure (no extra text before or after):

### Failure Analysis
For each failure pattern, explain WHY the agent is failing and what knowledge gap the SKILL.md has.

### Suggested SKILL.md Amendments
Provide the exact text to ADD to the SKILL.md file. Format as markdown that can be appended to the existing file. Each amendment should:
1. Be a clear, specific instruction (not vague guidance)
2. Include concrete examples where helpful
3. Reference the failure pattern it addresses

### Confidence
Rate your confidence that these amendments would reduce the failure rate: HIGH / MEDIUM / LOW
Explain your rating in one sentence."""


def _format_suggestion_file(
    agent: str,
    clusters: list[dict[str, Any]],
    llm_response: str,
    date_str: str,
) -> str:
    """Format the final suggestion markdown file."""
    lines = [
        f"# SKILL.md Amendment Suggestions: {agent}",
        f"Generated: {date_str}",
        "",
        "---",
        "",
        "## Failure Clusters Addressed",
        "",
    ]
    for c in clusters:
        lines.append(
            f"- **{c['criterion']}**: {c['count']} failures — {c.get('pattern', 'unknown')}"
        )
    lines.extend(
        [
            "",
            "---",
            "",
            llm_response,
            "",
            "---",
            "",
            f"*Target file: `app/ai/agents/{agent}/SKILL.md`*",
            "*Review and apply manually. Do NOT auto-merge.*",
        ]
    )
    return "\n".join(lines)


async def generate_suggestions(
    analysis_path: Path | None = None,
    output_dir: Path | None = None,
    min_cluster_size: int = _MIN_CLUSTER_SIZE,
) -> list[Path]:
    """Generate SKILL.md amendment suggestions from eval failure clusters.

    Returns list of suggestion file paths written.
    """
    analysis_path = analysis_path or _DEFAULT_ANALYSIS_PATH
    output_dir = output_dir or _DEFAULT_SUGGESTIONS_DIR

    analysis = _load_analysis(analysis_path)
    if analysis is None:
        logger.warning("amendment_suggester.no_analysis", path=str(analysis_path))
        return []

    clusters = analysis.get("failure_clusters", [])
    actionable = _filter_actionable_clusters(clusters, min_cluster_size)

    if not actionable:
        logger.info("amendment_suggester.no_actionable_clusters")
        return []

    settings = get_settings()
    registry = get_registry()
    provider = registry.get_llm(settings.ai.provider)
    model = resolve_model("complex")

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    written: list[Path] = []

    for agent, agent_clusters in sorted(actionable.items()):
        skill_md = _load_skill_md(agent)
        if skill_md is None:
            logger.warning("amendment_suggester.skill_not_found", agent=agent)
            continue

        prompt = _build_suggestion_prompt(agent, skill_md, agent_clusters)

        try:
            response: CompletionResponse = await provider.complete(
                [Message(role="user", content=prompt)],
                temperature=0.3,
                model=model,
            )
            llm_output = response.content
        except Exception:
            logger.warning(
                "amendment_suggester.llm_failed",
                agent=agent,
                exc_info=True,
            )
            continue

        suggestion = _format_suggestion_file(agent, agent_clusters, llm_output, date_str)
        out_path = output_dir / f"{agent}_{date_str}.md"
        out_path.write_text(suggestion)
        written.append(out_path)

        total_failures = sum(c["count"] for c in agent_clusters)
        logger.info(
            "amendment_suggester.suggestion_written",
            agent=agent,
            clusters=len(agent_clusters),
            total_failures=total_failures,
            path=str(out_path),
        )

    logger.info(
        "amendment_suggester.complete",
        suggestions_written=len(written),
        agents_processed=len(actionable),
    )
    return written


async def main() -> None:
    """CLI entry point for amendment suggester."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate SKILL.md amendment suggestions from eval failures"
    )
    parser.add_argument(
        "--analysis",
        default="traces/analysis.json",
        help="Path to analysis.json",
    )
    parser.add_argument(
        "--output",
        default="traces/suggestions",
        help="Output directory for suggestion files",
    )
    parser.add_argument(
        "--min-failures",
        type=int,
        default=_MIN_CLUSTER_SIZE,
        help="Minimum cluster size to trigger suggestion (default: 3)",
    )
    args = parser.parse_args()

    written = await generate_suggestions(
        analysis_path=Path(args.analysis),
        output_dir=Path(args.output),
        min_cluster_size=args.min_failures,
    )

    if written:
        print(f"\n✓ Generated {len(written)} suggestion(s):")
        for p in written:
            print(f"  → {p}")
    else:
        print("\nNo actionable failure clusters found (need 3+ failures per cluster).")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
