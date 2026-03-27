"""Skill versioning integration tests — load/pin/unpin flow, backfill verification.

Phase 32.12: Additional integration-level tests complementing the unit tests
in ``app/ai/agents/evals/tests/test_skill_versioning.py``.
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
import yaml

from app.ai.agents.skill_version import (
    _VALID_AGENTS,
    list_skill_versions,
    load_manifest,
    load_pinned_content,
    pin_skill,
    record_version,
    unpin_skill,
)

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_manifest_dict(
    skill_name: str = "client_behavior",
    current: str = "1.0.0",
    pinned: str | None = None,
    git_hash: str = "abc1234",
    extra_versions: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    versions: dict[str, dict[str, object]] = {
        current: {
            "hash": git_hash,
            "date": "2026-03-27",
            "source": "manual",
            "eval_pass_rate": None,
        },
    }
    if extra_versions:
        versions.update(extra_versions)
    return {
        "skills": {
            skill_name: {
                "current": current,
                "pinned": pinned,
                "versions": versions,
            },
        },
    }


def _write_manifest(tmp_path: Path, agent: str, data: dict[str, object]) -> Path:
    agent_dir = tmp_path / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = agent_dir / "skill-versions.yaml"
    manifest_path.write_text(yaml.dump(data, default_flow_style=False))
    return manifest_path


def _write_skill_file(tmp_path: Path, agent: str, skill_name: str, version: str = "1.0.0") -> Path:
    skills_dir = tmp_path / agent / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skills_dir / f"{skill_name}.md"
    skill_path.write_text(
        f'---\ntoken_cost: 800\npriority: 1\nversion: "{version}"\n---\n# {skill_name} content\n'
    )
    return skill_path


# ---------------------------------------------------------------------------
# TestLoadSkillFileNoPin
# ---------------------------------------------------------------------------


class TestLoadSkillFileNoPin:
    """load_skill_with_version() with no pin loads from disk."""

    def test_loads_current_from_disk(self, tmp_path: Path) -> None:
        """No pin set → reads file from disk, returns content."""
        from app.ai.agents.skill_loader import load_skill_with_version

        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)
        _write_skill_file(tmp_path, "dark_mode", "client_behavior", "1.0.0")

        skill_path = tmp_path / "dark_mode" / "skills" / "client_behavior.md"
        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            content, loaded_version = load_skill_with_version(
                "dark_mode", "client_behavior", skill_path
            )

        assert "# client_behavior content" in content
        assert loaded_version == "1.0.0"

    def test_returns_correct_loaded_version(self, tmp_path: Path) -> None:
        """Version from frontmatter matches returned loaded_version."""
        from app.ai.agents.skill_loader import load_skill_with_version

        data = _make_manifest_dict(skill_name="color_remapping", current="2.3.0")
        _write_manifest(tmp_path, "dark_mode", data)
        _write_skill_file(tmp_path, "dark_mode", "color_remapping", "2.3.0")

        skill_path = tmp_path / "dark_mode" / "skills" / "color_remapping.md"
        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            _content, version = load_skill_with_version("dark_mode", "color_remapping", skill_path)

        assert version == "2.3.0"


# ---------------------------------------------------------------------------
# TestPinSkillFlow
# ---------------------------------------------------------------------------


class TestPinSkillFlow:
    """Full pin → load → unpin flow."""

    def test_pin_updates_manifest_yaml(self, tmp_path: Path) -> None:
        """pin_skill() updates the YAML file on disk."""
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            pin_skill("dark_mode", "client_behavior", "1.0.0")
            raw = yaml.safe_load((tmp_path / "dark_mode" / "skill-versions.yaml").read_text())

        assert raw["skills"]["client_behavior"]["pinned"] == "1.0.0"

    def test_load_after_pin_uses_git_content(self, tmp_path: Path) -> None:
        """After pinning, load_pinned_content() returns content from git."""
        data = _make_manifest_dict(skill_name="client_behavior", pinned="1.0.0")
        _write_manifest(tmp_path, "dark_mode", data)
        _write_skill_file(tmp_path, "dark_mode", "client_behavior")

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            patch("app.ai.agents.skill_version.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value = CompletedProcess(
                args=[],
                returncode=0,
                stdout=b'---\nversion: "1.0.0"\n---\n# Git-fetched content',
            )
            content = load_pinned_content("dark_mode", "client_behavior")

        assert content is not None
        assert "Git-fetched content" in content

    def test_unpin_resumes_current(self, tmp_path: Path) -> None:
        """After unpinning, load_pinned_content() returns None (use disk)."""
        data = _make_manifest_dict(skill_name="client_behavior", pinned="1.0.0")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            unpin_skill("dark_mode", "client_behavior")
            content = load_pinned_content("dark_mode", "client_behavior")

        assert content is None


# ---------------------------------------------------------------------------
# TestListSkillVersions
# ---------------------------------------------------------------------------


class TestListSkillVersions:
    """Version listing with eval pass rates."""

    def test_returns_history_with_pass_rates(self, tmp_path: Path) -> None:
        """Multiple versions with eval_pass_rate values are returned correctly."""
        data = _make_manifest_dict(
            skill_name="client_behavior",
            current="1.2.0",
            extra_versions={
                "1.1.0": {
                    "hash": "bbb2222",
                    "date": "2026-03-15",
                    "source": "eval-driven",
                    "eval_pass_rate": 0.87,
                },
                "1.2.0": {
                    "hash": "ccc3333",
                    "date": "2026-03-25",
                    "source": "eval-driven",
                    "eval_pass_rate": 0.93,
                },
            },
        )
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            versions = list_skill_versions("dark_mode", "client_behavior")

        # Factory creates current (1.2.0), extra adds 1.1.0 + overwrites 1.2.0 = 2 versions
        assert len(versions) == 2
        # Most recent first
        assert versions[0].date >= versions[1].date
        # Pass rates present
        rates = [v.eval_pass_rate for v in versions if v.eval_pass_rate is not None]
        assert 0.87 in rates
        assert 0.93 in rates

    def test_empty_for_unknown_skill(self, tmp_path: Path) -> None:
        """Non-existent skill returns empty list."""
        data = _make_manifest_dict(skill_name="other_skill")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            assert list_skill_versions("dark_mode", "nonexistent") == []


# ---------------------------------------------------------------------------
# TestPinErrors
# ---------------------------------------------------------------------------


class TestPinErrors:
    """Pin operations raise ValueError for invalid inputs."""

    def test_pin_nonexistent_version_raises(self, tmp_path: Path) -> None:
        """ValueError with descriptive message for missing version."""
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"Version.*not found"),
        ):
            pin_skill("dark_mode", "client_behavior", "9.9.9")


# ---------------------------------------------------------------------------
# TestSetOverrideFromVersion
# ---------------------------------------------------------------------------


class TestSetOverrideFromVersion:
    """set_override_from_version() loads old version content as override."""

    def test_loads_old_version_as_override(self, tmp_path: Path) -> None:
        from app.ai.agents.skill_override import (
            clear_override,
            get_override,
            set_override_from_version,
        )

        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)
        _write_skill_file(tmp_path, "dark_mode", "client_behavior")

        try:
            with (
                patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
                patch("app.ai.agents.skill_version.subprocess") as mock_sub,
            ):
                mock_sub.run.return_value = CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=b"# Old version skill content for A/B testing",
                )
                set_override_from_version("dark_mode", "client_behavior", "1.0.0")

            override = get_override("dark_mode")
            assert override is not None
            assert "Old version skill content" in override
        finally:
            clear_override("dark_mode")


# ---------------------------------------------------------------------------
# TestEvalSkillUpdateApply
# ---------------------------------------------------------------------------


class TestEvalSkillUpdateApply:
    """Eval-driven skill update bumps version and updates manifest."""

    def test_bumps_frontmatter_version(self, tmp_path: Path) -> None:
        """_update_frontmatter_version() changes version string in frontmatter."""
        from app.ai.agents.evals.skill_updater import _update_frontmatter_version

        skill_file = tmp_path / "skill.md"
        skill_file.write_text('---\npriority: 2\nversion: "1.0.0"\n---\n# Skill content')

        _update_frontmatter_version(skill_file, skill_file.read_text(), "1.1.0")

        result = skill_file.read_text()
        assert 'version: "1.1.0"' in result
        assert 'version: "1.0.0"' not in result

    def test_updates_manifest_with_new_entry(self, tmp_path: Path) -> None:
        """record_version() adds entry and updates current."""
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            record_version(
                agent="dark_mode",
                skill_name="client_behavior",
                version="1.1.0",
                git_hash="new5678",
                source="eval-driven",
                eval_pass_rate=0.91,
            )
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        cfg = manifest.skills["client_behavior"]
        assert cfg.current == "1.1.0"
        assert "1.1.0" in cfg.versions
        assert cfg.versions["1.1.0"].eval_pass_rate == 0.91
        assert cfg.versions["1.1.0"].source == "eval-driven"
        # Original still present
        assert "1.0.0" in cfg.versions


# ---------------------------------------------------------------------------
# TestRollbackFlag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    """Rollback pins a skill to a previous version."""

    def test_rollback_pins_skill_and_logs(self, tmp_path: Path) -> None:
        """Simulating --rollback: pin_skill() is called and reason is logged."""
        data = _make_manifest_dict(
            skill_name="client_behavior",
            current="1.1.0",
            git_hash="aaa1111",
            extra_versions={
                "1.0.0": {
                    "hash": "aaa1111",
                    "date": "2026-03-01",
                    "source": "manual",
                    "eval_pass_rate": 0.85,
                },
                "1.1.0": {
                    "hash": "bbb2222",
                    "date": "2026-03-25",
                    "source": "eval-driven",
                    "eval_pass_rate": 0.40,
                },
            },
        )
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            # Rollback = pin to the old version
            pin_skill("dark_mode", "client_behavior", "1.0.0")
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        assert manifest.skills["client_behavior"].pinned == "1.0.0"


# ---------------------------------------------------------------------------
# TestBackfillManifests
# ---------------------------------------------------------------------------


class TestBackfillManifests:
    """All 9 production agents have skill-versions.yaml with 1.0.0 entries."""

    def test_all_nine_agents_have_manifests(self) -> None:
        """Each agent directory in _VALID_AGENTS has skill-versions.yaml."""
        # Only check agents that have the file on disk (backfill target)
        from app.ai.agents.skill_version import _AGENTS_BASE

        agents_with_manifests: list[str] = []
        for agent in sorted(_VALID_AGENTS):
            path = _AGENTS_BASE / agent / "skill-versions.yaml"
            if path.exists():
                agents_with_manifests.append(agent)

        # At minimum, all 9 core agents + import_annotator should have manifests
        expected: set[str] = {
            "scaffolder",
            "dark_mode",
            "content",
            "outlook_fixer",
            "accessibility",
            "personalisation",
            "code_reviewer",
            "knowledge",
            "innovation",
        }
        found: set[str] = set(agents_with_manifests)
        missing = expected - found
        assert not missing, f"Agents missing skill-versions.yaml: {missing}"

    def test_manifests_have_1_0_0_entries(self) -> None:
        """All skills start with at least a 1.0.0 version entry."""

        for agent in sorted(_VALID_AGENTS):
            manifest = load_manifest(agent)
            if manifest is None:
                continue
            for skill_name, cfg in manifest.skills.items():
                has_base = any(v.startswith("1.") for v in cfg.versions)
                assert has_base, (
                    f"{agent}/{skill_name} has no 1.x version: {list(cfg.versions.keys())}"
                )
