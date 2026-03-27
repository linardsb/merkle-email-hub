"""Pydantic schemas for email build pipeline."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ai.agents.visual_qa.schemas import VisualComparisonResult


class BuildRequest(BaseModel):
    """Request to build an email template."""

    project_id: int = Field(..., description="Project ID")
    template_name: str = Field(..., min_length=1, max_length=200)
    source_html: str = Field(..., min_length=1, description="Maizzle template source")
    config_overrides: dict[str, object] | None = Field(None, description="Maizzle config overrides")
    is_production: bool = Field(default=False, description="Use production config")


class PreviewRequest(BaseModel):
    """Request for a live preview build."""

    source_html: str = Field(..., min_length=1)
    config_overrides: dict[str, object] | None = None


class BuildResponse(BaseModel):
    """Response from a build execution."""

    id: int
    project_id: int
    template_name: str
    status: str
    compiled_html: str | None = None
    error_message: str | None = None
    is_production: bool
    passthrough: bool = False
    visual_drift: VisualComparisonResult | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PreviewResponse(BaseModel):
    """Response from a preview build."""

    compiled_html: str
    build_time_ms: float
    passthrough: bool = False


class CSSCompileRequest(BaseModel):
    """Request to compile/optimize CSS in email HTML."""

    html: str = Field(..., min_length=1, max_length=5_000_000, description="Email HTML to compile")
    target_clients: list[str] | None = Field(
        None,
        description="Target email client IDs. Uses config defaults if omitted.",
    )
    css_variables: dict[str, str] | None = Field(
        None,
        description="CSS custom property values to resolve var() references.",
    )


class CSSConversionSchema(BaseModel):
    """A CSS conversion applied during compilation."""

    original_property: str
    original_value: str
    replacement_property: str
    replacement_value: str
    reason: str
    affected_clients: list[str]


class CSSCompileResponse(BaseModel):
    """Response from CSS compilation."""

    html: str
    original_size: int
    compiled_size: int
    reduction_pct: float
    removed_properties: list[str]
    conversions: list[CSSConversionSchema]
    warnings: list[str]
    compile_time_ms: float


# ── Schema.org Auto-Markup ──


class DetectedIntentSchema(BaseModel):
    """Detected email intent."""

    intent_type: str = Field(
        description="Classified intent: promotional, transactional, event, newsletter, notification"
    )
    confidence: float = Field(description="Classification confidence (0.0-1.0)")
    entity_count: int = Field(description="Number of extracted entities")


class ExtractedEntitySchema(BaseModel):
    """An entity extracted from email content."""

    entity_type: str = Field(
        description="Entity type: price, date, order_number, product_name, url"
    )
    value: str = Field(description="Extracted value")


class SchemaMarkupSchema(BaseModel):
    """Generated schema.org markup details."""

    schema_types: list[str] = Field(description="Schema.org types in generated JSON-LD")
    json_ld: str = Field(description="Generated JSON-LD markup")


class SchemaInjectRequest(BaseModel):
    """Request to inject schema.org markup into email HTML."""

    html: str = Field(min_length=1, max_length=5_000_000, description="Email HTML content")
    subject: str = Field(
        default="",
        max_length=500,
        description="Email subject line (improves classification accuracy)",
    )


class SchemaInjectResponse(BaseModel):
    """Response from schema.org markup injection."""

    html: str = Field(
        description="Email HTML with injected JSON-LD (unchanged if no markup injected)"
    )
    injected: bool = Field(description="Whether markup was actually injected")
    intent: DetectedIntentSchema = Field(description="Detected email intent")
    entities: list[ExtractedEntitySchema] = Field(description="Extracted entities used for markup")
    schema_types: list[str] = Field(description="Schema.org types in injected markup")
    validation_errors: list[str] = Field(description="Validation errors (if injection was skipped)")
    inject_time_ms: float = Field(description="Processing time in milliseconds")


# ── Import Annotation ──


class AnnotationDecisionSchema(BaseModel):
    """A detected section annotation."""

    section_id: str
    component_name: str
    element_selector: str
    layout_type: str


class ImportAnnotateRequest(BaseModel):
    """Request to annotate imported email HTML."""

    html: str = Field(..., min_length=10, max_length=2_097_152)  # 2MB
    esp_platform: str | None = Field(
        None,
        pattern=r"^(braze|sfmc|klaviyo|mailchimp|hubspot|adobe_campaign|iterable)$",
    )


class ImportAnnotateResponse(BaseModel):
    """Response from import annotation."""

    annotated_html: str
    sections: list[AnnotationDecisionSchema]
    warnings: list[str]
