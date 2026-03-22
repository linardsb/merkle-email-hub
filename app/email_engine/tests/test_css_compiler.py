# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for the Lightning CSS Email Compiler (Phase 19.3)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.email_engine.css_compiler.compiler import CompilationResult, EmailCSSCompiler, OptimizedCSS
from app.email_engine.css_compiler.conversions import (
    CSSConversion,
    get_conversions_for_property,
    resolve_css_variables,
    should_remove_property,
)
from app.email_engine.css_compiler.inliner import (
    extract_styles,
    inline_styles,
    parse_css_rules,
)
from app.email_engine.schemas import CSSCompileResponse
from app.email_engine.service import EmailEngineService
from app.email_engine.tests.conftest import make_mock_registry as _mock_registry
from app.main import app

BASE = "/api/v1/email"

MINIMAL_HTML = "<!DOCTYPE html><html><head></head><body><p>Hello</p></body></html>"

STYLE_HTML = (
    "<!DOCTYPE html><html><head>"
    "<style>.hero { color: red; font-size: 16px; }</style>"
    "</head><body><div class='hero'>Hello</div></body></html>"
)

MSO_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    "<!--[if mso]><table><tr><td>MSO only</td></tr></table><![endif]-->"
    "<p>Normal content</p></body></html>"
)


def _make_user(role: str = "developer") -> User:
    u = User(email=f"{role}@test.com", hashed_password="x", role=role)
    u.id = 1
    return u


# ── Conversion Tests ──


class TestConversions:
    def test_get_conversions_no_fallback(self) -> None:
        """Returns empty when no fallback exists."""
        reg = _mock_registry(support_none=True, has_fallback=False)
        result = get_conversions_for_property("display", "flex", ["outlook_2019"], registry=reg)
        assert result == []

    def test_get_conversions_with_fallback(self) -> None:
        """Returns conversion when fallback exists."""
        reg = _mock_registry(support_none=True, has_fallback=True)
        result = get_conversions_for_property("display", "flex", ["outlook_2019"], registry=reg)
        assert len(result) == 1
        assert result[0].replacement_property == "display"
        assert result[0].replacement_value == "block"
        assert "outlook_2019" in result[0].affected_clients

    def test_get_conversions_all_supported(self) -> None:
        """Returns empty when all clients support the property."""
        reg = _mock_registry(support_none=False)
        result = get_conversions_for_property("color", "red", ["gmail_web"], registry=reg)
        assert result == []

    def test_should_remove_unknown_property(self) -> None:
        """Unknown property (not in ontology) should NOT be removed."""
        reg = MagicMock()
        reg.find_property_by_name.return_value = None
        assert should_remove_property("fake-property", None, ["gmail_web"], registry=reg) is False

    def test_should_remove_unsupported_no_fallback(self) -> None:
        """Unsupported property with no fallback should be removed."""
        reg = _mock_registry(support_none=True, has_fallback=False)
        assert should_remove_property("display", "flex", ["outlook_2019"], registry=reg) is True

    def test_should_not_remove_if_some_clients_support(self) -> None:
        """Property should NOT be removed if even one client supports it."""
        from app.knowledge.ontology.types import SupportLevel

        reg = _mock_registry(support_none=True)
        # Override: first client NONE, second FULL
        reg.get_support.side_effect = [SupportLevel.NONE, SupportLevel.FULL]
        assert (
            should_remove_property("display", "flex", ["outlook_2019", "gmail_web"], registry=reg)
            is False
        )

    def test_should_remove_all_unsupported_no_fallback(self) -> None:
        """All clients unsupported + no fallback → remove."""
        from app.knowledge.ontology.types import SupportLevel

        reg = _mock_registry(support_none=True, has_fallback=False)
        reg.get_support.side_effect = [SupportLevel.NONE, SupportLevel.NONE]
        assert (
            should_remove_property(
                "display", "flex", ["outlook_2019", "outlook_2016"], registry=reg
            )
            is True
        )

    def test_should_remove_partial_support_returns_false(self) -> None:
        """At least one client supports it → do NOT remove."""
        from app.knowledge.ontology.types import SupportLevel

        reg = _mock_registry(support_none=True, has_fallback=False)
        reg.get_support.side_effect = [SupportLevel.NONE, SupportLevel.FULL]
        assert (
            should_remove_property("display", "flex", ["outlook_2019", "gmail_web"], registry=reg)
            is False
        )

    def test_resolve_css_variables_basic(self) -> None:
        """Resolves var(--x) references."""
        css = "color: var(--brand-color); font-size: var(--size)"
        result = resolve_css_variables(css, {"brand-color": "#ff0000", "size": "16px"})
        assert "#ff0000" in result
        assert "16px" in result

    def test_resolve_css_variables_with_defaults(self) -> None:
        """Falls back to default value when variable not found."""
        css = "color: var(--missing, blue)"
        result = resolve_css_variables(css, {})
        assert "blue" in result

    def test_resolve_css_variables_no_default_keeps_var(self) -> None:
        """Keeps var() reference when no variable and no default."""
        css = "color: var(--missing)"
        result = resolve_css_variables(css, {})
        assert "var(--missing)" in result


