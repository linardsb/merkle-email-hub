"""Tests for ontology registry loading and indexing."""

from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import (
    ClientEngine,
    CSSCategory,
    SupportLevel,
)


class TestLoadOntology:
    """Verify YAML loading produces a populated registry."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()
        self.registry = load_ontology()

    def test_client_count(self) -> None:
        assert len(self.registry.clients) >= 26

    def test_property_count(self) -> None:
        assert len(self.registry.properties) >= 300

    def test_support_entries_exist(self) -> None:
        assert len(self.registry.support_entries) > 0

    def test_fallbacks_exist(self) -> None:
        assert len(self.registry.fallbacks) > 0


class TestClientIndex:
    """Verify client lookup by ID."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()
        self.registry = load_ontology()

    def test_known_client(self) -> None:
        client = self.registry.get_client("outlook_2019_win")
        assert client is not None
        assert client.engine == ClientEngine.WORD
        assert client.family == "outlook"

    def test_new_outlook_client(self) -> None:
        client = self.registry.get_client("outlook_new_win")
        assert client is not None
        assert client.engine == ClientEngine.CUSTOM
        assert client.family == "outlook"
        assert client.platform == "windows"

    def test_unknown_client(self) -> None:
        assert self.registry.get_client("nonexistent") is None

    def test_client_ids_list(self) -> None:
        ids = self.registry.client_ids()
        assert "gmail_web" in ids
        assert "apple_mail_ios" in ids
        assert len(ids) >= 26


class TestPropertyIndex:
    """Verify property lookup by ID."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()
        self.registry = load_ontology()

    def test_known_property(self) -> None:
        prop = self.registry.get_property("display_flex")
        assert prop is not None
        assert prop.property_name == "display"
        assert prop.value == "flex"
        assert prop.category == CSSCategory.FLEXBOX

    def test_unknown_property(self) -> None:
        assert self.registry.get_property("nonexistent") is None

    def test_properties_by_category(self) -> None:
        layout_props = self.registry.properties_by_category(CSSCategory.LAYOUT)
        assert len(layout_props) > 0
        for p in layout_props:
            assert p.category == CSSCategory.LAYOUT


class TestSupportLookup:
    """Verify support matrix queries."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()
        self.registry = load_ontology()

    def test_unsupported_property(self) -> None:
        level = self.registry.get_support("display_flex", "outlook_2019_win")
        assert level == SupportLevel.NONE

    def test_default_full(self) -> None:
        level = self.registry.get_support("display_block", "apple_mail_macos")
        assert level == SupportLevel.FULL

    def test_clients_not_supporting_flex(self) -> None:
        clients = self.registry.clients_not_supporting("display_flex")
        client_ids = [c.id for c in clients]
        assert "outlook_2019_win" in client_ids
        assert "outlook_365_win" in client_ids

    def test_properties_unsupported_by_outlook(self) -> None:
        props = self.registry.properties_unsupported_by("outlook_2019_win")
        prop_ids = [p.id for p in props]
        assert "display_flex" in prop_ids
        assert len(props) > 10


class TestFallbackLookup:
    """Verify fallback queries."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()
        self.registry = load_ontology()

    def test_fallbacks_for_flex(self) -> None:
        fallbacks = self.registry.fallbacks_for("display_flex")
        assert len(fallbacks) > 0

    def test_no_fallbacks_for_block(self) -> None:
        fallbacks = self.registry.fallbacks_for("display_block")
        assert len(fallbacks) == 0


class TestCaching:
    """Verify lru_cache returns same instance."""

    def test_same_instance(self) -> None:
        load_ontology.cache_clear()
        r1 = load_ontology()
        r2 = load_ontology()
        assert r1 is r2
