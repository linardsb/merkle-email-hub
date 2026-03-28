"""Unit tests for Token IR — parse, emit, round-trip, edge cases."""

from __future__ import annotations

import pytest

from app.connectors.token_ir import (
    FilterExpr,
    TokenIR,
    VariableToken,
    detect_and_parse,
    emit_tokens,
    parse_tokens,
)
from app.core.exceptions import DomainValidationError

# ---------------------------------------------------------------------------
# Parse tests — one per ESP
# ---------------------------------------------------------------------------


class TestParseBraze:
    def test_parse_variables(self) -> None:
        html = '<td>{{ first_name | default: "Friend" }}</td>'
        ir = parse_tokens(html, "braze")
        assert len(ir.variables) == 1
        v = ir.variables[0]
        assert v.name == "first_name"
        assert v.fallback == "Friend"
        assert len(v.filters) == 1
        assert v.filters[0].name == "default"

    def test_parse_conditional(self) -> None:
        html = "{% if vip %}VIP content{% else %}Regular{% endif %}"
        ir = parse_tokens(html, "braze")
        assert len(ir.conditionals) == 1
        c = ir.conditionals[0]
        assert c.variable == "vip"
        assert c.operator == "exists"
        assert "VIP content" in c.body_html
        assert c.else_html is not None

    def test_parse_loop(self) -> None:
        html = "{% for item in products %}{{ item.name }}{% endfor %}"
        ir = parse_tokens(html, "braze")
        assert len(ir.loops) == 1
        assert ir.loops[0].item_name == "item"
        assert ir.loops[0].collection == "products"


class TestParseSFMC:
    def test_parse_output(self) -> None:
        html = "<td>%%=v(@first_name)=%%</td>"
        ir = parse_tokens(html, "sfmc")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "first_name"

    def test_parse_conditional(self) -> None:
        html = "%%[IF Empty(@name) THEN]%%Fallback%%[ELSE]%%%%=v(@name)=%%%%[ENDIF]%%"
        ir = parse_tokens(html, "sfmc")
        assert len(ir.conditionals) == 1
        assert ir.conditionals[0].variable == "name"
        assert ir.conditionals[0].operator == "exists"


class TestParseKlaviyo:
    def test_parse_person_var(self) -> None:
        html = '<td>{{ person.first_name | default: "there" }}</td>'
        ir = parse_tokens(html, "klaviyo")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "first_name"  # person. prefix stripped
        assert ir.variables[0].fallback == "there"


class TestParseHubSpot:
    def test_parse_contact_var(self) -> None:
        html = '{{ contact.firstname | default("Friend") }}'
        ir = parse_tokens(html, "hubspot")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "firstname"  # contact. prefix stripped

    def test_parse_conditional(self) -> None:
        html = '{% if contact.vip == "yes" %}VIP{% endif %}'
        ir = parse_tokens(html, "hubspot")
        assert len(ir.conditionals) == 1
        c = ir.conditionals[0]
        assert c.variable == "vip"
        assert c.operator == "eq"
        assert c.value == "yes"


class TestParseMailchimp:
    def test_parse_merge_tags(self) -> None:
        html = "<td>Hello *|FNAME|*, welcome!</td>"
        ir = parse_tokens(html, "mailchimp")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "fname"

    def test_parse_conditional(self) -> None:
        html = "*|IF:FNAME|*Hi *|FNAME|**|ELSE:|*Hello*|END:IF|*"
        ir = parse_tokens(html, "mailchimp")
        assert len(ir.conditionals) == 1
        assert ir.conditionals[0].variable == "FNAME"


class TestParseIterable:
    def test_parse_handlebars_var(self) -> None:
        html = "<td>{{firstName}}</td>"
        ir = parse_tokens(html, "iterable")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "firstName"

    def test_parse_default_helper(self) -> None:
        html = '{{defaultIfEmpty firstName "Friend"}}'
        ir = parse_tokens(html, "iterable")
        assert len(ir.variables) == 1
        assert ir.variables[0].fallback == "Friend"

    def test_parse_each_loop(self) -> None:
        html = "{{#each items}}{{this.name}}{{/each}}"
        ir = parse_tokens(html, "iterable")
        assert len(ir.loops) == 1
        assert ir.loops[0].collection == "items"


