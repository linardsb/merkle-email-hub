"""Eval-driven skill file update detector and patch generator.

Monitors agent eval pass rates from analysis.json, detects persistent failure
patterns, generates proposed L3 skill file patches via LLM, and creates git
branches for human review.

CLI: python scripts/eval-skill-update.py [--dry-run] [--threshold 0.80]
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.core.config import get_settings
from app.core.logging import get_logger

from .schemas import SkillFilePatch, SkillUpdateCandidate

logger = get_logger(__name__)

_DEFAULT_ANALYSIS_PATH = Path("traces/analysis.json")
_DEFAULT_TOOL_USAGE_PATH = Path("traces/tool_usage.jsonl")
_SKILL_BASE = Path("app/ai/agents")

SKILL_UPDATE_THRESHOLD = 0.80
MIN_FAILURE_COUNT = 5
TOOL_USAGE_PROMOTION_THRESHOLD = 10

# Maps agent → criterion → L3 skill filename.
# Falls back to SKILL.md if criterion not mapped.
CRITERION_SKILL_MAP: dict[str, dict[str, str]] = {
    "scaffolder": {
        "brief_fidelity": "email_structure.md",
        "email_layout": "table_layouts.md",
        "mso_conditionals": "mso_vml_quick_ref.md",
        "table_structure": "table_layouts.md",
        "code_quality": "css_email_reference.md",
    },
    "dark_mode": {
        "color_coherence": "color_remapping.md",
        "html_preservation": "dom_rendering_reference.md",
        "outlook_selectors": "outlook_dark_mode.md",
        "media_query": "client_behavior.md",
        "meta_tags": "meta_tag_injection.md",
    },
    "content": {
        "copy_quality": "brand_voice.md",
        "tone_match": "brand_voice.md",
        "spam_avoidance": "spam_triggers.md",
        "length_appropriate": "operation_best_practices.md",
        "grammar": "operation_best_practices.md",
    },
    "outlook_fixer": {
        "mso_conditional_correctness": "mso_conditionals.md",
        "vml_wellformedness": "vml_reference.md",
        "html_preservation": "diagnostic.md",
        "fix_completeness": "mso_bug_fixes.md",
        "outlook_version_targeting": "mso_conditionals.md",
    },
    "accessibility": {
        "wcag_aa_compliance": "wcag_email_mapping.md",
        "alt_text_quality": "alt_text_guidelines.md",
        "contrast_ratio_accuracy": "color_contrast.md",
        "semantic_structure": "wcag_email_mapping.md",
        "screen_reader_compatibility": "screen_reader_behavior.md",
    },
    "personalisation": {
        "syntax_correctness": "braze_liquid.md",
        "fallback_completeness": "fallback_patterns.md",
        "html_preservation": "fallback_patterns.md",
        "platform_accuracy": "sfmc_ampscript.md",
        "logic_match": "braze_liquid.md",
    },
    "code_reviewer": {
        "issue_genuineness": "anti_patterns.md",
        "suggestion_actionability": "quality_checklist.md",
        "severity_accuracy": "css_client_support.md",
        "coverage_completeness": "quality_checklist.md",
        "output_format": "quality_checklist.md",
    },
    "knowledge": {
        "answer_accuracy": "rag_strategies.md",
        "citation_grounding": "citation_rules.md",
        "code_example_quality": "can_i_email_reference.md",
        "source_relevance": "rag_strategies.md",
        "completeness": "rag_strategies.md",
    },
    "innovation": {
        "technique_correctness": "css_checkbox_hacks.md",
        "fallback_quality": "feasibility_framework.md",
        "client_coverage_accuracy": "feasibility_framework.md",
        "feasibility_assessment": "feasibility_framework.md",
        "innovation_value": "competitive_landscape.md",
    },
}


def _load_analysis(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        logger.warning("skill_updater.load_failed", path=str(path))
        return None


def _resolve_skill_file(agent: str, criterion: str) -> str:
    """Resolve criterion to L3 skill file path, falling back to SKILL.md."""
    agent_map = CRITERION_SKILL_MAP.get(agent, {})
    filename = agent_map.get(criterion)
    if filename:
        return str(_SKILL_BASE / agent / "skills" / filename)
    return str(_SKILL_BASE / agent / "SKILL.md")


def _load_skill_content(skill_file_path: str) -> str | None:
    path = Path(skill_file_path)
    if not path.exists():
        return None
    return path.read_text()


class SkillUpdateDetector:
    """Detects skill update opportunities from eval analysis data."""

    def __init__(
        self,
        analysis_path: Path | None = None,
        tool_usage_path: Path | None = None,
        threshold: float = SKILL_UPDATE_THRESHOLD,
        min_failures: int = MIN_FAILURE_COUNT,
    ) -> None:
        self._analysis_path = analysis_path or _DEFAULT_ANALYSIS_PATH
        self._tool_usage_path = tool_usage_path or _DEFAULT_TOOL_USAGE_PATH
        self._threshold = threshold
        self._min_failures = min_failures

    def detect_update_candidates(
        self,
        agent_filter: str | None = None,
    ) -> list[SkillUpdateCandidate]:
        """Find criteria needing skill file updates based on eval pass rates."""
        analysis = _load_analysis(self._analysis_path)
        if analysis is None:
            logger.warning(
                "skill_updater.no_analysis",
                path=str(self._analysis_path),
            )
            return []

        pass_rates: dict[str, dict[str, float]] = analysis.get("pass_rates", {})
        clusters = analysis.get("failure_clusters", [])

        # Index clusters by (agent, criterion)
        cluster_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        for cluster in clusters:
            key = (cluster["agent"], cluster["criterion"])
            cluster_lookup[key] = cluster

        candidates: list[SkillUpdateCandidate] = []

        for agent, criteria in pass_rates.items():
            if agent_filter and agent != agent_filter:
                continue

            for criterion, rate in criteria.items():
                if rate >= self._threshold:
                    continue

                cluster = cluster_lookup.get((agent, criterion))
                failure_count: int = cluster.get("count", 0) if cluster else 0

                if failure_count < self._min_failures:
                    continue

                target = _resolve_skill_file(agent, criterion)
                sample_reasons: list[str] = cluster.get("sample_reasonings", []) if cluster else []
                pattern = cluster.get("pattern", "unknown") if cluster else "unknown"

                candidates.append(
                    SkillUpdateCandidate(
                        agent=agent,
                        criterion=criterion,
                        pass_rate=rate,
                        failure_count=failure_count,
                        failure_cluster=pattern,
                        sample_reasons=sample_reasons,
                        target_skill_file=target,
                        source="eval",
                    )
                )

        # Also check tool usage for promotion candidates
        candidates.extend(self._detect_tool_usage_promotions(agent_filter))

        # Sort by impact: lowest pass rate first, then highest failure count
        candidates.sort(key=lambda c: (c.pass_rate, -c.failure_count))

        logger.info(
            "skill_updater.candidates_detected",
            count=len(candidates),
            threshold=self._threshold,
            min_failures=self._min_failures,
        )
        return candidates

    def _detect_tool_usage_promotions(
        self,
        agent_filter: str | None = None,
    ) -> list[SkillUpdateCandidate]:
        """Detect frequently queried facts that should be promoted to L2."""
        if not self._tool_usage_path.exists():
            return []

        try:
            lines = self._tool_usage_path.read_text().strip().split("\n")
        except OSError:
            return []

        # Count queries by (agent, property, client)
        query_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            agent = entry.get("agent", "")
            prop = entry.get("property", "")
            client = entry.get("client", "")
            if agent and prop:
                query_counts[(agent, prop, client)] += 1

        candidates: list[SkillUpdateCandidate] = []
        for (agent, prop, client), count in query_counts.items():
            if agent_filter and agent != agent_filter:
                continue
            if count < TOOL_USAGE_PROMOTION_THRESHOLD:
                continue

            target = str(_SKILL_BASE / agent / "SKILL.md")
            description = f"{prop} for {client}" if client else prop

            candidates.append(
                SkillUpdateCandidate(
                    agent=agent,
                    criterion=f"tool_query:{prop}",
                    pass_rate=0.0,
                    failure_count=count,
                    failure_cluster=f"Frequently queried: {description} ({count} lookups)",
                    target_skill_file=target,
                    source="tool_usage",
                )
            )

        return candidates

    async def generate_patch(
        self,
        candidate: SkillUpdateCandidate,
    ) -> SkillFilePatch | None:
        """Generate an LLM-drafted patch for a skill file."""
        skill_content = _load_skill_content(candidate.target_skill_file)
        if skill_content is None:
            logger.warning(
                "skill_updater.skill_not_found",
                path=candidate.target_skill_file,
            )
            return None

        prompt = self._build_patch_prompt(candidate, skill_content)

        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("complex")

        try:
            response: CompletionResponse = await provider.complete(
                [Message(role="user", content=prompt)],
                temperature=0.0,
                model=model,
            )
            patch_content, confidence = self._parse_patch_response(response.content)
        except Exception:
            logger.warning(
                "skill_updater.llm_failed",
                agent=candidate.agent,
                criterion=candidate.criterion,
                exc_info=True,
            )
            return None

        # Check for duplicate content
        if self._is_duplicate(patch_content, skill_content):
            logger.info(
                "skill_updater.duplicate_skipped",
                agent=candidate.agent,
                criterion=candidate.criterion,
            )
            return None

        return SkillFilePatch(
            skill_file_path=candidate.target_skill_file,
            patch_content=patch_content,
            candidate=candidate,
            confidence=confidence,
        )

    @staticmethod
    def _build_patch_prompt(
        candidate: SkillUpdateCandidate,
        skill_content: str,
    ) -> str:
        sample_text = ""
        for i, reason in enumerate(candidate.sample_reasons[:3], 1):
            sample_text += f"  {i}. {reason}\n"

        return f"""You are an expert email development engineer updating a skill file for the "{candidate.agent}" AI agent.

