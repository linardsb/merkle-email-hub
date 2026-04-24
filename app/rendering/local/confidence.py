"""Rendering confidence scoring for local email client emulation.

Quantifies how faithful a local preview is expected to be relative
to the real email client, based on emulator coverage, CSS compatibility,
calibration seeds, and layout complexity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from app.knowledge.ontology.query import _extract_css_content
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import SupportLevel
from app.rendering.local.emulators import _EMULATORS
from app.rendering.local.profiles import RenderingProfile

logger = get_logger(__name__)

_SEEDS_PATH = Path(__file__).parent / "confidence_seeds.yaml"

# ── Mapping: emulator_id -> ontology client_id(s) ──
# Emulators map to one or more ontology clients for CSS compatibility lookup.
_EMULATOR_TO_ONTOLOGY: dict[str, list[str]] = {
    "gmail_web": ["gmail_web"],
    "outlook_web": ["outlook_web"],
    "yahoo_web": ["yahoo_web"],
    "yahoo_mobile": ["yahoo_ios"],
    "samsung_mail": ["samsung_email"],
    "outlook_desktop": ["outlook_2021"],
    "thunderbird": ["thunderbird"],
    "android_gmail": ["gmail_android"],
}

# ── Layout complexity patterns ──
_TABLE_OPEN_RE = re.compile(r"<table\b", re.IGNORECASE)
_FLEXBOX_RE = re.compile(r"display\s*:\s*(?:flex|inline-flex)", re.IGNORECASE)
_GRID_RE = re.compile(r"display\s*:\s*(?:grid|inline-grid)", re.IGNORECASE)
_POSITION_ABS_RE = re.compile(r"position\s*:\s*(?:absolute|fixed)", re.IGNORECASE)
_VML_RE = re.compile(r"<v:", re.IGNORECASE)
_MSO_CONDITIONAL_RE = re.compile(r"<!--\[if\s+mso", re.IGNORECASE)
_MEDIA_QUERY_RE = re.compile(r"@media\b", re.IGNORECASE)


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Component scores that feed into the overall confidence score."""

    emulator_coverage: float  # 0.0-1.0
    css_compatibility: float  # 0.0-1.0
    calibration_accuracy: float  # 0.0-1.0
    layout_complexity: float  # 0.0-1.0 (higher = more complex)
    known_blind_spots: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class RenderingConfidence:
    """Confidence assessment for a rendering preview."""

    score: float  # 0-100
    breakdown: ConfidenceBreakdown
    recommendations: list[str] = field(default_factory=list[str])

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON storage / API response."""
        return {
            "score": round(self.score, 1),
            "breakdown": {
                "emulator_coverage": round(self.breakdown.emulator_coverage, 3),
                "css_compatibility": round(self.breakdown.css_compatibility, 3),
                "calibration_accuracy": round(self.breakdown.calibration_accuracy, 3),
                "layout_complexity": round(self.breakdown.layout_complexity, 3),
                "known_blind_spots": self.breakdown.known_blind_spots,
            },
            "recommendations": self.recommendations,
        }


def _load_seeds() -> dict[str, dict[str, Any]]:
    """Load calibration seed data from YAML."""
    if not _SEEDS_PATH.exists():
        logger.warning("confidence.seeds_not_found", path=str(_SEEDS_PATH))
        return {}
    with _SEEDS_PATH.open() as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def _table_nesting_depth(html: str) -> int:
    """Compute max nesting depth of <table> elements."""
    depth = 0
    max_depth = 0
    lower = html.lower()
    i = 0
    while i < len(lower):
        if lower[i : i + 6] == "<table":
            depth += 1
            max_depth = max(max_depth, depth)
            i += 6
        elif lower[i : i + 8] == "</table>":
            depth = max(0, depth - 1)
            i += 8
        else:
            i += 1
    return max_depth


def layout_complexity_score(html: str) -> float:
    """Score layout complexity from 0.0 (simple) to 1.0 (highly complex).

    Factors: table nesting depth, flexbox/grid, absolute positioning,
    VML blocks, MSO conditionals, media query count.
    """
    score = 0.0

    # Table nesting >3 deep
    nesting = _table_nesting_depth(html)
    if nesting > 3:
        score += 0.2

    # Flexbox usage
    if _FLEXBOX_RE.search(html):
        score += 0.15

    # Grid usage
    if _GRID_RE.search(html):
        score += 0.15

    # Absolute/fixed positioning
    if _POSITION_ABS_RE.search(html):
        score += 0.1

    # VML blocks
    if _VML_RE.search(html):
        score += 0.1

    # MSO conditionals
    if _MSO_CONDITIONAL_RE.search(html):
        score += 0.05

    # Media queries >5
    mq_count = len(_MEDIA_QUERY_RE.findall(html))
    if mq_count > 5:
        score += 0.1

    return min(1.0, score)


def _emulator_coverage_score(profile: RenderingProfile) -> float:
    """Calculate emulator rule coverage as fraction of known behaviors modeled.

    Profiles with an emulator get coverage based on rule count relative to
    known behavior count. Profiles without emulators get a baseline 0.3
    (CSS injection only).
    """
    if not profile.emulator_id:
        return 0.3  # CSS injection only, no emulator

    emulator = _EMULATORS.get(profile.emulator_id)
    if not emulator:
        return 0.3

    rule_count = len(emulator.rules)

    # Known behavior counts per client (estimated total behaviors
    # a real client applies, including those we can't emulate).
    _KNOWN_BEHAVIORS: dict[str, int] = {
        "gmail_web": 8,
        "outlook_web": 5,
        "yahoo_web": 5,
        "yahoo_mobile": 6,
        "samsung_mail": 5,
        "outlook_desktop": 10,
        "thunderbird": 3,
        "android_gmail": 10,
    }

    known = _KNOWN_BEHAVIORS.get(profile.emulator_id, max(rule_count + 2, 5))
    return min(1.0, rule_count / known)


def _css_compatibility_score(
    html: str,
    profile: RenderingProfile,
    ontology: OntologyRegistry,
) -> float:
    """Fraction of CSS properties in HTML that are supported by the target client.

    Returns 1.0 if all CSS is supported (or no CSS found), lower if the
    target client doesn't support some properties used in the HTML.
    """
    css_content = _extract_css_content(html)
    if not css_content:
        return 1.0  # No CSS = nothing to be incompatible with

    emulator_id = profile.emulator_id or profile.name
    ontology_clients = _EMULATOR_TO_ONTOLOGY.get(emulator_id, [])
    if not ontology_clients:
        return 0.8  # Unknown client -- conservative estimate

    # Count total CSS properties used and how many are supported
    total_props = 0
    supported_props = 0.0

    for prop in ontology.properties:
        prop_escaped = re.escape(prop.property_name)
        if prop.value:
            val_escaped = re.escape(prop.value)
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:\s*{val_escaped}"
        else:
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:"

        if not re.search(pattern, css_content):
            continue

        total_props += 1

        # Check worst-case support across mapped ontology clients
        worst: SupportLevel = SupportLevel.FULL
        for client_id in ontology_clients:
            level = ontology.get_support(prop.id, client_id)
            if level == SupportLevel.NONE:
                worst = SupportLevel.NONE
                break
            if level == SupportLevel.PARTIAL:
                worst = SupportLevel.PARTIAL

        if worst in (SupportLevel.FULL, SupportLevel.UNKNOWN):
            supported_props += 1
        elif worst == SupportLevel.PARTIAL:
            supported_props += 0.5

    if total_props == 0:
        return 1.0

    return supported_props / total_props


class RenderingConfidenceScorer:
    """Computes rendering confidence scores for email client previews."""

    def __init__(self) -> None:
        self._seeds = _load_seeds()

    def get_seed(self, emulator_id: str) -> dict[str, Any]:
        """Get calibration seed data for an emulator."""
        return dict(
            self._seeds.get(
                emulator_id,
                {
                    "accuracy": 0.5,
                    "sample_count": 0,
                    "last_calibrated": "",
                    "known_blind_spots": [],
                },
            )
        )

    async def get_seed_with_db(self, emulator_id: str, db: AsyncSession) -> dict[str, Any]:
        """DB-first seed lookup, YAML fallback."""
        from app.rendering.calibration.repository import CalibrationRepository

        repo = CalibrationRepository(db)
        summary = await repo.get_summary(emulator_id)
        if summary and summary.sample_count > 0:
            return {
                "accuracy": summary.current_accuracy / 100.0,
                "sample_count": summary.sample_count,
                "last_calibrated": str(summary.updated_at) if summary.updated_at else "",
                "known_blind_spots": list(summary.known_blind_spots),
            }
        return self.get_seed(emulator_id)

    def score(self, html: str, profile: RenderingProfile) -> RenderingConfidence:
        """Compute rendering confidence for a profile against given HTML."""
        emulator_id = profile.emulator_id or profile.name
        seed = self.get_seed(emulator_id)
        ontology = load_ontology()

        # Component scores
        emulator_cov = _emulator_coverage_score(profile)
        css_compat = _css_compatibility_score(html, profile, ontology)
        calibration_acc = float(seed.get("accuracy", 0.5))
        layout_complex = layout_complexity_score(html)
        blind_spots: list[str] = list(seed.get("known_blind_spots", []))

        breakdown = ConfidenceBreakdown(
            emulator_coverage=emulator_cov,
            css_compatibility=css_compat,
            calibration_accuracy=calibration_acc,
            layout_complexity=layout_complex,
            known_blind_spots=blind_spots,
        )

        # Weighted formula
        raw = (
            emulator_cov * 0.25
            + css_compat * 0.25
            + calibration_acc * 0.35
            + (1.0 - layout_complex) * 0.15
        )
        final_score = round(min(100.0, max(0.0, raw * 100)), 1)

        # Generate recommendations
        recommendations = self._build_recommendations(final_score, breakdown, emulator_id)

        return RenderingConfidence(
            score=final_score,
            breakdown=breakdown,
            recommendations=recommendations,
        )

    def _build_recommendations(
        self,
        score: float,
        breakdown: ConfidenceBreakdown,
        emulator_id: str,
    ) -> list[str]:
        """Generate actionable recommendations based on confidence breakdown."""
        recs: list[str] = []

        if score < 70:
            recs.append(
                f"Low confidence ({score:.0f}%) — consider using Litmus or "
                "Email on Acid for this client."
            )

        if breakdown.css_compatibility < 0.7:
            recs.append(
                "CSS compatibility is low — some properties used in this "
                "email are unsupported by this client."
            )

        if breakdown.layout_complexity > 0.5:
            recs.append(
                "Complex layout detected — emulator accuracy decreases "
                "with nested tables, flexbox, or VML."
            )

        if breakdown.emulator_coverage < 0.5:
            recs.append(
                f"Emulator coverage for {emulator_id} is limited — "
                "not all client behaviors are modeled."
            )

        if breakdown.known_blind_spots:
            spots = ", ".join(breakdown.known_blind_spots[:3])
            recs.append(f"Known blind spots: {spots}")

        return recs
