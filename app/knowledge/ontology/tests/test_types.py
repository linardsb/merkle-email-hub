"""Tests for ontology type definitions."""

import pytest

from app.knowledge.ontology.types import (
    ClientEngine,
    CSSCategory,
    CSSProperty,
    EmailClient,
    Fallback,
    SupportEntry,
    SupportLevel,
)


class TestEnums:
    """Verify enum members and values."""

    def test_support_level_members(self) -> None:
        assert SupportLevel.FULL.value == "full"
        assert SupportLevel.PARTIAL.value == "partial"
        assert SupportLevel.NONE.value == "none"
        assert SupportLevel.UNKNOWN.value == "unknown"
        assert len(SupportLevel) == 4

    def test_client_engine_members(self) -> None:
        assert ClientEngine.WEBKIT.value == "webkit"
        assert ClientEngine.BLINK.value == "blink"
        assert ClientEngine.WORD.value == "word"
        assert ClientEngine.GECKO.value == "gecko"
        assert ClientEngine.PRESTO.value == "presto"
        assert ClientEngine.CUSTOM.value == "custom"
        assert len(ClientEngine) == 6

    def test_css_category_members(self) -> None:
        assert CSSCategory.LAYOUT.value == "layout"
        assert CSSCategory.FLEXBOX.value == "flexbox"
        assert CSSCategory.GRID.value == "grid"
        assert CSSCategory.DARK_MODE.value == "dark_mode"
        assert len(CSSCategory) == 14

    def test_enum_from_string(self) -> None:
        assert SupportLevel("full") == SupportLevel.FULL
        assert ClientEngine("word") == ClientEngine.WORD
        assert CSSCategory("box_model") == CSSCategory.BOX_MODEL


class TestEmailClient:
    """Verify EmailClient frozen dataclass."""

    def test_construction(self) -> None:
        client = EmailClient(
            id="test_client",
            name="Test Client",
            family="test",
            platform="web",
            engine=ClientEngine.WEBKIT,
        )
        assert client.id == "test_client"
        assert client.engine == ClientEngine.WEBKIT
        assert client.market_share == 0.0
        assert client.tags == ()

    def test_frozen(self) -> None:
        client = EmailClient(
            id="test", name="Test", family="t", platform="web", engine=ClientEngine.CUSTOM
        )
        with pytest.raises(AttributeError):
            client.id = "modified"  # type: ignore[misc]


class TestCSSProperty:
    """Verify CSSProperty frozen dataclass."""

    def test_construction_with_value(self) -> None:
        prop = CSSProperty(
            id="display_flex",
            property_name="display",
            value="flex",
            category=CSSCategory.FLEXBOX,
        )
        assert prop.id == "display_flex"
        assert prop.value == "flex"
        assert prop.category == CSSCategory.FLEXBOX

    def test_construction_without_value(self) -> None:
        prop = CSSProperty(id="margin_top", property_name="margin-top")
        assert prop.value is None
        assert prop.category == CSSCategory.OTHER

    def test_frozen(self) -> None:
        prop = CSSProperty(id="test", property_name="test")
        with pytest.raises(AttributeError):
            prop.id = "modified"  # type: ignore[misc]


class TestSupportEntry:
    """Verify SupportEntry frozen dataclass."""

    def test_construction(self) -> None:
        entry = SupportEntry(
            property_id="display_flex",
            client_id="outlook_2019_win",
            level=SupportLevel.NONE,
            notes="Word engine does not support flexbox",
            workaround="Use table-based layout",
        )
        assert entry.level == SupportLevel.NONE
        assert entry.fallback_ids == ()

    def test_frozen(self) -> None:
        entry = SupportEntry(property_id="test", client_id="test", level=SupportLevel.FULL)
        with pytest.raises(AttributeError):
            entry.level = SupportLevel.NONE  # type: ignore[misc]


class TestFallback:
    """Verify Fallback frozen dataclass."""

    def test_construction(self) -> None:
        fb = Fallback(
            id="flex_to_table",
            source_property_id="display_flex",
            target_property_id="display_table",
            client_ids=("outlook_2019_win",),
            technique="table_layout",
        )
        assert fb.client_ids == ("outlook_2019_win",)
        assert fb.code_example == ""

    def test_frozen(self) -> None:
        fb = Fallback(id="test", source_property_id="a", target_property_id="b")
        with pytest.raises(AttributeError):
            fb.id = "modified"  # type: ignore[misc]
