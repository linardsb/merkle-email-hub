"""Email intent classifier for schema.org markup injection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class IntentType(Enum):
    """Email intent types for schema.org markup."""

    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    EVENT = "event"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"


@dataclass(frozen=True)
class ExtractedEntity:
    """An entity extracted from email content."""

    entity_type: str  # "price", "date", "order_number", "product_name", "url"
    value: str
    raw_text: str


@dataclass(frozen=True)
class EmailIntent:
    """Classified email intent with extracted entities."""

    intent_type: IntentType
    confidence: float
    extracted_entities: tuple[ExtractedEntity, ...] = ()


# ── Pre-compiled regex patterns ──

# Price patterns: $50, €29.99, £100, 50% off, etc.
_PRICE_PATTERN = re.compile(
    r"(?:[$€£¥]\s?\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s?(?:[$€£¥])|(\d+)\s?%\s*(?:off|discount|savings?))",
    re.IGNORECASE,
)

# Currency codes: USD 50, EUR 29.99
_CURRENCY_CODE_PATTERN = re.compile(
    r"\b(?:USD|EUR|GBP|JPY|CAD|AUD)\s?\d+(?:[.,]\d{1,2})?\b",
    re.IGNORECASE,
)

# Promotional CTA patterns
_PROMO_CTA_PATTERN = re.compile(
    r"\b(?:shop\s+now|buy\s+now|order\s+now|add\s+to\s+cart|get\s+(?:the\s+)?deal|claim\s+(?:your\s+)?(?:offer|discount)|limited\s+(?:time\s+)?offer|sale\s+ends?|flash\s+sale|free\s+shipping)\b",
    re.IGNORECASE,
)

# Promotional keywords
_PROMO_KEYWORD_PATTERN = re.compile(
    r"\b(?:sale|discount|offer|promo(?:tion)?|coupon|voucher|clearance|markdown|savings?|deal)\b",
    re.IGNORECASE,
)

# Expiry date patterns: "expires March 30", "valid until 2026-04-01", "ends tomorrow"
_EXPIRY_PATTERN = re.compile(
    r"\b(?:expires?|valid\s+(?:until|through|till)|ends?|deadline|last\s+(?:day|chance))\s*:?\s*(.{5,30})",
    re.IGNORECASE,
)

# Order number patterns: Order #12345, Order: ABC-123
_ORDER_PATTERN = re.compile(
    r"\b(?:order|confirmation|invoice|receipt)\s*(?:#|number|no\.?|:)\s*([A-Z0-9][\w-]{3,20})",
    re.IGNORECASE,
)

# Shipping/tracking patterns
_SHIPPING_PATTERN = re.compile(
    r"\b(?:ship(?:ping|ped|ment)|track(?:ing)?|deliver(?:y|ed)|dispatch(?:ed)?|in\s+transit|out\s+for\s+delivery|estimated\s+(?:delivery|arrival))\b",
    re.IGNORECASE,
)

# Tracking number pattern
_TRACKING_PATTERN = re.compile(
    r"\b(?:tracking\s*(?:#|number|no\.?|:)\s*:?\s*([A-Z0-9]{8,30}))\b",
    re.IGNORECASE,
)

# Receipt/transaction keywords
_RECEIPT_PATTERN = re.compile(
    r"\b(?:receipt|payment\s+(?:confirmed?|received|processed)|transaction|invoice|billing\s+(?:summary|statement)|amount\s+(?:charged|paid)|total\s+(?:charged|paid))\b",
    re.IGNORECASE,
)

# Event date/time patterns
_EVENT_DATE_PATTERN = re.compile(
    r"\b(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)

# Event RSVP/registration patterns
_EVENT_ACTION_PATTERN = re.compile(
    r"\b(?:RSVP|register\s+(?:now|here|today)|attend|join\s+(?:us|the\s+event)|save\s+(?:your\s+)?(?:spot|seat)|sign\s+up|(?:event|webinar|conference|workshop|meetup)\s+(?:registration|invite|invitation))\b",
    re.IGNORECASE,
)

# Event location patterns
_EVENT_LOCATION_PATTERN = re.compile(
    r"\b(?:(?:venue|location|where|address)\s*:\s*(.{5,60}))\b",
    re.IGNORECASE,
)

# Newsletter indicators
_NEWSLETTER_PATTERN = re.compile(
    r"\b(?:unsubscribe|email\s+preferences|manage\s+(?:your\s+)?subscription|opt[\s-]?out|mailing\s+list)\b",
    re.IGNORECASE,
)

# Notification/status patterns
_NOTIFICATION_PATTERN = re.compile(
    r"\b(?:status\s+update|account\s+(?:activity|update|notification)|password\s+(?:reset|changed)|security\s+alert|(?:your|a\s+new)\s+(?:login|sign[\s-]?in)|verification\s+(?:code|link)|two[\s-]?factor|2FA)\b",
    re.IGNORECASE,
)

# URL extraction
_URL_PATTERN = re.compile(
    r'(?:href=["\'])(https?://[^"\'>\s]+)(?:["\'])',
    re.IGNORECASE,
)

# Product name heuristic: text before/near price
_PRODUCT_PATTERN = re.compile(
    r"(?:product|item|name)\s*[:\-]\s*([^<\n]{3,50})",
    re.IGNORECASE,
)


def _strip_html_tags(html: str) -> str:
    """Strip HTML tags for text analysis."""
    return re.sub(r"<[^>]+>", " ", html)


class EmailIntentClassifier:
    """Classifies email intent using regex-first pattern matching.

    Follows the QueryRouter pattern (Phase 16.1): pre-compiled regex
    patterns with confidence scoring and entity extraction. No LLM
    fallback — email intent classification is deterministic.
    """

    def classify(self, html: str, subject: str = "") -> EmailIntent:
        """Classify email intent from HTML content and subject line.

        Args:
            html: Email HTML content.
            subject: Email subject line (optional, boosts accuracy).

        Returns:
            EmailIntent with type, confidence, and extracted entities.
        """
        text = _strip_html_tags(html)
        combined = f"{subject} {text}"

        # Score each intent
        scores: dict[IntentType, float] = dict.fromkeys(IntentType, 0.0)
        entities: list[ExtractedEntity] = []

        # ── Promotional signals ──
        price_matches = _PRICE_PATTERN.findall(combined)
        currency_matches = _CURRENCY_CODE_PATTERN.findall(combined)
        promo_cta_matches = _PROMO_CTA_PATTERN.findall(combined)
        promo_keyword_matches = _PROMO_KEYWORD_PATTERN.findall(combined)

        if price_matches or currency_matches:
            scores[IntentType.PROMOTIONAL] += 2.0
            for m in _PRICE_PATTERN.finditer(combined):
                entities.append(ExtractedEntity("price", m.group(0).strip(), m.group(0)))
        if promo_cta_matches:
            scores[IntentType.PROMOTIONAL] += 1.5
        if promo_keyword_matches:
            scores[IntentType.PROMOTIONAL] += 1.0

        # Extract expiry dates for promotions
        for m in _EXPIRY_PATTERN.finditer(combined):
            entities.append(ExtractedEntity("expiry_date", m.group(1).strip(), m.group(0)))

        # ── Transactional signals ──
        order_matches = list(_ORDER_PATTERN.finditer(combined))
        shipping_matches = _SHIPPING_PATTERN.findall(combined)
        tracking_matches = list(_TRACKING_PATTERN.finditer(combined))
        receipt_matches = _RECEIPT_PATTERN.findall(combined)

        if order_matches:
            scores[IntentType.TRANSACTIONAL] += 2.5
            for m in order_matches:
                entities.append(ExtractedEntity("order_number", m.group(1).strip(), m.group(0)))
        if shipping_matches:
            scores[IntentType.TRANSACTIONAL] += 2.0
        if tracking_matches:
            scores[IntentType.TRANSACTIONAL] += 1.5
            for m in tracking_matches:
                entities.append(ExtractedEntity("tracking_number", m.group(1).strip(), m.group(0)))
        if receipt_matches:
            scores[IntentType.TRANSACTIONAL] += 1.5

        # ── Event signals ──
        event_date_matches = _EVENT_DATE_PATTERN.findall(combined)
        event_action_matches = _EVENT_ACTION_PATTERN.findall(combined)

        if event_action_matches:
            scores[IntentType.EVENT] += 2.0
        if event_date_matches and event_action_matches:
            scores[IntentType.EVENT] += 1.5
            for m in _EVENT_DATE_PATTERN.finditer(combined):
                entities.append(ExtractedEntity("event_date", m.group(0).strip(), m.group(0)))
        elif event_date_matches:
            scores[IntentType.EVENT] += 0.5  # Dates alone are weak signal

        # Extract location
        for m in _EVENT_LOCATION_PATTERN.finditer(combined):
            entities.append(ExtractedEntity("location", m.group(1).strip(), m.group(0)))

        # ── Newsletter signals ──
        newsletter_matches = _NEWSLETTER_PATTERN.findall(combined)
        if newsletter_matches:
            scores[IntentType.NEWSLETTER] += 1.0
            # Newsletter + no commercial CTA = newsletter
            if not promo_cta_matches and not order_matches:
                scores[IntentType.NEWSLETTER] += 1.0

        # ── Notification signals ──
        notification_matches = _NOTIFICATION_PATTERN.findall(combined)
        if notification_matches:
            scores[IntentType.NOTIFICATION] += 2.0

        # ── Cross-intent suppression ──
        # Transactional with prices should stay transactional (receipts have prices)
        if (
            scores[IntentType.TRANSACTIONAL] > 0
            and scores[IntentType.PROMOTIONAL] > 0
            and (order_matches or receipt_matches)
        ):
            scores[IntentType.PROMOTIONAL] *= 0.3

        # Newsletter unsubscribe link is present in most marketing emails too
        if scores[IntentType.NEWSLETTER] > 0 and scores[IntentType.PROMOTIONAL] > 1.0:
            scores[IntentType.NEWSLETTER] *= 0.4

        # Notification vs transactional: order confirmation is transactional
        if scores[IntentType.NOTIFICATION] > 0 and scores[IntentType.TRANSACTIONAL] > 2.0:
            scores[IntentType.NOTIFICATION] *= 0.3

        # ── Extract URLs from HTML (for action URLs) ──
        for m in _URL_PATTERN.finditer(html):
            entities.append(ExtractedEntity("url", m.group(1), m.group(0)))

        # Extract product names
        for m in _PRODUCT_PATTERN.finditer(combined):
            entities.append(ExtractedEntity("product_name", m.group(1).strip(), m.group(0)))

        # ── Determine winner ──
        best_intent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_intent]

        # No signal at all → newsletter (safest default, no markup injected)
        if best_score == 0:
            return EmailIntent(
                intent_type=IntentType.NEWSLETTER,
                confidence=0.3,
                extracted_entities=tuple(entities),
            )

        # Normalize confidence: floor 0.5, cap at 1.0
        confidence = min(best_score / 4.0, 1.0)
        confidence = max(confidence, 0.5)

        logger.info(
            "schema_markup.intent_classified",
            intent=best_intent.value,
            confidence=confidence,
            entity_count=len(entities),
            scores={k.value: round(v, 2) for k, v in scores.items()},
        )

        return EmailIntent(
            intent_type=best_intent,
            confidence=confidence,
            extracted_entities=tuple(entities),
        )
