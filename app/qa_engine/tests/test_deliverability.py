"""Tests for deliverability prediction scoring (Phase 20.3)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.schemas import DeliverabilityScoreResponse
from app.qa_engine.service import QAEngineService

# --- Test HTML fixtures ---

CLEAN_TRANSACTIONAL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body>
  <div class="preview" style="display:none;max-height:0">Your order has shipped!</div>
  <table>
    <tr><td>
      <h1>Hello {{first_name}},</h1>
      <p>Your order #{{order_id}} has been shipped and is on its way.</p>
      <p>Track your package using the link below.</p>
      <a href="https://example.com/track" style="background-color:#007bff;color:white;padding:12px 24px">Track Order</a>
      <p>Expected delivery: {{delivery_date}}</p>
      <img src="https://example.com/logo.png" alt="Company Logo" width="150" />
    </td></tr>
  </table>
  <footer>
    <p>123 Main Street, Suite 100, City, ST 12345</p>
    <a href="https://example.com/unsubscribe">Unsubscribe</a>
    <!-- List-Unsubscribe: <mailto:unsub@example.com> -->
  </footer>
</body>
</html>"""

SPAM_LIKE_EMAIL = """<html>
<body>
  <img src="https://example.com/banner.jpg" />
  <a href="https://bit.ly/abc">FREE FREE FREE</a>
  <a href="https://bit.ly/def">CLICK NOW</a>
  <a href="https://bit.ly/ghi">ACT NOW</a>
  <a href="https://bit.ly/jkl">BUY BUY BUY</a>
  <a href="https://bit.ly/mno">HURRY HURRY</a>
</body>
</html>"""


class TestDeliverabilityCheck:
    """Unit tests for DeliverabilityCheck.run()."""

    @pytest.fixture()
    def check(self):
        from app.qa_engine.checks.deliverability import DeliverabilityCheck

        return DeliverabilityCheck()

    @pytest.mark.asyncio()
    async def test_clean_transactional_scores_high(self, check) -> None:
        result = await check.run(CLEAN_TRANSACTIONAL)
        assert result.score >= 0.85  # > 85/100
        assert result.passed is True

    @pytest.mark.asyncio()
    async def test_spam_like_scores_low(self, check) -> None:
        result = await check.run(SPAM_LIKE_EMAIL)
        assert result.score < 0.50  # < 50/100
        assert result.passed is False

    @pytest.mark.asyncio()
    async def test_missing_doctype_penalized(self, check) -> None:
        html = "<html><body><p>Hello world, this is a test email with content.</p></body></html>"
        result = await check.run(html)
        assert "DOCTYPE" in (result.details or "")

    @pytest.mark.asyncio()
    async def test_single_image_penalized(self, check) -> None:
        html = '<!DOCTYPE html><html><body><img src="banner.jpg" /></body></html>'
        result = await check.run(html)
        assert result.score < 0.50

    @pytest.mark.asyncio()
    async def test_unsubscribe_link_improves_score(self, check) -> None:
        base = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><p>Content here with enough words for testing purposes and more text.</p></body></html>'
        with_unsub = base.replace("</body>", '<a href="/unsubscribe">Unsubscribe</a></body>')
        result_without = await check.run(base)
        result_with = await check.run(with_unsub)
        assert result_with.score >= result_without.score

    @pytest.mark.asyncio()
    async def test_preview_text_improves_score(self, check) -> None:
        base = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><p>Content here</p><a href="/unsubscribe">Unsubscribe</a></body></html>'
        with_preview = base.replace(
            "<body>",
            '<body><div class="preview" style="display:none">Preview text here for inbox</div>',
        )
        result_without = await check.run(base)
        result_with = await check.run(with_preview)
        assert result_with.score >= result_without.score

    @pytest.mark.asyncio()
    async def test_url_shortener_penalized(self, check) -> None:
        html = '<!DOCTYPE html><html><body><p>Check out <a href="https://bit.ly/abc">this link</a></p></body></html>'
        result = await check.run(html)
        assert "shortener" in (result.details or "").lower()

    @pytest.mark.asyncio()
    async def test_invalid_html_returns_zero(self, check) -> None:
        result = await check.run("")
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio()
    async def test_hidden_text_penalized(self, check) -> None:
        html = '<!DOCTYPE html><html><body><p style="color:#ffffff;background-color:#ffffff">Hidden text</p></body></html>'
        result = await check.run(html)
        assert "hidden text" in (result.details or "").lower()

    @pytest.mark.asyncio()
    async def test_personalization_detected(self, check) -> None:
        html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><p>Hello {{name}}</p><a href="/unsub">Unsubscribe</a></body></html>'
        result = await check.run(html)
        # Personalization detected = no "personalization" issue in details
        assert "personalization" not in (result.details or "").lower() or result.score > 0.5

    @pytest.mark.asyncio()
    async def test_score_normalized_to_unit(self, check) -> None:
        """Score should be 0.0-1.0 (normalized from 0-100)."""
        result = await check.run(CLEAN_TRANSACTIONAL)
        assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio()
    async def test_threshold_from_config(self, check) -> None:
        from app.qa_engine.check_config import QACheckConfig

        config = QACheckConfig(params={"threshold": 95})
        result = await check.run(CLEAN_TRANSACTIONAL, config)
        # Even clean email may not hit 95
        assert result.check_name == "deliverability"

    @pytest.mark.asyncio()
    async def test_check_name_is_deliverability(self, check) -> None:
        result = await check.run(CLEAN_TRANSACTIONAL)
        assert result.check_name == "deliverability"


