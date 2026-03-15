"""Tests for component design-system agnosticism via default_tokens."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.agents.scaffolder.assembler import TemplateAssembler
from app.ai.agents.schemas.build_plan import DesignTokens
from app.ai.templates.models import DefaultTokens
from app.components.section_adapter import SectionAdapter


@dataclass
class FakeComponentVersion:
    """Fake ComponentVersion for testing."""

    id: int = 1
    component_id: int = 10
    version_number: int = 1
    html_source: str = '<div><a href="#" style="color: #aabbcc;">Click</a></div>'
    default_tokens: dict[str, object] | None = None


class TestSectionAdapterTokens:
    def test_passes_default_tokens(self) -> None:
        version = FakeComponentVersion(
            default_tokens={
                "colors": {"cta": "#aabbcc", "heading": "#112233"},
                "fonts": {"body": "Arial, sans-serif"},
            },
        )
        adapter = SectionAdapter()
        block = adapter.adapt(version, [])
        assert block.default_tokens is not None
        assert block.default_tokens.colors["cta"] == "#aabbcc"
        assert block.default_tokens.fonts["body"] == "Arial, sans-serif"

    def test_no_tokens(self) -> None:
        version = FakeComponentVersion(default_tokens=None)
        adapter = SectionAdapter()
        block = adapter.adapt(version, [])
        assert block.default_tokens is None


class TestComponentPaletteReplacement:
    def test_component_colors_replaced(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"cta": "#aabbcc"})
        tokens = DesignTokens(colors={"cta": "#ff0000"})

        html = '<a style="background-color: #aabbcc;">Click</a>'
        result = assembler._apply_palette_replacement(html, defaults, tokens)
        assert "#ff0000" in result
        assert "#aabbcc" not in result

    def test_agnostic_two_clients(self) -> None:
        """Same component defaults, two different client design systems -> different output."""
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"cta": "#aabbcc", "heading": "#112233"})

        # Client A
        tokens_a = DesignTokens(colors={"cta": "#ff0000", "heading": "#000000"})
        html = '<td style="background-color: #aabbcc;"><h1 style="color: #112233;">Hi</h1></td>'
        result_a = assembler._apply_palette_replacement(html, defaults, tokens_a)

        # Client B
        tokens_b = DesignTokens(colors={"cta": "#00ff00", "heading": "#333333"})
        result_b = assembler._apply_palette_replacement(html, defaults, tokens_b)

        # Different outputs
        assert "#ff0000" in result_a
        assert "#000000" in result_a
        assert "#00ff00" in result_b
        assert "#333333" in result_b
        assert result_a != result_b
