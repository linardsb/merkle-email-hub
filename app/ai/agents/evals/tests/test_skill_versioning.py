"""Tests for skill file version tracking, pinning, and rollback (Phase 32.10)."""

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import patch

import pytest
import yaml

from app.ai.agents.evals.schemas import SkillFilePatch, SkillUpdateCandidate, SkillVersionEntry
from app.ai.agents.skill_loader import SkillMeta, parse_skill_meta
from app.ai.agents.skill_version import (
    SkillVersionConfig,
    SkillVersionManifest,
    bump_version,
    list_skill_versions,
    load_manifest,
    load_pinned_content,
    pin_skill,
    record_version,
    save_manifest,
    unpin_skill,
)

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_version_entry(
    version: str = "1.0.0",
    git_hash: str = "abc1234",
    date: str = "2026-03-27",
    source: str = "manual",
    eval_pass_rate: float | None = None,
) -> SkillVersionEntry:
    return SkillVersionEntry(
        version=version,
        hash=git_hash,
        date=date,
        source=source,
        eval_pass_rate=eval_pass_rate,
    )


def _make_manifest_dict(
    skill_name: str = "client_behavior",
    current: str = "1.0.0",
    pinned: str | None = None,
    git_hash: str = "abc1234",
) -> dict[str, object]:
    return {
        "skills": {
            skill_name: {
                "current": current,
                "pinned": pinned,
                "versions": {
                    current: {
                        "hash": git_hash,
                        "date": "2026-03-27",
                        "source": "manual",
                        "eval_pass_rate": None,
                    },
                },
            },
        },
    }


def _write_manifest(tmp_path: Path, agent: str, data: dict[str, object]) -> Path:
    agent_dir = tmp_path / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = agent_dir / "skill-versions.yaml"
    manifest_path.write_text(yaml.dump(data, default_flow_style=False))
    return manifest_path


# ---------------------------------------------------------------------------
# TestSkillVersionManifest
# ---------------------------------------------------------------------------


class TestSkillVersionManifest:
    """Load/save YAML manifests."""

    def test_load_manifest(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="color_remapping")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        assert manifest.agent == "dark_mode"
        assert "color_remapping" in manifest.skills
        cfg = manifest.skills["color_remapping"]
        assert cfg.current == "1.0.0"
        assert cfg.pinned is None
        assert "1.0.0" in cfg.versions

    def test_load_missing_manifest_returns_none(self, tmp_path: Path) -> None:
        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            assert load_manifest("nonexistent") is None

    def test_load_invalid_yaml_returns_none(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / "broken"
        agent_dir.mkdir()
        (agent_dir / "skill-versions.yaml").write_text(": : invalid yaml [[[")

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            assert load_manifest("broken") is None

    def test_save_manifest_roundtrip(self, tmp_path: Path) -> None:
        entry = _make_version_entry(version="1.0.0", eval_pass_rate=0.85)
        manifest = SkillVersionManifest(
            agent="dark_mode",
            skills={
                "color_remapping": SkillVersionConfig(
                    current="1.0.0",
                    pinned=None,
                    versions={"1.0.0": entry},
                ),
            },
        )
        (tmp_path / "dark_mode").mkdir()

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            save_manifest(manifest)
            loaded = load_manifest("dark_mode")

        assert loaded is not None
        assert loaded.skills["color_remapping"].current == "1.0.0"
        assert loaded.skills["color_remapping"].versions["1.0.0"].eval_pass_rate == 0.85

    def test_load_manifest_with_multiple_versions(self, tmp_path: Path) -> None:
        data: dict[str, object] = {
            "skills": {
                "client_behavior": {
                    "current": "1.1.0",
                    "pinned": None,
                    "versions": {
                        "1.0.0": {
                            "hash": "aaa1111",
                            "date": "2026-03-01",
                            "source": "manual",
                            "eval_pass_rate": None,
                        },
                        "1.1.0": {
                            "hash": "bbb2222",
                            "date": "2026-03-20",
                            "source": "eval-driven",
                            "eval_pass_rate": 0.87,
                        },
                    },
                },
            },
        }
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        cfg = manifest.skills["client_behavior"]
        assert cfg.current == "1.1.0"
        assert len(cfg.versions) == 2
        assert cfg.versions["1.1.0"].source == "eval-driven"
        assert cfg.versions["1.1.0"].eval_pass_rate == 0.87


# ---------------------------------------------------------------------------
# TestPinUnpin
# ---------------------------------------------------------------------------


class TestPinUnpin:
    """Pin/unpin operations update the manifest."""

    def test_pin_skill_sets_pinned(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            pin_skill("dark_mode", "client_behavior", "1.0.0")
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        assert manifest.skills["client_behavior"].pinned == "1.0.0"

    def test_unpin_skill_clears_pinned(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior", pinned="1.0.0")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            unpin_skill("dark_mode", "client_behavior")
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        assert manifest.skills["client_behavior"].pinned is None

    def test_pin_nonexistent_version_raises(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"Version.*not found"),
        ):
            pin_skill("dark_mode", "client_behavior", "9.9.9")

    def test_pin_nonexistent_skill_raises(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match="not in manifest"),
        ):
            pin_skill("dark_mode", "nonexistent", "1.0.0")

    def test_pin_no_manifest_raises(self, tmp_path: Path) -> None:
        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"No skill-versions\.yaml"),
        ):
            pin_skill("dark_mode", "client_behavior", "1.0.0")


