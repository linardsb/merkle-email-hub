"""Shared fixtures for design_sync tests."""

from __future__ import annotations

from typing import Any

from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
)


def make_design_node(
    id: str = "node1",
    name: str = "Frame",
    type: DesignNodeType = DesignNodeType.FRAME,
    children: list[DesignNode] | None = None,
    **overrides: Any,
) -> DesignNode:
    """Build a DesignNode with sensible defaults — override any field via kwargs."""
    defaults: dict[str, Any] = {
        "id": id,
        "name": name,
        "type": type,
        "children": children or [],
        "width": 600.0,
        "height": 400.0,
        "x": 0.0,
        "y": 0.0,
        "visible": True,
        "opacity": 1.0,
    }
    defaults.update(overrides)
    return DesignNode(**defaults)


def make_file_structure(
    *frames: DesignNode,
    file_name: str = "test",
) -> DesignFileStructure:
    """Wrap frames into a single-page DesignFileStructure."""
    page = make_design_node(
        id="page1",
        name="Page",
        type=DesignNodeType.PAGE,
        children=list(frames),
    )
    return DesignFileStructure(file_name=file_name, pages=[page])
