"""Schema.org JSON-LD markup injector for email HTML."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, cast

from app.core.logging import get_logger
from app.email_engine.schema_markup.classifier import EmailIntent, ExtractedEntity, IntentType
from app.email_engine.schema_markup.validator import SchemaValidator

logger = get_logger(__name__)


def _find_entity(entities: tuple[ExtractedEntity, ...], entity_type: str) -> str | None:
    """Find first entity of given type."""
    for e in entities:
        if e.entity_type == entity_type:
            return e.value
    return None


def _find_first_https_url(entities: tuple[ExtractedEntity, ...]) -> str | None:
    """Find first HTTPS URL from extracted entities."""
    for e in entities:
        if e.entity_type == "url" and e.value.startswith("https://"):
            return e.value
    return None


def _parse_price(price_str: str) -> tuple[str, str] | None:
    """Extract numeric price and currency from price string.

    Returns (price, currency_code) or None.
    """
    # $50.00, €29.99, £100
    m = re.match(r"([$€£¥])\s?(\d+(?:[.,]\d{1,2})?)", price_str)
    if m:
        symbol_map = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
        return m.group(2).replace(",", "."), symbol_map.get(m.group(1), "USD")

    # 50 USD, 29.99 EUR
    m = re.match(r"(\d+(?:[.,]\d{1,2})?)\s?(USD|EUR|GBP|JPY|CAD|AUD)", price_str, re.IGNORECASE)
    if m:
        return m.group(1).replace(",", "."), m.group(2).upper()

    return None


@dataclass(frozen=True)
class InjectionResult:
    """Result of schema markup injection."""

    html: str
    injected: bool
    intent_type: str
    confidence: float
    schema_types: list[str] = field(default_factory=lambda: [])
    validation_errors: tuple[str, ...] = ()
    inject_time_ms: float = 0.0


class SchemaMarkupInjector:
    """Builds and injects schema.org JSON-LD into email HTML.

    Supports:
    - Promotional: Product + Offer + DealAnnotation (Gmail Promotions tab)
    - Transactional: Order + TrackAction
    - Event: Event + RsvpAction/ViewAction
    - Notification: ViewAction
    - Newsletter: no injection (intentional)
    """

    def __init__(self) -> None:
        self._validator = SchemaValidator()

    def inject(self, html: str, intent: EmailIntent) -> InjectionResult:
        """Inject schema.org JSON-LD into email HTML.

        Args:
            html: Email HTML content.
            intent: Classified email intent.

        Returns:
            InjectionResult with modified HTML and metadata.
        """
        start = time.perf_counter()

        # Newsletter gets no markup
        if intent.intent_type == IntentType.NEWSLETTER:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return InjectionResult(
                html=html,
                injected=False,
                intent_type=intent.intent_type.value,
                confidence=intent.confidence,
                schema_types=[],
                validation_errors=(),
                inject_time_ms=elapsed,
            )

        # Build JSON-LD based on intent
        json_ld = self._build_json_ld(intent)

        if json_ld is None:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return InjectionResult(
                html=html,
                injected=False,
                intent_type=intent.intent_type.value,
                confidence=intent.confidence,
                schema_types=[],
                validation_errors=(),
                inject_time_ms=elapsed,
            )

        # Validate before injection
        validation = self._validator.validate(json_ld)
        if not validation.valid:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            logger.warning(
                "schema_markup.injection_skipped",
                reason="validation_failed",
                errors=validation.errors,
            )
            return InjectionResult(
                html=html,
                injected=False,
                intent_type=intent.intent_type.value,
                confidence=intent.confidence,
                schema_types=[],
                validation_errors=validation.errors,
                inject_time_ms=elapsed,
            )

        # Inject into <head>
        schema_types = self._extract_types(json_ld)
        script_tag = (
            '<script type="application/ld+json">'
            + json.dumps(json_ld, ensure_ascii=False, separators=(",", ":"))
            + "</script>"
        )

        modified_html = self._inject_in_head(html, script_tag)
        elapsed = round((time.perf_counter() - start) * 1000, 1)

        logger.info(
            "schema_markup.injected",
            intent=intent.intent_type.value,
            schema_types=schema_types,
            inject_time_ms=elapsed,
        )

        return InjectionResult(
            html=modified_html,
            injected=True,
            intent_type=intent.intent_type.value,
            confidence=intent.confidence,
            schema_types=schema_types,
            validation_errors=(),
            inject_time_ms=elapsed,
        )

    def _build_json_ld(self, intent: EmailIntent) -> dict[str, Any] | None:
        """Build JSON-LD based on classified intent."""
        builders = {
            IntentType.PROMOTIONAL: self._build_promotional,
            IntentType.TRANSACTIONAL: self._build_transactional,
            IntentType.EVENT: self._build_event,
            IntentType.NOTIFICATION: self._build_notification,
        }
        builder = builders.get(intent.intent_type)
        if builder is None:
            return None
        return builder(intent)

    def _build_promotional(self, intent: EmailIntent) -> dict[str, Any]:
        """Build Product + Offer + DealAnnotation markup."""
        entities = intent.extracted_entities

        product_name = _find_entity(entities, "product_name") or "Special Offer"
        price_str = _find_entity(entities, "price")
        expiry = _find_entity(entities, "expiry_date")
        url = _find_first_https_url(entities)

        offer: dict[str, Any] = {
            "@type": "Offer",
            "availability": "https://schema.org/InStock",
        }

        if price_str:
            parsed = _parse_price(price_str)
            if parsed:
                offer["price"] = parsed[0]
                offer["priceCurrency"] = parsed[1]
            else:
                offer["price"] = price_str
                offer["priceCurrency"] = "USD"

        if expiry:
            offer["availabilityEnds"] = expiry

        if url:
            offer["url"] = url

        result: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product_name,
            "offers": offer,
        }

        return result

    def _build_transactional(self, intent: EmailIntent) -> dict[str, Any]:
        """Build Order + TrackAction markup."""
        entities = intent.extracted_entities

        order_number = _find_entity(entities, "order_number") or "N/A"
        tracking_url = _find_first_https_url(entities)

        result: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Order",
            "orderNumber": order_number,
            "merchant": {
                "@type": "Organization",
                "name": "Merchant",
            },
            "orderStatus": "https://schema.org/OrderDelivered",
        }

        if tracking_url:
            result["potentialAction"] = {
                "@type": "TrackAction",
                "url": tracking_url,
            }

        return result

    def _build_event(self, intent: EmailIntent) -> dict[str, Any]:
        """Build Event + RsvpAction/ViewAction markup."""
        entities = intent.extracted_entities

        event_date = _find_entity(entities, "event_date") or ""
        location = _find_entity(entities, "location")
        url = _find_first_https_url(entities)

        result: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Event",
            "startDate": event_date,
        }

        if location:
            result["location"] = {
                "@type": "Place",
                "name": location,
            }

        if url:
            result["potentialAction"] = {
                "@type": "RsvpAction",
                "handler": {
                    "@type": "HttpActionHandler",
                    "url": url,
                },
            }

        return result

    def _build_notification(self, intent: EmailIntent) -> dict[str, Any]:
        """Build ViewAction for notification emails."""
        entities = intent.extracted_entities
        url = _find_first_https_url(entities)

        result: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "EmailMessage",
        }

        if url:
            result["potentialAction"] = {
                "@type": "ViewAction",
                "url": url,
                "name": "View Details",
            }

        return result

    def _extract_types(self, json_ld: dict[str, Any]) -> list[str]:
        """Extract all @type values from JSON-LD (flat list)."""
        types: list[str] = []
        t = json_ld.get("@type")
        if isinstance(t, str):
            types.append(t)
        for v in json_ld.values():
            if isinstance(v, dict):
                types.extend(self._extract_types(cast(dict[str, Any], v)))
        return types

    def _inject_in_head(self, html: str, script_tag: str) -> str:
        """Inject script tag into <head> section."""
        # Try </head> first
        head_close = re.search(r"</head>", html, re.IGNORECASE)
        if head_close:
            pos = head_close.start()
            return html[:pos] + script_tag + html[pos:]

        # Fallback: after <head>
        head_open = re.search(r"<head[^>]*>", html, re.IGNORECASE)
        if head_open:
            pos = head_open.end()
            return html[:pos] + script_tag + html[pos:]

        # Last resort: prepend to html
        return script_tag + html
