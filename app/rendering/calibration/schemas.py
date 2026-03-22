"""Request/response schemas for emulator calibration."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalibrationResultSchema(BaseModel):
    """Result of a single calibration measurement."""

    client_id: str
    diff_percentage: float = Field(ge=0.0, le=100.0)
    accuracy_score: float = Field(ge=0.0, le=100.0)
    pixel_count: int = 0
    regression: bool = False
    regression_details: str | None = None


class CalibrationRecordResponse(BaseModel):
    """Serialized calibration record for API responses."""

    id: int
    client_id: str
    html_hash: str
    diff_percentage: float
    accuracy_score: float
    pixel_count: int
    external_provider: str
    emulator_version: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CalibrationSummaryResponse(BaseModel):
    """Serialized calibration summary for API responses."""

    client_id: str
    current_accuracy: float
    sample_count: int
    accuracy_trend: list[float] = []
    known_blind_spots: list[str] = []
    last_provider: str = ""
    last_calibrated: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CalibrationSummaryListResponse(BaseModel):
    """List of all client calibration summaries."""

    summaries: list[CalibrationSummaryResponse]


class CalibrationTriggerRequest(BaseModel):
    """Request to trigger a calibration run."""

    html: str = Field(..., min_length=1, max_length=500_000)
    client_ids: list[str] = Field(..., min_length=1, max_length=20)
    external_provider: str = Field(
        default="sandbox", pattern=r"^(litmus|emailonacid|sandbox|manual)$"
    )


class CalibrationTriggerResponse(BaseModel):
    """Response from a calibration trigger."""

    results: list[CalibrationResultSchema]
    records_created: int


class CalibrationHistoryResponse(BaseModel):
    """Per-client calibration history."""

    client_id: str
    records: list[CalibrationRecordResponse]
    total: int
