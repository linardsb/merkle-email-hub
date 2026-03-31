"""Frozen dataclass models for the diagnostic pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataLossEvent:
    """A single instance of data being silently lost in the pipeline."""

    type: str  # "depth_truncated"|"image_fill_ignored"|"text_empty"|...
    node_id: str
    node_name: str
    detail: str
    stage: str


@dataclass(frozen=True)
class SectionTrace:
    """Full diagnostic trace for one email section through the pipeline."""

    section_idx: int
    node_id: str
    node_name: str
    classified_type: str  # "HERO"|"CONTENT"|"FOOTER"|"UNKNOWN"
    matched_component: str  # "hero-block"|"article-card"|...
    match_confidence: float
    texts_found: int
    images_found: int
    buttons_found: int
    slot_fills: tuple[dict[str, str], ...]
    unfilled_slots: tuple[str, ...]
    html_preview: str  # First 3000 chars of rendered HTML


@dataclass(frozen=True)
class StageResult:
    """Diagnostic result for one pipeline stage."""

    name: str  # "layout_analysis"|"component_matching"|...
    elapsed_ms: float
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    data_loss: tuple[DataLossEvent, ...]
    warnings: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class DesignSummary:
    """Catalog of design patterns in the Figma file."""

    total_nodes: int
    node_type_counts: dict[str, int]
    max_tree_depth: int
    image_fill_frames: tuple[dict[str, str], ...]
    auto_layout_frames: int
    naming_compliance: float
    naming_misses: tuple[str, ...]


@dataclass(frozen=True)
class DiagnosticReport:
    """Complete diagnostic report from one pipeline run."""

    id: str
    connection_id: int | None
    timestamp: str
    total_elapsed_ms: float
    stages_completed: int
    total_warnings: int
    total_data_loss_events: int
    design_summary: DesignSummary
    stages: tuple[StageResult, ...]
    section_traces: tuple[SectionTrace, ...]
    final_html_preview: str  # First 5000 chars
    final_html_length: int
    images: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    design_image_path: str | None = None
    design_image_width: int | None = None
    design_image_height: int | None = None
