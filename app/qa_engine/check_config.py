"""QA check configuration: per-check settings with YAML defaults and per-project overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULTS_PATH = Path(__file__).parent / "defaults.yaml"
_cached_defaults: QAProfileConfig | None = None


class QACheckConfig(BaseModel):
    """Configuration for a single QA check."""

    enabled: bool = True
    severity: str = Field(default="warning", pattern=r"^(error|warning|info)$")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    params: dict[str, Any] = Field(default_factory=dict)


class QAProfileConfig(BaseModel):
    """Aggregate config for all QA checks (a 'QA profile')."""

    html_validation: QACheckConfig = Field(default_factory=QACheckConfig)
    css_support: QACheckConfig = Field(default_factory=QACheckConfig)
    file_size: QACheckConfig = Field(default_factory=QACheckConfig)
    link_validation: QACheckConfig = Field(default_factory=QACheckConfig)
    spam_score: QACheckConfig = Field(default_factory=QACheckConfig)
    dark_mode: QACheckConfig = Field(default_factory=QACheckConfig)
    accessibility: QACheckConfig = Field(default_factory=QACheckConfig)
    fallback: QACheckConfig = Field(default_factory=QACheckConfig)
    image_optimization: QACheckConfig = Field(default_factory=QACheckConfig)
    brand_compliance: QACheckConfig = Field(default_factory=QACheckConfig)
    personalisation_syntax: QACheckConfig = Field(default_factory=QACheckConfig)
    deliverability: QACheckConfig = Field(default_factory=lambda: QACheckConfig(enabled=False))

    def get_check_config(self, check_name: str) -> QACheckConfig | None:
        """Get config for a check by name. Returns None if check name is unknown."""
        return getattr(self, check_name, None)


def load_defaults() -> QAProfileConfig:
    """Load default QA profile from defaults.yaml. Cached after first call."""
    global _cached_defaults
    if _cached_defaults is not None:
        return _cached_defaults

    if not _DEFAULTS_PATH.exists():
        logger.warning("qa_config.defaults_missing", path=str(_DEFAULTS_PATH))
        _cached_defaults = QAProfileConfig()
        return _cached_defaults

    with _DEFAULTS_PATH.open() as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    _cached_defaults = QAProfileConfig.model_validate(raw)
    logger.info("qa_config.defaults_loaded", checks=len(raw))
    return _cached_defaults


def merge_profile(
    defaults: QAProfileConfig,
    overrides: dict[str, Any] | None,
) -> QAProfileConfig:
    """Merge per-project overrides on top of defaults.

    Only fields present in overrides are changed; everything else falls through to defaults.
    """
    if not overrides:
        return defaults

    merged = defaults.model_dump()
    for check_name, check_overrides in overrides.items():
        if check_name in merged and isinstance(check_overrides, dict):
            merged[check_name].update(check_overrides)

    return QAProfileConfig.model_validate(merged)
