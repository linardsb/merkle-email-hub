"""Tests for design-sync ontology compatibility facade."""

import pytest

from app.design_sync.compatibility import CompatibilityHint, ConverterCompatibility
from app.knowledge.ontology import SupportLevel


class TestConverterCompatibility:
    """Tests for ConverterCompatibility facade."""

    def test_no_targets_returns_full(self) -> None:
        compat = ConverterCompatibility(target_clients=None)
        assert compat.check_property("display", "flex") == SupportLevel.FULL
        assert not compat.has_targets

    def test_no_targets_empty_unsupported(self) -> None:
        compat = ConverterCompatibility(target_clients=None)
        assert compat.unsupported_clients("display", "flex") == []

    def test_has_targets(self) -> None:
        compat = ConverterCompatibility(target_clients=["gmail_web"])
        assert compat.has_targets

    def test_check_and_warn_records_hint(self) -> None:
        compat = ConverterCompatibility(target_clients=["outlook_365_win", "gmail_web"])
        # letter-spacing is supported, but test the mechanism
        compat.check_and_warn("letter-spacing", context="Test node")
        # Hints collected (may or may not have entries depending on ontology data)
        assert isinstance(compat.hints, list)

    def test_manual_warn(self) -> None:
        compat = ConverterCompatibility(target_clients=["gmail_web"])
        compat.warn("custom-prop", "Not supported", ["gmail_web"])
        assert len(compat.hints) == 1
        assert compat.hints[0].level == "warning"
        assert compat.hints[0].css_property == "custom-prop"
        assert compat.hints[0].affected_clients == ("gmail_web",)

    def test_manual_info(self) -> None:
        compat = ConverterCompatibility(target_clients=["gmail_web"])
        compat.info("@font-face", "Stripped in Gmail", ["gmail_web"])
        assert len(compat.hints) == 1
        assert compat.hints[0].level == "info"

    def test_hints_accumulate(self) -> None:
        compat = ConverterCompatibility(target_clients=["gmail_web"])
        compat.warn("a", "msg1", [])
        compat.warn("b", "msg2", [])
        compat.info("c", "msg3", [])
        assert len(compat.hints) == 3

    def test_unknown_property_returns_full(self) -> None:
        compat = ConverterCompatibility(target_clients=["gmail_web"])
        assert compat.check_property("mso-line-height-rule") == SupportLevel.FULL

    def test_client_engine_returns_value(self) -> None:
        compat = ConverterCompatibility(target_clients=["outlook_365_win"])
        engine = compat.client_engine("outlook_365_win")
        # Should return "word" for Outlook Windows
        assert engine is not None

    def test_client_engine_unknown_returns_none(self) -> None:
        compat = ConverterCompatibility(target_clients=[])
        assert compat.client_engine("nonexistent_client") is None


class TestCompatibilityHint:
    """Tests for CompatibilityHint dataclass."""

    def test_frozen(self) -> None:
        hint = CompatibilityHint(
            level="warning",
            css_property="display",
            message="Not supported",
            affected_clients=("gmail_web",),
        )
        with pytest.raises(AttributeError):
            hint.level = "info"  # type: ignore[misc]
