"""Read-only endpoint exposing per-agent skill metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

AGENT_NAMES = [
    "scaffolder",
    "dark_mode",
    "content",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "knowledge",
    "innovation",
]

AGENTS_DIR = Path(__file__).resolve().parent  # app/ai/agents/
TRACES_DIR = Path(__file__).resolve().parents[2] / "traces"


def _load_analysis() -> dict[str, Any]:
    """Load traces/analysis.json once, returning empty dict on failure."""
    analysis_path = TRACES_DIR / "analysis.json"
    if not analysis_path.exists():
        return {}
    try:
        return json.loads(analysis_path.read_text())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("agents.skills_load_analysis_failed", error=str(exc))
        return {}


def _parse_l4_sources(skill_path: Path) -> list[str]:
    """Extract l4_sources from SKILL.md YAML frontmatter."""
    if not skill_path.exists():
        return []
    content = skill_path.read_text()
    if not content.startswith("---"):
        return []
    parts = content.split("---", 2)
    if len(parts) < 3:
        return []
    try:
        raw = yaml.safe_load(parts[1])  # pyright: ignore[reportAny]
        if not isinstance(raw, dict):
            return []
        meta: dict[str, object] = raw  # pyright: ignore[reportUnknownVariableType]
        sources = meta.get("l4_sources", [])
        if isinstance(sources, list):
            return [str(s) for s in sources]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
        return []
    except yaml.YAMLError:
        return []


def _get_agent_skill_info(agent_name: str, analysis: dict[str, Any]) -> dict[str, object]:
    agent_dir = AGENTS_DIR / agent_name
    skill_file = agent_dir / "SKILL.md"
    skills_dir = agent_dir / "skills"

    l3_files: list[str] = []
    if skills_dir.is_dir():
        l3_files = sorted(f.name for f in skills_dir.glob("*.md"))

    # Check if failure warnings would fire for this agent
    has_failure_warnings = False
    agent_data = analysis.get("per_agent", {}).get(agent_name, {})
    criteria = agent_data.get("per_criterion", {})
    has_failure_warnings = any(c.get("pass_rate", 1.0) < 0.85 for c in criteria.values())

    return {
        "name": agent_name,
        "skill_file": "SKILL.md" if skill_file.exists() else None,
        "l3_files": l3_files,
        "l4_sources": _parse_l4_sources(skill_file),
        "has_failure_warnings": has_failure_warnings,
    }


@router.get("/skills")
async def list_agent_skills(
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, list[dict[str, object]]]:
    """Return skill metadata for all agents."""
    analysis = _load_analysis()
    agents = [_get_agent_skill_info(name, analysis) for name in AGENT_NAMES]
    return {"agents": agents}
