# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Tests for the shared QA rule engine."""

from pathlib import Path

from lxml import html as lxml_html
from lxml.html import HtmlElement

# Ensure custom checks are registered
import app.qa_engine.custom_checks  # noqa: F401
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import (
    _CHECK_TYPES,
    _CUSTOM_CHECKS,
    Rule,
    RuleEngine,
    clear_rules_cache,
    load_rules,
)


def _doc(html: str) -> HtmlElement:
    """Parse HTML into an lxml document."""
    return lxml_html.document_fromstring(html)


class TestLoadRules:
    def setup_method(self):
        clear_rules_cache()

    def test_loads_valid_yaml(self, tmp_path: Path):
        yaml_file = tmp_path / "test_rules.yaml"
        yaml_file.write_text("""
rules:
  - id: "test-rule"
    group: "test"
    name: "Test Rule"
    check: "element_present"
    selector: "img"
    message: "No images found"
        """)
        rules = load_rules(yaml_file)
        assert len(rules) == 1
        assert rules[0].id == "test-rule"
        assert rules[0].check_type == "element_present"

    def test_missing_file_returns_empty(self, tmp_path: Path):
        rules = load_rules(tmp_path / "nonexistent.yaml")
        assert rules == []

    def test_malformed_yaml_returns_empty(self, tmp_path: Path):
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("{{invalid yaml")
        rules = load_rules(yaml_file)
        assert rules == []

    def test_skips_invalid_rules(self, tmp_path: Path):
        yaml_file = tmp_path / "partial.yaml"
        yaml_file.write_text("""
rules:
  - id: "good"
    group: "test"
    name: "Good"
    check: "element_present"
    message: "Ok"
  - group: "test"
    name: "Missing ID"
    check: "element_present"
    message: "Bad"
        """)
        rules = load_rules(yaml_file)
        assert len(rules) == 1
        assert rules[0].id == "good"

    def test_caches_after_first_load(self, tmp_path: Path):
        yaml_file = tmp_path / "cached.yaml"
        yaml_file.write_text("""
rules:
  - id: "r1"
    group: "test"
    name: "R1"
    check: "element_present"
    message: "m"
        """)
        rules1 = load_rules(yaml_file)
        rules2 = load_rules(yaml_file)
        assert rules1 is rules2


