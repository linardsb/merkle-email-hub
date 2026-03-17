# pyright: reportUnknownMemberType=false
"""Tests for Audience-Aware Outlook Migration Planner (Phase 19.2)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.outlook_analyzer.detector import OutlookDependencyDetector
from app.qa_engine.outlook_analyzer.planner import DEFAULT_AUDIENCE, MigrationPlanner
from app.qa_engine.outlook_analyzer.types import (
    AudienceProfile,
)
from app.qa_engine.schemas import MigrationPlanResponse, OutlookAnalysisResponse
from app.qa_engine.service import QAEngineService

# --- Test HTML Fixtures ---

VML_BUTTON_HTML = """\
<html xmlns:v="urn:schemas-microsoft-com:vml">
<body>
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" style="height:40px;width:200px"
  arcsize="10%" strokecolor="#1e3650" fillcolor="#ff6600">
  <v:textbox><center style="color:#ffffff">Click Here</center></v:textbox>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="#" style="background-color:#ff6600;border-radius:4px;color:#ffffff;padding:10px 20px;">Click Here</a>
<!--<![endif]-->
</body>
</html>"""

MULTI_DEP_HTML = """\
<html xmlns:v="urn:schemas-microsoft-com:vml">
<head><style>
.content { mso-line-height-rule: exactly; }
.ExternalClass { width: 100%; }
td { word-wrap: break-all; }
</style></head>
<body>
<!--[if mso]>
<table role="presentation"><tr><td>
<![endif]-->
<v:roundrect style="height:40px;width:200px" fillcolor="#ff6600"></v:roundrect>
<img src="logo.png" width="300" height="100" style="width:150px;height:50px;">
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body>
</html>"""

CLEAN_HTML = """\
<html><head><style>
.content { font-size: 16px; color: #333; }
</style></head><body>
<div style="max-width:600px"><p>Modern email</p></div>
</body></html>"""


# ========================
# Planner Unit Tests
# ========================


class TestMigrationPlanner:
    def setup_method(self) -> None:
        self.detector = OutlookDependencyDetector()
        self.planner = MigrationPlanner()

    def test_plan_empty_analysis(self) -> None:
        analysis = self.detector.analyze(CLEAN_HTML)
        plan = self.planner.plan(analysis)
        assert plan.phases == []
        assert plan.total_dependencies == 0
        assert plan.recommendation == "aggressive"
        assert "No Outlook" in plan.risk_assessment

    def test_plan_low_word_engine_share(self) -> None:
        """< 2% Word engine → aggressive, all safe 'now'."""
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.01, "gmail_web": 0.90})
        plan = self.planner.plan(analysis, audience)
        assert plan.recommendation == "aggressive"
        for phase in plan.phases:
            assert phase.safe_when == "now"

    def test_plan_moderate_word_engine_share(self) -> None:
        """5-10% Word engine → moderate."""
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(
            client_distribution={"outlook_2016": 0.05, "outlook_2019": 0.03, "gmail_web": 0.70}
        )
        plan = self.planner.plan(analysis, audience)
        assert plan.recommendation == "moderate"
        # Low-risk should be "now", high-risk should wait
        for phase in plan.phases:
            if phase.risk_level == "low":
                assert phase.safe_when == "now"
            elif phase.risk_level == "high":
                assert "5%" in phase.safe_when

    def test_plan_high_word_engine_share(self) -> None:
        """40% Word engine → conservative."""
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(
            client_distribution={"outlook_2016": 0.20, "outlook_2019": 0.20, "gmail_web": 0.30}
        )
        plan = self.planner.plan(analysis, audience)
        assert plan.recommendation == "conservative"
        high_risk = [p for p in plan.phases if p.risk_level == "high"]
        for phase in high_risk:
            assert phase.safe_when == "after word_engine sunset"

    def test_plan_default_audience(self) -> None:
        """None audience → uses DEFAULT_AUDIENCE (industry averages)."""
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        plan = self.planner.plan(analysis, None)
        # DEFAULT_AUDIENCE has 19% word engine share (>= 10%) → conservative
        assert plan.recommendation == "conservative"
        assert plan.word_engine_audience == pytest.approx(DEFAULT_AUDIENCE.word_engine_share)

    def test_plan_phase_ordering(self) -> None:
        """Phases sorted low→medium→high risk."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        risk_order = {"low": 0, "medium": 1, "high": 2}
        risks = [risk_order[p.risk_level] for p in plan.phases]
        assert risks == sorted(risks)

    def test_audience_profile_word_engine_share(self) -> None:
        profile = AudienceProfile(
            client_distribution={
                "outlook_2016": 0.10,
                "outlook_2019": 0.05,
                "gmail_web": 0.50,
            }
        )
        assert profile.word_engine_share == pytest.approx(0.15)

    def test_audience_profile_new_outlook_share(self) -> None:
        profile = AudienceProfile(
            client_distribution={
                "new_outlook": 0.12,
                "outlook_web": 0.08,
                "gmail_web": 0.50,
            }
        )
        assert profile.new_outlook_share == pytest.approx(0.20)

    def test_plan_single_dependency_type(self) -> None:
        """One dependency type → one phase."""
        html = (
            "<html><head><style>.ExternalClass { width: 100%; }</style></head><body></body></html>"
        )
        analysis = self.detector.analyze(html)
        assert analysis.total_count > 0, "Expected ExternalClass to be detected"
        plan = self.planner.plan(analysis)
        ext_phases = [p for p in plan.phases if "external_class" in p.dependency_types]
        assert len(ext_phases) == 1

    def test_plan_all_dependency_types(self) -> None:
        """Multiple types → multiple phases, correctly ordered."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        assert len(plan.phases) >= 2
        all_types = {t for p in plan.phases for t in p.dependency_types}
        # Should have at least some of these types
        assert len(all_types) >= 2

    def test_plan_total_savings_sum(self) -> None:
        """total_savings_bytes == sum of phase estimated_byte_savings."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        assert plan.total_savings_bytes == sum(p.estimated_byte_savings for p in plan.phases)

    def test_plan_phase_names_human_readable(self) -> None:
        """Each dependency type maps to a human-readable phase name."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        for phase in plan.phases:
            # Should not be a raw type like "vml_shape"
            assert " " in phase.name  # Human-readable names have spaces

    def test_plan_phase_descriptions_include_count(self) -> None:
        """Phase description includes the dependency count."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        for phase in plan.phases:
            dep_count = len(phase.dependencies_to_remove)
            assert str(dep_count) in phase.description

    def test_safe_when_low_risk_below_10pct(self) -> None:
        """Low-risk deps with <10% word engine → safe_when='now'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.05, "gmail_web": 0.80})
        plan = self.planner.plan(analysis, audience)
        low_phases = [p for p in plan.phases if p.risk_level == "low"]
        for phase in low_phases:
            assert phase.safe_when == "now"

    def test_safe_when_low_risk_above_10pct(self) -> None:
        """Low-risk deps with >10% word engine → safe_when='when word_engine < 10%'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.15, "gmail_web": 0.60})
        plan = self.planner.plan(analysis, audience)
        low_phases = [p for p in plan.phases if p.risk_level == "low"]
        for phase in low_phases:
            assert phase.safe_when == "when word_engine < 10%"

    def test_safe_when_medium_risk_below_2pct(self) -> None:
        """Medium-risk deps with <2% word engine → safe_when='now'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.01, "gmail_web": 0.90})
        plan = self.planner.plan(analysis, audience)
        medium_phases = [p for p in plan.phases if p.risk_level == "medium"]
        for phase in medium_phases:
            assert phase.safe_when == "now"

    def test_safe_when_medium_risk_5_to_10pct(self) -> None:
        """Medium-risk deps with 5% word engine → safe_when='when word_engine < 5%'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.05, "gmail_web": 0.80})
        plan = self.planner.plan(analysis, audience)
        medium_phases = [p for p in plan.phases if p.risk_level == "medium"]
        for phase in medium_phases:
            assert phase.safe_when == "when word_engine < 5%"

    def test_safe_when_high_risk_above_25pct(self) -> None:
        """High-risk deps with 30% word engine → safe_when='after word_engine sunset'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.30, "gmail_web": 0.40})
        plan = self.planner.plan(analysis, audience)
        high_phases = [p for p in plan.phases if p.risk_level == "high"]
        for phase in high_phases:
            assert phase.safe_when == "after word_engine sunset"

    def test_safe_when_high_risk_10_to_25pct(self) -> None:
        """High-risk deps with 15% word engine → safe_when='when word_engine < 10%'."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.15, "gmail_web": 0.60})
        plan = self.planner.plan(analysis, audience)
        high_phases = [p for p in plan.phases if p.risk_level == "high"]
        for phase in high_phases:
            assert phase.safe_when == "when word_engine < 10%"

    def test_risk_assessment_text_aggressive(self) -> None:
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.005, "gmail_web": 0.90})
        plan = self.planner.plan(analysis, audience)
        assert "safely removed" in plan.risk_assessment
        assert "0.5%" in plan.risk_assessment

    def test_risk_assessment_text_moderate(self) -> None:
        """Moderate risk assessment mentions low-risk removal."""
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.05, "gmail_web": 0.80})
        plan = self.planner.plan(analysis, audience)
        assert "Low-risk" in plan.risk_assessment

    def test_risk_assessment_text_conservative(self) -> None:
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        audience = AudienceProfile(client_distribution={"outlook_2016": 0.30, "gmail_web": 0.40})
        plan = self.planner.plan(analysis, audience)
        assert "significant share" in plan.risk_assessment

    def test_plan_phase_count_matches_dep_types(self) -> None:
        """Each unique dependency type gets its own phase."""
        analysis = self.detector.analyze(MULTI_DEP_HTML)
        plan = self.planner.plan(analysis)
        dep_types_in_analysis = {d.type for d in analysis.dependencies}
        phase_types = {t for p in plan.phases for t in p.dependency_types}
        assert dep_types_in_analysis == phase_types


