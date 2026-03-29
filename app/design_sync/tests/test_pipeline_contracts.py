"""Contract tests: each pipeline stage output is valid input for the next (39.2.3).

Validates:
1. parse → normalize: parsed fixtures can be normalized without error
2. normalize → analyze: normalized output produces valid DesignLayoutDescription
3. Section ID disjointness: text and button IDs never overlap
4. Field completeness: no None ids in the full tree
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSectionType,
    analyze_layout,
)
from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.figma.tree_normalizer import normalize_tree
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
)

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "figma" / "tests" / "fixtures"

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


def _load_and_parse(svc: FigmaDesignSyncService, name: str) -> DesignFileStructure:
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    node = svc._parse_node(data, current_depth=0, max_depth=10)
    page = DesignNode(id="p1", name="Page", type=DesignNodeType.PAGE, children=[node])
    return DesignFileStructure(file_name=name, pages=[page])


# ------------------------------------------------------------------
# Contract 1: parse → normalize
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_parse_output_normalizable(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Parsed fixture must be normalizable without error."""
    struct = _load_and_parse(svc, fixture)
    result, stats = normalize_tree(struct)
    assert result.file_name == fixture
    assert len(result.pages) >= 1
    assert stats.nodes_removed >= 0
    assert stats.groups_flattened >= 0


# ------------------------------------------------------------------
# Contract 2: normalize → analyze
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_normalize_output_analyzable(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Normalized output must produce a valid DesignLayoutDescription."""
    struct = _load_and_parse(svc, fixture)
    normalized, _ = normalize_tree(struct)
    layout = analyze_layout(normalized)
    assert isinstance(layout, DesignLayoutDescription)
    # Width should be detected from the fixture frames
    assert layout.overall_width is None or layout.overall_width > 0
    # At least one section should be detected
    assert len(layout.sections) >= 1
    for section in layout.sections:
        assert section.section_type in EmailSectionType
        assert section.node_id
        assert section.node_name


# ------------------------------------------------------------------
# Contract 3: section text/button IDs are disjoint
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_section_ids_disjoint(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Button IDs must not appear in text IDs within the same section."""
    struct = _load_and_parse(svc, fixture)
    normalized, _ = normalize_tree(struct)
    layout = analyze_layout(normalized)
    for section in layout.sections:
        text_ids = {t.node_id for t in section.texts}
        button_ids = {b.node_id for b in section.buttons}
        overlap = text_ids & button_ids
        assert not overlap, f"Section {section.node_name}: text/button ID overlap: {overlap}"


# ------------------------------------------------------------------
# Contract 4: field completeness — no None ids
# ------------------------------------------------------------------


def _collect_all_nodes(node: DesignNode) -> list[DesignNode]:
    result = [node]
    for child in node.children:
        result.extend(_collect_all_nodes(child))
    return result


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_no_none_ids(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Every node in the parsed tree must have non-None id, name, type."""
    struct = _load_and_parse(svc, fixture)
    for page in struct.pages:
        for node in _collect_all_nodes(page):
            assert node.id is not None, f"Node has None id: {node.name}"
            assert node.name is not None, f"Node {node.id} has None name"
            assert node.type is not None, f"Node {node.id} has None type"


# ------------------------------------------------------------------
# Contract 5: normalize preserves page structure
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_normalize_preserves_pages(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Normalization must not lose pages."""
    struct = _load_and_parse(svc, fixture)
    page_count = len(struct.pages)
    result, _ = normalize_tree(struct)
    assert len(result.pages) == page_count


# ------------------------------------------------------------------
# Contract 6: analyze sections reference valid node IDs
# ------------------------------------------------------------------


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_section_node_ids_exist_in_tree(svc: FigmaDesignSyncService, fixture: str) -> None:
    """Every section.node_id must correspond to a node in the normalized tree."""
    struct = _load_and_parse(svc, fixture)
    normalized, _ = normalize_tree(struct)
    all_ids: set[str] = set()
    for page in normalized.pages:
        for node in _collect_all_nodes(page):
            all_ids.add(node.id)

    layout = analyze_layout(normalized)
    for section in layout.sections:
        assert section.node_id in all_ids, (
            f"Section {section.node_name} references non-existent node {section.node_id}"
        )
