"""Tests for the email component tree schema."""

# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from app.components.tree_schema import (
    ButtonSlot,
    EmailTree,
    HtmlSlot,
    ImageSlot,
    TextSlot,
    TreeMetadata,
    TreeSection,
    export_json_schema,
    validate_tree_against_manifest,
)
from app.mcp.resources import register_resources

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "email-tree.json"

# --- Fixtures ---


def _make_tree(**overrides: Any) -> EmailTree:
    """Build a valid EmailTree with sensible defaults."""
    defaults: dict[str, Any] = {
        "metadata": {"subject": "Weekly Newsletter"},
        "sections": [
            {
                "component_slug": "hero-block",
                "slot_fills": {
                    "headline": {"type": "text", "text": "Hello World"},
                    "hero_image": {
                        "type": "image",
                        "src": "https://example.com/hero.png",
                        "alt": "Hero",
                        "width": 600,
                        "height": 300,
                    },
                },
            },
            {
                "component_slug": "text-block",
                "slot_fills": {
                    "body": {"type": "text", "text": "Lorem ipsum dolor sit amet."},
                },
            },
            {
                "component_slug": "button",
                "slot_fills": {
                    "cta": {
                        "type": "button",
                        "text": "Shop Now",
                        "href": "https://example.com",
                        "bg_color": "#0066cc",
                        "text_color": "#ffffff",
                    },
                },
            },
            {
                "component_slug": "social-icons",
                "style_overrides": {"background-color": "#f5f5f5"},
            },
            {
                "component_slug": "divider",
            },
        ],
    }
    defaults.update(overrides)
    return EmailTree.model_validate(defaults)


class TestEmailTreeValidation:
    """Pydantic model validation tests."""

    def test_valid_tree_5_sections(self) -> None:
        """Valid tree with 5 sections, mixed slot types passes."""
        tree = _make_tree()
        assert len(tree.sections) == 5
        assert tree.metadata.subject == "Weekly Newsletter"
        assert tree.metadata.preheader == ""
        # Check slot types are correctly discriminated
        hero = tree.sections[0]
        assert isinstance(hero.slot_fills["headline"], TextSlot)
        assert isinstance(hero.slot_fills["hero_image"], ImageSlot)
        cta_section = tree.sections[2]
        assert isinstance(cta_section.slot_fills["cta"], ButtonSlot)

    def test_custom_html_without_custom_slug_error(self) -> None:
        """custom_html on non-__custom__ slug raises ValidationError."""
        with pytest.raises(ValidationError, match="custom_html is only allowed"):
            TreeSection(
                component_slug="hero-block",
                custom_html="<table><tr><td>Custom</td></tr></table>",
            )

    def test_custom_html_with_custom_slug_ok(self) -> None:
        """__custom__ slug + custom_html passes validation."""
        section = TreeSection(
            component_slug="__custom__",
            custom_html="<table><tr><td>Custom</td></tr></table>",
        )
        assert section.custom_html is not None
        assert section.component_slug == "__custom__"

    def test_invalid_css_property_name(self) -> None:
        """style_overrides with bad key raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid CSS property name"):
            TreeSection(
                component_slug="hero-block",
                style_overrides={"123bad": "red"},
            )

    def test_empty_sections_error(self) -> None:
        """sections=[] raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError, match="List should have at least 1 item"):
            EmailTree(
                metadata=TreeMetadata(subject="Test"),
                sections=[],
            )

    def test_slot_discriminated_union(self) -> None:
        """Each SlotValue variant round-trips through JSON correctly."""
        slots: dict[str, dict[str, Any]] = {
            "text_slot": {"type": "text", "text": "Hello"},
            "image_slot": {
                "type": "image",
                "src": "img.png",
                "alt": "Alt",
                "width": 100,
                "height": 100,
            },
            "button_slot": {
                "type": "button",
                "text": "Click",
                "href": "https://x.com",
                "bg_color": "#000000",
                "text_color": "#ffffff",
            },
            "html_slot": {"type": "html", "html": "<b>Bold</b>"},
        }
        section = TreeSection.model_validate({"component_slug": "hero-block", "slot_fills": slots})
        # Round-trip through JSON
        raw = section.model_dump(mode="json")
        restored = TreeSection.model_validate(raw)
        assert isinstance(restored.slot_fills["text_slot"], TextSlot)
        assert isinstance(restored.slot_fills["image_slot"], ImageSlot)
        assert isinstance(restored.slot_fills["button_slot"], ButtonSlot)
        assert isinstance(restored.slot_fills["html_slot"], HtmlSlot)


class TestManifestValidation:
    """Manifest cross-validation tests."""

    def test_unknown_slug_manifest_validation(self) -> None:
        """validate_tree_against_manifest catches unknown slug."""
        tree = _make_tree(
            sections=[{"component_slug": "nonexistent-widget"}],
        )
        errors = validate_tree_against_manifest(
            tree,
            manifest_slugs={"hero-block", "button"},
            slot_definitions={},
        )
        assert len(errors) == 1
        assert "unknown component_slug 'nonexistent-widget'" in errors[0]

    def test_wrong_slot_name_manifest_validation(self) -> None:
        """validate_tree_against_manifest catches invalid slot key."""
        tree = _make_tree(
            sections=[
                {
                    "component_slug": "button",
                    "slot_fills": {
                        "bogus_slot": {"type": "text", "text": "Oops"},
                    },
                },
            ],
        )
        errors = validate_tree_against_manifest(
            tree,
            manifest_slugs={"button"},
            slot_definitions={"button": ["cta_url", "cta_text"]},
        )
        assert len(errors) == 1
        assert "slot 'bogus_slot' not defined for component 'button'" in errors[0]


class TestJsonSchemaExport:
    """JSON Schema export and drift detection."""

    def test_json_schema_export_matches_file(self) -> None:
        """export_json_schema() matches checked-in schemas/email-tree.json."""
        assert SCHEMA_PATH.exists(), f"Schema file not found: {SCHEMA_PATH}"
        checked_in = json.loads(SCHEMA_PATH.read_text())
        generated = export_json_schema()
        assert generated == checked_in, (
            "JSON Schema drift detected — run: "
            'python -c "from app.components.tree_schema import write_json_schema; write_json_schema()"'
        )


class TestMCPResource:
    """MCP resource integration test."""

    def test_mcp_resource_returns_schema(self) -> None:
        """MCP resource hub://component-tree-schema returns valid JSON Schema."""
        mcp = FastMCP("test")

        # Patch settings to avoid real config loading
        with MagicMock() as _:
            register_resources(mcp)

        resources: Any = mcp._resource_manager._resources
        assert "hub://component-tree-schema" in resources

        result = resources["hub://component-tree-schema"].fn()
        schema = json.loads(result)
        assert schema["title"] == "EmailTree"
        assert "$defs" in schema
        assert "TreeSection" in schema["$defs"]