# ---------------------------------------------------------------------------
# TestLoadPinnedContent
# ---------------------------------------------------------------------------


class TestLoadPinnedContent:
    """Loading pinned versions from git."""

    def test_returns_none_when_no_pin(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            result = load_pinned_content("dark_mode", "client_behavior")

        assert result is None

    def test_returns_none_when_no_manifest(self, tmp_path: Path) -> None:
        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            result = load_pinned_content("dark_mode", "client_behavior")

        assert result is None

    def test_loads_content_from_git_when_pinned(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior", pinned="1.0.0")
        _write_manifest(tmp_path, "dark_mode", data)
        # Create skills dir so path resolution finds it
        (tmp_path / "dark_mode" / "skills").mkdir(parents=True)
        (tmp_path / "dark_mode" / "skills" / "client_behavior.md").write_text("on-disk")

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            patch("app.ai.agents.skill_version.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value = CompletedProcess(
                args=[],
                returncode=0,
                stdout=b'---\nversion: "1.0.0"\n---\n# Pinned content from git',
            )
            result = load_pinned_content("dark_mode", "client_behavior")

        assert result is not None
        assert "Pinned content from git" in result

    def test_returns_none_on_git_failure(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior", pinned="1.0.0")
        _write_manifest(tmp_path, "dark_mode", data)
        (tmp_path / "dark_mode" / "skills").mkdir(parents=True)
        (tmp_path / "dark_mode" / "skills" / "client_behavior.md").write_text("on-disk")

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            patch("app.ai.agents.skill_version.subprocess") as mock_sub,
        ):
            mock_sub.run.side_effect = CalledProcessError(
                returncode=128,
                cmd=["git", "show"],
            )
            result = load_pinned_content("dark_mode", "client_behavior")

        assert result is None


# ---------------------------------------------------------------------------
# TestBumpVersion
# ---------------------------------------------------------------------------


class TestBumpVersion:
    """Semver minor bump logic."""

    def test_minor_bump(self) -> None:
        assert bump_version("1.0.0") == "1.1.0"

    def test_increments_minor(self) -> None:
        assert bump_version("1.3.0") == "1.4.0"

    def test_resets_patch_implied(self) -> None:
        assert bump_version("2.5.3") == "2.6.0"

    def test_invalid_format_returns_default(self) -> None:
        assert bump_version("bad") == "1.1.0"

    def test_non_numeric_returns_default(self) -> None:
        assert bump_version("a.b.c") == "1.1.0"


# ---------------------------------------------------------------------------
# TestRecordVersion
# ---------------------------------------------------------------------------


class TestRecordVersion:
    """Recording a new version entry."""

    def test_adds_version_and_updates_current(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            record_version(
                agent="dark_mode",
                skill_name="client_behavior",
                version="1.1.0",
                git_hash="def5678",
                source="eval-driven",
                eval_pass_rate=0.90,
            )
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        cfg = manifest.skills["client_behavior"]
        assert cfg.current == "1.1.0"
        assert "1.1.0" in cfg.versions
        assert cfg.versions["1.1.0"].hash == "def5678"
        assert cfg.versions["1.1.0"].source == "eval-driven"
        assert cfg.versions["1.1.0"].eval_pass_rate == 0.90
        # Original version still present
        assert "1.0.0" in cfg.versions

    def test_no_manifest_raises(self, tmp_path: Path) -> None:
        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"No skill-versions\.yaml"),
        ):
            record_version("dark_mode", "skill", "1.0.0", "abc1234")


# ---------------------------------------------------------------------------
# TestSkillMetaVersion
# ---------------------------------------------------------------------------


class TestSkillMetaVersion:
    """parse_skill_meta() extracts the version field."""

    def test_parses_version_from_frontmatter(self) -> None:
        content = '---\ntoken_cost: 800\npriority: 1\nversion: "2.1.0"\n---\n# Content'
        meta, _body = parse_skill_meta(content)
        assert meta.version == "2.1.0"
        assert meta.token_cost == 800

    def test_version_without_quotes(self) -> None:
        content = "---\nversion: 1.3.0\n---\n# Content"
        meta, _body = parse_skill_meta(content)
        assert meta.version == "1.3.0"

    def test_default_version_when_missing(self) -> None:
        content = "---\ntoken_cost: 500\n---\n# Content"
        meta, _body = parse_skill_meta(content)
        assert meta.version == "1.0.0"

    def test_default_version_when_no_frontmatter(self) -> None:
        content = "# No frontmatter"
        meta, _body = parse_skill_meta(content)
        assert meta.version == "1.0.0"

    def test_skill_meta_has_version_field(self) -> None:
        meta = SkillMeta(token_cost=100, priority=1, version="3.0.0")
        assert meta.version == "3.0.0"

    def test_skill_meta_default_version(self) -> None:
        meta = SkillMeta()
        assert meta.version == "1.0.0"


# ---------------------------------------------------------------------------
# TestListSkillVersions
# ---------------------------------------------------------------------------


class TestListSkillVersions:
    """Version listing returns sorted entries."""

    def test_returns_versions_sorted_by_date_desc(self, tmp_path: Path) -> None:
        data: dict[str, object] = {
            "skills": {
                "client_behavior": {
                    "current": "1.1.0",
                    "pinned": None,
                    "versions": {
                        "1.0.0": {
                            "hash": "aaa1111",
                            "date": "2026-03-01",
                            "source": "manual",
                            "eval_pass_rate": None,
                        },
                        "1.1.0": {
                            "hash": "bbb2222",
                            "date": "2026-03-20",
                            "source": "eval-driven",
                            "eval_pass_rate": 0.87,
                        },
                    },
                },
            },
        }
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            versions = list_skill_versions("dark_mode", "client_behavior")

        assert len(versions) == 2
        assert versions[0].version == "1.1.0"  # Most recent first
        assert versions[1].version == "1.0.0"

    def test_returns_empty_for_missing_manifest(self, tmp_path: Path) -> None:
        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            assert list_skill_versions("dark_mode", "client_behavior") == []

    def test_returns_empty_for_missing_skill(self, tmp_path: Path) -> None:
        data = _make_manifest_dict(skill_name="other_skill")
        _write_manifest(tmp_path, "dark_mode", data)

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            assert list_skill_versions("dark_mode", "client_behavior") == []


# ---------------------------------------------------------------------------
# TestSetOverrideFromVersion
# ---------------------------------------------------------------------------


class TestSetOverrideFromVersion:
    """Version-aware override for A/B testing."""

    def test_sets_override_from_git_content(self, tmp_path: Path) -> None:
        from app.ai.agents.skill_override import (
            clear_override,
            get_override,
            set_override_from_version,
        )

        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)
        (tmp_path / "dark_mode" / "skills").mkdir(parents=True)
        (tmp_path / "dark_mode" / "skills" / "client_behavior.md").write_text("disk")

        try:
            with (
                patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
                patch("app.ai.agents.skill_version.subprocess") as mock_sub,
            ):
                mock_sub.run.return_value = CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=b"# Versioned content",
                )
                set_override_from_version("dark_mode", "client_behavior", "1.0.0")

            assert get_override("dark_mode") == "# Versioned content"
        finally:
            clear_override("dark_mode")

    def test_raises_for_missing_manifest(self, tmp_path: Path) -> None:
        from app.ai.agents.skill_override import set_override_from_version

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"No skill-versions\.yaml"),
        ):
            set_override_from_version("dark_mode", "client_behavior", "1.0.0")

    def test_raises_for_missing_version(self, tmp_path: Path) -> None:
        from app.ai.agents.skill_override import set_override_from_version

        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        with (
            patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path),
            pytest.raises(ValueError, match=r"Version.*not found"),
        ):
            set_override_from_version("dark_mode", "client_behavior", "9.9.9")


