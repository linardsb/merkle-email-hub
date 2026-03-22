"""Pydantic schemas for sandbox API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SandboxDOMDiff(BaseModel):
    """Serializable DOM diff result."""

    removed_elements: list[str] = Field(default_factory=list)
    removed_attributes: dict[str, list[str]] = Field(default_factory=dict)
    removed_css_properties: dict[str, list[str]] = Field(default_factory=dict)
    added_elements: list[str] = Field(default_factory=list)
    modified_styles: dict[str, tuple[str, str]] = Field(default_factory=dict)


class SandboxProfileResult(BaseModel):
    """Result from a single sandbox profile capture."""

    profile: str
    rendered_html: str
    screenshot_base64: str | None = None
    dom_diff: SandboxDOMDiff | None = None


class SandboxTestRequest(BaseModel):
    """Request to send email through sandbox and capture results."""

    html: str = Field(..., min_length=1, max_length=500_000)
    subject: str = Field(default="Sandbox Test", max_length=200)
    profiles: list[str] = Field(default=["mailpit"])


class SandboxTestResponse(BaseModel):
    """Response with per-profile sandbox capture results."""

    message_id: str
    results: list[SandboxProfileResult]


class SandboxHealthResponse(BaseModel):
    """Health check for sandbox infrastructure."""

    sandbox_enabled: bool
    mailpit_reachable: bool = False
    roundcube_reachable: bool = False
    smtp_reachable: bool = False
