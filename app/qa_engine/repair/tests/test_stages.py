"""Unit tests for individual repair stages."""

from app.qa_engine.repair.accessibility import AccessibilityRepair
from app.qa_engine.repair.dark_mode import DarkModeRepair
from app.qa_engine.repair.links import LinkRepair
from app.qa_engine.repair.mso import MSORepair
from app.qa_engine.repair.personalisation import PersonalisationRepair
from app.qa_engine.repair.size import SizeRepair
from app.qa_engine.repair.structure import StructureRepair


class TestStructureRepair:
    def test_adds_missing_doctype(self) -> None:
        stage = StructureRepair()
        result = stage.repair("<html><head></head><body>hi</body></html>")
        assert result.html.startswith("<!DOCTYPE html>")
        assert "added_doctype" in result.repairs_applied

    def test_adds_missing_head(self) -> None:
        stage = StructureRepair()
        result = stage.repair("<!DOCTYPE html>\n<html><body>hi</body></html>")
        assert "<head></head>" in result.html
        assert "added_head" in result.repairs_applied

    def test_adds_missing_body(self) -> None:
        stage = StructureRepair()
        result = stage.repair("<!DOCTYPE html>\n<html><head></head>content</html>")
        assert "<body>" in result.html
        assert "</body>" in result.html
        assert "added_body" in result.repairs_applied

    def test_no_changes_on_complete_html(self) -> None:
        complete = "<!DOCTYPE html>\n<html><head></head><body>hi</body></html>"
        stage = StructureRepair()
        result = stage.repair(complete)
        assert result.repairs_applied == []

    def test_idempotent(self) -> None:
        stage = StructureRepair()
        html = "<p>bare content</p>"
        result1 = stage.repair(html)
        result2 = stage.repair(result1.html)
        assert result2.repairs_applied == []
        assert result1.html == result2.html


class TestMSORepair:
    def test_no_op_on_valid_html(self) -> None:
        stage = MSORepair()
        result = stage.repair("<html><body>no mso</body></html>")
        assert result.repairs_applied == []

    def test_repairs_unbalanced_conditionals(self) -> None:
        stage = MSORepair()
        html = "<html><body><!--[if mso]><p>outlook</p></body></html>"
        result = stage.repair(html)
        assert "<![endif]-->" in result.html


class TestDarkModeRepair:
    def test_injects_meta_tags(self) -> None:
        stage = DarkModeRepair()
        html = "<!DOCTYPE html><html><head><style>body{}</style></head><body>hi</body></html>"
        result = stage.repair(html)
        assert "color-scheme" in result.html

    def test_injects_media_query(self) -> None:
        stage = DarkModeRepair()
        html = (
            "<!DOCTYPE html><html><head>"
            '<meta name="color-scheme" content="light dark">'
            '<meta name="supported-color-schemes" content="light dark">'
            "<style>body{}</style></head><body>hi</body></html>"
        )
        result = stage.repair(html)
        assert "prefers-color-scheme" in result.html
        assert "media_query_placeholder" in result.repairs_applied

    def test_idempotent(self) -> None:
        stage = DarkModeRepair()
        html = (
            "<!DOCTYPE html><html><head>"
            '<meta name="color-scheme" content="light dark">'
            '<meta name="supported-color-schemes" content="light dark">'
            "<style>@media (prefers-color-scheme: dark) { body {} }</style>"
            "</head><body>hi</body></html>"
        )
        result = stage.repair(html)
        assert result.repairs_applied == []


