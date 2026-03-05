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
