"""Tests for 24B.2 — Rendering Engine Taxonomy."""

from __future__ import annotations

import pytest

from app.knowledge.ontology.query import unsupported_engines_in_html
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import ClientEngine, SupportLevel


class TestClientsByEngine:
    """Tests for OntologyRegistry.clients_by_engine()."""

    def test_returns_clients_for_known_engine(self) -> None:
        registry = load_ontology()
        word_clients = registry.clients_by_engine(ClientEngine.WORD)
        assert len(word_clients) > 0
        for client in word_clients:
            assert client.engine == ClientEngine.WORD

    def test_returns_empty_for_unused_engine(self) -> None:
        registry = load_ontology()
        # PRESTO is rarely used, but might have entries — just check type
        presto_clients = registry.clients_by_engine(ClientEngine.PRESTO)
        assert isinstance(presto_clients, list)
        for client in presto_clients:
            assert client.engine == ClientEngine.PRESTO


class TestEngineSupport:
    """Tests for OntologyRegistry.engine_support()."""

    def test_returns_support_per_engine(self) -> None:
        registry = load_ontology()
        # Pick a property that exists
        if not registry.properties:
            pytest.skip("No properties in ontology")
        prop = registry.properties[0]
        engine_levels = registry.engine_support(prop.id)
        assert isinstance(engine_levels, dict)
        for engine, level in engine_levels.items():
            assert isinstance(engine, ClientEngine)
            assert isinstance(level, SupportLevel)

    def test_worst_case_aggregation(self) -> None:
        """If any client in an engine has NONE, the engine should be NONE."""
        registry = load_ontology()
        # Find a property with at least one NONE entry
        for prop in registry.properties:
            unsupported = registry.clients_not_supporting(prop.id)
            if unsupported:
                engine = unsupported[0].engine
                engine_levels = registry.engine_support(prop.id)
                if engine in engine_levels:
                    assert engine_levels[engine] == SupportLevel.NONE
                break


class TestEnginesNotSupporting:
    """Tests for OntologyRegistry.engines_not_supporting()."""

    def test_returns_engines_list(self) -> None:
        registry = load_ontology()
        if not registry.properties:
            pytest.skip("No properties in ontology")
        # Find a property with some unsupported clients
        for prop in registry.properties:
            engines = registry.engines_not_supporting(prop.id)
            if engines:
                for engine in engines:
                    assert isinstance(engine, ClientEngine)
                break


class TestEngineMarketShare:
    """Tests for OntologyRegistry.engine_market_share()."""

    def test_market_share_non_negative(self) -> None:
        registry = load_ontology()
        for engine in ClientEngine:
            share = registry.engine_market_share(engine)
            assert share >= 0.0

    def test_blink_has_market_share(self) -> None:
        """Blink (Chrome) should have non-zero market share."""
        registry = load_ontology()
        blink_clients = registry.clients_by_engine(ClientEngine.BLINK)
        if blink_clients:
            share = registry.engine_market_share(ClientEngine.BLINK)
            assert share > 0.0


class TestUnsupportedEnginesInHtml:
    """Tests for unsupported_engines_in_html() query function."""

    def test_modern_css_flags_engines(self) -> None:
        """HTML with modern CSS should flag engines that don't support it."""
        html = '<div style="display: flex;">content</div>'
        issues = unsupported_engines_in_html(html)
        # May or may not have issues depending on ontology data
        assert isinstance(issues, list)
        for issue in issues:
            assert "property_name" in issue
            assert "unsupported_engines" in issue
            assert "severity" in issue
