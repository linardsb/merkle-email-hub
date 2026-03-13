"""Tests for the scope validator — per-agent modification constraint enforcement."""


from app.ai.blueprints.protocols import AllowedScope
from app.ai.blueprints.scope_validator import validate_scope


class TestStylesOnly:
    """Tests for styles_only scope constraint."""

    def test_allowed_change_style_block(self) -> None:
        """Only style block differs → no violations."""
        pre = "<html><head><style>body{color:black}</style></head><body><p>Hello</p></body></html>"
        post = "<html><head><style>body{color:white}</style></head><body><p>Hello</p></body></html>"
        scope = AllowedScope(styles_only=True)
        violations = validate_scope(pre, post, scope, "dark_mode")
        assert violations == []

    def test_structure_violation(self) -> None:
        """Tag removed → structure violation detected."""
        pre = "<html><body><p>Hello</p><div>Extra</div></body></html>"
        post = "<html><body><p>Hello</p></body></html>"
        scope = AllowedScope(styles_only=True)
        violations = validate_scope(pre, post, scope, "dark_mode")
        assert len(violations) >= 1
        assert any(v.violation_type == "structure_changed" for v in violations)

    def test_text_violation(self) -> None:
        """Body text changed → text violation detected."""
        pre = "<html><body><p>Hello World</p></body></html>"
        post = "<html><body><p>Changed Text</p></body></html>"
        scope = AllowedScope(styles_only=True)
        violations = validate_scope(pre, post, scope, "dark_mode")
        assert any(v.violation_type == "text_changed" for v in violations)


class TestAdditiveOnly:
    """Tests for additive_only scope constraint."""

    def test_allowed_add_element(self) -> None:
        """New element added → no violations."""
        pre = "<html><body><p>Hello</p></body></html>"
        post = "<html><body><p>Hello</p><div><!--[if mso]>fix<![endif]--></div></body></html>"
        scope = AllowedScope(additive_only=True)
        violations = validate_scope(pre, post, scope, "outlook_fixer")
        assert violations == []

    def test_removal_violation(self) -> None:
        """Element removed → violation."""
        pre = "<html><body><table><tr><td>A</td></tr></table><p>Keep</p></body></html>"
        post = "<html><body><p>Keep</p></body></html>"
        scope = AllowedScope(additive_only=True)
        violations = validate_scope(pre, post, scope, "outlook_fixer")
        assert len(violations) >= 1
        assert any(v.violation_type == "tag_removed" for v in violations)


class TestTextOnly:
    """Tests for text_only scope constraint."""

    def test_allowed_text_change(self) -> None:
        """Text content changed, structure same → no violations."""
        pre = '<html><body><img alt="old text"/></body></html>'
        post = '<html><body><img alt="new text"/></body></html>'
        scope = AllowedScope(text_only=True)
        violations = validate_scope(pre, post, scope, "personalisation")
        assert violations == []

    def test_structure_violation(self) -> None:
        """New div added → structure violation."""
        pre = "<html><body><p>Text</p></body></html>"
        post = "<html><body><p>Text</p><div>New</div></body></html>"
        scope = AllowedScope(text_only=True)
        violations = validate_scope(pre, post, scope, "personalisation")
        assert any(v.violation_type == "structure_changed" for v in violations)


class TestStructureOnly:
    """Tests for structure_only scope constraint."""

    def test_allowed_structural_change(self) -> None:
        """HTML structure changed without new stylesheets → no violations."""
        pre = "<html><body><p>Hello</p></body></html>"
        post = "<html><body><div><p>Hello</p></div></body></html>"
        scope = AllowedScope(structure_only=True)
        violations = validate_scope(pre, post, scope, "scaffolder")
        assert violations == []

    def test_stylesheet_violation(self) -> None:
        """New link rel=stylesheet added → violation."""
        pre = "<html><head></head><body><p>Hello</p></body></html>"
        post = '<html><head><link rel="stylesheet" href="https://cdn.example.com/bad.css"/></head><body><p>Hello</p></body></html>'
        scope = AllowedScope(structure_only=True)
        violations = validate_scope(pre, post, scope, "scaffolder")
        assert any(v.violation_type == "style_changed" for v in violations)


class TestEdgeCases:
    """Tests for edge cases and graceful handling."""

    def test_parse_failure_returns_empty(self) -> None:
        """Invalid HTML → no crash (lxml is lenient, may still parse)."""
        # lxml is very forgiving, so we just verify no exception is raised
        violations = validate_scope(
            pre_html="",
            post_html="",
            scope=AllowedScope(styles_only=True),
            agent_name="dark_mode",
        )
        # Empty strings cause parse failure → should return empty
        assert violations == []

    def test_no_scope_flags_returns_empty(self) -> None:
        """No scope flags set → no validation (pass through)."""
        pre = "<html><body><p>Hello</p></body></html>"
        post = "<html><body><div>Completely different</div></body></html>"
        scope = AllowedScope()  # All False
        violations = validate_scope(pre, post, scope, "accessibility")
        assert violations == []

    def test_identical_html_no_violations(self) -> None:
        """Identical pre/post → no violations regardless of scope."""
        html = "<html><body><p>Hello</p></body></html>"
        scope = AllowedScope(styles_only=True)
        violations = validate_scope(html, html, scope, "dark_mode")
        assert violations == []