class TestParseAdobe:
    def test_parse_jssp_output(self) -> None:
        html = "<td><%= recipient.firstName %></td>"
        ir = parse_tokens(html, "adobe_campaign")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "recipient.firstName"


class TestParseSendGrid:
    def test_sendgrid_uses_iterable_parser(self) -> None:
        html = "{{firstName}}"
        ir = parse_tokens(html, "sendgrid")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "firstName"


class TestParseBrevo:
    def test_parse_contact_var(self) -> None:
        html = '{{ contact.FIRSTNAME | default: "there" }}'
        ir = parse_tokens(html, "brevo")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "FIRSTNAME"


# ---------------------------------------------------------------------------
# Emit tests — representative targets
# ---------------------------------------------------------------------------


class TestEmitBraze:
    def test_emit_variable(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="first_name",
                    filters=(FilterExpr(name="default", args=("Friend",)),),
                    fallback="Friend",
                    source_syntax="PLACEHOLDER",
                    source_span=(4, 15),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        html = "<td>PLACEHOLDER</td>"
        result, warnings = emit_tokens(ir, html, "braze")
        assert '{{ first_name | default: "Friend" }}' in result
        assert warnings == []


class TestEmitSFMC:
    def test_emit_variable_with_fallback(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="first_name",
                    filters=(FilterExpr(name="default", args=("Friend",)),),
                    fallback="Friend",
                    source_syntax="PLACEHOLDER",
                    source_span=(4, 15),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        html = "<td>PLACEHOLDER</td>"
        result, _ = emit_tokens(ir, html, "sfmc")
        assert "IIF(Empty(@first_name)" in result
        assert '"Friend"' in result

    def test_emit_uppercase_filter(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="city",
                    filters=(FilterExpr(name="uppercase", args=()),),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, _ = emit_tokens(ir, "XX", "sfmc")
        assert "Uppercase(v(@city))" in result


class TestEmitKlaviyo:
    def test_emit_variable(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="first_name",
                    filters=(),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, _ = emit_tokens(ir, "XX", "klaviyo")
        assert "person.first_name" in result


class TestEmitHubSpot:
    def test_emit_variable_with_filter(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="first_name",
                    filters=(FilterExpr(name="uppercase", args=()),),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, _ = emit_tokens(ir, "XX", "hubspot")
        assert "contact.first_name" in result
        assert "upper" in result


class TestEmitMailchimp:
    def test_emit_merge_tag(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="fname",
                    filters=(),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, _ = emit_tokens(ir, "XX", "mailchimp")
        assert "*|FNAME|*" in result

    def test_unsupported_filter_warns(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="city",
                    filters=(FilterExpr(name="uppercase", args=()),),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        _, warnings = emit_tokens(ir, "XX", "mailchimp")
        assert any("not supported" in w for w in warnings)


class TestEmitIterable:
    def test_emit_default_helper(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="firstName",
                    filters=(FilterExpr(name="default", args=("Friend",)),),
                    fallback="Friend",
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, _ = emit_tokens(ir, "XX", "iterable")
        assert "defaultIfEmpty" in result
        assert "Friend" in result


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_klaviyo_to_hubspot(self) -> None:
        src = '{{ person.first_name | default: "Friend" }}'
        ir = parse_tokens(src, "klaviyo")
        result, _ = emit_tokens(ir, src, "hubspot")
        # Re-parse the HubSpot output
        ir2 = parse_tokens(result, "hubspot")
        assert len(ir2.variables) == 1
        assert ir2.variables[0].name == "first_name"
        assert ir2.variables[0].fallback == "Friend"

    def test_braze_to_klaviyo(self) -> None:
        src = '{{ first_name | default: "there" }}'
        ir = parse_tokens(src, "braze")
        result, _ = emit_tokens(ir, src, "klaviyo")
        assert "person.first_name" in result
        ir2 = parse_tokens(result, "klaviyo")
        assert ir2.variables[0].name == "first_name"

    def test_braze_to_sfmc(self) -> None:
        src = "{{ first_name }}"
        ir = parse_tokens(src, "braze")
        result, _ = emit_tokens(ir, src, "sfmc")
        assert "%%=v(@first_name)=%%" in result

    def test_braze_to_iterable(self) -> None:
        src = "{{ first_name }}"
        ir = parse_tokens(src, "braze")
        result, _ = emit_tokens(ir, src, "iterable")
        assert "{{first_name}}" in result

    def test_braze_to_mailchimp(self) -> None:
        src = "{{ first_name }}"
        ir = parse_tokens(src, "braze")
        result, _ = emit_tokens(ir, src, "mailchimp")
        assert "*|FIRST_NAME|*" in result


# ---------------------------------------------------------------------------
# Filter mapping
# ---------------------------------------------------------------------------


class TestFilterMapping:
    def test_supported_filter_translates(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="city",
                    filters=(FilterExpr(name="uppercase", args=()),),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        result, warnings = emit_tokens(ir, "XX", "braze")
        assert "upcase" in result
        assert warnings == []

    def test_unsupported_filter_warns(self) -> None:
        ir = TokenIR(
            variables=(
                VariableToken(
                    name="x",
                    filters=(FilterExpr(name="date", args=("%b %d",)),),
                    fallback=None,
                    source_syntax="XX",
                    source_span=(0, 2),
                ),
            ),
            conditionals=(),
            loops=(),
        )
        _, warnings = emit_tokens(ir, "XX", "mailchimp")
        assert any("not supported" in w for w in warnings)

    def test_chained_filters(self) -> None:
        html = "{{ name | upcase | truncate: 10 }}"
        ir = parse_tokens(html, "braze")
        assert len(ir.variables) == 1
        assert len(ir.variables[0].filters) == 2
        assert ir.variables[0].filters[0].name == "uppercase"
        assert ir.variables[0].filters[1].name == "truncate"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_html_returns_empty_ir(self) -> None:
        ir = parse_tokens("", "braze")
        assert ir.variables == ()
        assert ir.conditionals == ()
        assert ir.loops == ()

    def test_no_tokens_returns_empty_ir(self) -> None:
        ir = parse_tokens("<table><tr><td>Hello</td></tr></table>", "braze")
        assert ir.variables == ()

    def test_tokens_in_href(self) -> None:
        html = '<a href="https://example.com/{{ tracking_id }}">Click</a>'
        ir = parse_tokens(html, "braze")
        assert len(ir.variables) == 1
        assert ir.variables[0].name == "tracking_id"

    def test_detect_and_parse_braze(self) -> None:
        html = '{% connected_content https://api.example.com %}{{ first_name | default: "there" }}'
        ir, platform = detect_and_parse(html)
        assert platform == "braze"
        assert len(ir.variables) >= 1

    def test_detect_and_parse_no_esp_raises(self) -> None:
        with pytest.raises(DomainValidationError, match="Could not detect"):
            detect_and_parse("<table><tr><td>Plain HTML</td></tr></table>")

    def test_invalid_platform_raises(self) -> None:
        with pytest.raises(DomainValidationError, match="No parser"):
            parse_tokens("<td>hello</td>", "nonexistent_esp")  # type: ignore[arg-type]

    def test_conditional_with_comparison(self) -> None:
        html = "{% if score > 90 %}High{% else %}Low{% endif %}"
        ir = parse_tokens(html, "braze")
        assert len(ir.conditionals) == 1
        c = ir.conditionals[0]
        assert c.variable == "score"
        assert c.operator == "gt"
        assert c.value == "90"
