"""Pydantic models for per-case regression manifests.

Each ``data/debug/<case>/manifest.yaml`` describes the expected converter
behaviour for that design: section count, component selection, CTA colours,
font tokens, and required/forbidden content strings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CTAExpectation(BaseModel):
    """Expected call-to-action button properties."""

    text: str
    bg_color: str | None = None
    has_vml: bool = False


class ComponentExpectation(BaseModel):
    """Expected component selection for a section."""

    index: int | None = None
    match_by: Literal["content", "index", "type"] = "content"
    content_hint: str = ""
    expected_component: str
    repeat_count: int | None = None
    container_bgcolor: str | None = None


class TokenExpectations(BaseModel):
    """Expected design-token presence/absence in output HTML."""

    primary_font: str | None = None
    banned_fonts: list[str] = []
    text_color: str | None = None
    banned_colors: list[str] = []


class SectionExpectations(BaseModel):
    """Section-level expectations."""

    count: int
    tolerance: int = 1
    components: list[ComponentExpectation] = []


class CaseManifest(BaseModel):
    """Top-level manifest for a single regression case."""

    name: str
    figma_file: str | None = None
    figma_node: str | None = None
    description: str = ""
    reference_only: bool = False
    sections: SectionExpectations
    tokens: TokenExpectations | None = None
    ctas: list[CTAExpectation] = []
    required_content: list[str] = []
    forbidden_content: list[str] = []
    patterns: list[str] = []
