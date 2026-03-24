"""Fixtures for visual regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rendering.tests.visual_regression.regression_runner import (
    VisualRegressionRunner,
)

BASELINES_DIR = Path(__file__).parent / "baselines"


@pytest.fixture
def visual_baselines() -> Path:
    """Path to the committed baselines directory."""
    return BASELINES_DIR


@pytest.fixture
def regression_runner(visual_baselines: Path) -> VisualRegressionRunner:
    """Initialized runner with default config."""
    return VisualRegressionRunner(baseline_dir=visual_baselines)
