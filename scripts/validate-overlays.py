#!/usr/bin/env python3
"""Validate per-client skill overlay files in data/clients/.

Phase 32.11 — Checks:
1. Frontmatter is valid (required fields, valid enums).
2. ``replaces`` references a valid core skill in the agent's SKILL_FILES.
3. No two overlays for the same client+agent replace the same core skill.

Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Resolve project root so imports work when run as a script
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from app.ai.agents.skill_loader import _VALID_OVERLAY_MODES, parse_overlay_meta

_CLIENTS_DIR = _PROJECT_ROOT / "data" / "clients"

# Map agent directory names to the module path containing SKILL_FILES
_AGENT_SKILL_MODULES: dict[str, str] = {
    "scaffolder": "app.ai.agents.scaffolder.prompt",
    "dark_mode": "app.ai.agents.dark_mode.prompt",
    "content": "app.ai.agents.content.prompt",
    "outlook_fixer": "app.ai.agents.outlook_fixer.prompt",
    "accessibility": "app.ai.agents.accessibility.prompt",
    "personalisation": "app.ai.agents.personalisation.prompt",
    "code_reviewer": "app.ai.agents.code_reviewer.prompt",
    "knowledge": "app.ai.agents.knowledge.prompt",
    "innovation": "app.ai.agents.innovation.prompt",
    "import_annotator": "app.ai.agents.import_annotator.prompt",
    "visual_qa": "app.ai.agents.visual_qa.prompt",
}


def _get_skill_files(agent_name: str) -> set[str]:
    """Import the agent's prompt module and return its SKILL_FILES keys."""
    module_path = _AGENT_SKILL_MODULES.get(agent_name)
    if not module_path:
        return set()
    try:
        mod = importlib.import_module(module_path)
        return set(getattr(mod, "SKILL_FILES", {}).keys())
    except Exception:
        return set()


def validate() -> list[str]:
    """Validate all overlay files. Returns list of error messages."""
    errors: list[str] = []

    if not _CLIENTS_DIR.is_dir():
        return errors  # No overlays to validate

    # Track replace targets per (client, agent) to detect conflicts
    replace_targets: dict[tuple[str, str], list[tuple[str, Path]]] = {}

    for md_file in sorted(_CLIENTS_DIR.rglob("*.md")):
        # Only validate files matching data/clients/{client}/agents/{agent}/skills/*.md
        rel = md_file.relative_to(_CLIENTS_DIR)
        parts = rel.parts
        if len(parts) != 5 or parts[1] != "agents" or parts[3] != "skills":
            continue

        client_id = parts[0]
        agent_name = parts[2]
        file_label = f"{client_id}/{agent_name}/{parts[4]}"

        raw = md_file.read_text(encoding="utf-8")
        meta, _body = parse_overlay_meta(raw)

        # 1. Validate overlay_mode
        if meta.overlay_mode not in _VALID_OVERLAY_MODES:
            errors.append(
                f"{file_label}: invalid overlay_mode '{meta.overlay_mode}' "
                f"(must be one of {sorted(_VALID_OVERLAY_MODES)})"
            )

        # 2. Validate token_cost is positive
        if meta.token_cost <= 0:
            errors.append(f"{file_label}: token_cost must be positive, got {meta.token_cost}")

        # 3. Validate priority
        if meta.priority not in (1, 2, 3):
            errors.append(f"{file_label}: priority must be 1, 2, or 3, got {meta.priority}")

        # 4. Validate replaces reference
        if meta.overlay_mode == "replace":
            if not meta.replaces:
                errors.append(f"{file_label}: overlay_mode='replace' requires 'replaces' field")
            else:
                core_skills = _get_skill_files(agent_name)
                if core_skills and meta.replaces not in core_skills:
                    errors.append(
                        f"{file_label}: replaces '{meta.replaces}' not found in "
                        f"{agent_name}'s SKILL_FILES (available: {sorted(core_skills)})"
                    )

                # Track for conflict detection
                key = (client_id, agent_name)
                replace_targets.setdefault(key, []).append((meta.replaces, md_file))

    # 5. Check for conflicting replaces
    for (client_id, agent_name), targets in replace_targets.items():
        seen: dict[str, Path] = {}
        for replaces_name, file_path in targets:
            if replaces_name in seen:
                errors.append(
                    f"Conflict: {client_id}/{agent_name} — both "
                    f"'{seen[replaces_name].name}' and '{file_path.name}' "
                    f"replace core skill '{replaces_name}'"
                )
            else:
                seen[replaces_name] = file_path

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"Overlay validation failed ({len(errors)} errors):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    # Count validated files
    count = 0
    if _CLIENTS_DIR.is_dir():
        for md in _CLIENTS_DIR.rglob("*.md"):
            rel = md.relative_to(_CLIENTS_DIR)
            parts = rel.parts
            if len(parts) == 5 and parts[1] == "agents" and parts[3] == "skills":
                count += 1
    print(f"Overlay validation passed ({count} files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
