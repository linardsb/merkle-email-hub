"""Pydantic schemas for rendering tests."""

import datetime

from pydantic import BaseModel, ConfigDict, Field

# Default email clients for rendering tests
DEFAULT_CLIENTS: list[str] = [
    "gmail_web",
    "gmail_android",
    "gmail_ios",
    "outlook_2021",
    "outlook_365",
    "outlook_web",
    "apple_mail_16",
    "apple_mail_ios_16",
    "yahoo_web",
    "yahoo_ios",
    "samsung_email",
    "thunderbird",
    "outlook_dark",
    "gmail_dark",
    "apple_dark",
    "windows_mail",
    "aol_web",
    "protonmail",
    "hey",
    "fastmail",
]


class RenderingTestRequest(BaseModel):
    """Request to submit a rendering test."""

    html: str = Field(..., min_length=1, max_length=500_000, description="Compiled HTML to render")
    subject: str = Field(default="Rendering Test", max_length=200)
    clients: list[str] = Field(default_factory=lambda: DEFAULT_CLIENTS[:20])
    build_id: int | None = Field(None, description="Optional link to email build")
    template_version_id: int | None = Field(None, description="Optional link to template version")


class ScreenshotResult(BaseModel):
    """A single client rendering screenshot."""

    client_name: str
    screenshot_url: str | None = None
    os: str = ""
    category: str = ""  # desktop, mobile, web, dark_mode
    status: str = "pending"  # pending, complete, failed


class RenderingTestResponse(BaseModel):
    """Response for a rendering test."""

    id: int
    external_test_id: str
    provider: str
    status: str  # pending, processing, complete, failed
    build_id: int | None = None
    template_version_id: int | None = None
    clients_requested: int
    clients_completed: int = 0
    screenshots: list[ScreenshotResult] = []
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class RenderingComparisonRequest(BaseModel):
    """Request to compare two rendering test results."""

    baseline_test_id: int = Field(..., description="ID of the baseline rendering test")
    current_test_id: int = Field(..., description="ID of the current rendering test")


class RenderingDiff(BaseModel):
    """Visual diff result for a single client."""

    client_name: str
    diff_percentage: float = Field(ge=0.0, le=100.0)
    has_regression: bool = False
    baseline_url: str | None = None
    current_url: str | None = None


class RenderingComparisonResponse(BaseModel):
    """Response for a rendering comparison."""

    baseline_test_id: int
    current_test_id: int
    total_clients: int
    regressions_found: int
    diffs: list[RenderingDiff] = []


class ScreenshotRequest(BaseModel):
    """Request for local email screenshot rendering."""

    html: str = Field(..., min_length=1, max_length=500_000)
    clients: list[str] = Field(
        default_factory=lambda: [
            "gmail_web",
            "outlook_2019",
            "apple_mail",
            "outlook_dark",
            "mobile_ios",
        ]
    )


class ConfidenceBreakdownSchema(BaseModel):
    """Component scores for rendering confidence."""

    emulator_coverage: float = Field(ge=0.0, le=1.0)
    css_compatibility: float = Field(ge=0.0, le=1.0)
    calibration_accuracy: float = Field(ge=0.0, le=1.0)
    layout_complexity: float = Field(ge=0.0, le=1.0)
    known_blind_spots: list[str] = []


class ClientConfidenceResponse(BaseModel):
    """Current confidence data for a specific client."""

    client_id: str
    accuracy: float
    sample_count: int
    last_calibrated: str
    known_blind_spots: list[str] = []
    emulator_rule_count: int
    profiles: list[str] = []


class ScreenshotClientResult(BaseModel):
    """Single client screenshot result with base64 image."""

    client_name: str
    image_base64: str
    viewport: str
    browser: str
    confidence_score: float | None = None
    confidence_breakdown: ConfidenceBreakdownSchema | None = None
    confidence_recommendations: list[str] | None = None


class ScreenshotResponse(BaseModel):
    """Response with rendered screenshots."""

    screenshots: list[ScreenshotClientResult]
    clients_rendered: int
    clients_failed: int = 0


# ── Visual Diff & Baselines (Phase 17.2) ──

VALID_ENTITY_TYPES = {"component_version", "golden_template"}


class VisualDiffRequest(BaseModel):
    """Request for visual diff between two images."""

    baseline_image: str = Field(
        ..., max_length=14_000_000, description="Base64-encoded PNG baseline"
    )
    current_image: str = Field(..., max_length=14_000_000, description="Base64-encoded PNG current")
    threshold: float | None = Field(None, ge=0.0, le=1.0, description="Override default threshold")


class Region(BaseModel):
    """A rectangular region of pixel changes."""

    x: int
    y: int
    width: int
    height: int


class VisualDiffResponse(BaseModel):
    """Result of visual diff comparison."""

    identical: bool
    diff_percentage: float = Field(ge=0.0, le=100.0)
    diff_image: str | None = None
    pixel_count: int = 0
    changed_regions: list[Region] = []
    threshold_used: float


class BaselineResponse(BaseModel):
    """Response for a stored baseline."""

    id: int
    entity_type: str
    entity_id: int
    client_name: str
    image_hash: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BaselineListResponse(BaseModel):
    """List of baselines for an entity."""

    entity_type: str
    entity_id: int
    baselines: list[BaselineResponse]


class BaselineUpdateRequest(BaseModel):
    """Request to update/create a baseline."""

    client_name: str = Field(..., max_length=100)
    image_base64: str = Field(
        ..., min_length=1, max_length=14_000_000, description="Base64-encoded PNG image"
    )
