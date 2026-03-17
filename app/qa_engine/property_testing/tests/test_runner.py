# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for property test runner and API endpoint."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.exceptions import DomainValidationError
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.property_testing.runner import PropertyTestRunner
from app.qa_engine.schemas import PropertyTestResponse
from app.qa_engine.service import QAEngineService

BASE = "/api/v1/qa"


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


# ── Runner Tests ──


class TestPropertyTestRunner:
    async def test_run_all_invariants(self):
        runner = PropertyTestRunner()
        report = await runner.run(num_cases=10, seed=42)
        assert report.total_cases == 10
        assert report.passed + report.failed == report.total_cases
        assert report.seed == 42

    async def test_seed_reproducibility(self):
        runner = PropertyTestRunner()
        report1 = await runner.run(num_cases=10, seed=12345)
        report2 = await runner.run(num_cases=10, seed=12345)
        assert report1.total_cases == report2.total_cases
        assert report1.passed == report2.passed
        assert report1.failed == report2.failed
        assert len(report1.failures) == len(report2.failures)

    async def test_specific_invariants(self):
        runner = PropertyTestRunner()
        report = await runner.run(
            invariant_names=["size_limit", "encoding_valid"],
            num_cases=5,
            seed=99,
        )
        assert report.total_cases == 5
        for f in report.failures:
            assert f.invariant_name in ("size_limit", "encoding_valid")

    async def test_detects_invariant_violations(self):
        """With enough cases, some violations should be found."""
        runner = PropertyTestRunner()
        report = await runner.run(num_cases=50, seed=42)
        assert report.failed > 0, "Expected some invariant violations with 50 cases"

    async def test_unknown_invariant_raises_error(self):
        runner = PropertyTestRunner()
        with pytest.raises(DomainValidationError, match="Unknown invariants"):
            await runner.run(invariant_names=["nonexistent"], num_cases=5, seed=1)

    async def test_random_seed_when_none(self):
        runner = PropertyTestRunner()
        report = await runner.run(num_cases=5, seed=None)
        assert report.seed > 0
        assert report.total_cases == 5


# ── Route Tests ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestPropertyTestRoute:
    def test_property_test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/property-test", json={"num_cases": 5})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_disabled_returns_403(self, client: TestClient) -> None:
        with patch("app.qa_engine.service.get_settings") as mock_settings:
            mock_settings.return_value.qa_property_testing.enabled = False
            resp = client.post(f"{BASE}/property-test", json={"num_cases": 5})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_success(self, client: TestClient) -> None:
        mock_response = PropertyTestResponse(
            total_cases=10,
            passed=8,
            failed=2,
            failures=[],
            seed=42,
            invariants_tested=["size_limit", "encoding_valid"],
        )
        with patch.object(
            QAEngineService,
            "run_property_test",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(f"{BASE}/property-test", json={"num_cases": 10, "seed": 42})

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_cases"] == 10
        assert body["passed"] == 8
        assert body["seed"] == 42

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_with_specific_invariants(self, client: TestClient) -> None:
        mock_response = PropertyTestResponse(
            total_cases=5,
            passed=5,
            failed=0,
            failures=[],
            seed=99,
            invariants_tested=["size_limit"],
        )
        with patch.object(
            QAEngineService,
            "run_property_test",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(
                f"{BASE}/property-test",
                json={"invariants": ["size_limit"], "num_cases": 5, "seed": 99},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["invariants_tested"] == ["size_limit"]

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_validates_num_cases(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/property-test", json={"num_cases": 0})
        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_max_cases_limit(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/property-test", json={"num_cases": 1001})
        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_property_test_unknown_invariant_returns_422(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_property_test",
            new_callable=AsyncMock,
            side_effect=DomainValidationError("Unknown invariants: bogus"),
        ):
            resp = client.post(
                f"{BASE}/property-test",
                json={"invariants": ["bogus"], "num_cases": 5},
            )
        assert resp.status_code == 422
