"""Shared utility for output-mode-aware SKILL.md section extraction.

Phase 5 addition: Budget-aware skill loading with front matter metadata.
Phase 32.11 addition: Per-client skill overlays (extend/replace).
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)

OutputMode = Literal["html", "structured"]

_OUTPUT_FORMAT_RE = re.compile(r"^## Output Format: (.+)$", re.MULTILINE)
_SECURITY_RULES_RE = re.compile(r"^## Security Rules.*$", re.MULTILINE)
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class SkillMeta:
    """Metadata parsed from skill file front matter.

    Attributes:
        token_cost: Estimated token cost of loading this skill file.
        priority: Loading priority (1=critical, 2=standard, 3=supplementary).
        version: Semver version string from front matter (default ``1.0.0``).
    """

    token_cost: int = 500
    priority: int = 2
    version: str = "1.0.0"


def parse_skill_meta(content: str) -> tuple[SkillMeta, str]:
    """Parse YAML-like front matter from a skill file.

    Returns (metadata, remaining_content). If no front matter is found,
    returns default SkillMeta and original content (backward compatible).
    """
    match = _FRONT_MATTER_RE.match(content)
    if not match:
        return SkillMeta(), content

    front_matter = match.group(1)
    body = content[match.end() :]

    token_cost = 500
    priority = 2
    version = "1.0.0"

    for line in front_matter.strip().splitlines():
        line = line.strip()
        if line.startswith("token_cost:"):
            with contextlib.suppress(ValueError):
                token_cost = int(line.split(":", 1)[1].strip())
        elif line.startswith("priority:"):
            with contextlib.suppress(ValueError):
                priority = int(line.split(":", 1)[1].strip())
        elif line.startswith("version:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val:
                version = val

    return SkillMeta(token_cost=token_cost, priority=priority, version=version), body


def should_load_skill(
    meta: SkillMeta,
    cumulative_cost: int,
    remaining_budget: int,
    budget_max: int,
) -> bool:
    """Decide whether to load a skill file based on budget constraints.

    Priority 1 (critical): always loaded.
    Priority 2 (standard): skipped when budget is below 30% capacity.
    Priority 3 (supplementary): skipped when any budget pressure exists (below 70%).

    Args:
        meta: Skill file metadata.
        cumulative_cost: Tokens already consumed by previously loaded skills.
        remaining_budget: Remaining token budget for skill docs.
        budget_max: Total skill docs budget from ContextBudget.

    Returns:
        True if the skill should be loaded.
    """
    if meta.priority == 1:
        return True

    available = remaining_budget - cumulative_cost
    if available < meta.token_cost:
        return False

    capacity_ratio = available / budget_max if budget_max > 0 else 0.0

    if meta.priority == 3 and capacity_ratio < 0.70:
        return False

    return not (meta.priority == 2 and capacity_ratio < 0.3)


# ---------------------------------------------------------------------------
# Phase 32.11: Per-client skill overlays
# ---------------------------------------------------------------------------

_OVERLAYS_BASE = Path(__file__).resolve().parents[2] / "data" / "clients"

_VALID_OVERLAY_MODES = frozenset({"extend", "replace"})


@dataclass(frozen=True)
class OverlayMeta:
    """Metadata for a client skill overlay file."""

    token_cost: int = 500
    priority: int = 2
    overlay_mode: str = "extend"
    replaces: str | None = None
    client_id: str = ""
    content: str = ""
    source_path: str = ""


def parse_overlay_meta(content: str) -> tuple[OverlayMeta, str]:
    """Parse overlay-specific frontmatter (superset of SkillMeta fields).

    Returns (OverlayMeta, remaining_content). If no front matter found,
    returns defaults and original content.
    """
    match = _FRONT_MATTER_RE.match(content)
    if not match:
        return OverlayMeta(), content

    front_matter = match.group(1)
    body = content[match.end() :]

    token_cost = 500
    priority = 2
    overlay_mode = "extend"
    replaces: str | None = None
    client_id = ""

    for line in front_matter.strip().splitlines():
        line = line.strip()
        if line.startswith("token_cost:"):
            with contextlib.suppress(ValueError):
                token_cost = int(line.split(":", 1)[1].strip())
        elif line.startswith("priority:"):
            with contextlib.suppress(ValueError):
                priority = int(line.split(":", 1)[1].strip())
        elif line.startswith("overlay_mode:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val in _VALID_OVERLAY_MODES:
                overlay_mode = val
        elif line.startswith("replaces:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val and val != "null":
                replaces = val
        elif line.startswith("client_id:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val:
                client_id = val

    return (
        OverlayMeta(
            token_cost=token_cost,
            priority=priority,
            overlay_mode=overlay_mode,
            replaces=replaces,
            client_id=client_id,
        ),
        body,
    )


@lru_cache(maxsize=128)
def discover_overlays(agent_name: str, client_id: str) -> tuple[OverlayMeta, ...]:
    """Discover overlay skill files for a client+agent pair.

    Scans ``data/clients/{client_id}/agents/{agent_name}/skills/*.md``.
    Returns a tuple (hashable for cache). Empty tuple if path is invalid
    or no overlay files exist.
    """
    # Path traversal guard
    if "/" in client_id or "\\" in client_id or ".." in client_id:
        logger.warning("skill_loader.invalid_client_id", client_id=client_id)
        return ()

    overlay_dir = _OVERLAYS_BASE / client_id / "agents" / agent_name / "skills"
    if not overlay_dir.is_dir():
        return ()

    overlays: list[OverlayMeta] = []
    for md_file in sorted(overlay_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        meta, body = parse_overlay_meta(raw)
        overlays.append(
            OverlayMeta(
                token_cost=meta.token_cost,
                priority=meta.priority,
                overlay_mode=meta.overlay_mode,
                replaces=meta.replaces,
                client_id=client_id,
                content=body,
                source_path=str(md_file.relative_to(_OVERLAYS_BASE)),
            )
        )

    return tuple(overlays)


def apply_overlays(
    skill_parts: list[str],
    loaded_skills: set[str],
    overlays: tuple[OverlayMeta, ...],
    cumulative_cost: int,
    remaining_budget: int,
    budget_max: int,
) -> tuple[list[str], int, list[str]]:
    """Apply client overlays to the skill loading pipeline.

    Handles ``extend`` (append after core skills) and ``replace`` (remove
    named core skill, load overlay in its place) modes. Budget-aware —
    overlays use the same priority/threshold logic as core skills.

    Returns:
        (updated_parts, updated_cumulative_cost, overlay_names_loaded)
    """
    overlay_names: list[str] = []

    for overlay in overlays:
        # Handle "replace" mode: remove the named core skill
        if overlay.overlay_mode == "replace" and overlay.replaces:
            tag = f"--- REFERENCE: {overlay.replaces} ---"
            skill_parts = [p for p in skill_parts if tag not in p]
            loaded_skills.discard(overlay.replaces)

        # Budget check using same logic as core skills
        meta = SkillMeta(token_cost=overlay.token_cost, priority=overlay.priority)
        if not should_load_skill(meta, cumulative_cost, remaining_budget, budget_max):
            continue

        cumulative_cost += overlay.token_cost
        overlay_name = Path(overlay.source_path).stem
        label = f"overlay:{overlay.client_id}/{overlay_name}"
        skill_parts.append(f"\n\n--- REFERENCE: {label} ---\n\n{overlay.content}")
        overlay_names.append(label)

    if overlay_names:
        logger.info(
            "skill_loader.overlays_applied",
            overlays=overlay_names,
            count=len(overlay_names),
        )

    return skill_parts, cumulative_cost, overlay_names


def load_skill_with_version(
    agent: str,
    skill_name: str,
    skill_path: Path,
) -> tuple[str, str]:
    """Load skill content, respecting version pins.

    Returns ``(content, loaded_version)``. If the skill is pinned, content
    is retrieved from git at the pinned revision. Otherwise the on-disk
    file is used.
    """
    from app.ai.agents.skill_version import load_pinned_content

    pinned = load_pinned_content(agent, skill_name)
    if pinned is not None:
        meta, _body = parse_skill_meta(pinned)
        return pinned, meta.version

    content = skill_path.read_text(encoding="utf-8")
    meta, _body = parse_skill_meta(content)
    return content, meta.version


def extract_skill_for_mode(skill_content: str, output_mode: str = "html") -> str:
    """Extract shared sections + the matching output format section from SKILL.md.

    Returns the full SKILL.md content with only the relevant output format
    section included. If no output format sections are found (legacy SKILL.md),
    returns the content unchanged for backward compatibility.

    Args:
        skill_content: Full SKILL.md content (L1 frontmatter + L2 body).
        output_mode: "html" or "structured".

    Returns:
        SKILL.md content with only the matching output format section.
    """
    format_matches = list(_OUTPUT_FORMAT_RE.finditer(skill_content))
    if not format_matches:
        return skill_content  # No output format sections -- backward compatible

    # Everything before first Output Format header = shared domain knowledge
    shared_end = format_matches[0].start()
    shared = skill_content[:shared_end].rstrip()

    # Find the matching output format section
    target = "HTML" if output_mode == "html" else "Structured"
    mode_section = ""
    for i, match in enumerate(format_matches):
        if match.group(1).strip().startswith(target):
            start = match.start()
            # Section extends to next Output Format header, Security Rules, or EOF
            end = len(skill_content)
            if i + 1 < len(format_matches):
                end = format_matches[i + 1].start()
            else:
                # Check for Security Rules after last format section
                sec_match = _SECURITY_RULES_RE.search(skill_content, start + 1)
                if sec_match:
                    end = sec_match.start()
            mode_section = skill_content[start:end].rstrip()
            break

    # Security Rules section (after all Output Format sections) -- always included
    security = ""
    sec_match = _SECURITY_RULES_RE.search(skill_content, format_matches[-1].start())
    if sec_match:
        security = skill_content[sec_match.start() :].rstrip()

    parts = [shared]
    if mode_section:
        parts.append(mode_section)
    if security:
        parts.append(security)

    return "\n\n".join(parts)
