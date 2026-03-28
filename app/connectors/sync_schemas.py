"""Pydantic schemas for ESP bidirectional sync."""

from __future__ import annotations

import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ESPTemplate(BaseModel):
    """A template stored in an external ESP."""

    id: str
    name: str
    html: str
    esp_type: str
    created_at: str
    updated_at: str


class ESPTemplateList(BaseModel):
    """Paginated list of ESP templates."""

    templates: list[ESPTemplate]
    count: int


class ESPConnectionCreate(BaseModel):
    """Request to create an ESP connection."""

    esp_type: str = Field(
        ...,
        pattern=r"^(braze|sfmc|adobe_campaign|taxi|klaviyo|hubspot|mailchimp|sendgrid|activecampaign|iterable|brevo)$",
        max_length=50,
    )
    name: str = Field(..., min_length=1, max_length=200)
    project_id: int
    credentials: dict[str, str] = Field(
        ..., description="ESP-specific credentials (encrypted at rest)"
    )


class ESPConnectionResponse(BaseModel):
    """Response for an ESP connection."""

    id: int
    esp_type: str
    name: str
    status: str
    credentials_hint: str
    project_id: int
    project_name: str | None = None
    last_synced_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ESPImportRequest(BaseModel):
    """Request to import a template from an ESP into Hub."""

    template_id: str = Field(..., min_length=1, description="Remote ESP template ID")


class ESPPushRequest(BaseModel):
    """Request to push a local Hub template to an ESP."""

    template_id: int = Field(..., description="Local Hub template ID")


class TokenRewriteRequest(BaseModel):
    """Request to rewrite ESP personalisation tokens from one ESP format to another."""

    html: str = Field(..., max_length=5_000_000)
    target_esp: str = Field(
        ...,
        pattern=r"^(braze|sfmc|adobe_campaign|klaviyo|hubspot|mailchimp|sendgrid|activecampaign|iterable|brevo)$",
    )
    source_esp: str | None = Field(
        default=None,
        pattern=r"^(braze|sfmc|adobe_campaign|klaviyo|hubspot|mailchimp|sendgrid|activecampaign|iterable|brevo)$",
    )


class TokenRewriteResponse(BaseModel):
    """Response from token rewrite operation."""

    html: str
    source_esp: str
    target_esp: str
    tokens_rewritten: int
    warnings: list[str]


# ── Export Orchestration ──

_ESP_TYPE_PATTERN = r"^(braze|sfmc|adobe_campaign|taxi|klaviyo|hubspot|mailchimp|sendgrid|activecampaign|iterable|brevo)$"


class ExportRequest(BaseModel):
    """Request to export HTML to an ESP via a connection."""

    html: str | None = Field(None, max_length=5_000_000)
    template_id: int | None = None
    target_esp: str = Field(..., pattern=_ESP_TYPE_PATTERN)
    connection_id: int
    template_name: str = Field("Exported Email", max_length=500)
    source_esp: str | None = Field(default=None, pattern=_ESP_TYPE_PATTERN)
    rewrite_tokens: bool = True

    @model_validator(mode="after")
    def require_html_or_template_id(self) -> Self:
        if self.html is None and self.template_id is None:
            msg = "Either html or template_id is required"
            raise ValueError(msg)
        return self


class ExportResponse(BaseModel):
    """Response from a single export operation."""

    esp_template_id: str
    template_name: str
    target_esp: str
    tokens_rewritten: int
    warnings: list[str]


class BulkExportRequest(BaseModel):
    """Request to export multiple templates to an ESP."""

    template_ids: list[int] = Field(..., min_length=1, max_length=50)
    target_esp: str = Field(..., pattern=_ESP_TYPE_PATTERN)
    connection_id: int
    rewrite_tokens: bool = True


class BulkExportItemResult(BaseModel):
    """Result for a single item in a bulk export."""

    template_id: int
    success: bool
    esp_template_id: str | None = None
    error: str | None = None
    tokens_rewritten: int = 0


class BulkExportResponse(BaseModel):
    """Response from a bulk export operation."""

    results: list[BulkExportItemResult]
    total: int
    succeeded: int
    failed: int
