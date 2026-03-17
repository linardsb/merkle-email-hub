"""Frozen dataclasses for Outlook dependency analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutlookDependency:
    """A single Word-engine dependency found in the HTML."""

    type: str  # vml_shape | ghost_table | mso_conditional | mso_css | dpi_image | external_class | word_wrap_hack
    location: str  # Human-readable location (e.g., "line 45, <v:roundrect>")
    line_number: int  # 1-based line number
    code_snippet: str  # Trimmed source excerpt (max 200 chars)
    severity: str  # high | medium | low
    removable: bool  # Whether it can be safely removed for New Outlook
    modern_replacement: str | None  # CSS/HTML replacement suggestion, or None


@dataclass(frozen=True)
class ModernizationStep:
    """A single modernization action to apply."""

    description: str  # What this step does
    dependency_type: str  # Which dependency type it addresses
    removals: int  # How many instances it removes
    byte_savings: int  # Estimated bytes saved


@dataclass(frozen=True)
class OutlookAnalysis:
    """Complete analysis result."""

    dependencies: list[OutlookDependency] = field(default_factory=lambda: [])
    total_count: int = 0
    removable_count: int = 0
    byte_savings: int = 0
    modernization_plan: list[ModernizationStep] = field(default_factory=lambda: [])
    # Breakdown by type
    vml_count: int = 0
    ghost_table_count: int = 0
    mso_conditional_count: int = 0
    mso_css_count: int = 0
    dpi_image_count: int = 0
    external_class_count: int = 0
    word_wrap_count: int = 0


@dataclass(frozen=True)
class ModernizeResult:
    """Result of modernization."""

    html: str
    changes_applied: int
    bytes_before: int
    bytes_after: int
    target: str


# --- Audience-Aware Migration Planning (Phase 19.2) ---

# Canonical client names for audience profiles
WORD_ENGINE_CLIENTS: frozenset[str] = frozenset(
    {
        "outlook_2007",
        "outlook_2010",
        "outlook_2013",
        "outlook_2016",
        "outlook_2019",
        "outlook_2021",
    }
)

NEW_OUTLOOK_CLIENTS: frozenset[str] = frozenset(
    {
        "new_outlook",
        "outlook_web",
    }
)

# Which dependency types are only needed for Word-engine Outlook
WORD_ENGINE_DEPENDENCY_TYPES: frozenset[str] = frozenset(
    {
        "vml_shape",
        "ghost_table",
        "mso_conditional",
        "mso_css",
        "dpi_image",
        "external_class",
        "word_wrap_hack",
    }
)

# Risk tiers: dependency_type -> base risk if removed while audience still on old Outlook
DEPENDENCY_RISK: dict[str, str] = {
    "vml_shape": "high",  # VML buttons break completely
    "ghost_table": "high",  # Layout breaks without ghost tables
    "mso_conditional": "high",  # Conditional content disappears
    "mso_css": "medium",  # Spacing/alignment shifts
    "dpi_image": "low",  # Images may render at wrong DPI
    "external_class": "low",  # Minor spacing issues in Outlook.com
    "word_wrap_hack": "low",  # Text may not wrap in edge cases
}


@dataclass(frozen=True)
class AudienceProfile:
    """Email client distribution as percentages (0.0-1.0).

    Keys are canonical client names, values are share of audience.
    Example: {"outlook_2016": 0.15, "gmail_web": 0.35, "apple_mail": 0.25, ...}
    """

    client_distribution: dict[str, float]

    @property
    def word_engine_share(self) -> float:
        """Total audience share on Word-engine Outlook versions."""
        return sum(
            share
            for client, share in self.client_distribution.items()
            if client in WORD_ENGINE_CLIENTS
        )

    @property
    def new_outlook_share(self) -> float:
        """Total audience share on New Outlook (Chromium-based)."""
        return sum(
            share
            for client, share in self.client_distribution.items()
            if client in NEW_OUTLOOK_CLIENTS
        )


@dataclass(frozen=True)
class MigrationPhase:
    """A single phase of the migration plan."""

    name: str
    description: str
    dependencies_to_remove: list[OutlookDependency]
    dependency_types: list[str]  # Unique types in this phase
    audience_impact: float  # % of audience affected (0.0-1.0)
    safe_when: str  # "now" | "when word_engine < 10%" | "when word_engine < 5%" | "after word_engine sunset"
    risk_level: str  # "low" | "medium" | "high"
    estimated_byte_savings: int


@dataclass(frozen=True)
class MigrationPlan:
    """Complete phased migration plan."""

    phases: list[MigrationPhase]
    total_dependencies: int
    total_removable: int
    total_savings_bytes: int
    word_engine_audience: float  # Current Word-engine share
    risk_assessment: str  # Overall risk summary
    recommendation: str  # "aggressive" | "moderate" | "conservative"