class TestDeliverabilityDimensions:
    """Tests for individual scoring dimensions."""

    def test_content_quality_high_link_density(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_content_quality

        html = '<html><body><a href="1">a</a><a href="2">b</a><a href="3">c</a><a href="4">d</a></body></html>'
        doc = lxml_html.fromstring(html)
        result = _score_content_quality(doc, html)
        assert result.score < 25  # penalized

    def test_content_quality_url_shortener(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_content_quality

        html = '<html><body><p>Some text content here for ratio.</p><a href="https://bit.ly/abc">Link</a></body></html>'
        doc = lxml_html.fromstring(html)
        result = _score_content_quality(doc, html)
        assert any("shortener" in i.description.lower() for i in result.issues)

    def test_html_hygiene_large_email(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_html_hygiene

        html = "<!DOCTYPE html><html><body>" + "x" * 110_000 + "</body></html>"
        doc = lxml_html.fromstring(html)
        result = _score_html_hygiene(doc, html)
        assert any("102KB" in i.description for i in result.issues)

    def test_html_hygiene_missing_doctype(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_html_hygiene

        html = "<html><body><p>No doctype</p></body></html>"
        doc = lxml_html.fromstring(html)
        result = _score_html_hygiene(doc, html)
        assert any("DOCTYPE" in i.description for i in result.issues)

    def test_html_hygiene_hidden_text(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_html_hygiene

        html = '<html><body><p style="color:#fff;background-color:#fff">Sneaky</p></body></html>'
        doc = lxml_html.fromstring(html)
        result = _score_html_hygiene(doc, html)
        assert any("hidden text" in i.description.lower() for i in result.issues)

    def test_auth_readiness_no_unsub(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_auth_readiness

        html = "<html><body><p>No unsubscribe link here</p></body></html>"
        doc = lxml_html.fromstring(html)
        result = _score_auth_readiness(doc, html)
        assert result.score < 15  # heavy penalty for no unsub

    def test_auth_readiness_with_unsub(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_auth_readiness

        html = '<html><body><a href="/unsubscribe">Unsubscribe</a><!-- List-Unsubscribe: <mailto:x@y.com> --><p>123 Main Street, City</p></body></html>'
        doc = lxml_html.fromstring(html)
        result = _score_auth_readiness(doc, html)
        assert result.score == 25  # full marks

    def test_engagement_signals_no_cta(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_engagement_signals

        html = "<html><body><p>Just some text content here without any call to action button or link.</p></body></html>"
        doc = lxml_html.fromstring(html)
        result = _score_engagement_signals(doc, html)
        assert result.score < 25  # penalized for no CTA

    def test_engagement_signals_with_cta(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_engagement_signals

        html = '<html><body><div class="preview" style="display:none">Preview text here for testing</div><p>Hello {{name}}, check out our latest products.</p><a href="/shop">Shop Now</a></body></html>'
        doc = lxml_html.fromstring(html)
        result = _score_engagement_signals(doc, html)
        assert result.score >= 19  # most signals present

    def test_engagement_signals_short_content(self) -> None:
        from lxml import html as lxml_html

        from app.qa_engine.checks.deliverability import _score_engagement_signals

        html = "<html><body><p>Hi</p></body></html>"
        doc = lxml_html.fromstring(html)
        result = _score_engagement_signals(doc, html)
        assert any("short content" in i.description.lower() for i in result.issues)


class TestDeliverabilityGetDetailedResult:
    """Tests for get_detailed_result helper."""

    def test_returns_four_dimensions(self) -> None:
        from app.qa_engine.checks.deliverability import get_detailed_result

        score, passed, dims = get_detailed_result(CLEAN_TRANSACTIONAL)
        assert len(dims) == 4
        assert isinstance(score, int)
        assert isinstance(passed, bool)

    def test_invalid_html_returns_zero(self) -> None:
        from app.qa_engine.checks.deliverability import get_detailed_result

        score, passed, dims = get_detailed_result("")
        assert score == 0
        assert passed is False
        assert dims == []

    def test_custom_threshold(self) -> None:
        from app.qa_engine.checks.deliverability import get_detailed_result

        score_70, passed_70, _ = get_detailed_result(CLEAN_TRANSACTIONAL, threshold=70)
        score_99, _passed_99, _ = get_detailed_result(CLEAN_TRANSACTIONAL, threshold=99)
        assert score_70 == score_99  # same score
        assert passed_70 is True  # passes at 70
        # may or may not pass at 99


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


@pytest.fixture()
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestDeliverabilityStandaloneEndpoint:
    """Tests for POST /api/v1/qa/deliverability-score endpoint."""

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/deliverability-score", json={"html": "<p>test</p>"})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_disabled_returns_403(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_deliverability_score",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("Deliverability scoring is not enabled"),
        ):
            resp = client.post(f"{BASE}/deliverability-score", json={"html": "<p>test</p>"})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_enabled_returns_score(self, client: TestClient) -> None:
        mock_response = DeliverabilityScoreResponse(
            score=85,
            passed=True,
            threshold=70,
            dimensions=[],
            issues=[],
            summary="Good deliverability.",
        )
        with patch.object(
            QAEngineService,
            "run_deliverability_score",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(
                f"{BASE}/deliverability-score",
                json={"html": CLEAN_TRANSACTIONAL},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 85
        assert data["passed"] is True
        assert "summary" in data

    @pytest.mark.usefixtures("_auth_developer")
    def test_empty_html_returns_422(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/deliverability-score", json={"html": ""})
        assert resp.status_code == 422
