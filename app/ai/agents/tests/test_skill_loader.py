"""Tests for output-mode-aware SKILL.md section extraction."""

from app.ai.agents.skill_loader import (
    SkillMeta,
    extract_skill_for_mode,
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
