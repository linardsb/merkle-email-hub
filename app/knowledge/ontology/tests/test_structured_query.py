"""Tests for OntologyQueryEngine structured compatibility queries."""

from __future__ import annotations

from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.structured_query import (
    CompatibilityAnswer,
    OntologyQueryEngine,
)
from app.knowledge.ontology.types import SupportLevel


class TestOntologyQueryEngine:
    """Tests for OntologyQueryEngine."""

    def setup_method(self) -> None:
        self.registry = load_ontology()
        self.engine = OntologyQueryEngine(self.registry)

    def test_query_known_property_all_clients(self) -> None:
        """Querying a known property returns results for all clients."""
        prop_ids = self.registry.property_ids()
        assert prop_ids, "Ontology must have properties"
        answer = self.engine.query_property_support(prop_ids[0])
        assert answer is not None
        assert isinstance(answer, CompatibilityAnswer)
        assert len(answer.client_results) == len(self.registry.clients)
        assert answer.summary

    def test_query_known_property_specific_clients(self) -> None:
        """Querying with specific client_ids filters results."""
        prop_ids = self.registry.property_ids()
        client_ids = self.registry.client_ids()[:2]
        answer = self.engine.query_property_support(prop_ids[0], client_ids=client_ids)
        assert answer is not None
        assert len(answer.client_results) == 2

    def test_query_unknown_property_returns_none(self) -> None:
        """Unknown property ID returns None."""
        answer = self.engine.query_property_support("nonexistent_property_xyz")
        assert answer is None

    def test_query_client_limitations(self) -> None:
        """Client limitations returns list of unsupported properties."""
        client_ids = self.registry.client_ids()
        assert client_ids
        # At least one client should have unsupported properties
        found_any = False
        for cid in client_ids:
            result = self.engine.query_client_limitations(cid)
            if result:
                found_any = True
                break
        assert found_any, "At least one client should have unsupported properties"

    def test_find_safe_alternatives(self) -> None:
        """find_safe_alternatives returns fallbacks for known property."""
        for prop_id in self.registry.property_ids():
            fallbacks = self.engine.find_safe_alternatives(prop_id)
            if fallbacks:
                assert all(hasattr(fb, "target_property_id") for fb in fallbacks)
                break

    def test_find_safe_alternatives_with_client_filter(self) -> None:
        """find_safe_alternatives with target_clients filters correctly."""
        for prop_id in self.registry.property_ids():
            all_fb = self.engine.find_safe_alternatives(prop_id)
            if all_fb:
                filtered = self.engine.find_safe_alternatives(
                    prop_id, target_clients=["nonexistent_client"]
                )
                # Fallbacks with no client_ids restriction pass through
                for fb in filtered:
                    assert not fb.client_ids or "nonexistent_client" in fb.client_ids
                break

    def test_format_as_search_results(self) -> None:
        """format_as_search_results returns SearchResult-compatible dicts."""
        prop_ids = self.registry.property_ids()
        answer = self.engine.query_property_support(prop_ids[0])
        assert answer is not None
        results = self.engine.format_as_search_results(answer)
        assert results
        first = results[0]
        assert "chunk_content" in first
        assert first["document_id"] == 0
        assert first["document_filename"] == "ontology"
        assert first["domain"] == "css_support"
        assert first["score"] == 1.0

    def test_format_includes_fallbacks(self) -> None:
        """format_as_search_results includes fallback entries."""
        for prop_id in self.registry.property_ids():
            answer = self.engine.query_property_support(prop_id)
            if answer and answer.fallbacks:
                results = self.engine.format_as_search_results(answer)
                # Main result + one per fallback
                assert len(results) == 1 + len(answer.fallbacks)
                break

    def test_summary_all_supported(self) -> None:
        """Summary says 'fully supported' when all clients support property."""
        for prop_id in self.registry.property_ids():
            answer = self.engine.query_property_support(prop_id)
            if answer and all(cr.level == SupportLevel.FULL for cr in answer.client_results):
                assert "fully supported" in answer.summary
                break

    def test_summary_unsupported_mentions_clients(self) -> None:
        """Summary mentions client names when some don't support."""
        for prop_id in self.registry.property_ids():
            answer = self.engine.query_property_support(prop_id)
            if answer and any(cr.level == SupportLevel.NONE for cr in answer.client_results):
                assert "not supported" in answer.summary
                break


class TestRegistryFuzzyLookup:
    """Tests for find_property_by_name and find_client_by_name."""

    def setup_method(self) -> None:
        self.registry = load_ontology()

    def test_find_property_exact_css_name(self) -> None:
        """Exact CSS name resolves to a property."""
        prop = self.registry.properties[0]
        result = self.registry.find_property_by_name(prop.property_name)
        assert result is not None
        assert result.property_name == prop.property_name

    def test_find_property_case_insensitive(self) -> None:
        """Case-insensitive lookup works."""
        prop = self.registry.properties[0]
        result = self.registry.find_property_by_name(prop.property_name.upper())
        assert result is not None

    def test_find_property_unknown_returns_none(self) -> None:
        """Unknown property name returns None."""
        assert self.registry.find_property_by_name("zzz-nonexistent") is None

    def test_find_client_exact_name(self) -> None:
        """Exact client name resolves."""
        client = self.registry.clients[0]
        result = self.registry.find_client_by_name(client.name)
        assert result is not None
        assert result.name == client.name

    def test_find_client_family_match(self) -> None:
        """Family name resolves to highest market share client."""
        client = self.registry.clients[0]
        result = self.registry.find_client_by_name(client.family)
        assert result is not None
        assert result.family == client.family

    def test_find_client_case_insensitive(self) -> None:
        """Case-insensitive client lookup works."""
        client = self.registry.clients[0]
        result = self.registry.find_client_by_name(client.name.upper())
        assert result is not None

    def test_find_client_unknown_returns_none(self) -> None:
        """Unknown client name returns None."""
        assert self.registry.find_client_by_name("ZzzNonexistentClient") is None
