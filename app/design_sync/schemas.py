"""Pydantic schemas for design sync."""

import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

# ── Requests ──


class ConnectionCreateRequest(BaseModel):
    """Request to create a design tool connection."""

    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    provider: str = Field(default="figma", max_length=50, description="Design tool provider")
    file_url: str = Field(..., min_length=1, max_length=500, description="Design file URL")
    access_token: str = Field(..., min_length=1, description="Provider access token / PAT")
    project_id: int | None = Field(default=None, description="Link to a project")


class BrowseFilesRequest(BaseModel):
    """Request to browse design files from a provider."""

    provider: str = Field(..., max_length=50, description="Design tool provider")
    access_token: str = Field(..., min_length=1, description="Provider access token / PAT")


class DesignFileResponse(BaseModel):
    """A single browsable design file."""

    file_id: str
    name: str
    url: str
    thumbnail_url: str | None = None
    last_modified: datetime.datetime | None = None
    folder: str | None = None


class BrowseFilesResponse(BaseModel):
    """Result of browsing design files."""

    provider: str
    files: list[DesignFileResponse]
    total: int


class ConnectionDeleteRequest(BaseModel):
    """Request to delete a connection."""

    id: int = Field(..., description="Connection ID to delete")


class ConnectionSyncRequest(BaseModel):
    """Request to sync tokens from a connection."""

    id: int = Field(..., description="Connection ID to sync")


class ConnectionUpdateTokenRequest(BaseModel):
    """Request to update the access token on an existing connection."""

    access_token: str = Field(..., min_length=1, description="New provider access token / PAT")


class ConnectionLinkProjectRequest(BaseModel):
    """Request to link/unlink a connection to a project."""

    project_id: int | None = Field(None, description="Project ID to link (null to unlink)")


# ── Responses ──


class ConnectionResponse(BaseModel):
    """Design connection response (maps DB fields for frontend compat)."""

    id: int
    name: str
    provider: str
    file_key: str = Field(description="Provider file reference")
    file_url: str
    access_token_last4: str = Field(description="Last 4 chars of token for display")
    status: str
    error_message: str | None = None
    last_synced_at: datetime.datetime | None = None
    project_id: int | None = None
    project_name: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(
        cls,
        conn: "object",
        project_name: str | None = None,
    ) -> "ConnectionResponse":
        """Build response from a DesignConnection model, mapping field names."""
        from app.design_sync.models import DesignConnection

        if not isinstance(conn, DesignConnection):
            msg = "Expected DesignConnection instance"
            raise TypeError(msg)
        return cls(
            id=conn.id,
            name=conn.name,
            provider=conn.provider,
            file_key=conn.file_ref,
            file_url=conn.file_url,
            access_token_last4=conn.token_last4,
            status=conn.status,
            error_message=conn.error_message,
            last_synced_at=conn.last_synced_at,
            project_id=conn.project_id,
            project_name=project_name,
            created_at=cast(datetime.datetime, conn.created_at),
            updated_at=cast(datetime.datetime, conn.updated_at),
        )


class DesignColorResponse(BaseModel):
    """Single design colour."""

    name: str
    hex: str
    opacity: float


class DesignTypographyResponse(BaseModel):
    """Single typography style."""

    name: str
    family: str
    weight: str
    size: float
    lineHeight: float
    letterSpacing: float | None = None
    textTransform: str | None = None
    textDecoration: str | None = None


class DesignSpacingResponse(BaseModel):
    """Single spacing value."""

    name: str
    value: float


class CompatibilityHintResponse(BaseModel):
    """A client compatibility observation surfaced during conversion."""

    level: str  # "info" | "warning"
    css_property: str
    message: str
    affected_clients: list[str]


class DesignGradientStopResponse(BaseModel):
    """A single gradient stop."""

    hex: str
    position: float


class DesignGradientResponse(BaseModel):
    """A gradient extracted from a design file."""

    name: str
    type: str
    angle: float
    stops: list[DesignGradientStopResponse]
    fallback_hex: str


class DesignTokensResponse(BaseModel):
    """Design tokens extracted from a connection."""

    connection_id: int
    colors: list[DesignColorResponse]
    dark_colors: list[DesignColorResponse] = Field(default_factory=list)
    typography: list[DesignTypographyResponse]
    spacing: list[DesignSpacingResponse]
    gradients: list[DesignGradientResponse] = Field(default_factory=list)
    extracted_at: datetime.datetime
    warnings: list[str] | None = None
    compatibility_hints: list[CompatibilityHintResponse] | None = None


