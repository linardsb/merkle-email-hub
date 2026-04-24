"""Pydantic schemas for QA engine."""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QARunRequest(BaseModel):
    """Request to run QA checks on compiled HTML."""

    build_id: int | None = Field(default=None, description="Email build ID to validate")
    template_version_id: int | None = Field(
        default=None, description="Template version ID for audit linkage"
    )
    project_id: int | None = Field(
        default=None, description="Project ID for per-project QA config (optional)"
    )
    html: str = Field(
        ..., min_length=1, max_length=500_000, description="Compiled HTML to validate"
    )


class QACheckResult(BaseModel):
    """Result of a single QA check."""

    check_name: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: str | None = None
    severity: str = "warning"


class QAOverrideRequest(BaseModel):
    """Request to override failing QA checks."""

    justification: str = Field(
        ..., min_length=10, max_length=2000, description="Reason for overriding failing checks"
    )
    checks_overridden: list[str] = Field(..., min_length=1, description="Check names to override")


class QAOverrideResponse(BaseModel):
    """Response for a QA override."""

    id: int
    qa_result_id: int
    overridden_by_id: int
    justification: str
    checks_overridden: list[str]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class QAVisualDefect(BaseModel):
    """A rendering defect detected by visual QA precheck (per-client)."""

    type: str = Field(description="Defect type, e.g. 'layout_collapse', 'style_stripping'")
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    client_id: str = Field(description="Email client ID, e.g. 'outlook_2019'")
    description: str = Field(description="Human-readable defect description")
    suggested_agent: str | None = Field(
        default=None, description="Fixer agent to route to, e.g. 'outlook_fixer'"
    )
    screenshot_ref: str | None = Field(
        default=None, description="Content block ID for downstream multimodal injection"
    )
    bounding_box: dict[str, int] | None = Field(
        default=None, description="Defect region: {x, y, w, h}"
    )


class QAResultResponse(BaseModel):
    """Full QA result with individual checks."""

    id: int
    build_id: int | None = None
    template_version_id: int | None = None
    overall_score: float
    passed: bool
    checks_passed: int
    checks_total: int
    checks: list[QACheckResult] = []
    override: QAOverrideResponse | None = None
    resilience_score: float | None = None
    visual_defects: list[QAVisualDefect] = []
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ChaosTestRequest(BaseModel):
    """Request to run chaos testing on HTML."""

    html: str = Field(..., min_length=1, max_length=500_000)
    profiles: list[str] | None = Field(
        None,
        description="Profile names to test. None = use defaults from config.",
    )
    project_id: int | None = Field(
        None,
        description="Project ID for auto-documenting failures to knowledge base.",
    )


class ChaosFailure(BaseModel):
    """A specific QA check failure introduced by a chaos profile."""

    profile: str
    check_name: str
    severity: str
    description: str


class ChaosProfileResult(BaseModel):
    """QA results for a single chaos profile."""

    profile: str
    description: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    checks_passed: int
    checks_total: int
    failures: list[ChaosFailure] = []


class ChaosTestResponse(BaseModel):
    """Complete chaos test results."""

    original_score: float = Field(ge=0.0, le=1.0)
    resilience_score: float = Field(ge=0.0, le=1.0)
    profiles_tested: int
    profile_results: list[ChaosProfileResult] = []
    critical_failures: list[ChaosFailure] = []


# --- Property-based testing schemas (Phase 18.2) ---


class PropertyFailureSchema(BaseModel):
    """A property test failure with the config that caused it."""

    invariant_name: str
    violations: list[str]
    config: dict[str, object]


class PropertyTestRequest(BaseModel):
    """Request to run property-based tests."""

    invariants: list[str] | None = Field(None, description="Invariant names to test. None = all.")
    num_cases: int | None = Field(
        None,
        ge=1,
        le=1000,
        description="Number of random emails to generate. Defaults to config value.",
    )
    seed: int | None = Field(None, description="Fixed seed for reproducibility")


class PropertyTestResponse(BaseModel):
    """Complete property test results."""

    total_cases: int
    passed: int
    failed: int
    failures: list[PropertyFailureSchema] = []
    seed: int
    invariants_tested: list[str] = []


# --- Outlook Dependency Analyzer (Phase 19.1) ---


class OutlookDependencySchema(BaseModel):
    """A single Word-engine dependency."""

    type: str
    location: str
    line_number: int
    code_snippet: str = Field(max_length=200)
    severity: str  # high | medium | low
    removable: bool
    modern_replacement: str | None = None


class ModernizationStepSchema(BaseModel):
    """A single modernization action."""

    description: str
    dependency_type: str
    removals: int
    byte_savings: int


class OutlookAnalysisRequest(BaseModel):
    """Request to analyze HTML for Word-engine dependencies."""

    html: str = Field(..., min_length=1, max_length=500_000)


class OutlookAnalysisResponse(BaseModel):
    """Complete Outlook dependency analysis."""

    dependencies: list[OutlookDependencySchema] = []
    total_count: int = 0
    removable_count: int = 0
    byte_savings: int = 0
    modernization_plan: list[ModernizationStepSchema] = []
    vml_count: int = 0
    ghost_table_count: int = 0
    mso_conditional_count: int = 0
    mso_css_count: int = 0
    dpi_image_count: int = 0
    external_class_count: int = 0
    word_wrap_count: int = 0


class OutlookModernizeRequest(BaseModel):
    """Request to modernize HTML by removing Word-engine dependencies."""

    html: str = Field(..., min_length=1, max_length=500_000)
    target: str = Field(
        default="dual_support",
        description="Modernization target: new_outlook (aggressive), dual_support (keep conditionals), audit_only (no changes)",
    )


