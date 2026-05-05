"""Tests for 40.6: Export images exactly as-is — no background color added.

Validates:
- _walk_for_images() sets export_node_id on FRAME-wrapping-IMAGE
- _collect_image_node_ids() prefers export_node_id for Figma API calls
- URL mapping remaps export→display node IDs
- Quality contract catches background-color on image containers
- Dimension validation detects mismatches
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.design_sync.figma.layout_analyzer import (
    ImagePlaceholder,
    _walk_for_images,
    validate_image_dimensions,
)
from app.design_sync.import_service import DesignImportService
from app.design_sync.protocol import DesignNode, DesignNodeType
from app.design_sync.quality_contracts import check_image_container_bgcolor
from app.design_sync.tests.conftest import make_design_node


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = "admin"
    return user


# ── _walk_for_images: export_node_id ──


class TestWalkForImagesExportNodeId:
    """FRAME-wrapping-IMAGE case sets export_node_id to the frame."""

    def test_frame_wrapping_image_uses_frame_export_id(self) -> None:
        img_child = make_design_node(
            id="img:1",
            name="Product Photo",
            type=DesignNodeType.IMAGE,
            width=200.0,
            height=200.0,
        )
        frame = make_design_node(
            id="frame:1",
            name="mj-image-Frame",
            type=DesignNodeType.FRAME,
            width=260.0,
            height=260.0,
            children=[img_child],
        )
        results: list[ImagePlaceholder] = []
        _walk_for_images(frame, results)

        assert len(results) == 1
        assert results[0].export_node_id == "frame:1"

    def test_frame_wrapping_image_keeps_child_display_id(self) -> None:
        img_child = make_design_node(
            id="img:1",
            name="Photo",
            type=DesignNodeType.IMAGE,
            width=200.0,
            height=200.0,
        )
        frame = make_design_node(
            id="frame:1",
            name="Frame",
            type=DesignNodeType.FRAME,
            width=260.0,
            height=260.0,
            children=[img_child],
        )
        results: list[ImagePlaceholder] = []
        _walk_for_images(frame, results)

        assert results[0].node_id == "img:1"
        assert results[0].node_name == "Photo"

    def test_frame_wrapping_image_uses_frame_dimensions(self) -> None:
        img_child = make_design_node(
            id="img:1",
            name="Photo",
            type=DesignNodeType.IMAGE,
            width=200.0,
            height=200.0,
        )
        frame = make_design_node(
            id="frame:1",
            name="Frame",
            type=DesignNodeType.FRAME,
            width=260.0,
            height=260.0,
            children=[img_child],
        )
        results: list[ImagePlaceholder] = []
        _walk_for_images(frame, results)

        assert results[0].width == 260.0
        assert results[0].height == 260.0

    def test_standalone_image_no_export_node_id(self) -> None:
        node = make_design_node(
            id="img:2",
            name="Hero",
            type=DesignNodeType.IMAGE,
            width=600.0,
            height=400.0,
        )
        results: list[ImagePlaceholder] = []
        _walk_for_images(node, results)

        assert len(results) == 1
        assert results[0].export_node_id is None
        assert results[0].node_id == "img:2"

    def test_background_frame_no_export_node_id(self) -> None:
        """FRAME with image_ref is already the frame — no separate export ID needed."""
        node = DesignNode(
            id="bg:1",
            name="Hero BG",
            type=DesignNodeType.FRAME,
            width=600.0,
            height=400.0,
            image_ref="ref:abc",
            children=[],
            x=0,
            y=0,
            visible=True,
            opacity=1.0,
        )
        results: list[ImagePlaceholder] = []
        _walk_for_images(node, results)

        assert len(results) == 1
        assert results[0].export_node_id is None
        assert results[0].is_background is True


# ── _collect_image_node_ids: export_node_id preference ──


class TestCollectImageNodeIdsExportPreference:
    """_collect_image_node_ids prefers export_node_id for Figma API calls."""

    def test_prefers_export_node_id(self) -> None:
        svc = DesignImportService(user=_make_user())

        layout = MagicMock(spec=["sections"])
        img = MagicMock()
        img.node_id = "img:1"
        img.export_node_id = "frame:1"
        section = MagicMock()
        section.images = [img]
        layout.sections = [section]

        node_ids, mapping = svc._collect_image_node_ids(layout)
        assert node_ids == ["frame:1"]
        assert mapping == {"frame:1": "img:1"}

    def test_falls_back_to_node_id_when_no_export(self) -> None:
        svc = DesignImportService(user=_make_user())

        layout = MagicMock(spec=["sections"])
        img = MagicMock()
        img.node_id = "img:1"
        img.export_node_id = None
        section = MagicMock()
        section.images = [img]
        layout.sections = [section]

        node_ids, mapping = svc._collect_image_node_ids(layout)
        assert node_ids == ["img:1"]
        assert mapping == {}

    def test_mixed_export_and_direct(self) -> None:
        svc = DesignImportService(user=_make_user())

        layout = MagicMock(spec=["sections"])
        img1 = MagicMock()
        img1.node_id = "img:1"
        img1.export_node_id = "frame:1"
        img2 = MagicMock()
        img2.node_id = "img:2"
        img2.export_node_id = None
        section = MagicMock()
        section.images = [img1, img2]
        layout.sections = [section]

        node_ids, mapping = svc._collect_image_node_ids(layout)
        assert node_ids == ["frame:1", "img:2"]
        assert mapping == {"frame:1": "img:1"}


# ── Quality contract: no bgcolor on image containers ──


class TestImageContainerBgcolorContract:
    """check_image_container_bgcolor flags background-color on <td>/<div> with <img>."""

    def test_flags_bgcolor_attr_on_td(self) -> None:
        html = '<html><body><table><tr><td bgcolor="#F0F0F0"><img src="x.png" /></td></tr></table></body></html>'
        warnings = check_image_container_bgcolor(html)
        assert len(warnings) == 1
        assert warnings[0].category == "image_bgcolor"
        assert "#F0F0F0" in warnings[0].message

    def test_flags_css_background_color_on_td(self) -> None:
        html = '<html><body><table><tr><td style="background-color:#ccc;"><img src="x.png" /></td></tr></table></body></html>'
        warnings = check_image_container_bgcolor(html)
        assert len(warnings) == 1

    def test_clean_output_passes(self) -> None:
        html = '<html><body><table><tr><td style="padding:10px;"><img src="x.png" /></td></tr></table></body></html>'
        warnings = check_image_container_bgcolor(html)
        assert warnings == []

    def test_bgcolor_on_non_image_td_ignored(self) -> None:
        """bgcolor on a <td> without <img> is fine — structural section background."""
        html = (
            '<html><body><table><tr><td bgcolor="#fff"><p>Text</p></td></tr></table></body></html>'
        )
        warnings = check_image_container_bgcolor(html)
        assert warnings == []


# ── Dimension validation ──


class TestDimensionValidation:
    """validate_image_dimensions compares exported dims against design bounds."""

    def test_matching_dimensions(self) -> None:
        placeholder = ImagePlaceholder(
            node_id="img:1",
            node_name="Photo",
            width=260.0,
            height=260.0,
        )
        result = validate_image_dimensions(placeholder, 520, 520, scale=2.0)
        assert result is None

    def test_mismatched_dimensions(self) -> None:
        placeholder = ImagePlaceholder(
            node_id="img:1",
            node_name="Photo",
            width=260.0,
            height=260.0,
        )
        result = validate_image_dimensions(placeholder, 400, 400, scale=2.0)
        assert result is not None
        assert "dimension mismatch" in result
        assert "img:1" in result

    def test_within_tolerance(self) -> None:
        """1px tolerance for rounding."""
        placeholder = ImagePlaceholder(
            node_id="img:1",
            node_name="Photo",
            width=260.0,
            height=260.0,
        )
        result = validate_image_dimensions(placeholder, 521, 519, scale=2.0)
        assert result is None

    def test_none_dimensions_skip(self) -> None:
        placeholder = ImagePlaceholder(
            node_id="img:1",
            node_name="Photo",
            width=None,
            height=None,
        )
        result = validate_image_dimensions(placeholder, 520, 520, scale=2.0)
        assert result is None