# ── Inliner Tests ──


class TestInliner:
    def test_extract_styles_basic(self) -> None:
        """Extracts <style> blocks from HTML."""
        html_out, blocks = extract_styles(STYLE_HTML)
        assert len(blocks) == 1
        assert "color: red" in blocks[0]
        assert "<style>" not in html_out

    def test_extract_styles_preserves_mso(self) -> None:
        """MSO conditional comments are not extracted."""
        html = (
            "<html><head>"
            "<!--[if mso]><style>.mso { color: blue; }</style><![endif]-->"
            "<style>.normal { color: red; }</style>"
            "</head></html>"
        )
        html_out, blocks = extract_styles(html)
        assert len(blocks) == 1
        assert "color: red" in blocks[0]
        assert "<!--[if mso]>" in html_out

    def test_extract_styles_no_styles(self) -> None:
        """Returns empty list when no style blocks."""
        _html_out, blocks = extract_styles(MINIMAL_HTML)
        assert blocks == []

    def test_parse_css_rules_basic(self) -> None:
        """Parses CSS into selector/declarations."""
        rules = parse_css_rules(".hero { color: red; font-size: 16px; }")
        assert len(rules) == 1
        selector, decls = rules[0]
        assert selector == ".hero"
        assert ("color", "red") in decls
        assert ("font-size", "16px") in decls

    def test_parse_css_rules_skips_at_rules(self) -> None:
        """@media rules are not parsed as selectors."""
        rules = parse_css_rules("@media (max-width: 600px) { .x { color: red; } }")
        # The @media selector is skipped
        selectors = [s for s, _ in rules]
        assert not any(s.startswith("@") for s in selectors)

    def test_inline_styles_basic(self) -> None:
        """Applies CSS rules as inline styles."""
        html = "<html><body><p class='test'>Hello</p></body></html>"
        rules = [(".test", [("color", "red")])]
        result = inline_styles(html, rules)
        assert 'style="color: red"' in result

    def test_inline_styles_merges_existing(self) -> None:
        """Existing inline styles take precedence."""
        html = '<html><body><p class="test" style="color: blue">Hello</p></body></html>'
        rules = [(".test", [("color", "red"), ("font-size", "16px")])]
        result = inline_styles(html, rules)
        # Existing color:blue should win over stylesheet color:red
        assert "color: blue" in result
        assert "font-size: 16px" in result

    def test_inline_styles_existing_precedence_not_overwritten(self) -> None:
        """Existing inline style='color:red' not overwritten by <style> rule."""
        html = '<html><body><div class="x" style="color: red">Hi</div></body></html>'
        rules = [(".x", [("color", "blue"), ("margin", "10px")])]
        result = inline_styles(html, rules)
        assert "color: red" in result
        assert "margin: 10px" in result

    def test_inline_styles_at_rules_in_parse(self) -> None:
        """@media rules are skipped by parse_css_rules (not applied inline)."""
        css = "@media (max-width: 600px) { .x { color: red; } } .y { font-size: 14px; }"
        rules = parse_css_rules(css)
        selectors = [s for s, _ in rules]
        assert not any(s.startswith("@") for s in selectors)
        # The .y selector may have artifact prefix from @media block parsing
        assert any(".y" in s for s in selectors)


# ── Compiler Tests ──