class TestCheckTypes:
    """Test each check type evaluator with minimal DOM fixtures."""

    def test_raw_html_pattern_present(self):
        """raw_html_pattern passes when pattern IS found."""
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="raw_html_pattern",
            message="Missing DOCTYPE",
            patterns=("(?i)<!doctype",),
            default_deduction=0.15,
        )
        fn = _CHECK_TYPES["raw_html_pattern"]
        html = "<!DOCTYPE html><html><body></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_raw_html_pattern_absent(self):
        """raw_html_pattern fails when pattern NOT found."""
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="raw_html_pattern",
            message="Missing DOCTYPE",
            patterns=("(?i)<!doctype",),
            default_deduction=0.15,
        )
        fn = _CHECK_TYPES["raw_html_pattern"]
        html = "<html><body></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is False
        assert result.deduction == 0.15

    def test_element_present_passes(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="element_present",
            message="No img",
            selector="img",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["element_present"]
        html = '<html><body><img src="x.png"></body></html>'
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_element_present_fails(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="element_present",
            message="No img",
            selector="img",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["element_present"]
        html = "<html><body><p>Hello</p></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is False
        assert result.deduction == 0.10

    def test_element_absent_passes(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="element_absent",
            message="Found template",
            selector="template",
            default_deduction=0.15,
        )
        fn = _CHECK_TYPES["element_absent"]
        html = "<html><body><p>OK</p></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_element_count_within_bounds(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="element_count",
            message="Wrong count",
            selector="p",
            min_count=1,
            max_count=3,
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["element_count"]
        html = "<html><body><p>A</p><p>B</p></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_element_count_exceeds_max(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="element_count",
            message="Too many",
            selector="p",
            min_count=0,
            max_count=1,
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["element_count"]
        html = "<html><body><p>A</p><p>B</p><p>C</p></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is False

    def test_attr_present_single(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="attr_present",
            message="Missing alt",
            selector="img",
            attr="alt",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["attr_present"]
        html = '<html><body><img src="x.png" alt="Test"></body></html>'
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_attr_present_missing(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="attr_present",
            message="Missing alt",
            selector="img",
            attr="alt",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["attr_present"]
        html = '<html><body><img src="x.png"></body></html>'
        result = fn(_doc(html), html, rule, None)
        assert result.passed is False

    def test_attr_value_matches(self):
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="attr_value",
            message="Wrong role",
            selector="table",
            attr="role",
            value="presentation",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["attr_value"]
        html = '<html><body><table role="presentation"></table></body></html>'
        result = fn(_doc(html), html, rule, None)
        assert result.passed is True

    def test_custom_delegates_correctly(self):
        """Custom check type delegates to registered function."""
        rule = Rule(
            id="test",
            group="test",
            name="T",
            check_type="custom",
            message="Custom fail",
            custom_fn="check_title",
            default_deduction=0.10,
        )
        fn = _CHECK_TYPES["custom"]
        # HTML with empty title
        html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title></title></head><body></body></html>"
        result = fn(_doc(html), html, rule, None)
        assert result.passed is False
        assert "title" in result.issues[0].lower()


class TestRuleEngine:
    """Test the engine orchestrator."""

    def test_all_rules_pass(self):
        rules = [
            Rule(
                id="r1",
                group="test",
                name="R1",
                check_type="raw_html_pattern",
                message="Missing DOCTYPE",
                patterns=("(?i)<!doctype",),
                default_deduction=0.15,
            ),
        ]
        engine = RuleEngine(rules)
        html = "<!DOCTYPE html><html><body></body></html>"
        issues, deduction = engine.evaluate(_doc(html), html)
        assert issues == []
        assert deduction == 0.0

    def test_deductions_accumulate(self):
        rules = [
            Rule(
                id="r1",
                group="test",
                name="R1",
                check_type="raw_html_pattern",
                message="Missing A",
                patterns=("PATTERN_A",),
                default_deduction=0.10,
            ),
            Rule(
                id="r2",
                group="test",
                name="R2",
                check_type="raw_html_pattern",
                message="Missing B",
                patterns=("PATTERN_B",),
                default_deduction=0.20,
            ),
        ]
        engine = RuleEngine(rules)
        html = "<html><body>No patterns here</body></html>"
        issues, deduction = engine.evaluate(_doc(html), html)
        assert len(issues) == 2
        assert round(deduction, 2) == 0.30

    def test_unknown_check_type_skipped(self):
        rules = [
            Rule(
                id="r1",
                group="test",
                name="R1",
                check_type="nonexistent_check",
                message="Should be skipped",
                default_deduction=0.50,
            ),
        ]
        engine = RuleEngine(rules)
        html = "<html><body></body></html>"
        issues, deduction = engine.evaluate(_doc(html), html)
        assert issues == []
        assert deduction == 0.0

    def test_config_overrides_deduction(self):
        rules = [
            Rule(
                id="r1",
                group="test",
                name="R1",
                check_type="raw_html_pattern",
                message="Missing DOCTYPE",
                patterns=("(?i)<!doctype",),
                deduction_key="deduction_doctype",
                default_deduction=0.15,
            ),
        ]
        engine = RuleEngine(rules)
        html = "<html><body></body></html>"  # Missing DOCTYPE
        config = QACheckConfig(params={"deduction_doctype": 0.01})
        issues, deduction = engine.evaluate(_doc(html), html, config)
        assert len(issues) == 1
        assert deduction == 0.01


class TestAccessibilityYaml:
    """Validate that rules/accessibility.yaml loads correctly."""

    def setup_method(self):
        clear_rules_cache()

    def test_yaml_loads(self):
        path = Path(__file__).parent.parent / "rules" / "accessibility.yaml"
        rules = load_rules(path)
        assert len(rules) == 24

    def test_all_rules_have_required_fields(self):
        path = Path(__file__).parent.parent / "rules" / "accessibility.yaml"
        rules = load_rules(path)
        for rule in rules:
            assert rule.id, "Rule missing id"
            assert rule.group, f"Rule {rule.id} missing group"
            assert rule.name, f"Rule {rule.id} missing name"
            assert rule.check_type, f"Rule {rule.id} missing check_type"
            assert rule.message, f"Rule {rule.id} missing message"

    def test_all_check_types_registered(self):
        """Every check type used in accessibility.yaml is registered."""
        path = Path(__file__).parent.parent / "rules" / "accessibility.yaml"
        rules = load_rules(path)
        for rule in rules:
            assert rule.check_type in _CHECK_TYPES, f"Unregistered check type: {rule.check_type}"

    def test_all_custom_fns_registered(self):
        """Every custom_fn referenced in rules is registered."""
        path = Path(__file__).parent.parent / "rules" / "accessibility.yaml"
        rules = load_rules(path)
        for rule in rules:
            if rule.check_type == "custom":
                assert rule.custom_fn in _CUSTOM_CHECKS, f"Unregistered custom_fn: {rule.custom_fn}"

    def test_unique_rule_ids(self):
        """All rule IDs are unique."""
        path = Path(__file__).parent.parent / "rules" / "accessibility.yaml"
        rules = load_rules(path)
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs found: {[i for i in ids if ids.count(i) > 1]}"
        )


class TestEmailStructureYaml:
    """Validate that rules/email_structure.yaml loads correctly."""

    def setup_method(self):
        clear_rules_cache()

    def test_yaml_loads(self):
        path = Path(__file__).parent.parent / "rules" / "email_structure.yaml"
        rules = load_rules(path)
        assert len(rules) == 20

    def test_all_rules_have_required_fields(self):
        path = Path(__file__).parent.parent / "rules" / "email_structure.yaml"
        rules = load_rules(path)
        for rule in rules:
            assert rule.id, "Rule missing id"
            assert rule.group, f"Rule {rule.id} missing group"
            assert rule.name, f"Rule {rule.id} missing name"
            assert rule.check_type, f"Rule {rule.id} missing check_type"
            assert rule.message, f"Rule {rule.id} missing message"

    def test_all_check_types_registered(self):
        """Every check type used in email_structure.yaml is registered."""
        path = Path(__file__).parent.parent / "rules" / "email_structure.yaml"
        rules = load_rules(path)
        for rule in rules:
            assert rule.check_type in _CHECK_TYPES, f"Unregistered check type: {rule.check_type}"

    def test_all_custom_fns_registered(self):
        """Every custom_fn referenced in rules is registered."""
        path = Path(__file__).parent.parent / "rules" / "email_structure.yaml"
        rules = load_rules(path)
        for rule in rules:
            if rule.check_type == "custom":
                assert rule.custom_fn in _CUSTOM_CHECKS, f"Unregistered custom_fn: {rule.custom_fn}"

    def test_unique_rule_ids(self):
        """All rule IDs are unique."""
        path = Path(__file__).parent.parent / "rules" / "email_structure.yaml"
        rules = load_rules(path)
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs found: {[i for i in ids if ids.count(i) > 1]}"
        )
