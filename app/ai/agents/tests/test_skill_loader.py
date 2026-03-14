"""Tests for output-mode-aware SKILL.md section extraction."""

from app.ai.agents.skill_loader import extract_skill_for_mode

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
