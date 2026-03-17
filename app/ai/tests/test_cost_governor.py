"""Tests for cost governor (Phase 22.5)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ai.cost_governor import (
    _DEFAULT_PRICING,
    BudgetStatus,
    CostGovernor,
    CostReport,
    _get_pricing,
    reset_cost_governor,
)
from app.ai.exceptions import BudgetExceededError
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app

# ── Helpers ──


def _make_user(role: str = "admin") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


# ── Pricing resolution tests ──


class TestPricingResolution:
    """Model pricing lookup tests."""

    def test_exact_match(self) -> None:
        pricing = _get_pricing("gpt-4o")
        assert pricing.input_per_million == 1.97
        assert pricing.output_per_million == 7.90

    def test_prefix_match(self) -> None:
        pricing = _get_pricing("gpt-4o-2024-08-06")
        assert pricing.input_per_million == 1.97

    def test_anthropic_exact(self) -> None:
        pricing = _get_pricing("claude-sonnet-4-20250514")
        assert pricing.input_per_million == 2.37

    def test_unknown_model_returns_default(self) -> None:
        pricing = _get_pricing("totally-unknown-model-xyz")
        assert pricing == _DEFAULT_PRICING

    def test_prefix_match_longest_wins(self) -> None:
        """gpt-4.1-mini should match gpt-4.1-mini, not gpt-4.1."""
        pricing = _get_pricing("gpt-4.1-mini-2025-01-01")
        assert pricing.input_per_million == 0.32  # gpt-4.1-mini pricing


# ── Cost calculation tests ──


class TestCostCalculation:
    """Pence calculation tests."""

    def test_basic_cost(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        pence = gov._cost_pence("gpt-4o", input_tokens=1_000_000, output_tokens=0)
        # 1M input * 1.97 £/M * 100 pence/£ = 197 pence
        assert pence == 197

    def test_output_tokens(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        pence = gov._cost_pence("gpt-4o", input_tokens=0, output_tokens=1_000_000)
        # 1M output * 7.90 £/M * 100 pence/£ = 790 pence
        assert pence == 790

    def test_minimum_1_pence(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        pence = gov._cost_pence("gpt-4o-mini", input_tokens=1, output_tokens=1)
        assert pence == 1  # Minimum granularity

    def test_combined_cost(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        pence = gov._cost_pence("gpt-4o", input_tokens=500_000, output_tokens=500_000)
        # 0.5M * 1.97 * 100 + 0.5M * 7.90 * 100 = 98.5 + 395 = 493
        assert pence == 493


# ── Budget check tests ──


class TestBudgetCheck:
    """Budget status threshold tests."""

    @pytest.mark.asyncio
    async def test_ok_status(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        # No spending — should be OK
        status = await gov.check_budget()
        assert status == BudgetStatus.OK

    @pytest.mark.asyncio
    async def test_unlimited_budget(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=0.0)
        status = await gov.check_budget()
        assert status == BudgetStatus.OK

    @pytest.mark.asyncio
    async def test_warning_threshold(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=10.0, warning_threshold=0.8)
        # Simulate spending 850 pence (85% of 1000 pence budget)
        gov._fallback_totals["cost:monthly:2026-03"] = 850
        with patch("app.ai.cost_governor._current_month_key", return_value="2026-03"):
            status = await gov.check_budget()
        assert status == BudgetStatus.WARNING

    @pytest.mark.asyncio
    async def test_exceeded_threshold(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=10.0)
        # Simulate spending 1100 pence (over 1000 pence budget)
        gov._fallback_totals["cost:monthly:2026-03"] = 1100
        with patch("app.ai.cost_governor._current_month_key", return_value="2026-03"):
            status = await gov.check_budget()
        assert status == BudgetStatus.EXCEEDED


# ── Record tests ──


class TestRecord:
    """Cost recording tests."""

    @pytest.mark.asyncio
    async def test_record_returns_cost_record(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        record = await gov.record(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            agent="scaffolder",
            project_id="proj-123",
        )
        assert record.model == "gpt-4o"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost_gbp > 0
        assert record.monthly_total_pence > 0

    @pytest.mark.asyncio
    async def test_record_increments_total(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        r1 = await gov.record(model="gpt-4o", input_tokens=1000, output_tokens=500)
        r2 = await gov.record(model="gpt-4o", input_tokens=1000, output_tokens=500)
        assert r2.monthly_total_pence > r1.monthly_total_pence

    @pytest.mark.asyncio
    async def test_record_tracks_dimensions(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        await gov.record(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            agent="scaffolder",
            project_id="proj-1",
        )
        # Check that dimension keys were set in fallback totals
        month_keys = [k for k in gov._fallback_totals if "model:gpt-4o" in k]
        agent_keys = [k for k in gov._fallback_totals if "agent:scaffolder" in k]
        project_keys = [k for k in gov._fallback_totals if "project:proj-1" in k]
        assert len(month_keys) == 1
        assert len(agent_keys) == 1
        assert len(project_keys) == 1

    @pytest.mark.asyncio
    async def test_record_skips_empty_dimensions(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        await gov.record(model="gpt-4o", input_tokens=1000, output_tokens=500)
        agent_keys = [k for k in gov._fallback_totals if ":agent:" in k]
        project_keys = [k for k in gov._fallback_totals if ":project:" in k]
        assert len(agent_keys) == 0
        assert len(project_keys) == 0


# ── Report tests ──


class TestReport:
    """Cost report generation tests."""

    @pytest.mark.asyncio
    async def test_report_empty(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        report = await gov.get_report()
        assert report.total_gbp == 0.0
        assert report.status == BudgetStatus.OK
        assert report.by_model == {}

    @pytest.mark.asyncio
    async def test_report_with_data(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=100.0)
        await gov.record(
            model="gpt-4o", input_tokens=1_000_000, output_tokens=0, agent="scaffolder"
        )
        report = await gov.get_report()
        assert report.total_gbp > 0
        assert "gpt-4o" in report.by_model
        assert "scaffolder" in report.by_agent

    @pytest.mark.asyncio
    async def test_report_status_reflects_budget(self) -> None:
        gov = CostGovernor(monthly_budget_gbp=0.01)  # 1 pence budget
        await gov.record(model="gpt-4o", input_tokens=1000, output_tokens=500)
        report = await gov.get_report()
        assert report.status == BudgetStatus.EXCEEDED


# ── BudgetExceededError tests ──


class TestBudgetExceededError:
    """Exception hierarchy tests."""

    def test_is_ai_error(self) -> None:
        from app.ai.exceptions import AIError

        exc = BudgetExceededError("test")
        assert isinstance(exc, AIError)

    def test_message(self) -> None:
        exc = BudgetExceededError("Monthly AI budget exceeded")
        assert str(exc) == "Monthly AI budget exceeded"


# ── Adapter integration tests ──


class TestAdapterIntegration:
    """Tests for cost governor integration in adapters."""

    @pytest.mark.asyncio
    async def test_check_cost_budget_raises_on_exceeded(self) -> None:
        """Adapter _check_cost_budget raises BudgetExceededError when exceeded."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        with (
            patch("app.ai.adapters.openai_compat.get_settings") as mock_settings,
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov,
        ):
            settings = mock_settings.return_value
            settings.ai.cost_governor_enabled = True
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False

            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.EXCEEDED
            mock_gov.return_value = gov

            provider = OpenAICompatProvider()
            with pytest.raises(BudgetExceededError):
                await provider._check_cost_budget()

    @pytest.mark.asyncio
    async def test_check_cost_budget_skips_when_disabled(self) -> None:
        """_check_cost_budget does nothing when cost governor is disabled."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.cost_governor_enabled = False
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False

            provider = OpenAICompatProvider()
            await provider._check_cost_budget()  # Should not raise

    @pytest.mark.asyncio
    async def test_report_cost_is_fire_and_forget(self) -> None:
        """_report_cost swallows exceptions."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        with (
            patch("app.ai.adapters.openai_compat.get_settings") as mock_settings,
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov,
        ):
            settings = mock_settings.return_value
            settings.ai.cost_governor_enabled = True
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False

            gov = AsyncMock()
            gov.record.side_effect = RuntimeError("Redis down")
            mock_gov.return_value = gov

            provider = OpenAICompatProvider()
            # Should NOT raise
            await provider._report_cost(
                "gpt-4o", {"prompt_tokens": 100, "completion_tokens": 50}, {}
            )