# ---------------------------------------------------------------------------
# TestUpdaterIntegration
# ---------------------------------------------------------------------------


class TestUpdaterIntegration:
    """Skill updater bumps version and updates manifest."""

    def test_update_frontmatter_version_adds_to_existing(self, tmp_path: Path) -> None:
        from app.ai.agents.evals.skill_updater import _update_frontmatter_version

        skill_file = tmp_path / "skill.md"
        skill_file.write_text('---\npriority: 2\nversion: "1.0.0"\n---\n# Content')

        _update_frontmatter_version(skill_file, skill_file.read_text(), "1.1.0")

        result = skill_file.read_text()
        assert 'version: "1.1.0"' in result
        assert 'version: "1.0.0"' not in result
        assert "priority: 2" in result

    def test_update_frontmatter_version_no_existing_version(self, tmp_path: Path) -> None:
        from app.ai.agents.evals.skill_updater import _update_frontmatter_version

        skill_file = tmp_path / "skill.md"
        skill_file.write_text("---\npriority: 3\n---\n# Content")

        _update_frontmatter_version(skill_file, skill_file.read_text(), "1.1.0")

        result = skill_file.read_text()
        assert 'version: "1.1.0"' in result
        assert "priority: 3" in result

    def test_update_frontmatter_version_no_frontmatter(self, tmp_path: Path) -> None:
        from app.ai.agents.evals.skill_updater import _update_frontmatter_version

        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Content only")

        _update_frontmatter_version(skill_file, skill_file.read_text(), "1.1.0")

        result = skill_file.read_text()
        assert result.startswith("---\n")
        assert 'version: "1.1.0"' in result
        assert "# Content only" in result

    def test_update_version_manifests(self, tmp_path: Path) -> None:
        from app.ai.agents.evals.skill_updater import _update_version_manifests

        # Create skill file with version
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        skill_file = skill_dir / "client_behavior.md"
        skill_file.write_text('---\nversion: "1.0.0"\n---\n# Skill')

        # Create manifest
        data = _make_manifest_dict(skill_name="client_behavior")
        _write_manifest(tmp_path, "dark_mode", data)

        candidate = SkillUpdateCandidate(
            agent="dark_mode",
            criterion="media_query",
            pass_rate=0.65,
            failure_count=8,
            failure_cluster="missing query",
            target_skill_file=str(skill_file),
        )
        patch_obj = SkillFilePatch(
            skill_file_path=str(skill_file),
            patch_content="## New section",
            candidate=candidate,
            confidence="HIGH",
        )

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            manifest_files = _update_version_manifests([patch_obj])

        # Frontmatter bumped
        content = skill_file.read_text()
        assert 'version: "1.1.0"' in content

        # Manifest updated
        assert len(manifest_files) >= 1

        with patch("app.ai.agents.skill_version._AGENTS_BASE", tmp_path):
            manifest = load_manifest("dark_mode")

        assert manifest is not None
        cfg = manifest.skills["client_behavior"]
        assert cfg.current == "1.1.0"
        assert "1.1.0" in cfg.versions
        assert cfg.versions["1.1.0"].source == "eval-driven"
