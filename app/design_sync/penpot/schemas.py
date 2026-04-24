"""Penpot REST API response models (internal)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PenpotProject(BaseModel):
    id: str
    name: str
    team_id: str


class PenpotFile(BaseModel):
    id: str
    name: str
    project_id: str


class PenpotColor(BaseModel):
    """Shared color from Penpot library."""

    id: str
    name: str
    color: str  # hex #RRGGBB or #RRGGBBAA
    opacity: float = 1.0


class PenpotTypographyStyle(BaseModel):
    """Typography style from Penpot library."""

    id: str
    name: str
    font_family: str = Field(alias="fontFamily")
    font_weight: str = Field(alias="fontWeight", default="400")
    font_size: str = Field(alias="fontSize", default="16")
    line_height: str = Field(alias="lineHeight", default="1.5")

    model_config = {"populate_by_name": True}


class PenpotComponent(BaseModel):
    """Component from Penpot file."""

    id: str
    name: str
    path: str = ""  # Component group path


class PenpotPage(BaseModel):
    id: str
    name: str


class PenpotNode(BaseModel):
    """Node from Penpot file data. Penpot uses UUIDs for node IDs."""

    id: str
    name: str = ""
    type: str = "frame"
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    children: list[PenpotNode] = Field(default_factory=list["PenpotNode"])
    content: str | None = None  # text content for text nodes
    fills: list[dict[str, Any]] | None = None
    font_family: str | None = Field(None, alias="fontFamily")
    font_size: float | None = Field(None, alias="fontSize")

    model_config = {"populate_by_name": True}
