"""Tests for the HtmlImportAdapter — E2E and route tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.design_sync.email_design_document import EmailDesignDocument
from app.design_sync.exceptions import HtmlImportError
from app.design_sync.html_import.adapter import HtmlImportAdapter

_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "ai" / "templates" / "library"


def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / f"{name}.html").read_text()


# ── Adapter E2E tests ──────────────────────────────────────────────


class TestHtmlImportAdapter:
    @pytest.mark.asyncio
    async def test_promotional_hero_valid_document(self) -> None:
        html = _load_template("promotional_hero")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert isinstance(doc, EmailDesignDocument)
        assert doc.version == "1.0"
        assert len(doc.sections) >= 3
        assert doc.source is not None
        assert doc.source.provider == "html"

    @pytest.mark.asyncio
    async def test_newsletter_2col_parses(self) -> None:
        html = _load_template("newsletter_2col")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert len(doc.sections) >= 2

    @pytest.mark.asyncio
    async def test_minimal_text_parses(self) -> None:
        html = _load_template("minimal_text")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert len(doc.sections) >= 1

    @pytest.mark.asyncio
    async def test_transactional_receipt_parses(self) -> None:
        html = _load_template("transactional_receipt")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert len(doc.sections) >= 2

    @pytest.mark.asyncio
    async def test_schema_validation_passes(self) -> None:
        html = _load_template("promotional_hero")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        doc_json = doc.to_json()
        errors = EmailDesignDocument.validate(doc_json)
        assert errors == [], f"Schema validation errors: {errors}"

    @pytest.mark.asyncio
    async def test_size_limit_exceeded(self) -> None:
        adapter = HtmlImportAdapter()
        oversized = "x" * (3 * 1024 * 1024)
        with pytest.raises(HtmlImportError, match="exceeds maximum size"):
            await adapter.parse(oversized, use_ai=False)

    @pytest.mark.asyncio
    async def test_empty_html_raises(self) -> None:
        adapter = HtmlImportAdapter()
        with pytest.raises(HtmlImportError, match="empty"):
            await adapter.parse("", use_ai=False)

    @pytest.mark.asyncio
    async def test_source_name_propagation(self) -> None:
        html = _load_template("minimal_text")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False, source_name="test-import.html")

        assert doc.source is not None
        assert doc.source.file_ref == "test-import.html"

    @pytest.mark.asyncio
    async def test_tokens_populated(self) -> None:
        html = _load_template("promotional_hero")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert len(doc.tokens.colors) >= 1

    @pytest.mark.asyncio
    async def test_container_width_detected(self) -> None:
        html = _load_template("promotional_hero")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert doc.layout.container_width >= 580

    @pytest.mark.asyncio
    async def test_malformed_html_best_effort(self) -> None:
        html = "<html><body><table width='600'><tr><td><p>Unclosed"
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        assert isinstance(doc, EmailDesignDocument)

    @pytest.mark.asyncio
    async def test_roundtrip_json_serialization(self) -> None:
        html = _load_template("promotional_hero")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        # Roundtrip through JSON
        doc_json = doc.to_json()
        restored = EmailDesignDocument.from_json(doc_json)
        assert len(restored.sections) == len(doc.sections)
        assert restored.version == doc.version

    @pytest.mark.asyncio
    async def test_ai_disabled_no_classification_confidence(self) -> None:
        html = _load_template("minimal_text")
        adapter = HtmlImportAdapter()
        with patch.object(adapter, "_resolve_ai_enabled", return_value=False):
            doc = await adapter.parse(html, use_ai=False)

        # AI-classified sections would have confidence; heuristic-only won't
        ai_sections = [s for s in doc.sections if s.classification_confidence is not None]
        assert len(ai_sections) == 0


# ── Route tests ────────────────────────────────────────────────────


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    return user


class TestHtmlImportRoute:
    @pytest.fixture()
    def client(self) -> Iterator[TestClient]:
        from app.auth.dependencies import get_current_user
        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        yield TestClient(app)
        app.dependency_overrides.clear()
        limiter.enabled = True

    def test_import_html_success(self, client: TestClient) -> None:
        html = _load_template("minimal_text")
        resp = client.post(
            "/api/v1/design-sync/import/html",
            json={"html": html, "use_ai": False},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "document" in body
        assert body["section_count"] >= 1
        assert "ai_sections_classified" in body
        assert "warnings" in body

    def test_import_html_missing_field(self, client: TestClient) -> None:
        resp = client.post("/api/v1/design-sync/import/html", json={})
        assert resp.status_code == 422

    def test_import_html_empty_html(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/design-sync/import/html",
            json={"html": "", "use_ai": False},
        )
        assert resp.status_code == 422

    def test_import_html_unauthenticated(self) -> None:
        from app.core.rate_limit import limiter
        from app.main import app

        limiter.enabled = False
        # No dependency override → auth required
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/design-sync/import/html",
                json={"html": "<html></html>"},
            )
            assert resp.status_code in (401, 403)
        limiter.enabled = True
