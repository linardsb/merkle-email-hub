"""Test _parse_node against real Figma API response fixtures (39.2.1)."""

from __future__ import annotations

import json
import pathlib

import pytest

from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.protocol import DesignNode, DesignNodeType

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

ALL_FIXTURES = [
    "mammut_hero",
    "ecommerce_grid",
    "newsletter_2col",
    "transactional",
    "navigation_header",
]


@pytest.fixture()
def svc() -> FigmaDesignSyncService:
    return FigmaDesignSyncService()


# ------------------------------------------------------------------
# Generic invariants — every fixture must satisfy these
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_parse_real_fixture_invariants(
    svc: FigmaDesignSyncService,
    fixture_name: str,
) -> None:
    """Core invariants: id, type, visible, opacity, dimensions, children count."""
    data = json.loads((FIXTURES / f"{fixture_name}.json").read_text())
    node = svc._parse_node(data, current_depth=0, max_depth=10)

    # Identity
    assert node.id == data["id"]
    assert node.name == data["name"]
    assert node.type is not None

    # Visibility / opacity (falsy-safe — 0.0 must survive)
    assert node.visible is not None
    assert node.opacity is not None
    if "opacity" in data:
        assert node.opacity == data["opacity"], "opacity must be preserved exactly"

    # Bounding box
    if data.get("absoluteBoundingBox"):
        assert node.width is not None
        assert node.height is not None
        assert node.x is not None
        assert node.y is not None

    # Children count
    if data.get("children"):
        assert len(node.children) == len(data["children"])


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_all_descendant_ids_nonempty(
    svc: FigmaDesignSyncService,
    fixture_name: str,
) -> None:
    """Every node in the tree must have a non-empty id."""
    data = json.loads((FIXTURES / f"{fixture_name}.json").read_text())
    root = svc._parse_node(data, current_depth=0, max_depth=10)

    stack = [root]
    while stack:
        node = stack.pop()
        assert node.id, f"Node {node.name!r} has empty id"
        assert node.name is not None
        stack.extend(node.children)


# ------------------------------------------------------------------
# Archetype-specific tests
# ------------------------------------------------------------------


class TestMammutHero:
    def test_has_image_and_text(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "mammut_hero.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Hero has image fill on root + text children + instance CTA
        assert any(
            c.image_ref or c.type in (DesignNodeType.IMAGE, DesignNodeType.VECTOR)
            for c in node.children
        ), "Hero should have an image child"
        assert any(c.text_content for c in node.children), "Hero should have text children"

    def test_cta_button_parsed(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "mammut_hero.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        instances = [c for c in node.children if c.type == DesignNodeType.INSTANCE]
        assert len(instances) >= 1, "Should have at least one INSTANCE (CTA button)"
        cta = instances[0]
        assert cta.corner_radius is not None
        # CTA label inside
        assert any(c.text_content for c in cta.children)

    def test_subheadline_opacity(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "mammut_hero.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        sub = next(c for c in node.children if c.name == "Subheadline")
        assert sub.opacity == 0.8, "Subheadline opacity must be preserved"

    def test_typography_extracted(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "mammut_hero.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        headline = next(c for c in node.children if c.name == "Headline")
        assert headline.font_family == "Inter"
        assert headline.font_size == 36.0
        assert headline.font_weight == 700
        assert headline.text_transform == "uppercase"


class TestEcommerceGrid:
    def test_multiple_rows(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "ecommerce_grid.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        frames = [c for c in node.children if c.type == DesignNodeType.FRAME]
        # Row 1 and Row 2
        assert len(frames) >= 2, "Grid should have at least 2 row frames"

    def test_product_cards_have_images(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "ecommerce_grid.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Collect all product image nodes (RECTANGLE with IMAGE fill → parsed as IMAGE)
        images: list[DesignNode] = []
        stack = list(node.children)
        while stack:
            n = stack.pop()
            if n.type == DesignNodeType.IMAGE:
                images.append(n)
            stack.extend(n.children)
        assert len(images) >= 4, "Grid should have 4 product images"

    def test_opacity_zero_preserved(self, svc: FigmaDesignSyncService) -> None:
        """Product Image 4 has opacity=0.0 — must not be dropped."""
        data = json.loads((FIXTURES / "ecommerce_grid.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Find the node with opacity 0.0
        stack = list(node.children)
        found = False
        while stack:
            n = stack.pop()
            if n.name == "Product Image 4":
                assert n.opacity == 0.0, "opacity=0.0 must survive parsing"
                found = True
                break
            stack.extend(n.children)
        assert found, "Product Image 4 node not found"

    def test_corner_radii(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "ecommerce_grid.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Find Product Image 1 which has rectangleCornerRadii
        stack = list(node.children)
        while stack:
            n = stack.pop()
            if n.name == "Product Image 1":
                assert n.corner_radii == (8.0, 8.0, 0.0, 0.0)
                return
            stack.extend(n.children)
        pytest.fail("Product Image 1 not found")


class TestNewsletter2Col:
    def test_two_columns(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "newsletter_2col.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        layout_frame = next(c for c in node.children if c.name == "Two Column Layout")
        assert layout_frame.layout_mode == "HORIZONTAL"
        assert len(layout_frame.children) == 2

    def test_hyperlinks_extracted(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "newsletter_2col.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Find linked article title
        stack = list(node.children)
        links: list[str] = []
        while stack:
            n = stack.pop()
            if n.hyperlink:
                links.append(n.hyperlink)
            stack.extend(n.children)
        assert len(links) >= 1
        assert "example.com" in links[0]

    def test_stroke_extracted(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "newsletter_2col.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Root has a stroke
        assert node.stroke_color is not None
        assert node.stroke_weight is not None


class TestTransactional:
    def test_has_text_rows(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "transactional.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        # Count TEXT nodes in the tree
        texts: list[str] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.type == DesignNodeType.TEXT and n.text_content:
                texts.append(n.text_content)
            stack.extend(n.children)
        assert len(texts) >= 6, "Transactional should have 6+ text nodes"
        assert any("$" in t for t in texts), "Should have price amounts"

    def test_hidden_node_parsed(self, svc: FigmaDesignSyncService) -> None:
        """Hidden debug info (visible=false) must be parsed but marked invisible."""
        data = json.loads((FIXTURES / "transactional.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        hidden = next((c for c in node.children if c.name == "Hidden Debug Info"), None)
        assert hidden is not None, "Hidden node must still be parsed"
        assert hidden.visible is False
        assert hidden.opacity == 0.0


class TestNavigationHeader:
    def test_horizontal_layout(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "navigation_header.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        assert node.layout_mode == "HORIZONTAL"
        assert node.primary_axis_align == "space-between"

    def test_nav_links_have_hyperlinks(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "navigation_header.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        links: list[str] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.hyperlink:
                links.append(n.hyperlink)
            stack.extend(n.children)
        assert len(links) >= 4, "Nav bar should have 4 hyperlinks"
        assert any("mailto:" in lnk for lnk in links), "Should have mailto link"

    def test_text_transform_uppercase(self, svc: FigmaDesignSyncService) -> None:
        data = json.loads((FIXTURES / "navigation_header.json").read_text())
        node = svc._parse_node(data, current_depth=0, max_depth=10)
        stack = [node]
        uppercase_count = 0
        while stack:
            n = stack.pop()
            if n.text_transform == "uppercase":
                uppercase_count += 1
            stack.extend(n.children)
        assert uppercase_count >= 4, "All nav links should be uppercase"
