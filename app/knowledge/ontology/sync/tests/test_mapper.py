"""Tests for Can I Email → ontology mapper."""

from app.knowledge.ontology.sync.mapper import (
    extract_property_name_value,
    feature_to_css_property,
    feature_to_property_id,
    feature_to_support_entries,
    infer_category,
    map_support_value,
    resolve_client_id,
)
from app.knowledge.ontology.sync.schemas import CanIEmailFeature
from app.knowledge.ontology.types import CSSCategory, SupportLevel


def _make_feature(
    slug: str = "css-display-flex",
    title: str = "display:flex",
    category: str = "css",
    stats: dict[str, dict[str, dict[str, str]]] | None = None,
    notes: dict[str, str] | None = None,
) -> CanIEmailFeature:
    return CanIEmailFeature(
        slug=slug,
        title=title,
        category=category,
        last_test_date="2024-01-01",
        stats=stats or {},
        notes=notes or {},
    )


class TestMapSupportValue:
    def test_y_returns_full(self) -> None:
        assert map_support_value("y") == SupportLevel.FULL

    def test_n_returns_none(self) -> None:
        assert map_support_value("n") == SupportLevel.NONE

    def test_a_returns_partial(self) -> None:
        assert map_support_value("a") == SupportLevel.PARTIAL

    def test_u_returns_unknown(self) -> None:
        assert map_support_value("u") == SupportLevel.UNKNOWN

    def test_partial_with_note(self) -> None:
        assert map_support_value("a #1") == SupportLevel.PARTIAL

    def test_yes_uppercase(self) -> None:
        assert map_support_value("Y") == SupportLevel.FULL

    def test_unknown_value(self) -> None:
        assert map_support_value("x") == SupportLevel.UNKNOWN


class TestResolveClientId:
    def test_known_client(self) -> None:
        assert resolve_client_id("gmail", "desktop-webmail") == "gmail_web"
        assert resolve_client_id("outlook", "windows") == "outlook_2019_win"
        assert resolve_client_id("apple-mail", "ios") == "apple_mail_ios"

    def test_unknown_client(self) -> None:
        assert resolve_client_id("unknown-client", "desktop") is None


class TestFeatureToPropertyId:
    def test_css_prefix_stripped(self) -> None:
        assert feature_to_property_id("css-display-flex") == "display_flex"

    def test_html_prefix_stripped(self) -> None:
        assert feature_to_property_id("html-video") == "video"

    def test_hyphens_to_underscores(self) -> None:
        assert feature_to_property_id("css-background-color") == "background_color"

    def test_no_prefix(self) -> None:
        assert feature_to_property_id("some-feature") == "some_feature"


class TestInferCategory:
    def test_display(self) -> None:
        assert infer_category("css-display-flex", "display:flex") == CSSCategory.LAYOUT

    def test_background(self) -> None:
        assert (
            infer_category("css-background-color", "background-color")
            == CSSCategory.COLOR_BACKGROUND
        )

    def test_unknown(self) -> None:
        assert infer_category("css-clip-path", "clip-path") == CSSCategory.OTHER


class TestExtractPropertyNameValue:
    def test_with_colon(self) -> None:
        assert extract_property_name_value("display:flex") == ("display", "flex")

    def test_without_colon(self) -> None:
        assert extract_property_name_value("background-color") == (
            "background-color",
            None,
        )

    def test_empty_value_after_colon(self) -> None:
        name, value = extract_property_name_value("display:")
        assert name == "display"
        assert value is None


class TestFeatureToCSSProperty:
    def test_conversion(self) -> None:
        feat = _make_feature()
        prop = feature_to_css_property(feat)
        assert prop.id == "display_flex"
        assert prop.property_name == "display"
        assert prop.value == "flex"
        assert prop.category == CSSCategory.LAYOUT
        assert "caniemail" in prop.tags


class TestFeatureToSupportEntries:
    def test_basic(self) -> None:
        feat = _make_feature(
            stats={
                "gmail": {
                    "desktop-webmail": {"2023-01": "y"},
                },
            },
        )
        entries = feature_to_support_entries(feat)
        assert len(entries) == 1
        prop_id, client_id, level, note = entries[0]
        assert prop_id == "display_flex"
        assert client_id == "gmail_web"
        assert level == SupportLevel.FULL
        assert note == ""

    def test_note_extraction(self) -> None:
        feat = _make_feature(
            stats={
                "gmail": {
                    "desktop-webmail": {"2023-01": "a #1"},
                },
            },
            notes={"1": "Only with IMAP"},
        )
        entries = feature_to_support_entries(feat)
        assert entries[0][3] == "Only with IMAP"

    def test_skips_unmapped_clients(self) -> None:
        feat = _make_feature(
            stats={
                "unknown-client": {
                    "desktop": {"2023-01": "y"},
                },
            },
        )
        entries = feature_to_support_entries(feat)
        assert len(entries) == 0

    def test_uses_latest_version(self) -> None:
        feat = _make_feature(
            stats={
                "gmail": {
                    "desktop-webmail": {
                        "2020-01": "n",
                        "2023-01": "y",
                    },
                },
            },
        )
        entries = feature_to_support_entries(feat)
        assert entries[0][2] == SupportLevel.FULL

    def test_empty_versions(self) -> None:
        feat = _make_feature(
            stats={
                "gmail": {
                    "desktop-webmail": {},
                },
            },
        )
        entries = feature_to_support_entries(feat)
        assert len(entries) == 0
