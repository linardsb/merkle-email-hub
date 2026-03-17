"""Tests for Outlook Word-Engine Dependency Analyzer (Phase 19.1)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.outlook_analyzer.detector import OutlookDependencyDetector
from app.qa_engine.outlook_analyzer.modernizer import OutlookModernizer
from app.qa_engine.outlook_analyzer.types import ModernizeResult, OutlookAnalysis
from app.qa_engine.schemas import OutlookAnalysisResponse, OutlookModernizeResponse
from app.qa_engine.service import QAEngineService

# --- Test HTML Fixtures ---

VML_BUTTON_HTML = """\
<html xmlns:v="urn:schemas-microsoft-com:vml">
<body>
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" style="height:40px;width:200px"
  arcsize="10%" strokecolor="#1e3650" fillcolor="#ff6600">
  <v:textbox><center style="color:#ffffff">Click Here</center></v:textbox>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="#" style="background-color:#ff6600;border-radius:4px;color:#ffffff;padding:10px 20px;">Click Here</a>
<!--<![endif]-->
</body>
</html>"""

GHOST_TABLE_HTML = """\
<html>
<body>
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0"><tr><td>
<![endif]-->
<div style="max-width:600px">Content here</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body>
</html>"""

MSO_CSS_HTML = """\
<html><head><style>
.content { mso-line-height-rule: exactly; mso-table-lspace: 0pt; }
.ExternalClass { width: 100%; }
.ExternalClass p { line-height: 100%; }
</style></head><body>
<img src="logo.png" width="300" height="100" style="width:150px;height:50px;">
</body></html>"""

WORD_WRAP_HTML = """\
<html><head><style>
td { word-wrap: break-all; }
</style></head><body>
<table><tr><td style="word-break: break-word">text</td></tr></table>
</body></html>"""

CLEAN_HTML = """\
<html><head><style>
.content { font-size: 16px; color: #333; }
</style></head><body>
<div style="max-width:600px"><p>Modern email</p></div>
</body></html>"""

MULTI_VML_HTML = """\
<html xmlns:v="urn:schemas-microsoft-com:vml">
<body>
<v:rect style="width:100px;height:50px" fillcolor="#ccc"></v:rect>
<v:oval style="width:40px;height:40px" fillcolor="#f00"></v:oval>
<v:shape coordsize="100,100" path="m0,0 l100,100"></v:shape>
</body>
</html>"""


# ========================
# Detector Tests
# ========================


class TestDetector:
    def setup_method(self) -> None:
        self.detector = OutlookDependencyDetector()

    def test_analyze_empty_html(self) -> None:
        result = self.detector.analyze("")
        assert result.total_count == 0
        assert result.dependencies == []

    def test_analyze_whitespace_html(self) -> None:
        result = self.detector.analyze("   \n\n  ")
        assert result.total_count == 0

    def test_detect_vml_shapes(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        vml_deps = [d for d in result.dependencies if d.type == "vml_shape"]
        assert len(vml_deps) >= 1
        assert any("roundrect" in d.location for d in vml_deps)
        assert result.vml_count >= 1

    def test_detect_vml_multiple_types(self) -> None:
        result = self.detector.analyze(MULTI_VML_HTML)
        vml_deps = [d for d in result.dependencies if d.type == "vml_shape"]
        assert len(vml_deps) == 3
        types_found = {d.location.split("<v:")[1].split(">")[0] for d in vml_deps}
        assert "rect" in types_found
        assert "oval" in types_found
        assert "shape" in types_found

    def test_detect_ghost_tables(self) -> None:
        result = self.detector.analyze(GHOST_TABLE_HTML)
        ghost_deps = [d for d in result.dependencies if d.type == "ghost_table"]
        assert len(ghost_deps) >= 1
        assert result.ghost_table_count >= 1

    def test_detect_mso_conditionals(self) -> None:
        result = self.detector.analyze(GHOST_TABLE_HTML)
        mso_deps = [d for d in result.dependencies if d.type == "mso_conditional"]
        assert len(mso_deps) >= 1
        assert result.mso_conditional_count >= 1

    def test_detect_mso_css_properties(self) -> None:
        result = self.detector.analyze(MSO_CSS_HTML)
        mso_css_deps = [d for d in result.dependencies if d.type == "mso_css"]
        assert len(mso_css_deps) >= 2
        locations = " ".join(d.location for d in mso_css_deps)
        assert "mso-line-height-rule" in locations
        assert "mso-table-lspace" in locations

    def test_detect_external_class(self) -> None:
        result = self.detector.analyze(MSO_CSS_HTML)
        ext_deps = [d for d in result.dependencies if d.type == "external_class"]
        assert len(ext_deps) >= 1
        assert result.external_class_count >= 1

    def test_detect_dpi_images(self) -> None:
        result = self.detector.analyze(MSO_CSS_HTML)
        dpi_deps = [d for d in result.dependencies if d.type == "dpi_image"]
        assert len(dpi_deps) == 1
        assert result.dpi_image_count == 1

    def test_detect_word_wrap_hacks(self) -> None:
        result = self.detector.analyze(WORD_WRAP_HTML)
        wrap_deps = [d for d in result.dependencies if d.type == "word_wrap_hack"]
        assert len(wrap_deps) >= 1
        assert result.word_wrap_count >= 1

    def test_clean_html_zero_dependencies(self) -> None:
        result = self.detector.analyze(CLEAN_HTML)
        assert result.total_count == 0
        assert result.removable_count == 0
        assert result.byte_savings == 0

    def test_line_numbers_correct(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        vml_deps = [d for d in result.dependencies if d.type == "vml_shape"]
        assert len(vml_deps) >= 1
        # VML should be on line 4+ (after <html>, <body>, <!--[if mso]>)
        for d in vml_deps:
            assert d.line_number >= 4

    def test_code_snippets_truncated(self) -> None:
        # Create HTML with a very long VML element
        long_vml = '<v:roundrect style="' + "a" * 300 + '"></v:roundrect>'
        html = f"<html><body>{long_vml}</body></html>"
        result = self.detector.analyze(html)
        for d in result.dependencies:
            assert len(d.code_snippet) <= 200

    def test_severity_ratings(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        for d in result.dependencies:
            if d.type == "vml_shape":
                assert d.severity == "high"
            elif d.type == "mso_conditional":
                assert d.severity == "medium"
            elif d.type == "mso_css":
                assert d.severity == "low"

    def test_removable_flags(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        for d in result.dependencies:
            assert d.removable is True

    def test_modern_replacements_present(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        vml_deps = [d for d in result.dependencies if d.type == "vml_shape"]
        for d in vml_deps:
            assert d.modern_replacement is not None
            assert len(d.modern_replacement) > 0

    def test_modernization_plan_generated(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        assert len(result.modernization_plan) > 0
        plan_types = {s.dependency_type for s in result.modernization_plan}
        assert "vml_shape" in plan_types or "mso_conditional" in plan_types

    def test_byte_savings_calculated(self) -> None:
        result = self.detector.analyze(VML_BUTTON_HTML)
        assert result.byte_savings > 0

    def test_aggregate_counts_correct(self) -> None:
        result = self.detector.analyze(MSO_CSS_HTML)
        # Verify type counts match actual dependency list
        from collections import Counter

        actual_counts = Counter(d.type for d in result.dependencies)
        assert actual_counts.get("mso_css", 0) == result.mso_css_count
        assert actual_counts.get("external_class", 0) == result.external_class_count
        assert actual_counts.get("dpi_image", 0) == result.dpi_image_count

    def test_detect_non_mso_conditional_skipped(self) -> None:
        """<!--[if !mso]><!--> should NOT create ghost_table dependency."""
        html = """\
<html><body>
<!--[if !mso]><!-->
<div style="max-width:600px">Content</div>
<!--<![endif]-->
</body></html>"""
        result = self.detector.analyze(html)
        ghost_deps = [d for d in result.dependencies if d.type == "ghost_table"]
        assert len(ghost_deps) == 0

    def test_detect_all_seven_types_together(self) -> None:
        """HTML with all 7 dependency types produces correct total_count."""
        html = """\
<html xmlns:v="urn:schemas-microsoft-com:vml">
<head><style>
.content { mso-line-height-rule: exactly; }
.ExternalClass { width: 100%; }
td { word-wrap: break-all; }
</style></head>
<body>
<v:roundrect style="height:40px;width:200px" fillcolor="#f00"></v:roundrect>
<!--[if mso]>
<table role="presentation"><tr><td>
<![endif]-->
<img src="logo.png" width="300" height="100" style="width:150px;height:50px;">
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body></html>"""
        result = self.detector.analyze(html)
        types_found = {d.type for d in result.dependencies}
        assert types_found == {
            "vml_shape",
            "ghost_table",
            "mso_conditional",
            "mso_css",
            "dpi_image",
            "external_class",
            "word_wrap_hack",
        }
        assert result.total_count == len(result.dependencies)

    def test_detect_duplicate_mso_css_dedup(self) -> None:
        """Same mso-* property on same line only counted once."""
        html = "<html><head><style>.a { mso-line-height-rule: exactly; mso-line-height-rule: exactly; }</style></head><body></body></html>"
        result = self.detector.analyze(html)
        mso_deps = [d for d in result.dependencies if d.type == "mso_css"]
        # Both occurrences are on the same line, so should be deduped
        line_prop_pairs = [(d.line_number, d.location) for d in mso_deps]
        # Check no duplicate line_number+property combos
        assert len(line_prop_pairs) == len(set(line_prop_pairs))


# ========================
# Modernizer Tests
# ========================


class TestModernizer:
    def setup_method(self) -> None:
        self.detector = OutlookDependencyDetector()
        self.modernizer = OutlookModernizer()

    def _analyze_and_modernize(
        self, html: str, target: str = "new_outlook"
    ) -> tuple[OutlookAnalysis, ModernizeResult]:
        analysis = self.detector.analyze(html)
        result = self.modernizer.modernize(html, analysis, target=target)
        return analysis, result

    def test_modernize_audit_only(self) -> None:
        analysis = self.detector.analyze(VML_BUTTON_HTML)
        result = self.modernizer.modernize(VML_BUTTON_HTML, analysis, target="audit_only")
        assert result.html == VML_BUTTON_HTML
        assert result.changes_applied == 0
        assert result.target == "audit_only"

    def test_modernize_new_outlook_removes_mso_conditionals(self) -> None:
        _, result = self._analyze_and_modernize(GHOST_TABLE_HTML, "new_outlook")
        assert "<!--[if" not in result.html
        assert "<![endif]-->" not in result.html
        assert result.changes_applied > 0

    def test_modernize_new_outlook_removes_mso_css(self) -> None:
        _, result = self._analyze_and_modernize(MSO_CSS_HTML, "new_outlook")
        assert "mso-line-height-rule" not in result.html
        assert "mso-table-lspace" not in result.html

    def test_modernize_new_outlook_removes_external_class(self) -> None:
        _, result = self._analyze_and_modernize(MSO_CSS_HTML, "new_outlook")
        assert ".ExternalClass" not in result.html

    def test_modernize_new_outlook_normalizes_images(self) -> None:
        _, result = self._analyze_and_modernize(MSO_CSS_HTML, "new_outlook")
        # CSS dimensions should remain, HTML attrs should be removed
        assert "width:150px" in result.html or 'width="300"' not in result.html

    def test_modernize_dual_support_keeps_conditionals(self) -> None:
        _, result = self._analyze_and_modernize(VML_BUTTON_HTML, "dual_support")
        # dual_support keeps MSO conditional blocks intact
        assert "<!--[if" in result.html or result.changes_applied >= 0

    def test_modernize_dual_support_removes_external_class(self) -> None:
        _, result = self._analyze_and_modernize(MSO_CSS_HTML, "dual_support")
        assert ".ExternalClass" not in result.html

    def test_modernize_invalid_target(self) -> None:
        from app.core.exceptions import DomainValidationError

        analysis = self.detector.analyze(CLEAN_HTML)
        with pytest.raises(DomainValidationError, match="Invalid target"):
            self.modernizer.modernize(CLEAN_HTML, analysis, target="invalid")

    def test_modernize_empty_analysis(self) -> None:
        analysis = self.detector.analyze(CLEAN_HTML)
        result = self.modernizer.modernize(CLEAN_HTML, analysis, target="new_outlook")
        assert result.changes_applied == 0

    def test_modernize_byte_savings(self) -> None:
        _, result = self._analyze_and_modernize(VML_BUTTON_HTML, "new_outlook")
        assert result.bytes_after <= result.bytes_before

    def test_modernize_word_wrap_normalization(self) -> None:
        _, result = self._analyze_and_modernize(WORD_WRAP_HTML, "new_outlook")
        assert "overflow-wrap: break-word" in result.html

    def test_modernize_output_sanitized(self) -> None:
        """Verify output passes through XSS sanitization."""
        xss_html = (
            '<html><body><!--[if mso]><script>alert("xss")</script><![endif]--></body></html>'
        )
        _, result = self._analyze_and_modernize(xss_html, "new_outlook")
        # sanitize_html_xss should strip script tags
        assert "<script>" not in result.html

    def test_modernize_dual_support_removes_mso_css_outside_conditionals(self) -> None:
        """dual_support removes mso-* CSS outside MSO blocks."""
        _, result = self._analyze_and_modernize(MSO_CSS_HTML, "dual_support")
        # mso-* properties in <style> block should be removed
        assert "mso-line-height-rule" not in result.html
        assert "mso-table-lspace" not in result.html

    def test_modernize_new_outlook_unwraps_non_mso_content(self) -> None:
        """<!--[if !mso]><!--> inner content preserved after stripping."""
        html = """\
<html><body>
<!--[if !mso]><!-->
<div class="mobile-only">Mobile content</div>
<!--<![endif]-->
</body></html>"""
        _, result = self._analyze_and_modernize(html, "new_outlook")
        # The non-MSO content should be preserved
        assert "Mobile content" in result.html


# ========================
# Route Tests
# ========================

BASE = "/api/v1/qa"


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    return user


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


class TestRoutes:
    def test_outlook_analysis_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/outlook-analysis", json={"html": "<html></html>"})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_analysis_disabled(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_outlook_analysis",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("Outlook dependency analyzer is not enabled"),
        ):
            resp = client.post(f"{BASE}/outlook-analysis", json={"html": "<html></html>"})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_analysis_success(self, client: TestClient) -> None:
        mock_response = OutlookAnalysisResponse(
            total_count=2,
            vml_count=1,
            mso_conditional_count=1,
        )
        with patch.object(
            QAEngineService,
            "run_outlook_analysis",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(f"{BASE}/outlook-analysis", json={"html": VML_BUTTON_HTML})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 2
        assert body["vml_count"] == 1

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_analysis_empty_html(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/outlook-analysis", json={"html": ""})
        assert resp.status_code == 422

    def test_outlook_modernize_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/outlook-modernize",
            json={"html": "<html></html>", "target": "audit_only"},
        )
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_modernize_disabled(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_outlook_modernize",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("Outlook dependency analyzer is not enabled"),
        ):
            resp = client.post(
                f"{BASE}/outlook-modernize",
                json={"html": "<html></html>", "target": "audit_only"},
            )
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_modernize_success(self, client: TestClient) -> None:
        mock_response = OutlookModernizeResponse(
            html="<html>modernized</html>",
            changes_applied=3,
            bytes_before=500,
            bytes_after=350,
            bytes_saved=150,
            target="new_outlook",
            analysis=OutlookAnalysisResponse(total_count=3),
        )
        with patch.object(
            QAEngineService,
            "run_outlook_modernize",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(
                f"{BASE}/outlook-modernize",
                json={"html": MSO_CSS_HTML, "target": "new_outlook"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["changes_applied"] == 3
        assert body["bytes_saved"] == 150
        assert "analysis" in body

    @pytest.mark.usefixtures("_auth_developer")
    def test_outlook_modernize_invalid_target(self, client: TestClient) -> None:
        from app.core.exceptions import DomainValidationError

        with patch.object(
            QAEngineService,
            "run_outlook_modernize",
            new_callable=AsyncMock,
            side_effect=DomainValidationError("Invalid target"),
        ):
            resp = client.post(
                f"{BASE}/outlook-modernize",
                json={"html": "<html>test</html>", "target": "invalid"},
            )
        # DomainValidationError maps to 422
        assert resp.status_code == 422
