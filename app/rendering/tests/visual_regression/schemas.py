"""Schemas for visual regression testing results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BaselineResult:
    """Result of generating a single baseline screenshot."""

    template_slug: str
    profile_id: str
    output_path: Path
    size_bytes: int


@dataclass(frozen=True)
class BaselineManifest:
    """Manifest of all generated baselines."""

    baselines: list[BaselineResult]
    template_slugs: list[str]
    profile_ids: list[str]
    emulator_versions: dict[str, str]  # profile_id -> version hash


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing one baseline against current emulator output."""

    template: str
    profile: str
    diff_percentage: float
    passed: bool
    diff_image_path: Path | None  # generated only on failure
    error: str | None = None  # if rendering/comparison failed


@dataclass
class RegressionReport:
    """Aggregate report from a visual regression run."""

    passed: bool
    threshold: float
    results: list[ComparisonResult] = field(default_factory=list[ComparisonResult])
    skipped: list[str] = field(default_factory=list[str])  # profiles with no baseline

    @property
    def failures(self) -> list[ComparisonResult]:
        return [r for r in self.results if not r.passed]

    @property
    def total(self) -> int:
        return len(self.results)
