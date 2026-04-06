"""Tests for QA check meta-evaluation framework (48.9)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.main import app
from app.qa_engine.meta_eval import (
    AdversarialEmail,
    LabeledSample,
    MetaEvalReport,
    MetaEvaluator,
)

BASE = "/api/v1/qa"


# ── Helpers ──


def _make_user(role: str = "admin") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_pass_check(name: str) -> AsyncMock:
    """Create a mock check that always passes."""
    from app.qa_engine.schemas import QACheckResult

    check = AsyncMock()
    check.name = name
    check.run = AsyncMock(
        return_value=QACheckResult(
            check_name=name,
            passed=True,
            score=1.0,
            details=None,
            severity="info",
        )
    )
    return check


def _make_fail_check(name: str) -> AsyncMock:
    """Create a mock check that always fails."""
    from app.qa_engine.schemas import QACheckResult

    check = AsyncMock()
    check.name = name
    check.run = AsyncMock(
        return_value=QACheckResult(
            check_name=name,
            passed=False,
            score=0.0,
            details="Failed",
            severity="error",
        )
    )
    return check


# ── Fixtures ──


@pytest.fixture
def labeled_golden() -> list[LabeledSample]:
    """Samples where check_a should pass and check_b should fail."""
    return [
        LabeledSample(
            name="good-email",
            html="<html><body><table><tr><td>Hello</td></tr></table></body></html>",
            expected_qa={"check_a": "pass", "check_b": "fail"},
        ),
    ]


@pytest.fixture
def labeled_mixed() -> list[LabeledSample]:
    """Mix of pass/fail expectations for precision/recall testing."""
    return [
        LabeledSample(
            name="sample-1",
            html="<html>1</html>",
            expected_qa={"check_a": "pass"},
        ),
        LabeledSample(
            name="sample-2",
            html="<html>2</html>",
            expected_qa={"check_a": "fail"},
        ),
        LabeledSample(
            name="sample-3",
            html="<html>3</html>",
            expected_qa={"check_a": "pass"},
        ),
        LabeledSample(
            name="sample-4",
            html="<html>4</html>",
            expected_qa={"check_a": "fail"},
        ),
    ]


@pytest.fixture
def labeled_adversarial() -> list[AdversarialEmail]:
    """Adversarial emails targeting check_a."""
    return [
        AdversarialEmail(
            name="adversarial-1",
            html="<html><body>Adversarial</body></html>",
            expected_qa={"check_a": "fail"},
            target_check="check_a",
        ),
    ]


@pytest.fixture
def _auth_admin() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("viewer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── Unit Tests ──


@pytest.mark.asyncio
async def test_evaluate_check_all_pass(labeled_golden: list[LabeledSample]) -> None:
    """Golden ref where check passes — verify TP counted."""
    mock_check = _make_pass_check("check_a")
    evaluator = MetaEvaluator(checks=[mock_check])

    result = await evaluator.evaluate_check("check_a", labeled_golden)

    assert result.tp == 1
    assert result.fp == 0
    assert result.fn == 0
    assert result.tn == 0
    assert result.precision == 1.0
    assert result.recall == 1.0


@pytest.mark.asyncio
async def test_evaluate_check_all_fail(labeled_golden: list[LabeledSample]) -> None:
    """Check always fails — sample expects fail → TN counted."""
    mock_check = _make_fail_check("check_b")
    evaluator = MetaEvaluator(checks=[mock_check])

    result = await evaluator.evaluate_check("check_b", labeled_golden)

    assert result.tn == 1
    assert result.tp == 0
    assert result.fp == 0
    assert result.fn == 0


@pytest.mark.asyncio
async def test_evaluate_check_mixed(labeled_mixed: list[LabeledSample]) -> None:
    """Mix of pass/fail — verify precision/recall/F1 math."""
    # check_a always passes: sample-1 pass→TP, sample-2 fail→FP,
    # sample-3 pass→TP, sample-4 fail→FP
    mock_check = _make_pass_check("check_a")
    evaluator = MetaEvaluator(checks=[mock_check])

    result = await evaluator.evaluate_check("check_a", labeled_mixed)

    assert result.tp == 2
    assert result.fp == 2
    assert result.fn == 0
    assert result.tn == 0
    assert result.precision == pytest.approx(0.5)
    assert result.recall == pytest.approx(1.0)
    # F1 = 2 * 0.5 * 1.0 / (0.5 + 1.0) = 2/3
    assert result.f1 == pytest.approx(2.0 / 3.0)


@pytest.mark.asyncio
async def test_skip_labels_excluded() -> None:
    """Samples with 'skip' label excluded from confusion matrix."""
    samples = [
        LabeledSample(
            name="skip-sample",
            html="<html>skip</html>",
            expected_qa={"check_a": "skip"},
        ),
        LabeledSample(
            name="pass-sample",
            html="<html>pass</html>",
            expected_qa={"check_a": "pass"},
        ),
    ]
    mock_check = _make_pass_check("check_a")
    evaluator = MetaEvaluator(checks=[mock_check])

    result = await evaluator.evaluate_check("check_a", samples)

    # Only 1 sample should be counted (the non-skip one)
    total = result.tp + result.fp + result.tn + result.fn
    assert total == 1
    assert result.tp == 1


@pytest.mark.asyncio
async def test_threshold_recommendation_high_fp() -> None:
    """FP > 10% triggers recommendation."""
    # 1 TP, 2 FP → FP rate = 2/(2+0) = 100%
    samples = [
        LabeledSample(name="s1", html="<html>1</html>", expected_qa={"check_a": "pass"}),
        LabeledSample(name="s2", html="<html>2</html>", expected_qa={"check_a": "fail"}),
        LabeledSample(name="s3", html="<html>3</html>", expected_qa={"check_a": "fail"}),
    ]
    mock_check = _make_pass_check("check_a")
    evaluator = MetaEvaluator(checks=[mock_check], fp_threshold=0.10)

    report = await evaluator.evaluate_all_checks(samples)

    assert len(report.recommendations) >= 1
    rec = next(r for r in report.recommendations if r.check_name == "check_a")
    assert "FP rate" in rec.reasoning


@pytest.mark.asyncio
async def test_threshold_recommendation_high_fn() -> None:
    """FN > 5% triggers recommendation."""
    # check always fails: 2 expected pass → 2 FN, 1 expected fail → 1 TN
    samples = [
        LabeledSample(name="s1", html="<html>1</html>", expected_qa={"check_a": "pass"}),
        LabeledSample(name="s2", html="<html>2</html>", expected_qa={"check_a": "pass"}),
        LabeledSample(name="s3", html="<html>3</html>", expected_qa={"check_a": "fail"}),
    ]
    mock_check = _make_fail_check("check_a")
    evaluator = MetaEvaluator(checks=[mock_check], fn_threshold=0.05)

    report = await evaluator.evaluate_all_checks(samples)

    assert len(report.recommendations) >= 1
    rec = next(r for r in report.recommendations if r.check_name == "check_a")
    assert "FN rate" in rec.reasoning


@pytest.mark.asyncio
async def test_evaluate_all_checks(
    labeled_golden: list[LabeledSample],
) -> None:
    """Full pipeline with multiple checks — verify MetaEvalReport shape."""
    checks = [_make_pass_check("check_a"), _make_fail_check("check_b")]
    evaluator = MetaEvaluator(checks=checks)

    report = await evaluator.evaluate_all_checks(labeled_golden)

    assert isinstance(report, MetaEvalReport)
    assert "check_a" in report.checks
    assert "check_b" in report.checks
    assert report.golden_count == 1
    assert report.adversarial_count == 0
    assert report.timestamp is not None


@pytest.mark.asyncio
async def test_overall_f1_weighted(
    labeled_golden: list[LabeledSample],
) -> None:
    """Overall F1 is macro-average across checks with samples."""
    checks = [_make_pass_check("check_a"), _make_fail_check("check_b")]
    evaluator = MetaEvaluator(checks=checks)

    report = await evaluator.evaluate_all_checks(labeled_golden)

    # check_a: TP=1 → F1=1.0; check_b: TN=1 → precision=0, recall=0, F1=0
    # Macro-average = (1.0 + 0.0) / 2 = 0.5
    assert report.overall_f1 == pytest.approx(0.5)


class TestMetaEvalRoutes:
    @pytest.mark.usefixtures("_auth_viewer")
    def test_meta_eval_route_admin_only(self, client: TestClient) -> None:
        """Non-admin gets 403."""
        resp = client.post(f"{BASE}/meta-eval")
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_admin")
    def test_meta_eval_latest_route(self, client: TestClient) -> None:
        """Returns stored report when available."""
        mock_report: dict[str, Any] = {
            "checks": {},
            "overall_f1": 0.85,
            "timestamp": "2026-04-06T00:00:00+00:00",
            "recommendations": [],
            "golden_count": 14,
            "adversarial_count": 0,
        }
        with patch(
            "app.qa_engine.meta_eval.load_latest_report",
            return_value=mock_report,
        ):
            resp = client.get(f"{BASE}/meta-eval/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_f1"] == 0.85
        assert body["golden_count"] == 14
