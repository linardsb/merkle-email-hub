"""Shared schemas for eval analysis and calibration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FailureCluster:
    """A group of related failures sharing a root pattern."""

    cluster_id: str  # e.g., "scaffolder:brief_fidelity:missing_hero"
    agent: str
    criterion: str
    pattern: str  # Human-readable failure pattern description
    trace_ids: list[str] = field(default_factory=lambda: list[str]())
    sample_reasonings: list[str] = field(default_factory=lambda: list[str]())
    count: int = 0


@dataclass(frozen=True)
class HumanLabel:
    """A single human judgment on one trace+criterion."""

    trace_id: str
    agent: str
    criterion: str
    human_pass: bool
    notes: str = ""


@dataclass(frozen=True)
class CalibrationResult:
    """TPR/TNR metrics for one criterion."""

    agent: str
    criterion: str
    true_positives: int  # Judge=pass, Human=pass
    true_negatives: int  # Judge=fail, Human=fail
    false_positives: int  # Judge=pass, Human=fail
    false_negatives: int  # Judge=fail, Human=pass
    total: int

    @property
    def tpr(self) -> float:
        """True Positive Rate (sensitivity). Target > 0.85."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def tnr(self) -> float:
        """True Negative Rate (specificity). Target > 0.80."""
        denom = self.true_negatives + self.false_positives
        return self.true_negatives / denom if denom > 0 else 0.0

    @property
    def meets_targets(self) -> bool:
        """Check if both TPR and TNR meet minimum thresholds."""
        return self.tpr >= 0.85 and self.tnr >= 0.80


@dataclass(frozen=True)
class QACalibrationResult:
    """Agreement metrics for one QA check vs human labels."""

    check_name: str
    agreement_rate: float  # % of times QA check agrees with human
    false_pass_rate: float  # QA says pass but human says fail
    false_fail_rate: float  # QA says fail but human says pass
    total: int
    recommended_threshold: float | None = None


@dataclass(frozen=True)
class RegressionReport:
    """Comparison of current eval run vs baseline."""

    agent: str
    current_pass_rate: float
    baseline_pass_rate: float
    delta: float  # current - baseline
    regressed_criteria: list[str]  # Criteria where pass rate dropped > threshold
    improved_criteria: list[str]
    is_regression: bool  # True if any criterion regressed beyond tolerance


@dataclass(frozen=True)
class BlueprintEvalTrace:
    """End-to-end blueprint pipeline evaluation trace."""

    run_id: str
    blueprint_name: str
    brief: str
    total_steps: int
    total_retries: int
    qa_passed: bool | None
    final_html_length: int
    total_tokens: int
    elapsed_seconds: float
    node_trace: list[dict[str, object]]
    error: str | None = None
