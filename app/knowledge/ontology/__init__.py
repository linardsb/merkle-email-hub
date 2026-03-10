"""Email development ontology — CSS properties, email clients, support matrix.

Usage:
    from app.knowledge.ontology import get_ontology

    onto = get_ontology()
    level = onto.get_support("display_flex", "outlook_2019_win")  # SupportLevel.NONE
    unsupported = onto.properties_unsupported_by("gmail_web")
    fallbacks = onto.fallbacks_for("display_flex")
"""

from app.knowledge.ontology.competitive_feasibility import (
    CapabilityFeasibility,
    CompetitiveReport,
    build_competitive_report,
    compute_audience_coverage,
    format_feasibility_context,
)
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import (
    ClientEngine,
    CSSCategory,
    CSSProperty,
    EmailClient,
    Fallback,
    SupportEntry,
    SupportLevel,
)

__all__ = [
    "CSSCategory",
    "CSSProperty",
    "CapabilityFeasibility",
    "ClientEngine",
    "CompetitiveReport",
    "EmailClient",
    "Fallback",
    "OntologyRegistry",
    "SupportEntry",
    "SupportLevel",
    "build_competitive_report",
    "compute_audience_coverage",
    "format_feasibility_context",
    "get_ontology",
    "load_ontology",
]


def get_ontology() -> OntologyRegistry:
    """Get the cached ontology registry. Alias for load_ontology()."""
    return load_ontology()
