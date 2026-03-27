"""Tests for output-mode-aware SKILL.md section extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.agents.skill_loader import (
    OverlayMeta,
    SkillMeta,
    apply_overlays,
    discover_overlays,
    extract_skill_for_mode,
    parse_overlay_meta,
    parse_skill_meta,
    should_load_skill,
)

_SAMPLE_SKILL = """---
name: test-agent
---

# Test Agent

## Domain Knowledge

Important domain rules here.

## Confidence Assessment

Assess confidence based on...

## Output Format: HTML

Return complete HTML with all fixes applied.
Include <!-- CONFIDENCE: X.XX --> comment.

## Output Format: Structured

Return a JSON object matching TestPlan schema.
Do NOT return HTML.

### TestPlan Schema

```json
{"fixes": [], "reasoning": ""}
```

## Security Rules (ABSOLUTE)

Never include scripts or event handlers.
"""


class TestExtractSkillForMode:
    def test_html_mode_excludes_structured_section(self) -> None:
        result = extract_skill_for_mode(_SAMPLE_SKILL, "html")
        assert "## Output Format: HTML" in result
        assert "## Output Format: Structured" not in result
        assert "## Security Rules" in result
        assert "## Domain Knowledge" in result

    def test_structured_mode_excludes_html_section(self) -> None:
        result = extract_skill_for_mode(_SAMPLE_SKILL, "structured")
        assert "## Output Format: Structured" in result
        assert "## Output Format: HTML" not in result
        assert "## Security Rules" in result
        assert "## Domain Knowledge" in result

    def test_shared_sections_always_included(self) -> None:
        for mode in ("html", "structured"):
            result = extract_skill_for_mode(_SAMPLE_SKILL, mode)
            assert "# Test Agent" in result
            assert "## Domain Knowledge" in result
            assert "## Confidence Assessment" in result
            assert "## Security Rules (ABSOLUTE)" in result

    def test_backward_compatible_with_legacy_skill(self) -> None:
        legacy = "---\nname: old\n---\n# Old Agent\n\nNo output format sections."
        result = extract_skill_for_mode(legacy, "html")
        assert result == legacy
        result2 = extract_skill_for_mode(legacy, "structured")
        assert result2 == legacy

    def test_default_mode_is_html(self) -> None:
        result = extract_skill_for_mode(_SAMPLE_SKILL)
        assert "## Output Format: HTML" in result
        assert "## Output Format: Structured" not in result

    def test_preserves_frontmatter(self) -> None:
        result = extract_skill_for_mode(_SAMPLE_SKILL, "structured")
        assert "name: test-agent" in result

    def test_preserves_schema_in_structured(self) -> None:
        result = extract_skill_for_mode(_SAMPLE_SKILL, "structured")
        assert "TestPlan Schema" in result
        assert '"fixes": []' in result

    def test_empty_content(self) -> None:
        result = extract_skill_for_mode("", "html")
        assert result == ""

    def test_security_rules_included_in_both_modes(self) -> None:
        html = extract_skill_for_mode(_SAMPLE_SKILL, "html")
        structured = extract_skill_for_mode(_SAMPLE_SKILL, "structured")
        assert "Never include scripts" in html
        assert "Never include scripts" in structured


class TestParseSkillMeta:
    def test_parses_front_matter(self) -> None:
        content = "---\ntoken_cost: 1200\npriority: 1\n---\n# Skill content"
        meta, body = parse_skill_meta(content)
        assert meta.token_cost == 1200
        assert meta.priority == 1
        assert body.strip() == "# Skill content"

    def test_no_front_matter_returns_defaults(self) -> None:
        content = "# Skill content without front matter"
        meta, body = parse_skill_meta(content)
        assert meta.token_cost == 500
        assert meta.priority == 2
        assert body == content

    def test_partial_front_matter(self) -> None:
        content = "---\npriority: 3\n---\nBody"
        meta, _body = parse_skill_meta(content)
        assert meta.priority == 3
        assert meta.token_cost == 500  # default

    def test_invalid_values_use_defaults(self) -> None:
        content = "---\ntoken_cost: abc\npriority: xyz\n---\nBody"
        meta, _body = parse_skill_meta(content)
        assert meta.token_cost == 500
        assert meta.priority == 2


class TestShouldLoadSkill:
    def test_priority_1_always_loads(self) -> None:
        meta = SkillMeta(token_cost=5000, priority=1)
        assert should_load_skill(meta, cumulative_cost=0, remaining_budget=100, budget_max=1000)

    def test_priority_2_loads_with_budget(self) -> None:
        meta = SkillMeta(token_cost=500, priority=2)
        assert should_load_skill(meta, cumulative_cost=0, remaining_budget=2000, budget_max=2000)

    def test_priority_2_skipped_when_tight(self) -> None:
        meta = SkillMeta(token_cost=500, priority=2)
        # 20% capacity — below 30% threshold for priority 2
        assert not should_load_skill(
            meta, cumulative_cost=800, remaining_budget=1000, budget_max=1000
        )

    def test_priority_3_skipped_early(self) -> None:
        meta = SkillMeta(token_cost=500, priority=3)
        # 60% capacity — below 70% threshold for priority 3
        assert not should_load_skill(
            meta, cumulative_cost=400, remaining_budget=1000, budget_max=1000
        )

    def test_priority_3_loads_with_plenty_of_budget(self) -> None:
        meta = SkillMeta(token_cost=200, priority=3)
        assert should_load_skill(meta, cumulative_cost=0, remaining_budget=2000, budget_max=2000)

    def test_insufficient_absolute_budget(self) -> None:
        meta = SkillMeta(token_cost=1000, priority=2)
        assert not should_load_skill(
            meta, cumulative_cost=500, remaining_budget=600, budget_max=2000
        )


# ---------------------------------------------------------------------------
# Phase 32.11: Per-client skill overlay tests
# ---------------------------------------------------------------------------


class TestParseOverlayMeta:
    def test_parses_overlay_fields(self) -> None:
        content = (
            "---\n"
            "token_cost: 800\n"
            "priority: 1\n"
            'overlay_mode: "replace"\n'
            'replaces: "brand_voice"\n'
            'client_id: "acme"\n'
            "---\n"
            "# Brand patterns\n"
        )
        meta, body = parse_overlay_meta(content)
        assert meta.token_cost == 800
        assert meta.priority == 1
        assert meta.overlay_mode == "replace"
        assert meta.replaces == "brand_voice"
        assert meta.client_id == "acme"
        assert body.strip() == "# Brand patterns"

    def test_defaults_to_extend_mode(self) -> None:
        content = "---\ntoken_cost: 500\n---\nBody"
        meta, _body = parse_overlay_meta(content)
        assert meta.overlay_mode == "extend"
        assert meta.replaces is None

    def test_invalid_overlay_mode_uses_default(self) -> None:
        content = "---\noverlay_mode: invalid\n---\nBody"
        meta, _body = parse_overlay_meta(content)
        assert meta.overlay_mode == "extend"

    def test_replaces_null_is_none(self) -> None:
        content = "---\nreplaces: null\n---\nBody"
        meta, _body = parse_overlay_meta(content)
        assert meta.replaces is None

    def test_no_frontmatter_returns_defaults(self) -> None:
        content = "# No frontmatter here"
        meta, body = parse_overlay_meta(content)
        assert meta.overlay_mode == "extend"
        assert meta.token_cost == 500
        assert body == content

    def test_unquoted_values(self) -> None:
        content = (
            "---\noverlay_mode: replace\nreplaces: color_remapping\nclient_id: acme\n---\nBody"
        )
        meta, _body = parse_overlay_meta(content)
        assert meta.overlay_mode == "replace"
        assert meta.replaces == "color_remapping"
        assert meta.client_id == "acme"


class TestDiscoverOverlays:
    def test_returns_empty_for_nonexistent_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", Path("/nonexistent/path"))
        discover_overlays.cache_clear()
        result = discover_overlays("dark_mode", "acme")
        assert result == ()
        discover_overlays.cache_clear()

    def test_discovers_overlay_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()

        # Create overlay files
        skills_dir = tmp_path / "acme" / "agents" / "dark_mode" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "brand_colors.md").write_text(
            "---\ntoken_cost: 300\npriority: 2\noverlay_mode: extend\nclient_id: acme\n---\n"
            "Dark mode color mappings for Acme brand.\n"
        )
        (skills_dir / "accessibility.md").write_text(
            "---\ntoken_cost: 200\npriority: 3\noverlay_mode: extend\nclient_id: acme\n---\n"
            "Acme-specific a11y rules.\n"
        )

        result = discover_overlays("dark_mode", "acme")
        assert len(result) == 2
        # Sorted by filename
        assert result[0].source_path == "acme/agents/dark_mode/skills/accessibility.md"
        assert result[1].source_path == "acme/agents/dark_mode/skills/brand_colors.md"
        assert result[1].token_cost == 300
        assert result[1].client_id == "acme"
        assert "Dark mode color mappings" in result[1].content
        discover_overlays.cache_clear()

    def test_caches_results(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", tmp_path)
        discover_overlays.cache_clear()

        skills_dir = tmp_path / "acme" / "agents" / "scaffolder" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text("---\ntoken_cost: 100\n---\nTest\n")

        result1 = discover_overlays("scaffolder", "acme")
        result2 = discover_overlays("scaffolder", "acme")
        assert result1 is result2  # Same object from cache
        discover_overlays.cache_clear()

    def test_rejects_path_traversal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.ai.agents.skill_loader as sl

        monkeypatch.setattr(sl, "_OVERLAYS_BASE", Path("/tmp/test"))
        discover_overlays.cache_clear()

        assert discover_overlays("dark_mode", "../etc") == ()
        assert discover_overlays("dark_mode", "acme/../../etc") == ()
        assert discover_overlays("dark_mode", "acme\\..\\etc") == ()
        discover_overlays.cache_clear()


class TestApplyOverlays:
    def test_extend_mode_appends_content(self) -> None:
        parts = ["base prompt", "\n\n--- REFERENCE: color_remapping ---\n\nCore skill body"]
        overlays = (
            OverlayMeta(
                token_cost=300,
                priority=2,
                overlay_mode="extend",
                content="Brand color guidance.",
                client_id="acme",
                source_path="acme/agents/dark_mode/skills/brand_colors.md",
            ),
        )
        result_parts, cost, names = apply_overlays(
            parts, {"color_remapping"}, overlays, 0, 2000, 2000
        )
        assert len(result_parts) == 3
        assert "overlay:acme/brand_colors" in result_parts[2]
        assert "Brand color guidance." in result_parts[2]
        assert cost == 300
        assert names == ["overlay:acme/brand_colors"]

    def test_replace_mode_removes_core_skill(self) -> None:
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
                content="Acme brand voice.",
                client_id="acme",
                source_path="acme/agents/content/skills/brand_voice.md",
            ),
        )
        loaded = {"brand_voice", "spam_triggers"}
        result_parts, cost, names = apply_overlays(parts, loaded, overlays, 0, 2000, 2000)
        # Core brand_voice should be removed
        assert not any("--- REFERENCE: brand_voice ---" in p for p in result_parts)
        # Spam triggers should remain
        assert any("--- REFERENCE: spam_triggers ---" in p for p in result_parts)
        # Overlay should be added
        assert any("overlay:acme/brand_voice" in p for p in result_parts)
        assert "brand_voice" not in loaded  # Removed from set
        assert cost == 400
        assert names == ["overlay:acme/brand_voice"]

    def test_budget_pressure_drops_low_priority_overlay(self) -> None:
        overlays = (
            OverlayMeta(
                token_cost=500,
                priority=3,
                overlay_mode="extend",
                content="Supplementary content.",
                client_id="acme",
                source_path="acme/agents/dark_mode/skills/extra.md",
            ),
        )
        # 60% capacity — below 70% threshold for priority 3
        result_parts, cost, names = apply_overlays(["base"], set(), overlays, 400, 1000, 1000)
        assert len(result_parts) == 1  # Only base, overlay dropped
        assert cost == 400
        assert names == []

    def test_priority_1_overlay_always_loads(self) -> None:
        overlays = (
            OverlayMeta(
                token_cost=5000,
                priority=1,
                overlay_mode="extend",
                content="Critical brand rules.",
                client_id="acme",
                source_path="acme/agents/dark_mode/skills/critical.md",
            ),
        )
        result_parts, _cost, names = apply_overlays(["base"], set(), overlays, 0, 100, 1000)
        assert len(result_parts) == 2
        assert names == ["overlay:acme/critical"]

    def test_overlay_names_prefixed_with_overlay_colon(self) -> None:
        overlays = (
            OverlayMeta(
                token_cost=100,
                priority=2,
                overlay_mode="extend",
                content="Test.",
                client_id="brandx",
                source_path="brandx/agents/scaffolder/skills/layout_rules.md",
            ),
        )
        _parts, _cost, names = apply_overlays(["base"], set(), overlays, 0, 2000, 2000)
        assert names == ["overlay:brandx/layout_rules"]

    def test_empty_overlays_returns_unchanged(self) -> None:
        parts = ["base prompt", "skill content"]
        result_parts, cost, names = apply_overlays(parts, set(), (), 100, 2000, 2000)
        assert result_parts == parts
        assert cost == 100
        assert names == []
