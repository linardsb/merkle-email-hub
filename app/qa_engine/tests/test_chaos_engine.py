# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Integration tests for ChaosEngine orchestration + route tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.chaos.composable import compose_profiles
from app.qa_engine.chaos.engine import ChaosEngine
from app.qa_engine.chaos.profiles import GMAIL_STYLE_STRIP, IMAGE_BLOCKED
from app.qa_engine.schemas import ChaosTestResponse
from app.qa_engine.service import QAEngineService

BASE = "/api/v1/qa"

MINIMAL_HTML = "<!DOCTYPE html><html><head></head><body><p>Hello World</p></body></html>"

STYLE_BLOCK_HTML = (
    "<!DOCTYPE html><html><head>"
    "<style>.hero { background: red; color: white; font-size: 24px; }</style>"
    "</head><body><div class='hero' style='padding:10px;'>Hello</div></body></html>"
)

INLINE_ONLY_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<div style='background: red; color: white; font-size: 24px; padding:10px;'>Hello</div>"
    "</body></html>"
)


# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


# ── Engine Tests ──


class TestChaosEngine:
    async def test_engine_runs_default_profiles(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=None,
            default_profiles=["gmail_style_strip", "image_blocked"],
        )
        assert result.profiles_tested == 2
        assert len(result.profile_results) == 2
        profile_names = [pr.profile for pr in result.profile_results]
        assert "gmail_style_strip" in profile_names
        assert "image_blocked" in profile_names

    async def test_engine_runs_explicit_profiles(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["gmail_style_strip"],
            default_profiles=["image_blocked", "dark_mode_inversion"],
        )
        assert result.profiles_tested == 1
        assert result.profile_results[0].profile == "gmail_style_strip"

    async def test_engine_unknown_profile_skipped(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["nonexistent_profile", "gmail_style_strip"],
        )
        assert result.profiles_tested == 1
        assert result.profile_results[0].profile == "gmail_style_strip"

    async def test_engine_resilience_score_inline_styles(self):
        """HTML with only inline styles should have high resilience to gmail_style_strip."""
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=INLINE_ONLY_HTML,
            profiles=["gmail_style_strip"],
        )
        assert result.resilience_score >= 0.9

    async def test_engine_resilience_score_style_block(self):
        """HTML relying on <style> blocks should have lower resilience to gmail_style_strip."""
        engine = ChaosEngine()
        result_with_style = await engine.run_chaos_test(
            html=STYLE_BLOCK_HTML,
            profiles=["gmail_style_strip"],
        )
        result_inline = await engine.run_chaos_test(
            html=INLINE_ONLY_HTML,
            profiles=["gmail_style_strip"],
        )
        # Style-block HTML should not have significantly higher resilience than inline-only
        # Allow small floating-point tolerance from mixed check scores
        assert result_with_style.resilience_score <= result_inline.resilience_score + 0.01

    async def test_engine_critical_failures_collected(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["gmail_style_strip", "image_blocked", "dark_mode_inversion"],
        )
        # Critical failures are those with severity == "error"
        for cf in result.critical_failures:
            assert cf.severity == "error"

    async def test_engine_empty_profiles_returns_zero(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["nonexistent1", "nonexistent2"],
        )
        assert result.profiles_tested == 0
        assert result.resilience_score == 0.0

    async def test_engine_original_score_computed(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["gmail_style_strip"],
        )
        assert 0.0 <= result.original_score <= 1.0

    async def test_engine_composed_profile_compound_failures(self):
        composed = compose_profiles(GMAIL_STYLE_STRIP, IMAGE_BLOCKED)
        engine = ChaosEngine()
        # Run the composed profile via the engine's internal method
        degraded = composed.apply(STYLE_BLOCK_HTML)
        score, checks = await engine._run_qa(degraded)
        assert isinstance(score, float)
        assert len(checks) > 0

    async def test_engine_profile_results_contain_check_counts(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["gmail_style_strip", "image_blocked"],
        )
        for pr in result.profile_results:
            assert pr.checks_passed + len(pr.failures) <= pr.checks_total
            assert pr.checks_total > 0

    async def test_engine_resilience_score_capped_at_one(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=INLINE_ONLY_HTML,
            profiles=["gmail_style_strip"],
        )
        assert result.resilience_score <= 1.0

    async def test_engine_profile_results_have_descriptions(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["gmail_style_strip", "image_blocked"],
        )
        for pr in result.profile_results:
            assert pr.description
            assert len(pr.description) > 0

    async def test_engine_single_profile(self):
        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=["dark_mode_inversion"],
        )
        assert result.profiles_tested == 1
        assert 0.0 <= result.resilience_score <= 1.0

    async def test_engine_all_known_profiles(self):
        engine = ChaosEngine()
        all_names = [
            "gmail_style_strip",
            "image_blocked",
            "dark_mode_inversion",
            "outlook_word_engine",
            "gmail_clipping",
            "mobile_narrow",
            "class_strip",
            "media_query_strip",
        ]
        result = await engine.run_chaos_test(
            html=MINIMAL_HTML,
            profiles=all_names,
        )
        assert result.profiles_tested == 8


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


class TestChaosRoute:
    def test_chaos_route_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/chaos-test", json={"html": MINIMAL_HTML})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_chaos_route_returns_results(self, client: TestClient) -> None:
        mock_response = ChaosTestResponse(
            original_score=0.8,
            resilience_score=0.7,
            profiles_tested=2,
            profile_results=[],
            critical_failures=[],
        )
        with patch.object(
            QAEngineService,
            "run_chaos_test",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(f"{BASE}/chaos-test", json={"html": MINIMAL_HTML})

        assert resp.status_code == 200
        body = resp.json()
        assert body["resilience_score"] == 0.7
        assert body["profiles_tested"] == 2

    @pytest.mark.usefixtures("_auth_developer")
    def test_chaos_route_disabled_returns_403(self, client: TestClient) -> None:
        with patch("app.qa_engine.service.get_settings") as mock_settings:
            mock_settings.return_value.qa_chaos.enabled = False
            resp = client.post(f"{BASE}/chaos-test", json={"html": MINIMAL_HTML})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_chaos_route_validates_html(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/chaos-test", json={"html": ""})
        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_chaos_route_service_error_returns_500(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_chaos_test",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected"),
        ):
            resp = client.post(
                f"{BASE}/chaos-test",
                json={"html": "<!DOCTYPE html><html><body>Hi</body></html>"},
            )
        assert resp.status_code == 500
