# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for Schema.org Auto-Markup Injection (Phase 20.2)."""

from __future__ import annotations

import json
import re
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.email_engine.schema_markup.classifier import (
    EmailIntentClassifier,
    IntentType,
)
from app.email_engine.schema_markup.injector import SchemaMarkupInjector
from app.email_engine.schema_markup.validator import SchemaValidator
from app.email_engine.service import EmailEngineService
from app.main import app

BASE = "/api/v1/email"

MINIMAL_HTML = "<!DOCTYPE html><html><head></head><body><p>Hello</p></body></html>"

PROMO_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<p>Flash Sale! Get $50 off your order</p>"
    "<p>Use code SAVE50 — offer expires March 30, 2026</p>"
    '<a href="https://example.com/shop">Shop Now</a>'
    "</body></html>"
)

TRANSACTIONAL_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<p>Order Confirmation</p>"
    "<p>Order #ABC-12345 has been shipped!</p>"
    "<p>Tracking number: 1Z999AA10123456784</p>"
    '<a href="https://example.com/track">Track your package</a>'
    "</body></html>"
)

EVENT_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<p>You're Invited!</p>"
    "<p>Join us for the Annual Tech Conference</p>"
    "<p>March 25, 2026</p>"
    "<p>Venue: San Francisco Convention Center</p>"
    '<a href="https://example.com/rsvp">RSVP Now</a>'
    "</body></html>"
)

NOTIFICATION_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<p>Security Alert</p>"
    "<p>A new login was detected on your account</p>"
    '<a href="https://example.com/account">View Details</a>'
    "</body></html>"
)

NEWSLETTER_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<p>Weekly Newsletter</p>"
    "<p>Here are this week's top stories</p>"
    '<a href="https://example.com/unsubscribe">Unsubscribe</a>'
    "</body></html>"
)


def _make_user(role: str = "developer") -> User:
    u = User(email=f"{role}@test.com", hashed_password="x", role=role)
    u.id = 1
    return u


# ── Classifier tests ──


