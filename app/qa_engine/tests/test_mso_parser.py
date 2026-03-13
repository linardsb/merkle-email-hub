# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Unit tests for the MSO conditional comment parser."""

from app.qa_engine.mso_parser import validate_mso_conditionals


def _full_mso_html(
    *,
    namespaces: bool = True,
    conditionals: str = '<!--[if mso]><table width="600"><tr><td><![endif]-->',
    closers: str = "<!--[if mso]></td></tr></table><![endif]-->",
    vml: str = "",
    dpi: str = "<!--[if mso]><xml><o:OfficeDocumentSettings>"
    "<o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->",
    extra_head: str = "",
    extra_body: str = "",
) -> str:
    """Build a full MSO HTML document for testing."""
    ns = (
        ' xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"'
        if namespaces
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"{ns}>
<head>
<meta charset="utf-8">
{dpi}
{extra_head}
</head>
<body>
{conditionals}
<p>Content</p>
{closers}
{vml}
{extra_body}
</body>
</html>"""


class TestValidMSOHtml:
    def test_valid_complete_mso_html(self):
        """Full valid MSO HTML with balanced conditionals, namespaces, DPI fix."""
        html = _full_mso_html()
        result = validate_mso_conditionals(html)
        assert result.is_valid
        assert result.opener_count >= 2
        assert result.closer_count >= 2

    def test_non_mso_block_balanced(self):
        """<!--[if !mso]><!-->...<!--<![endif]--> correctly paired."""
        html = _full_mso_html(
            extra_body="<!--[if !mso]><!--><p>Non-Outlook content</p><!--<![endif]-->"
        )
        result = validate_mso_conditionals(html)
        assert result.is_valid

    def test_complex_nested_conditionals(self):
        """Multiple balanced blocks with different conditions."""
        html = _full_mso_html(
            conditionals=(
                '<!--[if mso]><table width="600"><tr><td><![endif]-->'
                "<!--[if gte mso 12]><v:rect><![endif]-->"
            ),
            closers=(
                "<!--[if gte mso 12]></v:rect><![endif]-->"
                "<!--[if mso]></td></tr></table><![endif]-->"
            ),
        )
        result = validate_mso_conditionals(html)
        # Should have no balance issues
        balance_issues = [i for i in result.issues if i.category == "balanced_pair"]
        assert len(balance_issues) == 0

    def test_valid_version_targeting(self):
        """<!--[if gte mso 12]> is valid syntax."""
        html = _full_mso_html(
            conditionals="<!--[if gte mso 12]><p>Outlook 2007+</p><![endif]-->",
            closers="",
        )
        result = validate_mso_conditionals(html)
        syntax_issues = [i for i in result.issues if i.category == "syntax"]
        assert len(syntax_issues) == 0

    def test_empty_html_no_issues(self):
        """Empty HTML has no MSO content — parser reports nothing."""
        result = validate_mso_conditionals("")
        assert result.is_valid
        assert result.opener_count == 0


class TestUnbalancedPairs:
    def test_extra_opener(self):
        """Extra <!--[if mso]> without closer."""
        html = _full_mso_html(
            conditionals="<!--[if mso]><p>First</p><![endif]--><!--[if mso]><p>Orphan</p>",
            closers="",
        )
        result = validate_mso_conditionals(html)
        balance_issues = [i for i in result.issues if i.category == "balanced_pair"]
        assert len(balance_issues) >= 1
        assert any("opener" in i.message.lower() for i in balance_issues)

    def test_extra_closer(self):
        """Extra <![endif]--> without opener."""
        html = _full_mso_html(
            conditionals="<!--[if mso]><p>Content</p><![endif]-->",
            closers="<![endif]-->",
        )
        result = validate_mso_conditionals(html)
        balance_issues = [i for i in result.issues if i.category == "balanced_pair"]
        assert len(balance_issues) >= 1
        assert any("closer" in i.message.lower() for i in balance_issues)

    def test_non_mso_block_unbalanced(self):
        """Missing <!--<![endif]--> for non-MSO block."""
        html = _full_mso_html(extra_body="<!--[if !mso]><!--><p>Non-Outlook content</p>")
        result = validate_mso_conditionals(html)
        balance_issues = [i for i in result.issues if i.category == "balanced_pair"]
        assert len(balance_issues) >= 1


class TestConditionalSyntax:
    def test_invalid_version_13(self):
        """<!--[if mso 13]> is not a valid Outlook version."""
        html = _full_mso_html(
            conditionals="<!--[if mso 13]><p>Bad</p><![endif]-->",
            closers="",
        )
        result = validate_mso_conditionals(html)
        syntax_issues = [i for i in result.issues if i.category == "syntax"]
        assert len(syntax_issues) >= 1
        assert any("13" in i.message for i in syntax_issues)

    def test_valid_versions_pass(self):
        """All valid version numbers should pass."""
        for version in [9, 10, 11, 12, 14, 15, 16]:
            html = _full_mso_html(
                conditionals=f"<!--[if gte mso {version}]><p>OK</p><![endif]-->",
                closers="",
            )
            result = validate_mso_conditionals(html)
            syntax_issues = [i for i in result.issues if i.category == "syntax"]
            assert len(syntax_issues) == 0, f"Version {version} should be valid"


class TestVMLNesting:
    def test_vml_outside_conditional(self):
        """<v:rect> without surrounding <!--[if mso]>."""
        html = _full_mso_html(
            vml="<v:rect></v:rect>",
        )
        result = validate_mso_conditionals(html)
        vml_issues = [i for i in result.issues if i.category == "vml_orphan"]
        assert len(vml_issues) >= 1

    def test_vml_inside_conditional(self):
        """VML inside <!--[if mso]> block — valid."""
        html = _full_mso_html(
            conditionals='<!--[if mso]><v:rect style="width:600px"><v:fill type="frame"/></v:rect><![endif]-->',
            closers="",
        )
        result = validate_mso_conditionals(html)
        vml_issues = [i for i in result.issues if i.category == "vml_orphan"]
        assert len(vml_issues) == 0


class TestNamespaces:
    def test_missing_xmlns_v(self):
        """VML present but no xmlns:v on <html>."""
        html = _full_mso_html(
            namespaces=False,
            conditionals="<!--[if mso]><v:rect></v:rect><![endif]-->",
            closers="",
        )
        result = validate_mso_conditionals(html)
        ns_issues = [i for i in result.issues if i.category == "namespace"]
        assert len(ns_issues) >= 1
        assert any("xmlns:v" in i.message for i in ns_issues)

    def test_missing_xmlns_o(self):
        """Office elements present but no xmlns:o."""
        # Remove only xmlns:o but keep xmlns:v
        html = """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head><meta charset="utf-8"></head>
<body>
<!--[if mso]><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings><![endif]-->
</body>
</html>"""
        result = validate_mso_conditionals(html)
        ns_issues = [i for i in result.issues if i.category == "namespace"]
        assert len(ns_issues) >= 1
        assert any("xmlns:o" in i.message for i in ns_issues)

    def test_no_vml_no_namespace_issues(self):
        """No VML elements — namespace check should not fire."""
        html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body><!--[if mso]><p>text only</p><![endif]--></body>
</html>"""
        result = validate_mso_conditionals(html)
        ns_issues = [i for i in result.issues if i.category == "namespace"]
        assert len(ns_issues) == 0


class TestGhostTables:
    def test_ghost_table_without_width(self):
        """Ghost table near max-width div without width attr."""
        html = _full_mso_html(
            extra_body=(
                '<div style="max-width: 600px;">'
                "<!--[if mso]><table><tr><td><![endif]-->"
                "<p>Content</p>"
                "<!--[if mso]></td></tr></table><![endif]-->"
                "</div>"
            ),
        )
        result = validate_mso_conditionals(html)
        ghost_issues = [i for i in result.issues if i.category == "ghost_table"]
        assert len(ghost_issues) >= 1

    def test_ghost_table_with_width(self):
        """Ghost table with proper width attr — valid."""
        html = _full_mso_html(
            extra_body=(
                '<div style="max-width: 600px;">'
                '<!--[if mso]><table width="600"><tr><td><![endif]-->'
                "<p>Content</p>"
                "<!--[if mso]></td></tr></table><![endif]-->"
                "</div>"
            ),
        )
        result = validate_mso_conditionals(html)
        ghost_issues = [i for i in result.issues if i.category == "ghost_table"]
        assert len(ghost_issues) == 0


class TestMultipleIssues:
    def test_unbalanced_plus_orphan_vml_plus_missing_namespace(self):
        """Multiple simultaneous issues all reported."""
        html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body>
<!--[if mso]><p>Unbalanced opener</p>
<v:rect>Orphan VML outside conditional</v:rect>
</body>
</html>"""
        result = validate_mso_conditionals(html)
        categories = {i.category for i in result.issues}
        assert "balanced_pair" in categories
        assert "vml_orphan" in categories
        assert "namespace" in categories
        assert len(result.issues) >= 3