# ========================
# Route Tests
# ========================

BASE = "/api/v1/qa"


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    return user


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestMigrationPlanRoutes:
    def test_migration_plan_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/outlook-migration-plan", json={"html": "<html></html>"})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_migration_plan_disabled(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_migration_plan",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("Outlook dependency analyzer is not enabled"),
        ):
            resp = client.post(f"{BASE}/outlook-migration-plan", json={"html": "<html></html>"})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_migration_plan_success(self, client: TestClient) -> None:
        mock_response = MigrationPlanResponse(
            phases=[],
            total_dependencies=0,
            total_removable=0,
            total_savings_bytes=0,
            word_engine_audience=0.19,
            risk_assessment="No dependencies.",
            recommendation="aggressive",
            analysis=OutlookAnalysisResponse(),
        )
        with patch.object(
            QAEngineService,
            "run_migration_plan",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(f"{BASE}/outlook-migration-plan", json={"html": CLEAN_HTML})
        assert resp.status_code == 200
        body = resp.json()
        assert body["recommendation"] == "aggressive"
        assert "analysis" in body

    @pytest.mark.usefixtures("_auth_developer")
    def test_migration_plan_with_audience(self, client: TestClient) -> None:
        mock_response = MigrationPlanResponse(
            phases=[],
            total_dependencies=0,
            total_removable=0,
            total_savings_bytes=0,
            word_engine_audience=0.01,
            risk_assessment="Low share.",
            recommendation="aggressive",
            analysis=OutlookAnalysisResponse(),
        )
        with patch.object(
            QAEngineService,
            "run_migration_plan",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(
                f"{BASE}/outlook-migration-plan",
                json={
                    "html": CLEAN_HTML,
                    "audience": {
                        "client_distribution": {
                            "outlook_2016": 0.01,
                            "gmail_web": 0.90,
                        }
                    },
                },
            )
        assert resp.status_code == 200

    @pytest.mark.usefixtures("_auth_developer")
    def test_migration_plan_empty_html(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/outlook-migration-plan", json={"html": ""})
        assert resp.status_code == 422


# ========================
# Schema Validation Tests
# ========================


class TestMigrationPlanSchemas:
    def test_audience_schema_invalid_share(self) -> None:
        from pydantic import ValidationError

        from app.qa_engine.schemas import AudienceProfileSchema

        with pytest.raises(ValidationError):
            AudienceProfileSchema(client_distribution={"outlook_2016": 1.5})

    def test_audience_schema_negative_share(self) -> None:
        from pydantic import ValidationError

        from app.qa_engine.schemas import AudienceProfileSchema

        with pytest.raises(ValidationError):
            AudienceProfileSchema(client_distribution={"outlook_2016": -0.1})