class TokenDiffEntry(BaseModel):
    """A single token change between snapshots."""

    category: str
    name: str
    change: Literal["added", "removed", "changed"]
    old_value: str | None = None
    new_value: str | None = None


class TokenDiffResponse(BaseModel):
    """Token diff between current and previous sync."""

    connection_id: int
    current_extracted_at: datetime.datetime
    previous_extracted_at: datetime.datetime | None = None
    entries: list[TokenDiffEntry]
    has_previous: bool = False


# ── File Structure Responses ──


class DesignNodeResponse(BaseModel):
    """A node in the design file tree."""

    id: str
    name: str
    type: str
    children: list["DesignNodeResponse"] = Field(default_factory=list["DesignNodeResponse"])
    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    text_content: str | None = None

    model_config = ConfigDict(from_attributes=True)


DesignNodeResponse.model_rebuild()


class FileStructureResponse(BaseModel):
    """Design file structure response."""

    connection_id: int
    file_name: str
    pages: list[DesignNodeResponse]
    thumbnails: dict[str, str] = Field(default_factory=dict, description="node_id → image URL")


# ── Component Responses ──


class DesignComponentResponse(BaseModel):
    """A reusable design component."""

    component_id: str
    name: str
    description: str = ""
    thumbnail_url: str | None = None
    containing_page: str | None = None


class ComponentListResponse(BaseModel):
    """List of design components."""

    connection_id: int
    components: list[DesignComponentResponse]
    total: int


# ── Image Export ──


class ExportImageRequest(BaseModel):
    """Request to export design nodes as images."""

    connection_id: int
    node_ids: list[str] = Field(..., min_length=1, max_length=500, description="Node IDs to export")
    format: str = Field(default="png", pattern=r"^(png|jpg|svg|pdf)$")
    scale: float = Field(default=2.0, ge=0.01, le=4.0)


class ExportedImageResponse(BaseModel):
    """An exported image."""

    node_id: str
    url: str
    format: str
    expires_at: datetime.datetime | None = None


class ImageExportResponse(BaseModel):
    """Image export result."""

    connection_id: int
    images: list[ExportedImageResponse]
    total: int


# ── Asset Storage ──


class DownloadAssetsRequest(BaseModel):
    """Request to download and store exported images locally."""

    connection_id: int
    node_ids: list[str] = Field(
        ..., min_length=1, max_length=500, description="Node IDs to download"
    )
    format: str = Field(default="png", pattern=r"^(png|jpg|svg|pdf)$")
    scale: float = Field(default=2.0, ge=0.01, le=4.0)


class StoredAssetResponse(BaseModel):
    """A locally stored asset."""

    node_id: str
    filename: str


class DownloadAssetsResponse(BaseModel):
    """Result of downloading and storing assets."""

    connection_id: int
    assets: list[StoredAssetResponse]
    total: int
    skipped: int = Field(description="Count of failed downloads")


class ImportedImageResponse(BaseModel):
    """Image asset imported from a design file and stored locally."""

    node_id: str
    filename: str
    hub_url: str


# ── Design Imports ──

IMPORT_STATUSES = {"pending", "extracting", "converting", "completed", "failed", "cancelled"}
ASSET_USAGES = {"hero", "logo", "icon", "background", "content"}


class CreateImportRequest(BaseModel):
    """Request to create a design import job."""

    connection_id: int
    project_id: int
    selected_node_ids: list[str] = Field(
        ..., min_length=1, max_length=500, description="Figma node IDs to import"
    )


class UpdateImportBriefRequest(BaseModel):
    """Request to update the generated brief before conversion."""

    generated_brief: str = Field(..., min_length=1, max_length=50000)


class ImportAssetResponse(BaseModel):
    """A single import asset."""

    id: int
    node_id: str
    node_name: str
    file_path: str
    width: int | None = None
    height: int | None = None
    format: str
    usage: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ImportResponse(BaseModel):
    """Design import job response."""

    id: int
    connection_id: int
    project_id: int
    status: str
    selected_node_ids: list[str]
    structure_json: dict[str, object] | None = None
    generated_brief: str | None = None
    result_template_id: int | None = None
    error_message: str | None = None
    created_by_id: int
    assets: list[ImportAssetResponse] = Field(default_factory=list[ImportAssetResponse])
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ImportListResponse(BaseModel):
    """List of design imports."""

    imports: list[ImportResponse]
    total: int