class TestAccessibilityRepair:
    def test_adds_lang(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair("<html><body>hi</body></html>")
        assert 'lang="en"' in result.html
        assert "added_lang" in result.repairs_applied

    def test_preserves_existing_lang(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair('<html lang="fr"><body>hi</body></html>')
        assert 'lang="fr"' in result.html
        assert "added_lang" not in result.repairs_applied

    def test_adds_role_presentation(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair(
            "<html lang='en'><body><table><tr><td>layout</td></tr></table></body></html>"
        )
        assert 'role="presentation"' in result.html

    def test_preserves_existing_role(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair(
            '<html lang="en"><body><table role="grid"><tr><td>data</td></tr></table></body></html>'
        )
        assert 'role="grid"' in result.html
        assert 'role="presentation"' not in result.html

    def test_skips_data_content_tables(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair(
            '<html lang="en"><body>'
            '<table data-content="true"><tr><td>data</td></tr></table>'
            "</body></html>"
        )
        assert 'role="presentation"' not in result.html

    def test_adds_empty_alt(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair('<html lang="en"><body><img src="logo.png"></body></html>')
        assert 'alt=""' in result.html

    def test_preserves_existing_alt(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair('<html lang="en"><body><img src="logo.png" alt="Logo"></body></html>')
        assert 'alt="Logo"' in result.html
        assert not any("alt" in r for r in result.repairs_applied)

    def test_adds_scope_to_th(self) -> None:
        stage = AccessibilityRepair()
        result = stage.repair(
            '<html lang="en"><body><table data-content="true"><tr><th>Header</th></tr></table></body></html>'
        )
        assert 'scope="col"' in result.html


class TestPersonalisationRepair:
    def test_warns_on_imbalanced_liquid(self) -> None:
        stage = PersonalisationRepair()
        result = stage.repair("<p>Hello {{ first_name</p>")
        assert any("imbalanced" in w for w in result.warnings)

    def test_no_warning_on_balanced(self) -> None:
        stage = PersonalisationRepair()
        result = stage.repair("<p>Hello {{ first_name }}</p>")
        assert result.warnings == []

    def test_warns_on_imbalanced_ampscript(self) -> None:
        stage = PersonalisationRepair()
        result = stage.repair("<p>%%[ SET @name = 'test'</p>")
        assert any("AMPscript" in w for w in result.warnings)

    def test_no_warning_on_balanced_ampscript(self) -> None:
        stage = PersonalisationRepair()
        result = stage.repair("<p>%%[ SET @name = 'test' ]%%</p>")
        assert result.warnings == []

    def test_no_warning_without_delimiters(self) -> None:
        stage = PersonalisationRepair()
        result = stage.repair("<p>plain text</p>")
        assert result.warnings == []


class TestSizeRepair:
    def test_strips_comments_except_mso(self) -> None:
        stage = SizeRepair()
        html = "<html><!-- comment --><body><!--[if mso]>mso<![endif]--></body></html>"
        result = stage.repair(html)
        assert "<!-- comment -->" not in result.html
        assert "<!--[if mso]>" in result.html
        assert "stripped_comments" in result.repairs_applied

    def test_removes_empty_style(self) -> None:
        stage = SizeRepair()
        result = stage.repair('<td style="">content</td>')
        assert 'style=""' not in result.html
        assert "removed_empty_styles" in result.repairs_applied

    def test_no_op_on_clean_html(self) -> None:
        stage = SizeRepair()
        result = stage.repair("<html><body>clean</body></html>")
        assert result.repairs_applied == []

    def test_preserves_mso_endif(self) -> None:
        stage = SizeRepair()
        html = "<!--[if gte mso 9]><xml><![endif]-->"
        result = stage.repair(html)
        assert "<!--[if gte mso 9]>" in result.html


class TestLinkRepair:
    def test_fixes_empty_href(self) -> None:
        stage = LinkRepair()
        result = stage.repair('<a href="">link</a>')
        assert 'href="#"' in result.html
        assert "fixed_empty_hrefs" in result.repairs_applied

    def test_warns_on_javascript_href(self) -> None:
        stage = LinkRepair()
        result = stage.repair('<a href="javascript:void(0)">link</a>')
        assert any("javascript" in w for w in result.warnings)

    def test_skips_template_variables(self) -> None:
        stage = LinkRepair()
        result = stage.repair('<a href="{{ cta_url }}">link</a>')
        assert result.warnings == []

    def test_warns_on_invalid_scheme(self) -> None:
        stage = LinkRepair()
        result = stage.repair('<a href="ftp://files.example.com">link</a>')
        assert any("invalid_scheme" in w for w in result.warnings)

    def test_accepts_valid_schemes(self) -> None:
        stage = LinkRepair()
        html = (
            '<a href="https://example.com">link</a>'
            '<a href="mailto:test@example.com">email</a>'
            '<a href="tel:+1234567890">call</a>'
        )
        result = stage.repair(html)
        assert result.warnings == []
        assert result.repairs_applied == []

    def test_fixes_single_quoted_empty_href(self) -> None:
        stage = LinkRepair()
        result = stage.repair("<a href=''>link</a>")
        assert 'href="#"' in result.html
        assert "fixed_empty_hrefs" in result.repairs_applied

    def test_warns_on_single_quoted_javascript(self) -> None:
        stage = LinkRepair()
        result = stage.repair("<a href='javascript:void(0)'>link</a>")
        assert any("javascript" in w for w in result.warnings)

    def test_validates_single_quoted_href_scheme(self) -> None:
        stage = LinkRepair()
        result = stage.repair("<a href='ftp://files.example.com'>link</a>")
        assert any("invalid_scheme" in w for w in result.warnings)
