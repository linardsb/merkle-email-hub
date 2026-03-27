"""Tests for caniemail.com loader and compatibility integration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.design_sync.caniemail import (
    CanieMailData,
    CanieMailSupport,
    clear_caniemail_cache,
    get_caniemail_support,
    load_caniemail_data,
)
from app.design_sync.compatibility import ConverterCompatibility
from app.knowledge.ontology import SupportLevel


class TestCanieMailLoader:
    """Loading caniemail-support.json."""

    def test_missing_file_returns_empty(self) -> None:
        clear_caniemail_cache()
        with patch("app.design_sync.caniemail._DATA_PATH", Path("/nonexistent/path.json")):
            clear_caniemail_cache()
            data = load_caniemail_data()
            assert data.features == {}
            assert data.metadata == {}
        clear_caniemail_cache()

    def test_valid_json_loads(self) -> None:
        clear_caniemail_cache()
        sample = {
            "metadata": {"source": "test", "feature_count": 1},
            "features": {
                "css-gap": {
                    "outlook_2019": {"support": "no", "notes": "Use tables"},
                    "gmail_web": {"support": "yes", "notes": ""},
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample, f)
            f.flush()
            with patch("app.design_sync.caniemail._DATA_PATH", Path(f.name)):
                clear_caniemail_cache()
                data = load_caniemail_data()
                assert len(data.features) == 1
                assert "css-gap" in data.features
                outlook = data.features["css-gap"]["outlook_2019"]
                assert outlook.support == "no"
                assert outlook.notes == "Use tables"
        clear_caniemail_cache()

    def test_malformed_json_returns_empty(self) -> None:
        clear_caniemail_cache()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            f.flush()
            with patch("app.design_sync.caniemail._DATA_PATH", Path(f.name)):
                clear_caniemail_cache()
                data = load_caniemail_data()
                assert data.features == {}
        clear_caniemail_cache()

    def test_lru_cache_singleton(self) -> None:
        clear_caniemail_cache()
        with patch("app.design_sync.caniemail._DATA_PATH", Path("/nonexistent")):
            clear_caniemail_cache()
            d1 = load_caniemail_data()
            d2 = load_caniemail_data()
            assert d1 is d2
        clear_caniemail_cache()


class TestGetCanieMailSupport:
    """Lookup helper tests."""

    def test_hit(self) -> None:
        data = CanieMailData(
            features={
                "css-gap": {
                    "gmail_web": CanieMailSupport(support="yes"),
                }
            }
        )
        clear_caniemail_cache()
        with patch("app.design_sync.caniemail.load_caniemail_data", return_value=data):
            result = get_caniemail_support("css-gap", "gmail_web")
            assert result is not None
            assert result.support == "yes"

    def test_miss_feature(self) -> None:
        data = CanieMailData(features={})
        with patch("app.design_sync.caniemail.load_caniemail_data", return_value=data):
            result = get_caniemail_support("unknown", "gmail_web")
            assert result is None

    def test_miss_client(self) -> None:
        data = CanieMailData(features={"css-gap": {"gmail_web": CanieMailSupport(support="yes")}})
        with patch("app.design_sync.caniemail.load_caniemail_data", return_value=data):
            result = get_caniemail_support("css-gap", "outlook_2019")
            assert result is None


class TestCompatibilityWithCaniemail:
    """ConverterCompatibility caniemail integration."""

    def _make_caniemail_data(self) -> CanieMailData:
        return CanieMailData(
            features={
                "css-gap": {
                    "outlook_2019": CanieMailSupport(support="no", notes="Use tables"),
                    "gmail_web": CanieMailSupport(support="yes"),
                },
                "css-flexbox": {
                    "outlook_2019": CanieMailSupport(support="no"),
                    "gmail_web": CanieMailSupport(support="partial"),
                },
            }
        )

    def test_caniemail_none_overrides(self) -> None:
        """Property unsupported in caniemail should return NONE."""
        compat = ConverterCompatibility(
            target_clients=["outlook_2019"],
            caniemail_data=self._make_caniemail_data(),
        )
        level = compat._check_caniemail("css-gap")
        assert level == SupportLevel.NONE

    def test_caniemail_partial(self) -> None:
        compat = ConverterCompatibility(
            target_clients=["gmail_web"],
            caniemail_data=self._make_caniemail_data(),
        )
        level = compat._check_caniemail("css-flexbox")
        assert level == SupportLevel.PARTIAL

    def test_caniemail_full(self) -> None:
        compat = ConverterCompatibility(
            target_clients=["gmail_web"],
            caniemail_data=self._make_caniemail_data(),
        )
        level = compat._check_caniemail("css-gap")
        assert level == SupportLevel.FULL

    def test_caniemail_unknown_feature(self) -> None:
        compat = ConverterCompatibility(
            target_clients=["gmail_web"],
            caniemail_data=self._make_caniemail_data(),
        )
        level = compat._check_caniemail("css-grid")
        assert level == SupportLevel.FULL

    def test_no_caniemail_data_returns_full(self) -> None:
        """Without caniemail data, _check_caniemail always returns FULL."""
        compat = ConverterCompatibility(target_clients=["outlook_2019"])
        level = compat._check_caniemail("css-gap")
        assert level == SupportLevel.FULL

    def test_check_property_with_source_ontology(self) -> None:
        """Source reporting works."""
        compat = ConverterCompatibility(
            target_clients=["outlook_2019"],
            caniemail_data=CanieMailData(features={}),
        )
        _level, source = compat.check_property_with_source("display", "flex")
        # With empty caniemail, source should be ontology
        assert source in {"ontology", "both"}

    def test_unsupported_clients_includes_caniemail(self) -> None:
        """unsupported_clients should include clients flagged by caniemail."""
        compat = ConverterCompatibility(
            target_clients=["outlook_2019", "gmail_web"],
            caniemail_data=self._make_caniemail_data(),
        )
        unsupported = compat.unsupported_clients("css-gap")
        # Outlook should be unsupported via caniemail (not in ontology as "css-gap")
        assert "outlook_2019" in unsupported


class TestValidateAndTransformWithCaniemail:
    """Threading caniemail_data through validate_and_transform."""

    def test_caniemail_kwarg_accepted(self) -> None:
        from app.design_sync.protocol import ExtractedColor, ExtractedTokens
        from app.design_sync.token_transforms import validate_and_transform

        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="bg", hex="#FFFFFF")],
        )
        caniemail = CanieMailData(features={})

        result, _warnings = validate_and_transform(tokens, caniemail_data=caniemail)
        assert len(result.colors) == 1

    def test_caniemail_none_is_default(self) -> None:
        from app.design_sync.protocol import ExtractedColor, ExtractedTokens
        from app.design_sync.token_transforms import validate_and_transform

        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="bg", hex="#FFFFFF")],
        )
        result, _ = validate_and_transform(tokens)
        assert len(result.colors) == 1