# ── Layout Analysis (12.4) ──


class TextBlockResponse(BaseModel):
    """A text element from the design."""

    node_id: str
    content: str
    font_size: float | None = None
    is_heading: bool = False
    font_family: str | None = None
    font_weight: int | None = None
    line_height: float | None = None
    letter_spacing: float | None = None


class ImagePlaceholderResponse(BaseModel):
    """An image placeholder from the design."""

    node_id: str
    node_name: str
    width: float | None = None
    height: float | None = None


class ButtonElementResponse(BaseModel):
    """A CTA button from the design."""

    node_id: str
    text: str
    width: float | None = None
    height: float | None = None


class AnalyzedSectionResponse(BaseModel):
    """A detected email section."""

    section_type: str
    node_id: str
    node_name: str
    y_position: float | None = None
    width: float | None = None
    height: float | None = None
    column_layout: str = "single"
    column_count: int = 1
    texts: list[TextBlockResponse] = Field(default_factory=list[TextBlockResponse])
    images: list[ImagePlaceholderResponse] = Field(default_factory=list[ImagePlaceholderResponse])
    buttons: list[ButtonElementResponse] = Field(default_factory=list[ButtonElementResponse])
    spacing_after: float | None = None
    bg_color: str | None = None


class LayoutAnalysisResponse(BaseModel):
    """Layout analysis result for preview."""

    connection_id: int
    file_name: str
    overall_width: float | None = None
    sections: list[AnalyzedSectionResponse]
    total_text_blocks: int
    total_images: int


class AnalyzeLayoutRequest(BaseModel):
    """Request to analyze layout of selected nodes."""

    connection_id: int
    selected_node_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Node IDs to analyze (empty = all top-level frames)",
    )


class GenerateBriefRequest(BaseModel):
    """Request to generate a campaign brief from design analysis."""

    connection_id: int
    selected_node_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Node IDs to include (empty = all top-level frames)",
    )
    include_tokens: bool = Field(default=True, description="Include design token summary")


class GenerateBriefResponse(BaseModel):
    """Generated campaign brief."""

    connection_id: int
    brief: str = Field(description="Structured markdown brief for the Scaffolder")
    sections_detected: int
    layout_summary: str


# ── Component Extraction (12.6) ──


class ExtractComponentsRequest(BaseModel):
    """Request to extract components from a design connection."""

    component_ids: list[str] | None = None  # None = extract all
    generate_html: bool = True  # False = preview-only, skip Scaffolder


class ExtractComponentsResponse(BaseModel):
    """Response for component extraction kickoff."""

    import_id: int
    status: str  # "extracting"
    total_components: int
    message: str


# ── Phase 12.5: AI-Assisted Conversion Pipeline ──


class DesignContextSchema(BaseModel):
    """Figma-specific context passed to the Scaffolder alongside the brief."""

    image_urls: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of node_id → locally stored asset URL",
    )
    layout_summary: str | None = Field(
        default=None,
        description="Detected layout summary (e.g. 'header, hero, 2-col content, cta, footer')",
    )
    sections: list[AnalyzedSectionResponse] = Field(
        default_factory=list[AnalyzedSectionResponse],
        description="Analyzed sections from layout analysis",
    )
    design_tokens: dict[str, object] | None = Field(
        default=None,
        description="Extracted design tokens (colors, typography, spacing)",
    )
    source_file: str | None = Field(
        default=None,
        description="Source Figma file name for provenance",
    )


class StartImportRequest(BaseModel):
    """Request to create a design import with a brief for conversion."""

    connection_id: int
    brief: str = Field(
        ..., min_length=10, max_length=50000, description="Campaign brief from ESP/CMS"
    )
    selected_node_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Figma node IDs to import (empty = all top-level frames)",
    )
    template_name: str | None = Field(
        default=None,
        max_length=200,
        description="Override template name (auto-derived from brief if omitted)",
    )


class ConvertImportRequest(BaseModel):
    """Request to trigger Scaffolder conversion on an existing import."""

    run_qa: bool = Field(default=True, description="Run QA gate on generated HTML")
    output_mode: Literal["html", "structured"] = Field(default="structured")
