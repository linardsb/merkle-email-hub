"""Per-client skill overlay tests — discovery, extend/replace, budget, validation.

Phase 32.12: Dedicated overlay integration tests complementing the unit tests
in ``test_skill_loader.py``.
"""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from app.ai.agents.skill_loader import (
    OverlayMeta,
    apply_overlays,
    discover_overlays,
    parse_overlay_meta,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _import_validate_overlays() -> ModuleType:
    """Import scripts/validate-overlays.py as a module (not a package)."""
    script_path = _PROJECT_ROOT / "scripts" / "validate-overlays.py"
    spec = importlib.util.spec_from_file_location("validate_overlays", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_overlays"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_overlay_file(
    base: Path,
    client_id: str,
    agent: str,
    filename: str,
    *,
    token_cost: int = 500,
    priority: int = 2,
    overlay_mode: str = "extend",
    replaces: str | None = None,
    content: str = "Overlay content.",
) -> Path:
    """Create an overlay .md file in the expected directory structure."""
    skills_dir = base / client_id / "agents" / agent / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"token_cost: {token_cost}",
        f"priority: {priority}",
        f"overlay_mode: {overlay_mode}",
    ]
    if replaces:
        lines.append(f"replaces: {replaces}")
    lines.append(f"client_id: {client_id}")
    lines.append("---")
    lines.append(content)
    path = skills_dir / filename
    path.write_text("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# TestDiscoverOverlays
# ---------------------------------------------------------------------------


class TestDiscoverOverlays:
    """Overlay discovery for client+agent pairs."""

    def test_finds_overlays_for_client(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """discover_overlays finds overlay files in data/clients/{client}/agents/{agent}/skills/."""
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()

        _create_overlay_file(
            tmp_path,
            "acme",
            "scaffolder",
            "brand_patterns.md",
            token_cost=400,
            content="Acme brand layout rules.",
        )
        _create_overlay_file(
            tmp_path,
            "acme",
            "scaffolder",
            "cta_styles.md",
            token_cost=200,
            content="Acme CTA styling rules.",
        )

        result = discover_overlays("scaffolder", "acme")
        assert len(result) == 2
        assert all(o.client_id == "acme" for o in result)
        # Sorted by filename
        assert "brand_patterns" in result[0].source_path
        discover_overlays.cache_clear()

    def test_empty_string_client_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty client_id string returns empty tuple."""
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()
        assert discover_overlays("scaffolder", "") == ()
        discover_overlays.cache_clear()

    def test_nonexistent_client_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-existent client returns empty tuple."""
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()
        assert discover_overlays("scaffolder", "nonexistent") == ()
        discover_overlays.cache_clear()

    def test_caching_second_call_uses_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two calls with same args return same object from cache."""
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()

        _create_overlay_file(tmp_path, "acme", "content", "tone.md")

        result1 = discover_overlays("content", "acme")
        result2 = discover_overlays("content", "acme")
        assert result1 is result2  # Same object — cache hit
        discover_overlays.cache_clear()


# ---------------------------------------------------------------------------
# TestExtendMode
# ---------------------------------------------------------------------------


class TestExtendMode:
    """Extend mode appends overlay content after core skills."""

    def test_core_skill_plus_overlay_appended(self) -> None:
        """Both core skill and overlay are present; overlay comes after."""
        parts = ["base prompt", "\n\n--- REFERENCE: brand_voice ---\n\nCore brand voice."]
        overlays = (
            OverlayMeta(
                token_cost=300,
                priority=2,
                overlay_mode="extend",
                content="Extended brand guidelines for Acme.",
                client_id="acme",
                source_path="acme/agents/content/skills/brand_extend.md",
            ),
        )
        result_parts, cost, _names = apply_overlays(parts, {"brand_voice"}, overlays, 0, 2000, 2000)
        assert len(result_parts) == 3
        # Core still present
        assert any("Core brand voice" in p for p in result_parts)
        # Overlay appended
        assert any("Extended brand guidelines" in p for p in result_parts)
        assert cost == 300

    def test_skills_loaded_includes_overlay_name(self) -> None:
        """Overlay name follows 'overlay:{client}/{stem}' format."""
        overlays = (
            OverlayMeta(
                token_cost=200,
                priority=2,
                overlay_mode="extend",
                content="Test.",
                client_id="acme",
                source_path="acme/agents/content/skills/brand_patterns.md",
            ),
        )
        _parts, _cost, names = apply_overlays(["base"], set(), overlays, 0, 2000, 2000)
        assert names == ["overlay:acme/brand_patterns"]


# ---------------------------------------------------------------------------
# TestReplaceMode
# ---------------------------------------------------------------------------


class TestReplaceMode:
    """Replace mode removes core skill and loads overlay in its place."""

    def test_core_skill_removed_overlay_loaded(self) -> None:
        """Core skill removed, overlay replaces it."""
        parts = [
            "base prompt",
            "\n\n--- REFERENCE: brand_voice ---\n\nOriginal brand voice.",
            "\n\n--- REFERENCE: spam_triggers ---\n\nSpam content.",
        ]
        overlays = (
            OverlayMeta(
                token_cost=400,
                priority=1,
                overlay_mode="replace",
                replaces="brand_voice",
                content="Acme-specific brand voice.",
                client_id="acme",
                source_path="acme/agents/content/skills/brand_voice.md",
            ),
        )
        loaded = {"brand_voice", "spam_triggers"}
        result_parts, cost, _names = apply_overlays(parts, loaded, overlays, 0, 2000, 2000)
        # Core brand_voice removed
        assert not any("--- REFERENCE: brand_voice ---" in p for p in result_parts)
        # Spam triggers untouched
        assert any("--- REFERENCE: spam_triggers ---" in p for p in result_parts)
        # Overlay added
        assert any("overlay:acme/brand_voice" in p for p in result_parts)
        assert cost == 400

    def test_skills_loaded_replaces_core_entry(self) -> None:
        """Core skill name removed from loaded set; overlay name added to names."""
        loaded = {"brand_voice", "other_skill"}
        overlays = (
            OverlayMeta(
                token_cost=300,
                priority=1,
                overlay_mode="replace",
                replaces="brand_voice",
                content="Replacement.",
                client_id="acme",
                source_path="acme/agents/content/skills/brand_voice.md",
            ),
        )
        _parts, _cost, names = apply_overlays(["base"], loaded, overlays, 0, 2000, 2000)
        assert "brand_voice" not in loaded
        assert "other_skill" in loaded
        assert names == ["overlay:acme/brand_voice"]


# ---------------------------------------------------------------------------
# TestBudgetAccounting
# ---------------------------------------------------------------------------


class TestBudgetAccounting:
    """Overlay token cost deducted from budget; low-priority overlays dropped."""

    def test_overlay_token_cost_deducted(self) -> None:
        """cumulative_cost increases by overlay's token_cost."""
        overlays = (
            OverlayMeta(
                token_cost=350,
                priority=2,
                overlay_mode="extend",
                content="Test.",
                client_id="acme",
                source_path="acme/agents/dark_mode/skills/brand_colors.md",
            ),
        )
        _parts, cost, _names = apply_overlays(["base"], set(), overlays, 100, 2000, 2000)
        assert cost == 100 + 350

    def test_priority_3_dropped_when_budget_low(self) -> None:
        """Budget < 70% capacity drops priority 3 overlay."""
        overlays = (
            OverlayMeta(
                token_cost=500,
                priority=3,
                overlay_mode="extend",
                content="Supplementary.",
                client_id="acme",
                source_path="acme/agents/dark_mode/skills/extra.md",
            ),
        )
        # 60% capacity (400 used of 1000 budget, 600 remaining = 60%)
        result_parts, cost, names = apply_overlays(["base"], set(), overlays, 400, 1000, 1000)
        assert len(result_parts) == 1  # Only base — overlay dropped
        assert cost == 400
        assert names == []


# ---------------------------------------------------------------------------
# TestValidateOverlaysScript
# ---------------------------------------------------------------------------


class TestValidateOverlaysScript:
    """validate-overlays.py detects invalid frontmatter and conflicts."""

    def test_missing_overlay_mode_defaults_to_extend(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Overlay without overlay_mode defaults to 'extend' (valid)."""
        # parse_overlay_meta defaults to "extend" if no overlay_mode specified
        content = "---\ntoken_cost: 300\nclient_id: test\n---\nBody"
        meta, _body = parse_overlay_meta(content)
        assert meta.overlay_mode == "extend"  # Default is valid

    def test_rejects_invalid_replaces_target(self, tmp_path: Path) -> None:
        """Overlay with overlay_mode=replace but no replaces field is caught by validator."""
        vo = _import_validate_overlays()

        # Create overlay with replace mode but missing replaces field
        monkeypatch_clients = tmp_path / "clients"
        monkeypatch_clients.mkdir()
        skills_dir = monkeypatch_clients / "test_client" / "agents" / "content" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "bad_overlay.md").write_text(
            "---\ntoken_cost: 300\noverlay_mode: replace\nclient_id: test_client\n---\nBody"
        )

        # Patch _CLIENTS_DIR in the validator (dynamic module — mypy can't resolve attrs)
        original = vo._CLIENTS_DIR
        vo._CLIENTS_DIR = monkeypatch_clients  # type: ignore[attr-defined]
        try:
            errors = vo.validate()
        finally:
            vo._CLIENTS_DIR = original  # type: ignore[attr-defined]

        assert any("requires 'replaces'" in e for e in errors)

    def test_rejects_duplicate_replacements(self, tmp_path: Path) -> None:
        """Two overlays replacing the same core skill for same client+agent is a conflict."""
        vo = _import_validate_overlays()

        monkeypatch_clients = tmp_path / "clients"
        skills_dir = monkeypatch_clients / "test_client" / "agents" / "content" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "overlay_a.md").write_text(
            "---\ntoken_cost: 300\noverlay_mode: replace\nreplaces: brand_voice\n"
            "client_id: test_client\n---\nOverlay A"
        )
        (skills_dir / "overlay_b.md").write_text(
            "---\ntoken_cost: 300\noverlay_mode: replace\nreplaces: brand_voice\n"
            "client_id: test_client\n---\nOverlay B"
        )

        original = vo._CLIENTS_DIR
        vo._CLIENTS_DIR = monkeypatch_clients  # type: ignore[attr-defined]
        try:
            errors = vo.validate()
        finally:
            vo._CLIENTS_DIR = original  # type: ignore[attr-defined]

        assert any("Conflict" in e and "brand_voice" in e for e in errors)

    def test_passes_for_example_overlay(self) -> None:
        """The _example client overlay validates without errors."""
        vo = _import_validate_overlays()

        errors = vo.validate()
        # Filter to only _example errors
        example_errors = [e for e in errors if "_example" in e]
        assert not example_errors, f"_example overlay has validation errors: {example_errors}"
