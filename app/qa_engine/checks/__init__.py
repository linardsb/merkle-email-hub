"""QA check implementations for the 14-point quality gate.

10 of 14 checks share the standard `RuleEngine + parse + score + filter`
pattern and are built declaratively via `_factory.RuleEngineCheck`. The 4
bespoke checks (`css_audit`, `css_support`, `deliverability`, `liquid_syntax`)
keep their own classes. `RenderingResilienceCheck` is intentionally NOT in
`ALL_CHECKS` — it iterates `ALL_CHECKS` itself for chaos-engine fault
injection, so registering it would cause infinite recursion. It is loaded
directly by `app.qa_engine.service` when chaos mode is enabled.
"""

from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

# Import custom checks to trigger registration of all custom check functions
import app.qa_engine.custom_checks as _custom_checks  # pyright: ignore[reportUnusedImport]
from app.projects.design_system import design_system_to_brand_rules, load_design_system
from app.qa_engine.brand_analyzer import clear_brand_cache
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.checks._factory import RuleEngineCheck
from app.qa_engine.checks.css_audit import CSSAuditCheck
from app.qa_engine.checks.css_support import CssSupportCheck
from app.qa_engine.checks.deliverability import DeliverabilityCheck
from app.qa_engine.checks.liquid_syntax import LiquidSyntaxCheck
from app.qa_engine.dark_mode_parser import clear_dm_cache
from app.qa_engine.file_size_analyzer import clear_file_size_cache
from app.qa_engine.image_analyzer import clear_image_cache
from app.qa_engine.link_parser import clear_link_cache
from app.qa_engine.mso_parser import clear_mso_cache
from app.qa_engine.personalisation_validator import clear_personalisation_cache
from app.qa_engine.schemas import QACheckResult


class QACheckProtocol(Protocol):
    """Protocol that all QA checks must satisfy."""

    name: str

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult: ...


_RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


# ── Brand-compliance helpers (split out of the original BrandComplianceCheck) ──


def _has_brand_rules(config: QACheckConfig | None) -> bool:
    if config is None:
        return False
    params = config.params
    return bool(
        params.get("allowed_colors")
        or params.get("required_fonts")
        or params.get("required_elements")
        or params.get("forbidden_patterns")
    )


def _enrich_brand_config(config: QACheckConfig | None) -> QACheckConfig | None:
    """Derive brand rules from `params['_design_system']` when no rules set."""
    if config is None:
        return None
    if _has_brand_rules(config):
        return config
    ds_raw = config.params.get("_design_system")
    if not ds_raw:
        return config
    try:
        ds = load_design_system(ds_raw)
    except ValidationError:
        return config
    if ds is None:
        return config
    derived = design_system_to_brand_rules(ds)
    merged_params = {k: v for k, v in config.params.items() if k != "_design_system"}
    merged_params.update(derived)
    return QACheckConfig(
        enabled=config.enabled,
        severity=config.severity,
        threshold=config.threshold,
        params=merged_params,
    )


def _brand_skip_predicate(config: QACheckConfig | None) -> bool:
    """Skip brand check (pass with info) when no brand rules are configured."""
    return not _has_brand_rules(config)


# ── Registry ──

ALL_CHECKS: list[QACheckProtocol] = [
    RuleEngineCheck(
        name="html_validation",
        rules_path=_RULES_DIR / "email_structure.yaml",
        failed_severity="error",
    ),
    CssSupportCheck(),
    CSSAuditCheck(),
    RuleEngineCheck(
        name="file_size",
        rules_path=_RULES_DIR / "file_size.yaml",
        cache_clear=clear_file_size_cache,
        empty_strategy="skip",
        error_threshold=0.30,
        summary_filter_prefix="Raw:",
        no_issues_details="All file size thresholds met",
        parse_error_message="Failed to parse HTML for file size analysis",
    ),
    RuleEngineCheck(
        name="link_validation",
        rules_path=_RULES_DIR / "link_validation.yaml",
        cache_clear=clear_link_cache,
    ),
    RuleEngineCheck(
        name="spam_score",
        rules_path=_RULES_DIR / "spam_score.yaml",
        threshold_pass=True,
    ),
    RuleEngineCheck(
        name="dark_mode",
        rules_path=_RULES_DIR / "dark_mode.yaml",
        cache_clear=clear_dm_cache,
    ),
    RuleEngineCheck(
        name="accessibility",
        rules_path=_RULES_DIR / "accessibility.yaml",
    ),
    RuleEngineCheck(
        name="fallback",
        rules_path=_RULES_DIR / "mso_fallback.yaml",
        cache_clear=clear_mso_cache,
    ),
    RuleEngineCheck(
        name="image_optimization",
        rules_path=_RULES_DIR / "image_optimization.yaml",
        cache_clear=clear_image_cache,
        empty_strategy="skip",
        error_threshold=0.30,
        summary_filter_prefix="Images:",
        no_issues_details="All images properly optimized",
        parse_error_message="Failed to parse HTML for image analysis",
    ),
    RuleEngineCheck(
        name="brand_compliance",
        rules_path=_RULES_DIR / "brand_compliance.yaml",
        cache_clear=clear_brand_cache,
        respects_disabled_config=True,
        disabled_message="Brand compliance check disabled by configuration",
        config_enricher=_enrich_brand_config,
        skip_predicate=_brand_skip_predicate,
        skip_message="No brand rules configured — set up brand profile for enforcement",
        error_threshold=0.50,
        summary_filter_prefix="Brand compliance:",
        no_issues_details="All brand rules satisfied",
    ),
    RuleEngineCheck(
        name="personalisation_syntax",
        rules_path=_RULES_DIR / "personalisation_syntax.yaml",
        cache_clear=clear_personalisation_cache,
        respects_disabled_config=True,
        disabled_message="Personalisation syntax check disabled by configuration",
        empty_strategy="pass_info",
        empty_message="Empty HTML document — no personalisation to validate",
        error_threshold=0.30,
        severity_mode="deduction",
        summary_filter_prefix="Summary:",
        no_issues_details="No personalisation issues found",
    ),
    DeliverabilityCheck(),
    LiquidSyntaxCheck(),
]

__all__ = ["ALL_CHECKS", "QACheckProtocol"]
