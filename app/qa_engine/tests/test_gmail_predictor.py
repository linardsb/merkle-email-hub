# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportArgumentType=false
"""Tests for Gmail AI summary predictor (Phase 20.1)."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.gmail_intelligence.html_extractor import extract_signals
from app.qa_engine.gmail_intelligence.optimizer import PreviewTextOptimizer
from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor, _guess_category
from app.qa_engine.gmail_intelligence.types import EmailSignals
from app.qa_engine.schemas import GmailOptimizeResponse, GmailPredictResponse
from app.qa_engine.service import QAEngineService

# --- HTML signal extractor tests (deterministic) ---


class TestExtractSignals:
    def test_promotional_html(self) -> None:
        """HTML with prices, CTAs, unsubscribe → correct signal counts."""
        html = """
        <html><body>
        <a href="/unsubscribe">Unsubscribe</a>
        <p>Shop now and save $29.99! Only 5 left — hurry!</p>
        <a href="/buy">Buy now</a>
        <a href="/shop">Shop now</a>
        <img src="banner.jpg" />
        <img src="product.jpg" />
        </body></html>
        """
        signals = extract_signals(html)
        assert signals.has_unsubscribe is True
        assert signals.has_schema_org is False
        assert signals.price_mentions >= 1
        assert signals.urgency_words >= 1
        assert signals.cta_count >= 2
        assert signals.link_count == 3
        assert signals.image_count == 2

    def test_transactional_html(self) -> None:
        """Schema.org, order details → has_schema_org=True."""
        html = """
        <html><body>
        <div itemtype="https://schema.org/Order">
        <p>Your order #12345 has shipped.</p>
        </div>
        </body></html>
        """
        signals = extract_signals(html)
        assert signals.has_schema_org is True
        assert signals.has_unsubscribe is False

    def test_empty_html(self) -> None:
        """Minimal HTML → zeroed signals."""
        signals = extract_signals("<html><body></body></html>")
        assert signals.cta_count == 0
        assert signals.price_mentions == 0
        assert signals.urgency_words == 0
        assert signals.link_count == 0
        assert signals.image_count == 0
        assert signals.has_unsubscribe is False
        assert signals.has_schema_org is False

    def test_preview_text_extraction(self) -> None:
        """Preview class element → extracted preview text."""
        html = """
        <html><body>
        <div class="preview-text">Check out our spring collection</div>
        <p>Main content here</p>
        </body></html>
        """
        signals = extract_signals(html)
        assert "spring collection" in signals.preview_text


# --- Predictor parse tests (deterministic) ---


class TestParsePrediction:
    def test_valid_json(self) -> None:
        """Complete JSON → correct GmailPrediction fields."""
        raw = json.dumps(
            {
                "summary_text": "Order #123 has shipped via FedEx.",
                "predicted_category": "Updates",
                "key_actions": ["Track package"],
                "promotion_signals": [],
                "improvement_suggestions": ["Add delivery date"],
                "confidence": 0.92,
            }
        )
        signals = EmailSignals(plain_text="test")
        result = GmailSummaryPredictor._parse_prediction(raw, signals)
        assert result.summary_text == "Order #123 has shipped via FedEx."
        assert result.predicted_category == "Updates"
        assert result.key_actions == ["Track package"]
        assert result.confidence == 0.92

    def test_invalid_json_fallback(self) -> None:
        """Garbage → fallback with confidence=0.0."""
        signals = EmailSignals(has_unsubscribe=True, price_mentions=2, plain_text="sale")
        result = GmailSummaryPredictor._parse_prediction("not json at all", signals)
        assert result.confidence == 0.0
        assert result.summary_text == "Unable to generate prediction"
        assert result.predicted_category == "Promotions"  # from signals

    def test_invalid_category(self) -> None:
        """Unknown category → defaults to 'Primary'."""
        raw = json.dumps(
            {
                "summary_text": "test",
                "predicted_category": "Spam",
                "confidence": 0.5,
            }
        )
        signals = EmailSignals(plain_text="test")
        result = GmailSummaryPredictor._parse_prediction(raw, signals)
        assert result.predicted_category == "Primary"

    def test_confidence_clamping(self) -> None:
        """Confidence > 1.0 → clamped to 1.0."""
        raw = json.dumps(
            {
                "summary_text": "test",
                "predicted_category": "Primary",
                "confidence": 1.5,
            }
        )
        signals = EmailSignals(plain_text="test")
        result = GmailSummaryPredictor._parse_prediction(raw, signals)
        assert result.confidence == 1.0

    def test_confidence_clamping_negative(self) -> None:
        """Confidence < 0.0 → clamped to 0.0."""
        raw = json.dumps(
            {
                "summary_text": "test",
                "predicted_category": "Primary",
                "confidence": -0.5,
            }
        )
        signals = EmailSignals(plain_text="test")
        result = GmailSummaryPredictor._parse_prediction(raw, signals)
        assert result.confidence == 0.0


# --- _guess_category tests (deterministic) ---


class TestGuessCategory:
    def test_promotional(self) -> None:
        """Unsubscribe + prices → 'Promotions'."""
        signals = EmailSignals(has_unsubscribe=True, price_mentions=2)
        assert _guess_category(signals) == "Promotions"

    def test_updates(self) -> None:
        """Schema.org → 'Updates'."""
        signals = EmailSignals(has_schema_org=True)
        assert _guess_category(signals) == "Updates"

    def test_primary(self) -> None:
        """No signals → 'Primary'."""
        signals = EmailSignals()
        assert _guess_category(signals) == "Primary"

    def test_unsubscribe_only(self) -> None:
        """Unsubscribe only (no prices/CTAs) → 'Promotions'."""
        signals = EmailSignals(has_unsubscribe=True)
        assert _guess_category(signals) == "Promotions"


# --- Optimizer parse tests (deterministic) ---


class TestParseOptimization:
    def test_valid_optimization(self) -> None:
        """Complete JSON → correct OptimizedPreview."""
        raw = json.dumps(
            {
                "suggested_subjects": ["Better subject 1", "Better subject 2"],
                "suggested_previews": ["Preview option A"],
                "reasoning": "Reduce promotional signals",
            }
        )
        result = PreviewTextOptimizer._parse_optimization(raw, "Original", "Original preview")
        assert result.original_subject == "Original"
        assert len(result.suggested_subjects) == 2
        assert result.reasoning == "Reduce promotional signals"

    def test_invalid_optimization(self) -> None:
        """Garbage → fallback with reasoning."""
        result = PreviewTextOptimizer._parse_optimization("not json", "Subject", "Preview")
        assert result.original_subject == "Subject"
        assert result.original_preview == "Preview"
        assert "Unable" in result.reasoning


# --- Service layer tests (mock settings) ---


class TestServiceDisabled:
    @pytest.mark.anyio
    async def test_predict_disabled(self) -> None:
        """enabled=False → ForbiddenError."""
        from app.core.exceptions import ForbiddenError
        from app.qa_engine.schemas import GmailPredictRequest
        from app.qa_engine.service import QAEngineService

        db = AsyncMock()
        service = QAEngineService(db)
        data = GmailPredictRequest(
            html="<html><body>test</body></html>",
            subject="Test",
            from_name="Sender",
        )

        with pytest.raises(ForbiddenError):
            await service.predict_gmail_summary(data)

    @pytest.mark.anyio
    async def test_optimize_disabled(self) -> None:
        """enabled=False → ForbiddenError."""
        from app.core.exceptions import ForbiddenError
        from app.qa_engine.schemas import GmailOptimizeRequest
        from app.qa_engine.service import QAEngineService

        db = AsyncMock()
        service = QAEngineService(db)
        data = GmailOptimizeRequest(
            html="<html><body>test</body></html>",
            subject="Test",
            from_name="Sender",
            target_summary=None,
        )

        with pytest.raises(ForbiddenError):
            await service.optimize_gmail_preview(data)


# --- Route tests (sync TestClient, matching project pattern) ---

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
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestRoutes:
    def test_gmail_predict_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/gmail-predict",
            json={"html": "<html></html>", "subject": "T", "from_name": "S"},
        )
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_gmail_predict_success(self, client: TestClient) -> None:
        mock_resp = GmailPredictResponse(
            summary_text="Test summary",
            predicted_category="Primary",
            key_actions=[],
            promotion_signals=[],
            improvement_suggestions=[],
            confidence=0.8,
        )
        with patch.object(
            QAEngineService, "predict_gmail_summary", new_callable=AsyncMock, return_value=mock_resp
        ):
            resp = client.post(
                f"{BASE}/gmail-predict",
                json={
                    "html": "<html><body>Hello</body></html>",
                    "subject": "Test email",
                    "from_name": "Sender",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["predicted_category"] == "Primary"

    @pytest.mark.usefixtures("_auth_developer")
    def test_gmail_predict_validation(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/gmail-predict", json={"html": "", "subject": "T", "from_name": "S"}
        )
        assert resp.status_code == 422

    def test_gmail_optimize_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/gmail-optimize",
            json={"html": "<html></html>", "subject": "T", "from_name": "S"},
        )
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_gmail_optimize_success(self, client: TestClient) -> None:
        mock_resp = GmailOptimizeResponse(
            original_subject="Test",
            suggested_subjects=["Better"],
            original_preview="",
            suggested_previews=["Better preview"],
            reasoning="Reasoning",
        )
        with patch.object(
            QAEngineService,
            "optimize_gmail_preview",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.post(
                f"{BASE}/gmail-optimize",
                json={
                    "html": "<html><body>Hello</body></html>",
                    "subject": "Test",
                    "from_name": "Sender",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["original_subject"] == "Test"