# ── Route tests ──


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Test client with rate limiting disabled."""
    limiter.enabled = False
    reset_cost_governor()
    yield TestClient(app)
    limiter.enabled = True
    app.dependency_overrides.clear()
    reset_cost_governor()


class TestRoutes:
    """Route tests for cost governor endpoints."""

    def test_report_requires_admin(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
        resp = client.get("/api/v1/ai/cost/report")
        assert resp.status_code == 403

    def test_report_admin_disabled(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        with patch("app.ai.cost_governor_routes.get_settings") as mock_settings:
            mock_settings.return_value.ai.cost_governor_enabled = False
            resp = client.get("/api/v1/ai/cost/report")
        assert resp.status_code == 403

    def test_report_admin_success(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        report = CostReport(
            month="2026-03",
            total_gbp=42.50,
            budget_gbp=600.0,
            utilization_pct=7.1,
            status=BudgetStatus.OK,
            by_model={"gpt-4o": 30.0},
            by_agent={"scaffolder": 12.50},
            by_project={},
        )
        with (
            patch("app.ai.cost_governor_routes.get_settings") as mock_settings,
            patch("app.ai.cost_governor_routes.get_cost_governor") as mock_gov,
        ):
            mock_settings.return_value.ai.cost_governor_enabled = True
            gov = AsyncMock()
            gov.get_report.return_value = report
            mock_gov.return_value = gov
            resp = client.get("/api/v1/ai/cost/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == "2026-03"
        assert data["total_gbp"] == 42.50
        assert data["status"] == "ok"
        assert len(data["by_model"]) == 1

    def test_report_with_month_param(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        report = CostReport(
            month="2026-02",
            total_gbp=0.0,
            budget_gbp=600.0,
            utilization_pct=0.0,
            status=BudgetStatus.OK,
            by_model={},
            by_agent={},
            by_project={},
        )
        with (
            patch("app.ai.cost_governor_routes.get_settings") as mock_settings,
            patch("app.ai.cost_governor_routes.get_cost_governor") as mock_gov,
        ):
            mock_settings.return_value.ai.cost_governor_enabled = True
            gov = AsyncMock()
            gov.get_report.return_value = report
            mock_gov.return_value = gov
            resp = client.get("/api/v1/ai/cost/report?month=2026-02")
        assert resp.status_code == 200
        assert resp.json()["month"] == "2026-02"

    def test_report_invalid_month_param(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        with patch("app.ai.cost_governor_routes.get_settings") as mock_settings:
            mock_settings.return_value.ai.cost_governor_enabled = True
            resp = client.get("/api/v1/ai/cost/report?month=invalid")
        assert resp.status_code == 422

    def test_status_admin_ok(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        with (
            patch("app.ai.cost_governor_routes.get_settings") as mock_settings,
            patch("app.ai.cost_governor_routes.get_cost_governor") as mock_gov,
        ):
            mock_settings.return_value.ai.cost_governor_enabled = True
            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.OK
            mock_gov.return_value = gov
            resp = client.get("/api/v1/ai/cost/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_status_developer_ok(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
        with (
            patch("app.ai.cost_governor_routes.get_settings") as mock_settings,
            patch("app.ai.cost_governor_routes.get_cost_governor") as mock_gov,
        ):
            mock_settings.return_value.ai.cost_governor_enabled = True
            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.WARNING
            mock_gov.return_value = gov
            resp = client.get("/api/v1/ai/cost/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "warning"

    def test_status_viewer_forbidden(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("viewer")
        resp = client.get("/api/v1/ai/cost/status")
        assert resp.status_code == 403

    def test_status_disabled(self, client: TestClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_user("admin")
        with patch("app.ai.cost_governor_routes.get_settings") as mock_settings:
            mock_settings.return_value.ai.cost_governor_enabled = False
            resp = client.get("/api/v1/ai/cost/status")
        assert resp.status_code == 403