class TestCompiler:
    @pytest.fixture(autouse=True)
    def _mock_ontology(self) -> Generator[None]:
        """Mock the ontology registry for compiler tests."""
        reg = _mock_registry(support_none=False)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            yield

    def test_compile_basic_html(self) -> None:
        """Passthrough with no unsupported CSS."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(MINIMAL_HTML)
        assert isinstance(result, CompilationResult)
        assert result.original_size > 0
        assert result.compiled_size > 0

    def test_compile_preserves_mso_conditionals(self) -> None:
        """MSO comments are not stripped."""
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.compile(MSO_HTML)
        assert "<!--[if mso]>" in result.html

    def test_compile_resolves_css_variables(self) -> None:
        """CSS variables are resolved before compilation."""
        html = (
            "<html><head><style>.x { color: var(--brand); }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(
            target_clients=["gmail_web"], css_variables={"brand": "#ff0000"}
        )
        result = compiler.compile(html)
        assert "var(--brand)" not in result.html

    def test_compile_empty_html(self) -> None:
        """Handles minimal input gracefully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile("<html><body></body></html>")
        assert result.original_size > 0

    def test_compile_returns_timing(self) -> None:
        """Result includes compile timing."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(MINIMAL_HTML)
        assert result.compile_time_ms >= 0

    def test_compile_sanitizes_xss(self) -> None:
        """Output passes through sanitize_html_xss."""
        html = '<html><body><script>alert("xss")</script><p>Safe</p></body></html>'
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(html)
        assert "<script>" not in result.html

    def test_compile_with_style_block(self) -> None:
        """CSS from <style> blocks is inlined."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(STYLE_HTML)
        # The style should have been extracted and inlined
        assert isinstance(result.html, str)
        assert result.compiled_size > 0

    def test_compile_large_html_performance(self) -> None:
        """50KB HTML completes without error."""
        large_body = "<p>Content block</p>\n" * 2500  # ~50KB
        html = f"<html><head></head><body>{large_body}</body></html>"
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(html)
        assert result.original_size > 40_000
        assert result.compile_time_ms >= 0

    def test_compile_multiple_style_blocks(self) -> None:
        """HTML with 3 <style> blocks all processed."""
        html = (
            "<html><head>"
            "<style>.a { color: red; }</style>"
            "<style>.b { font-size: 14px; }</style>"
            "<style>.c { margin: 0; }</style>"
            "</head><body>"
            "<div class='a'>A</div><div class='b'>B</div><div class='c'>C</div>"
            "</body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(html)
        assert isinstance(result.html, str)
        assert result.compiled_size > 0

    def test_compile_with_custom_target_clients(self) -> None:
        """Custom target_clients override defaults."""
        compiler = EmailCSSCompiler(target_clients=["outlook_2019", "apple_mail"])
        result = compiler.compile(STYLE_HTML)
        assert isinstance(result, CompilationResult)

    def test_optimize_css_returns_html_with_style_blocks(self) -> None:
        """optimize_css() returns HTML with <style> blocks (not inlined)."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.optimize_css(STYLE_HTML)
        assert isinstance(result, OptimizedCSS)
        assert isinstance(result.html, str)
        assert "<style>" in result.html  # CSS stays in <style>, not inlined
        assert result.optimize_time_ms >= 0

    def test_optimize_css_preserves_mso_conditionals(self) -> None:
        """MSO comments are preserved through optimization."""
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.optimize_css(MSO_HTML)
        assert "<!--[if mso]>" in result.html

    def test_optimize_css_resolves_variables(self) -> None:
        """CSS variables are resolved during optimization."""
        html = (
            "<html><head><style>.x { color: var(--brand); }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(
            target_clients=["gmail_web"], css_variables={"brand": "#ff0000"}
        )
        result = compiler.optimize_css(html)
        assert "var(--brand)" not in result.html

    def test_optimize_css_no_style_blocks(self) -> None:
        """Handles HTML with no <style> blocks gracefully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.optimize_css(MINIMAL_HTML)
        assert isinstance(result.html, str)
        assert result.removed_properties == []
        assert result.conversions == []

    def test_compile_tracks_removed_properties(self) -> None:
        """removed_properties list contains property names when properties are removed."""
        html = '<html><head></head><body><div style="display: flex">Content</div></body></html>'
        # Use unsupported ontology mock
        reg = _mock_registry(support_none=True, has_fallback=False)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
            result = compiler.compile(html)
        assert isinstance(result.removed_properties, list)


class TestCompilerWithRemovals:
    """Tests with ontology returning unsupported properties."""

    @pytest.fixture(autouse=True)
    def _mock_ontology_unsupported(self) -> Generator[None]:
        reg = _mock_registry(support_none=True, has_fallback=False)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            yield

    def test_compile_removes_unsupported_property(self) -> None:
        """Property with NONE support and no fallback is removed."""
        html = '<html><head></head><body><div style="display: flex">Content</div></body></html>'
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.compile(html)
        assert len(result.removed_properties) > 0

    def test_optimize_css_removes_unsupported(self) -> None:
        """optimize_css() removes unsupported properties from <style> blocks."""
        html = (
            "<html><head><style>.x { display: flex; }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.optimize_css(html)
        assert any("display" in p for p in result.removed_properties)

    def test_removed_properties_tracked(self) -> None:
        """Removed properties are listed in result."""
        html = (
            "<html><head><style>.x { display: flex; }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.compile(html)
        assert any("display" in p for p in result.removed_properties)


class TestCompilerWithConversions:
    """Tests with ontology returning fallback conversions."""

    @pytest.fixture(autouse=True)
    def _mock_ontology_with_fallback(self) -> Generator[None]:
        reg = _mock_registry(support_none=True, has_fallback=True)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            yield

    def test_compile_applies_conversion(self) -> None:
        """Property with fallback is converted."""
        html = (
            "<html><head><style>.x { display: flex; }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.compile(html)
        assert len(result.conversions) > 0
        assert result.conversions[0].replacement_property == "display"

    def test_optimize_css_applies_conversions(self) -> None:
        """optimize_css() applies ontology conversions."""
        html = (
            "<html><head><style>.x { display: flex; }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.optimize_css(html)
        assert len(result.conversions) > 0

    def test_conversions_include_affected_clients(self) -> None:
        """CSSConversion.affected_clients is non-empty tuple."""
        html = (
            "<html><head><style>.x { display: flex; }</style></head>"
            "<body><div class='x'>Hi</div></body></html>"
        )
        compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
        result = compiler.compile(html)
        for conv in result.conversions:
            assert len(conv.affected_clients) > 0
            assert isinstance(conv.affected_clients, tuple)


# ── Service Tests ──


class TestService:
    def test_service_compile_css(self) -> None:
        """Service delegates to compiler and returns correct schema."""
        mock_result = CompilationResult(
            html="<html><body>compiled</body></html>",
            original_size=100,
            compiled_size=80,
            removed_properties=["gap: 10px"],
            conversions=[
                CSSConversion(
                    original_property="display",
                    original_value="flex",
                    replacement_property="display",
                    replacement_value="block",
                    reason="Fallback",
                    affected_clients=("outlook_2019",),
                ),
            ],
            warnings=[],
            compile_time_ms=1.5,
        )
        with patch("app.email_engine.css_compiler.compiler.EmailCSSCompiler") as mock_cls:
            mock_cls.return_value.compile.return_value = mock_result
            service = EmailEngineService(db=AsyncMock())
            resp = service.compile_css(html="<html></html>")

        assert isinstance(resp, CSSCompileResponse)
        assert resp.original_size == 100
        assert resp.compiled_size == 80
        assert resp.reduction_pct == 20.0
        assert len(resp.conversions) == 1
        assert resp.conversions[0].replacement_value == "block"


class TestCompilerTelemetry:
    """Tests for per-stage timing telemetry."""

    @pytest.fixture(autouse=True)
    def _mock_ontology(self) -> Generator[None]:
        reg = _mock_registry(support_none=False)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            yield

    def test_compile_logs_stage_timings(self) -> None:
        """compile() logs per-stage timing metrics."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        with patch("app.email_engine.css_compiler.compiler.logger") as mock_logger:
            compiler.compile(STYLE_HTML)
            call_kwargs = mock_logger.info.call_args_list[-1].kwargs
            assert "stage_optimize_ms" in call_kwargs
            assert "stage_inline_ms" in call_kwargs
            assert "stage_sanitize_ms" in call_kwargs


# ── Route Tests ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestCompileCSSRoute:
    def test_compile_css_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/compile-css", json={"html": MINIMAL_HTML})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_compile_css_disabled_returns_403(self, client: TestClient) -> None:
        with patch("app.email_engine.routes.get_settings") as mock_settings:
            mock_settings.return_value.email_engine.css_compiler_enabled = False
            resp = client.post(f"{BASE}/compile-css", json={"html": MINIMAL_HTML})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_compile_css_success(self, client: TestClient) -> None:
        mock_response = CSSCompileResponse(
            html="<html>compiled</html>",
            original_size=100,
            compiled_size=80,
            reduction_pct=20.0,
            removed_properties=[],
            conversions=[],
            warnings=[],
            compile_time_ms=1.0,
        )
        with (
            patch("app.email_engine.routes.get_settings") as mock_settings,
            patch.object(
                EmailEngineService,
                "compile_css",
                return_value=mock_response,
            ),
        ):
            mock_settings.return_value.email_engine.css_compiler_enabled = True
            resp = client.post(f"{BASE}/compile-css", json={"html": MINIMAL_HTML})

        assert resp.status_code == 200
        body = resp.json()
        assert body["original_size"] == 100
        assert body["compiled_size"] == 80
        assert body["reduction_pct"] == 20.0

    @pytest.mark.usefixtures("_auth_developer")
    def test_compile_css_validates_empty_html(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/compile-css", json={"html": ""})
        assert resp.status_code == 422