## Task
Generate a concise, actionable addition to this skill file that addresses the observed failure pattern. Use the same formatting style as the existing file. Do NOT repeat existing content.

## Current Skill File Content
```markdown
{skill_content}
```

## Failure Pattern
- **Criterion:** {candidate.criterion}
- **Pass rate:** {candidate.pass_rate:.0%} (threshold: 80%)
- **Failure count:** {candidate.failure_count}
- **Pattern:** {candidate.failure_cluster}
- **Sample failures:**
{sample_text}

## Output Format
Respond with EXACTLY this structure:

### PATCH_START
(The markdown text to APPEND to the skill file. Must be new content addressing the failure pattern.)
### PATCH_END

### CONFIDENCE
(ONE word: HIGH, MEDIUM, or LOW)"""

    @staticmethod
    def _parse_patch_response(response: str) -> tuple[str, str]:
        """Extract patch content and confidence from LLM response."""
        patch_content = ""
        confidence = "MEDIUM"

        if "### PATCH_START" in response and "### PATCH_END" in response:
            start = response.index("### PATCH_START") + len("### PATCH_START")
            end = response.index("### PATCH_END")
            patch_content = response[start:end].strip()

        if "### CONFIDENCE" in response:
            after = response[response.index("### CONFIDENCE") + len("### CONFIDENCE") :]
            conf_word = after.strip().split()[0].upper() if after.strip() else "MEDIUM"
            if conf_word in {"HIGH", "MEDIUM", "LOW"}:
                confidence = conf_word

        if not patch_content:
            patch_content = response.strip()

        return patch_content, confidence

    @staticmethod
    def _is_duplicate(patch_content: str, existing_content: str) -> bool:
        """Check if the patch content substantially duplicates existing content."""
        patch_lines = {
            line.strip().lower()
            for line in patch_content.split("\n")
            if line.strip() and not line.startswith("#")
        }
        existing_lines = {
            line.strip().lower()
            for line in existing_content.split("\n")
            if line.strip() and not line.startswith("#")
        }
        if not patch_lines:
            return True
        overlap = patch_lines & existing_lines
        return len(overlap) / len(patch_lines) > 0.7


def _update_frontmatter_version(path: Path, content: str, new_version: str) -> None:
    """Update the ``version:`` field in a skill file's front matter.

    If no front matter exists, prepends a new block. If front matter exists
    but has no ``version:`` line, appends one before the closing ``---``.
    """
    import re

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not fm_match:
        # No front matter — prepend one
        path.write_text(f'---\nversion: "{new_version}"\n---\n{content}')
        return

    fm_text = fm_match.group(1)
    if re.search(r"^version:", fm_text, re.MULTILINE):
        new_fm = re.sub(
            r"^version:.*$",
            f'version: "{new_version}"',
            fm_text,
            flags=re.MULTILINE,
        )
    else:
        new_fm = fm_text.rstrip() + f'\nversion: "{new_version}"'

    rest = content[fm_match.end() :]
    path.write_text(f"---\n{new_fm}\n---\n{rest}")


def _update_version_manifests(
    patches: list[SkillFilePatch],
) -> list[str]:
    """Bump version in frontmatter and update skill-versions.yaml for patched files.

    Called *before* the git commit so manifest changes are included in the
    same commit. Returns list of additional changed file paths (manifests).
    """
    from app.ai.agents.skill_loader import parse_skill_meta
    from app.ai.agents.skill_version import (
        bump_version,
        load_manifest,
        manifest_path,
        record_version,
    )

    manifest_paths: set[str] = set()
    for patch in patches:
        path = Path(patch.skill_file_path)
        if not path.exists():
            continue

        content = path.read_text()
        meta, _body = parse_skill_meta(content)
        new_version = bump_version(meta.version)

        _update_frontmatter_version(path, content, new_version)

        agent = patch.candidate.agent
        skill_name = path.stem
        manifest = load_manifest(agent)
        if manifest is None:
            continue

        record_version(
            agent=agent,
            skill_name=skill_name,
            version=new_version,
            git_hash="pending",  # Will be the commit hash; updated post-merge
            source="eval-driven",
            eval_pass_rate=patch.candidate.pass_rate,
        )
        manifest_paths.add(str(manifest_path(agent)))

    return list(manifest_paths)


def apply_patches(
    patches: list[SkillFilePatch],
    dry_run: bool = False,
) -> str | None:
    """Apply patches to skill files and create a git branch.

    Returns branch name if created, None if dry_run or no patches.
    """
    if not patches or dry_run:
        return None

    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # Group by agent for branch naming
    agents = sorted({p.candidate.agent for p in patches})
    criteria = sorted({p.candidate.criterion for p in patches})

    if len(agents) == 1:
        branch = f"skill-update/{agents[0]}/{criteria[0]}/{date_str}"
    else:
        branch = f"skill-update/multi-agent/{date_str}"

    try:
        return _apply_patches_git(patches, branch, agents, criteria)
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "skill_updater.git_failed",
            branch=branch,
            returncode=exc.returncode,
            stderr=exc.stderr.decode() if exc.stderr else "",
        )
        # Best-effort cleanup — return to previous branch
        with contextlib.suppress(Exception):
            subprocess.run(
                ["git", "checkout", "-"],  # noqa: S607
                capture_output=True,
                check=False,
            )
        return None


def _apply_patches_git(
    patches: list[SkillFilePatch],
    branch: str,
    agents: list[str],
    criteria: list[str],
) -> str | None:
    """Inner git operations — separated for clean error handling."""
    # Create branch (inputs are validated constants, not user input)
    subprocess.run(  # noqa: S603
        ["git", "checkout", "-b", branch],  # noqa: S607
        check=True,
        capture_output=True,
    )

    changed_files: list[str] = []
    for patch in patches:
        path = Path(patch.skill_file_path)
        if not path.exists():
            logger.warning("skill_updater.target_missing", path=str(path))
            continue

        existing = path.read_text()
        separator = "\n\n" if not existing.endswith("\n\n") else ""
        path.write_text(existing + separator + patch.patch_content + "\n")
        changed_files.append(str(path))

    if not changed_files:
        # Clean up empty branch
        subprocess.run(
            ["git", "checkout", "-"],  # noqa: S607
            check=True,
            capture_output=True,
        )
        return None

    # Bump version in frontmatter and update skill-versions.yaml manifests
    manifest_files = _update_version_manifests(patches)
    changed_files.extend(manifest_files)

    subprocess.run(  # noqa: S603
        ["git", "add", *changed_files],  # noqa: S607
        check=True,
        capture_output=True,
    )

    agents_str = ", ".join(agents)
    criteria_str = ", ".join(criteria[:3])
    msg = f"fix(agents): update skill files for {agents_str} ({criteria_str}) (eval-driven)"

    subprocess.run(  # noqa: S603
        ["git", "commit", "-m", msg],  # noqa: S607
        check=True,
        capture_output=True,
    )

    logger.info(
        "skill_updater.branch_created",
        branch=branch,
        files=len(changed_files),
        patches=len(patches),
    )
    return branch


def format_candidate_report(candidates: list[SkillUpdateCandidate]) -> str:
    """Format candidates as human-readable text for --dry-run output."""
    if not candidates:
        return "No skill update candidates found."

    lines: list[str] = [
        f"Found {len(candidates)} skill update candidate(s):",
        "",
    ]

    eval_candidates = [c for c in candidates if c.source == "eval"]
    promo_candidates = [c for c in candidates if c.source == "tool_usage"]

    if eval_candidates:
        lines.append("## Eval Failure Patches")
        lines.append("")
        for c in eval_candidates:
            lines.append(
                f"  [{c.agent}] {c.criterion}: "
                f"{c.pass_rate:.0%} pass rate, {c.failure_count} failures"
            )
            lines.append(f"    Target: {c.target_skill_file}")
            lines.append(f"    Pattern: {c.failure_cluster}")
            lines.append("")

    if promo_candidates:
        lines.append("## Tool Usage Promotion Candidates")
        lines.append("")
        for c in promo_candidates:
            lines.append(f"  [{c.agent}] {c.criterion}: {c.failure_cluster}")
            lines.append(f"    Target: {c.target_skill_file} (promote to L2)")
            lines.append("")

    return "\n".join(lines)


def format_patch_report(patches: list[SkillFilePatch]) -> str:
    """Format generated patches as human-readable text."""
    if not patches:
        return "No patches generated."

    lines: list[str] = [
        f"Generated {len(patches)} patch(es):",
        "",
    ]
    for patch in patches:
        lines.append(f"--- {patch.skill_file_path} ---")
        lines.append(f"Confidence: {patch.confidence}")
        lines.append(f"Agent: {patch.candidate.agent}, Criterion: {patch.candidate.criterion}")
        lines.append("")
        lines.append(patch.patch_content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
