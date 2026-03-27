"""Pydantic response schemas for the diagnostic API endpoint."""

from __future__ import annotations

from pydantic import BaseModel

from app.design_sync.diagnose.models import DiagnosticReport


class DataLossEventResponse(BaseModel):
    type: str
    node_id: str
    node_name: str
    detail: str
    stage: str


class SectionTraceResponse(BaseModel):
    section_idx: int
    node_id: str
    node_name: str
    classified_type: str
    matched_component: str
    match_confidence: float
    texts_found: int
    images_found: int
    buttons_found: int
    slot_fills: list[dict[str, str]]
    unfilled_slots: list[str]
    html_preview: str


class StageResultResponse(BaseModel):
    name: str
    elapsed_ms: float
    input_summary: dict[str, object]
    output_summary: dict[str, object]
    data_loss: list[DataLossEventResponse]
    warnings: list[str]
    error: str | None = None


class DesignSummaryResponse(BaseModel):
    total_nodes: int
    node_type_counts: dict[str, int]
    max_tree_depth: int
    image_fill_frames: list[dict[str, str]]
    auto_layout_frames: int
    naming_compliance: float
    naming_misses: list[str]


class DiagnosticReportResponse(BaseModel):
    id: str
    connection_id: int | None
    timestamp: str
    total_elapsed_ms: float
    stages_completed: int
    total_warnings: int
    total_data_loss_events: int
    design_summary: DesignSummaryResponse
    stages: list[StageResultResponse]
    section_traces: list[SectionTraceResponse]
    final_html_preview: str
    final_html_length: int
    images: list[dict[str, str]]

    @classmethod
    def from_report(cls, report: DiagnosticReport) -> DiagnosticReportResponse:
        """Convert a DiagnosticReport dataclass to a Pydantic response model."""
        return cls(
            id=report.id,
            connection_id=report.connection_id,
            timestamp=report.timestamp,
            total_elapsed_ms=report.total_elapsed_ms,
            stages_completed=report.stages_completed,
            total_warnings=report.total_warnings,
            total_data_loss_events=report.total_data_loss_events,
            design_summary=DesignSummaryResponse(
                total_nodes=report.design_summary.total_nodes,
                node_type_counts=report.design_summary.node_type_counts,
                max_tree_depth=report.design_summary.max_tree_depth,
                image_fill_frames=list(report.design_summary.image_fill_frames),
                auto_layout_frames=report.design_summary.auto_layout_frames,
                naming_compliance=report.design_summary.naming_compliance,
                naming_misses=list(report.design_summary.naming_misses),
            ),
            stages=[
                StageResultResponse(
                    name=s.name,
                    elapsed_ms=s.elapsed_ms,
                    input_summary=dict(s.input_summary),
                    output_summary=dict(s.output_summary),
                    data_loss=[
                        DataLossEventResponse(
                            type=e.type,
                            node_id=e.node_id,
                            node_name=e.node_name,
                            detail=e.detail,
                            stage=e.stage,
                        )
                        for e in s.data_loss
                    ],
                    warnings=list(s.warnings),
                    error=s.error,
                )
                for s in report.stages
            ],
            section_traces=[
                SectionTraceResponse(
                    section_idx=t.section_idx,
                    node_id=t.node_id,
                    node_name=t.node_name,
                    classified_type=t.classified_type,
                    matched_component=t.matched_component,
                    match_confidence=t.match_confidence,
                    texts_found=t.texts_found,
                    images_found=t.images_found,
                    buttons_found=t.buttons_found,
                    slot_fills=list(t.slot_fills),
                    unfilled_slots=list(t.unfilled_slots),
                    html_preview=t.html_preview,
                )
                for t in report.section_traces
            ],
            final_html_preview=report.final_html_preview,
            final_html_length=report.final_html_length,
            images=report.images,
        )