class OutlookModernizeResponse(BaseModel):
    """Modernization result."""

    html: str
    changes_applied: int
    bytes_before: int
    bytes_after: int
    bytes_saved: int
    target: str
    analysis: OutlookAnalysisResponse


# --- Audience-Aware Migration Planner (Phase 19.2) ---


class AudienceProfileSchema(BaseModel):
    """Email client distribution as percentages (0.0-1.0)."""

    client_distribution: dict[str, float] = Field(
        ...,
        description="Client name to audience share mapping. Values should sum to ~1.0.",
        examples=[{"outlook_2016": 0.15, "gmail_web": 0.35, "apple_mail": 0.25}],
    )

    @field_validator("client_distribution")
    @classmethod
    def validate_distribution(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate all values are between 0 and 1."""
        for client, share in v.items():
            if not 0.0 <= share <= 1.0:
                msg = f"Share for '{client}' must be between 0.0 and 1.0, got {share}"
                raise ValueError(msg)
        return v


class MigrationPhaseSchema(BaseModel):
    """A single phase of the migration plan."""

    name: str
    description: str
    dependency_types: list[str]
    dependency_count: int
    audience_impact: float
    safe_when: str
    risk_level: str
    estimated_byte_savings: int


class MigrationPlanRequest(BaseModel):
    """Request for audience-aware migration plan."""

    html: str = Field(..., min_length=1, max_length=500_000)
    audience: AudienceProfileSchema | None = Field(
        default=None,
        description="Client distribution. Uses industry averages if omitted.",
    )


class MigrationPlanResponse(BaseModel):
    """Phased migration plan response."""

    phases: list[MigrationPhaseSchema]
    total_dependencies: int
    total_removable: int
    total_savings_bytes: int
    word_engine_audience: float
    risk_assessment: str
    recommendation: str
    analysis: OutlookAnalysisResponse


# --- Deliverability Prediction Score (Phase 20.3) ---


class DeliverabilityIssue(BaseModel):
    """A specific deliverability finding with fix recommendation."""

    dimension: str = Field(
        description="content_quality | html_hygiene | auth_readiness | engagement_signals"
    )
    severity: str = Field(description="error | warning | info")
    description: str
    fix: str


class DeliverabilityDimension(BaseModel):
    """Score breakdown for a single dimension (0-25 each)."""

    name: str
    score: int = Field(ge=0, le=25)
    max_score: int = 25
    issues: list[DeliverabilityIssue] = []


class DeliverabilityScoreRequest(BaseModel):
    """Request to score email deliverability."""

    html: str = Field(..., min_length=1, max_length=500_000)


class DeliverabilityScoreResponse(BaseModel):
    """Complete deliverability prediction result."""

    score: int = Field(ge=0, le=100, description="Overall deliverability score")
    passed: bool = Field(description="True if score >= threshold")
    threshold: int
    dimensions: list[DeliverabilityDimension] = []
    issues: list[DeliverabilityIssue] = []
    summary: str = Field(description="Human-readable summary of findings")


# --- Gmail AI Summary Predictor (Phase 20.1) ---


class GmailPredictRequest(BaseModel):
    """Request for Gmail AI summary prediction."""

    html: str = Field(..., min_length=1, max_length=500_000)
    subject: str = Field(..., min_length=1, max_length=998)
    from_name: str = Field(..., min_length=1, max_length=256)


class GmailPredictResponse(BaseModel):
    """Gmail AI summary prediction result."""

    summary_text: str
    predicted_category: str
    key_actions: list[str] = []
    promotion_signals: list[str] = []
    improvement_suggestions: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


class GmailOptimizeRequest(BaseModel):
    """Request for Gmail preview text optimization."""

    html: str = Field(..., min_length=1, max_length=500_000)
    subject: str = Field(..., min_length=1, max_length=998)
    from_name: str = Field(..., min_length=1, max_length=256)
    target_summary: str | None = Field(None, max_length=500, description="Desired summary focus")


class GmailOptimizeResponse(BaseModel):
    """Gmail preview text optimization result."""

    original_subject: str
    suggested_subjects: list[str] = []
    original_preview: str
    suggested_previews: list[str] = []
    reasoning: str = ""


# --- BIMI Readiness Check (Phase 20.4) ---


class BIMICheckRequest(BaseModel):
    """Request to check BIMI readiness for a domain."""

    domain: str = Field(
        ...,
        min_length=4,
        max_length=253,
        description="Sending domain to check (e.g. 'example.com')",
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain format (labels separated by dots, no leading hyphens)."""
        import re

        if not re.match(
            r"^[A-Za-z0-9]([A-Za-z0-9-]{0,62}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,62}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$",
            v,
        ):
            msg = "Invalid domain format"
            raise ValueError(msg)
        return v


class BIMICheckResponse(BaseModel):
    """Complete BIMI readiness check result."""

    domain: str
    ready: bool

    # DMARC
    dmarc_ready: bool
    dmarc_policy: str
    dmarc_record: str | None = None

    # BIMI record
    bimi_record_exists: bool = False
    bimi_record: str | None = None
    bimi_svg_url: str | None = None
    bimi_authority_url: str | None = None

    # SVG validation
    svg_valid: bool | None = None

    # CMC status
    cmc_status: str = "unknown"

    # Generated record template
    generated_record: str = ""

    # All issues found
    issues: list[str] = []