class TestEmailIntentClassifier:
    def test_classify_promotional(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(PROMO_HTML, "Flash Sale!")
        assert intent.intent_type == IntentType.PROMOTIONAL
        assert intent.confidence >= 0.5
        prices = [e for e in intent.extracted_entities if e.entity_type == "price"]
        assert len(prices) >= 1

    def test_classify_transactional(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(TRANSACTIONAL_HTML, "Order Confirmation")
        assert intent.intent_type == IntentType.TRANSACTIONAL
        orders = [e for e in intent.extracted_entities if e.entity_type == "order_number"]
        assert len(orders) >= 1
        assert orders[0].value == "ABC-12345"

    def test_classify_event(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(EVENT_HTML, "You're Invited!")
        assert intent.intent_type == IntentType.EVENT

    def test_classify_notification(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(NOTIFICATION_HTML, "Security Alert")
        assert intent.intent_type == IntentType.NOTIFICATION

    def test_classify_newsletter(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(NEWSLETTER_HTML, "Weekly Newsletter")
        assert intent.intent_type == IntentType.NEWSLETTER

    def test_classify_empty_html(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(MINIMAL_HTML)
        assert intent.intent_type == IntentType.NEWSLETTER  # Default
        assert intent.confidence < 0.5

    def test_transactional_suppresses_promotional(self) -> None:
        """Order confirmations with prices should be transactional, not promo."""
        html = (
            "<html><head></head><body>"
            "<p>Order #ORD-99999 confirmed</p>"
            "<p>Total: $149.99</p>"
            "</body></html>"
        )
        classifier = EmailIntentClassifier()
        intent = classifier.classify(html, "Order Confirmation")
        assert intent.intent_type == IntentType.TRANSACTIONAL

    def test_extract_urls(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(PROMO_HTML)
        urls = [e for e in intent.extracted_entities if e.entity_type == "url"]
        assert any("https://example.com/shop" in u.value for u in urls)

    def test_extract_tracking_number(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(TRANSACTIONAL_HTML)
        tracking = [e for e in intent.extracted_entities if e.entity_type == "tracking_number"]
        assert len(tracking) >= 1

    def test_extract_expiry_date(self) -> None:
        classifier = EmailIntentClassifier()
        intent = classifier.classify(PROMO_HTML)
        expiry = [e for e in intent.extracted_entities if e.entity_type == "expiry_date"]
        assert len(expiry) >= 1


# ── Validator tests ──


class TestSchemaValidator:
    def test_valid_product_offer(self) -> None:
        validator = SchemaValidator()
        result = validator.validate(
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Widget",
                "offers": {
                    "@type": "Offer",
                    "price": "50.00",
                    "priceCurrency": "USD",
                },
            }
        )
        assert result.valid

    def test_missing_context(self) -> None:
        validator = SchemaValidator()
        result = validator.validate({"@type": "Product", "name": "Widget"})
        assert not result.valid
        assert any("@context" in e for e in result.errors)

    def test_missing_type(self) -> None:
        validator = SchemaValidator()
        result = validator.validate({"@context": "https://schema.org"})
        assert not result.valid

    def test_missing_required_property(self) -> None:
        validator = SchemaValidator()
        result = validator.validate(
            {
                "@context": "https://schema.org",
                "@type": "Offer",
                # Missing price and priceCurrency
            }
        )
        assert not result.valid
        assert any("price" in e for e in result.errors)

    def test_non_https_action_url(self) -> None:
        validator = SchemaValidator()
        result = validator.validate(
            {
                "@context": "https://schema.org",
                "@type": "ViewAction",
                "url": "http://example.com/view",
                "name": "View",
            }
        )
        assert not result.valid
        assert any("HTTPS" in e for e in result.errors)

    def test_valid_event(self) -> None:
        validator = SchemaValidator()
        result = validator.validate(
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Conference",
                "startDate": "2026-03-25",
            }
        )
        assert result.valid


# ── Injector tests ──


class TestSchemaMarkupInjector:
    def test_inject_promotional(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(PROMO_HTML, "Flash Sale")
        result = injector.inject(PROMO_HTML, intent)
        assert result.injected
        assert "application/ld+json" in result.html
        assert "Product" in result.schema_types

    def test_inject_transactional(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(TRANSACTIONAL_HTML, "Order Confirmation")
        result = injector.inject(TRANSACTIONAL_HTML, intent)
        assert result.injected
        assert "Order" in result.schema_types

    def test_inject_event(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(EVENT_HTML, "You're Invited!")
        result = injector.inject(EVENT_HTML, intent)
        assert result.injected
        assert "Event" in result.schema_types

    def test_no_inject_newsletter(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(NEWSLETTER_HTML, "Weekly Newsletter")
        result = injector.inject(NEWSLETTER_HTML, intent)
        assert not result.injected
        assert result.html == NEWSLETTER_HTML  # Unchanged

    def test_inject_in_head(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(PROMO_HTML, "Sale")
        result = injector.inject(PROMO_HTML, intent)
        # JSON-LD should be in <head>
        head_end = result.html.find("</head>")
        script_pos = result.html.find("application/ld+json")
        assert script_pos < head_end

    def test_json_ld_is_valid_json(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(PROMO_HTML, "Sale")
        result = injector.inject(PROMO_HTML, intent)
        # Extract JSON-LD
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', result.html)
        assert m is not None
        parsed = json.loads(m.group(1))
        assert parsed["@context"] == "https://schema.org"

    def test_inject_time_recorded(self) -> None:
        classifier = EmailIntentClassifier()
        injector = SchemaMarkupInjector()
        intent = classifier.classify(PROMO_HTML, "Sale")
        result = injector.inject(PROMO_HTML, intent)
        assert result.inject_time_ms >= 0


# ── Service integration tests ──


class TestServiceInjectSchema:
    def test_service_inject_schema(self) -> None:
        service = EmailEngineService(db=AsyncMock())
        response = service.inject_schema(PROMO_HTML, "Flash Sale!")
        assert response.injected
        assert response.intent.intent_type == "promotional"
        assert len(response.schema_types) > 0

    def test_service_inject_newsletter_no_markup(self) -> None:
        service = EmailEngineService(db=AsyncMock())
        response = service.inject_schema(NEWSLETTER_HTML, "Newsletter")
        assert not response.injected


# ── Route tests ──


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield TestClient(app)
    app.dependency_overrides.clear()
    limiter.enabled = True


class TestSchemaInjectRoute:
    def test_inject_schema_success(self, client: TestClient) -> None:
        with patch("app.email_engine.routes.get_settings") as mock_settings:
            mock_settings.return_value.email_engine.schema_injection_enabled = True
            resp = client.post(
                f"{BASE}/inject-schema",
                json={"html": PROMO_HTML, "subject": "Flash Sale!"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["injected"] is True
        assert data["intent"]["intent_type"] == "promotional"

    def test_inject_schema_disabled(self, client: TestClient) -> None:
        with patch("app.email_engine.routes.get_settings") as mock_settings:
            mock_settings.return_value.email_engine.schema_injection_enabled = False
            resp = client.post(
                f"{BASE}/inject-schema",
                json={"html": PROMO_HTML, "subject": "Sale"},
            )
        assert resp.status_code == 403

    def test_inject_schema_requires_auth(self) -> None:
        limiter.enabled = False
        app.dependency_overrides.clear()
        client = TestClient(app)
        resp = client.post(
            f"{BASE}/inject-schema",
            json={"html": PROMO_HTML},
        )
        assert resp.status_code in (401, 403)
        limiter.enabled = True

    def test_inject_schema_viewer_forbidden(self) -> None:
        limiter.enabled = False
        app.dependency_overrides[get_current_user] = lambda: _make_user("viewer")
        client = TestClient(app)
        resp = client.post(
            f"{BASE}/inject-schema",
            json={"html": PROMO_HTML},
        )
        assert resp.status_code == 403
        app.dependency_overrides.clear()
        limiter.enabled = True

    def test_inject_schema_empty_html_rejected(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/inject-schema",
            json={"html": ""},
        )
        assert resp.status_code == 422

    def test_inject_schema_newsletter_no_inject(self, client: TestClient) -> None:
        with patch("app.email_engine.routes.get_settings") as mock_settings:
            mock_settings.return_value.email_engine.schema_injection_enabled = True
            resp = client.post(
                f"{BASE}/inject-schema",
                json={"html": NEWSLETTER_HTML, "subject": "Newsletter"},
            )
        assert resp.status_code == 200
        assert resp.json()["injected"] is False
