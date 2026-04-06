"""Tests for the deterministic EmailTree -> HTML compiler."""

# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from typing import Any

import pytest

from app.components.tree_compiler import CompiledEmail, TreeCompiler
from app.components.tree_schema import EmailTree
from app.core.exceptions import CompilationError


def _make_tree(**overrides: Any) -> EmailTree:
    """Build a valid EmailTree with sensible defaults."""
    defaults: dict[str, Any] = {
        "metadata": {"subject": "Test Email", "preheader": "Preview"},
        "sections": [
            {
                "component_slug": "hero-block",
                "slot_fills": {
                    "headline": {"type": "text", "text": "Hello World"},
                },
            },
        ],
    }
    defaults.update(overrides)
    return EmailTree.model_validate(defaults)


@pytest.fixture
def compiler() -> TreeCompiler:
    return TreeCompiler()


class TestCompile:
    """End-to-end compilation tests."""

    def test_single_section_valid_html(self, compiler: TreeCompiler) -> None:
        tree = _make_tree()
        result = compiler.compile(tree)

        assert isinstance(result, CompiledEmail)
        assert "<!DOCTYPE" in result.html
        assert "<html" in result.html
        assert "Hello World" in result.html
        assert result.sections_compiled == 1
        assert result.custom_sections == 0

    def test_five_sections_all_rendered(self, compiler: TreeCompiler) -> None:
        sections = [
            {
                "component_slug": "hero-block",
                "slot_fills": {"headline": {"type": "text", "text": f"Section {i}"}},
            }
            for i in range(5)
        ]
        tree = _make_tree(sections=sections)
        result = compiler.compile(tree)

        assert result.sections_compiled == 5
        for i in range(5):
            assert f"Section {i}" in result.html

    def test_custom_section_uses_provided_html(self, compiler: TreeCompiler) -> None:
        sections = [
            {
                "component_slug": "__custom__",
                "custom_html": '<table role="presentation"><tr><td>Custom Content</td></tr></table>',
            },
        ]
        tree = _make_tree(sections=sections)
        result = compiler.compile(tree)

        assert "Custom Content" in result.html
        assert result.custom_sections == 1

    def test_unknown_slug_raises_compilation_error(self, compiler: TreeCompiler) -> None:
        sections = [
            {
                "component_slug": "nonexistent-component",
                "slot_fills": {},
            },
        ]
        tree = _make_tree(sections=sections)
        with pytest.raises(CompilationError, match="nonexistent-component"):
            compiler.compile(tree)


class TestSlotFilling:
    """Slot type-specific filling tests."""

    def test_text_slot_fills_content(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "hero-block",
                    "slot_fills": {
                        "headline": {"type": "text", "text": "Welcome Message"},
                    },
                },
            ],
        )
        result = compiler.compile(tree)
        assert "Welcome Message" in result.html

    def test_image_slot_generates_img(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "hero-block",
                    "slot_fills": {
                        "headline": {"type": "text", "text": "Hero"},
                        "subtext": {
                            "type": "image",
                            "src": "https://example.com/img.png",
                            "alt": "Test Image",
                            "width": 600,
                            "height": 300,
                        },
                    },
                },
            ],
        )
        result = compiler.compile(tree)
        assert "https://example.com/img.png" in result.html
        assert 'alt="Test Image"' in result.html

    def test_button_slot_generates_link(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "button",
                    "slot_fills": {
                        "cta_url": {
                            "type": "button",
                            "text": "Click Me",
                            "href": "https://example.com/cta",
                            "bg_color": "#FF5500",
                            "text_color": "#FFFFFF",
                        },
                    },
                },
            ],
        )
        result = compiler.compile(tree)
        assert "https://example.com/cta" in result.html
        assert "Click Me" in result.html

    def test_button_slot_rejects_javascript_href(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "button",
                    "slot_fills": {
                        "cta_url": {
                            "type": "button",
                            "text": "Evil",
                            "href": "javascript:alert(1)",
                            "bg_color": "#000000",
                            "text_color": "#FFFFFF",
                        },
                    },
                },
            ],
        )
        with pytest.raises(CompilationError, match="Unsafe URL scheme"):
            compiler.compile(tree)

    def test_html_slot_sanitized(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "hero-block",
                    "slot_fills": {
                        "headline": {
                            "type": "html",
                            "html": "<script>alert(1)</script><b>ok</b>",
                        },
                    },
                },
            ],
        )
        result = compiler.compile(tree)
        assert "<script>" not in result.html
        assert "<b>ok</b>" in result.html


class TestStyleOverrides:
    """Style override application tests."""

    def test_style_override_applied_to_root(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "hero-block",
                    "slot_fills": {
                        "headline": {"type": "text", "text": "Styled"},
                    },
                    "style_overrides": {"background-color": "#FF0000"},
                },
            ],
        )
        result = compiler.compile(tree)
        assert "background-color: #FF0000" in result.html


class TestDocumentStructure:
    """Full document structure tests."""

    def test_dark_mode_media_query_present(self, compiler: TreeCompiler) -> None:
        tree = _make_tree()
        result = compiler.compile(tree)
        assert "prefers-color-scheme: dark" in result.html

    def test_mso_conditionals_preserved(self, compiler: TreeCompiler) -> None:
        tree = _make_tree()
        result = compiler.compile(tree)
        assert "<!--[if mso]>" in result.html

    def test_preheader_injected(self, compiler: TreeCompiler) -> None:
        tree = _make_tree(
            metadata={"subject": "Test", "preheader": "Preview text here"},
        )
        result = compiler.compile(tree)
        assert "Preview text here" in result.html


class TestCaching:
    """Section-level caching tests."""

    def test_cache_hit_on_identical_compilation(self, compiler: TreeCompiler) -> None:
        tree = _make_tree()

        # First compile — populates cache
        result1 = compiler.compile(tree)

        # Second compile — should hit cache
        result2 = compiler.compile(tree)

        assert result1.html == result2.html
        # Verify cache is populated (internal check)
        assert len(compiler._section_cache) > 0
