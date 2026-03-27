"""Skill file version tracking, pinning, and rollback.

Phase 32.10: Adds version metadata to L3 skill files, per-agent manifests
(``skill-versions.yaml``), and runtime pinning via ``git show``.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, cast

import yaml

from app.ai.agents.evals.schemas import SkillVersionEntry
from app.core.logging import get_logger

logger = get_logger(__name__)

_AGENTS_BASE = Path(__file__).resolve().parent
_MANIFEST_FILENAME = "skill-versions.yaml"
_VALID_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")
_VALID_AGENTS = frozenset(
    {
        "scaffolder",
        "dark_mode",
        "content",
        "outlook_fixer",
        "accessibility",
        "personalisation",
        "code_reviewer",
        "knowledge",
        "innovation",
        "import_annotator",
    }
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillVersionConfig:
    """Version config for a single skill file within an agent manifest."""

    current: str = "1.0.0"
    pinned: str | None = None
    versions: dict[str, SkillVersionEntry] = field(
        default_factory=lambda: dict[str, SkillVersionEntry]()
    )


@dataclass(frozen=True)
class SkillVersionManifest:
    """Parsed ``skill-versions.yaml`` for one agent."""

    agent: str
    skills: dict[str, SkillVersionConfig] = field(
        default_factory=lambda: dict[str, SkillVersionConfig]()
    )


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------


def manifest_path(agent: str) -> Path:
    if "/" in agent or "\\" in agent or ".." in agent:
        msg = f"Invalid agent name: {agent!r}"
        raise ValueError(msg)
    return _AGENTS_BASE / agent / _MANIFEST_FILENAME


def load_manifest(agent: str) -> SkillVersionManifest | None:
    """Load and parse ``skill-versions.yaml`` for *agent*.

    Returns ``None`` if the manifest file does not exist.
    """
    path = manifest_path(agent)
    if not path.exists():
        return None

    try:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        logger.warning("skill_version.load_failed", agent=agent, path=str(path))
        return None

    skills: dict[str, SkillVersionConfig] = {}
    raw_skills: dict[str, Any] = raw.get("skills") or {}
    for skill_name, skill_raw in raw_skills.items():
        if not isinstance(skill_raw, dict):
            continue
        skill_data = cast(dict[str, Any], skill_raw)
        versions: dict[str, SkillVersionEntry] = {}
        raw_versions: dict[str, Any] = skill_data.get("versions") or {}
        for ver_str, ver_raw in raw_versions.items():
            if not isinstance(ver_raw, dict):
                continue
            vd = cast(dict[str, Any], ver_raw)
            raw_rate: float | int | None = vd.get("eval_pass_rate")
            eval_pass_rate: float | None = float(raw_rate) if raw_rate is not None else None
            versions[str(ver_str)] = SkillVersionEntry(
                version=str(ver_str),
                hash=str(vd.get("hash") or ""),
                date=str(vd.get("date") or ""),
                source=str(vd.get("source") or "manual"),
                eval_pass_rate=eval_pass_rate,
            )
        raw_pinned: str | None = skill_data.get("pinned")
        pinned_val: str | None = str(raw_pinned) if raw_pinned is not None else None
        raw_current: str = skill_data.get("current") or "1.0.0"
        skills[skill_name] = SkillVersionConfig(
            current=str(raw_current),
            pinned=pinned_val,
            versions=versions,
        )

    return SkillVersionManifest(agent=agent, skills=skills)


def save_manifest(manifest: SkillVersionManifest) -> None:
    """Serialise *manifest* back to ``skill-versions.yaml``."""
    out: dict[str, Any] = {"skills": {}}
    for skill_name, cfg in sorted(manifest.skills.items()):
        versions_out: dict[str, dict[str, Any]] = {}
        for ver_str, entry in sorted(cfg.versions.items()):
            ver_dict: dict[str, Any] = {
                "hash": entry.hash,
                "date": entry.date,
                "source": entry.source,
            }
            ver_dict["eval_pass_rate"] = entry.eval_pass_rate
            versions_out[ver_str] = ver_dict

        out["skills"][skill_name] = {
            "current": cfg.current,
            "pinned": cfg.pinned,
            "versions": versions_out,
        }

    path = manifest_path(manifest.agent)
    path.write_text(
        yaml.dump(out, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    logger.info("skill_version.manifest_saved", agent=manifest.agent, path=str(path))


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def bump_version(current: str) -> str:
    """Semver minor bump: ``1.0.0`` → ``1.1.0``."""
    parts = current.split(".")
    if len(parts) != 3:
        return "1.1.0"
    try:
        major, minor, _patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return "1.1.0"
    return f"{major}.{minor + 1}.0"


# ---------------------------------------------------------------------------
# Pin / unpin
# ---------------------------------------------------------------------------


def pin_skill(agent: str, skill_name: str, version: str) -> None:
    """Pin *skill_name* for *agent* to *version*."""
    manifest = load_manifest(agent)
    if manifest is None:
        msg = f"No skill-versions.yaml for agent: {agent}"
        raise ValueError(msg)

    cfg = manifest.skills.get(skill_name)
    if cfg is None:
        msg = f"Skill {skill_name!r} not in manifest for {agent}"
        raise ValueError(msg)

    if version not in cfg.versions:
        msg = f"Version {version!r} not found for {agent}/{skill_name}"
        raise ValueError(msg)

    # Rebuild with updated pin
    new_cfg = SkillVersionConfig(
        current=cfg.current,
        pinned=version,
        versions=cfg.versions,
    )
    new_skills = {**manifest.skills, skill_name: new_cfg}
    save_manifest(SkillVersionManifest(agent=agent, skills=new_skills))

    logger.info(
        "skill_version.pinned",
        agent=agent,
        skill=skill_name,
        version=version,
    )


def unpin_skill(agent: str, skill_name: str) -> None:
    """Remove version pin for *skill_name* — resume using current on-disk file."""
    manifest = load_manifest(agent)
    if manifest is None:
        msg = f"No skill-versions.yaml for agent: {agent}"
        raise ValueError(msg)

    cfg = manifest.skills.get(skill_name)
    if cfg is None:
        msg = f"Skill {skill_name!r} not in manifest for {agent}"
        raise ValueError(msg)

    new_cfg = SkillVersionConfig(
        current=cfg.current,
        pinned=None,
        versions=cfg.versions,
    )
    new_skills = {**manifest.skills, skill_name: new_cfg}
    save_manifest(SkillVersionManifest(agent=agent, skills=new_skills))

    logger.info("skill_version.unpinned", agent=agent, skill=skill_name)


# ---------------------------------------------------------------------------
# Version listing
# ---------------------------------------------------------------------------


def list_skill_versions(agent: str, skill_name: str) -> list[SkillVersionEntry]:
    """Return version history for *skill_name* sorted by date descending."""
    manifest = load_manifest(agent)
    if manifest is None:
        return []
    cfg = manifest.skills.get(skill_name)
    if cfg is None:
        return []
    return sorted(cfg.versions.values(), key=lambda e: e.date, reverse=True)


# ---------------------------------------------------------------------------
# Git-based content loading for pinned versions
# ---------------------------------------------------------------------------


def resolve_skill_path(agent: str, skill_name: str) -> str:
    """Map *skill_name* to a repo-relative file path.

    Checks both ``app/ai/agents/{agent}/skills/{name}.md`` and the
    ``skills/l3/`` subdirectory (used by import_annotator).
    """
    base = Path("app/ai/agents") / agent / "skills"
    direct = base / f"{skill_name}.md"
    if (_AGENTS_BASE / agent / "skills" / f"{skill_name}.md").exists():
        return str(direct)
    nested = base / "l3" / f"{skill_name}.md"
    if (_AGENTS_BASE / agent / "skills" / "l3" / f"{skill_name}.md").exists():
        return str(nested)
    return str(direct)


def git_show_content(git_hash: str, repo_relative_path: str) -> str:
    """Load file content at a specific git revision via ``git show``.

    Raises ``ValueError`` if the hash is invalid or the command fails.
    """
    if not _VALID_HASH_RE.match(git_hash):
        msg = f"Invalid git hash: {git_hash!r}"
        raise ValueError(msg)

    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{git_hash}:{repo_relative_path}"],  # noqa: S607
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def load_pinned_content(agent: str, skill_name: str) -> str | None:
    """If *skill_name* is pinned for *agent*, return its content from git.

    Returns ``None`` if no pin is set (caller should use the on-disk file).
    """
    manifest = load_manifest(agent)
    if manifest is None:
        return None

    cfg = manifest.skills.get(skill_name)
    if cfg is None or cfg.pinned is None:
        return None

    entry = cfg.versions.get(cfg.pinned)
    if entry is None:
        logger.warning(
            "skill_version.pinned_version_missing",
            agent=agent,
            skill=skill_name,
            pinned=cfg.pinned,
        )
        return None

    path = resolve_skill_path(agent, skill_name)

    try:
        return git_show_content(entry.hash, path)
    except (CalledProcessError, ValueError):
        logger.warning(
            "skill_version.git_show_failed",
            agent=agent,
            skill=skill_name,
            hash=entry.hash,
            path=path,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Record a new version
# ---------------------------------------------------------------------------


def record_version(
    agent: str,
    skill_name: str,
    version: str,
    git_hash: str,
    source: str = "manual",
    eval_pass_rate: float | None = None,
) -> None:
    """Add a version entry to the manifest and update ``current``."""
    manifest = load_manifest(agent)
    if manifest is None:
        msg = f"No skill-versions.yaml for agent: {agent}"
        raise ValueError(msg)

    cfg = manifest.skills.get(skill_name)
    if cfg is None:
        cfg = SkillVersionConfig()

    new_entry = SkillVersionEntry(
        version=version,
        hash=git_hash,
        date=datetime.now(tz=UTC).date().isoformat(),
        source=source,
        eval_pass_rate=eval_pass_rate,
    )
    new_versions = {**cfg.versions, version: new_entry}
    new_cfg = SkillVersionConfig(
        current=version,
        pinned=cfg.pinned,
        versions=new_versions,
    )
    new_skills = {**manifest.skills, skill_name: new_cfg}
    save_manifest(SkillVersionManifest(agent=agent, skills=new_skills))

    logger.info(
        "skill_version.recorded",
        agent=agent,
        skill=skill_name,
        version=version,
        source=source,
    )


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def print_all_versions() -> None:
    """Print a table of all agents' skill versions and pin status."""
    for agent in sorted(_VALID_AGENTS):
        manifest = load_manifest(agent)
        if manifest is None:
            print(f"\n{agent}: no skill-versions.yaml")  # noqa: T201
            continue
        print(f"\n{agent}:")  # noqa: T201
        for skill_name, cfg in sorted(manifest.skills.items()):
            pin_label = f" [PINNED → {cfg.pinned}]" if cfg.pinned else ""
            print(f"  {skill_name}: v{cfg.current}{pin_label}")  # noqa: T201
            for ver_str, entry in sorted(cfg.versions.items(), reverse=True):
                rate = (
                    f" pass_rate={entry.eval_pass_rate:.0%}"
                    if entry.eval_pass_rate is not None
                    else ""
                )
                print(f"    {ver_str}: {entry.hash} ({entry.date}, {entry.source}{rate})")  # noqa: T201
