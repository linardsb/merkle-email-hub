"""Tests for PII redaction in logs and eval traces."""

from __future__ import annotations

import pytest

from app.core.redaction import redact_event_dict, redact_pii, redact_value


class TestRedactPii:
    """Unit tests for the ``redact_pii`` string redactor."""

    def test_email_replaced(self) -> None:
        assert redact_pii("contact user@example.com please") == "contact [EMAIL] please"

    def test_phone_us_replaced(self) -> None:
        assert redact_pii("call 555-123-4567 now") == "call [PHONE] now"

    def test_phone_intl_replaced(self) -> None:
        assert redact_pii("ring +44 20 7946 0958 today") == "ring [PHONE_INTL] today"

    def test_ssn_replaced(self) -> None:
        assert redact_pii("ssn 123-45-6789 on file") == "ssn [SSN] on file"

    def test_credit_card_replaced(self) -> None:
        assert redact_pii("card 4111 1111 1111 1111 charged") == "card [CREDIT_CARD] charged"

    def test_mixed_pii_all_replaced(self) -> None:
        text = "Email user@test.com, phone 555.123.4567, ssn 999-88-7777"
        result = redact_pii(text)
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "[SSN]" in result
        assert "user@test.com" not in result
        assert "555.123.4567" not in result
        assert "999-88-7777" not in result

    def test_no_pii_unchanged(self) -> None:
        text = "Hello world, no sensitive data here."
        assert redact_pii(text) == text


class TestRedactValue:
    """Unit tests for the recursive ``redact_value`` function."""

    def test_nested_dict(self) -> None:
        data = {
            "brief": "Send to user@example.com",
            "meta": {"phone": "555-000-1234"},
        }
        result = redact_value(data)
        assert isinstance(result, dict)
        assert result["brief"] == "Send to [EMAIL]"
        assert result["meta"]["phone"] == "[PHONE]"

    def test_list_values(self) -> None:
        data = ["user@example.com", "clean text", 42]
        result = redact_value(data)
        assert isinstance(result, list)
        assert result[0] == "[EMAIL]"
        assert result[1] == "clean text"
        assert result[2] == 42


class TestRedactEventDict:
    """Unit tests for the structlog processor."""

    def test_pii_in_event_redacted(self) -> None:
        event_dict = {
            "event": "email.sent_to user@example.com",
            "level": "info",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        result = redact_event_dict(None, "info", event_dict)
        assert result["event"] == "email.sent_to [EMAIL]"

    @pytest.mark.parametrize("key", ["timestamp", "level", "request_id", "logger"])
    def test_metadata_keys_skipped(self, key: str) -> None:
        pii = "user@example.com"
        event_dict = {key: pii, "event": "test"}
        result = redact_event_dict(None, "info", event_dict)
        assert result[key] == pii  # metadata keys are NOT redacted
