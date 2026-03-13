# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
"""Unit tests for personalisation_validator module."""

import pytest

from app.qa_engine.personalisation_validator import (
    ESPPlatform,
    analyze_personalisation,
    check_conditional_balance,
    check_delimiter_balance,
    check_nesting_depth,
    clear_personalisation_cache,
    detect_all_platforms,
    detect_platform,
    extract_tags,
    validate_ampscript_syntax,
    validate_liquid_syntax,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear LRU cache between tests."""
    clear_personalisation_cache()
    yield
    clear_personalisation_cache()


# ── Platform Detection ──


class TestPlatformDetection:
    def test_braze_liquid_dollar_brace(self):
        html = '<p>Hi {{ ${first_name} | default: "Friend" }}</p>'
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.BRAZE
        assert confidence >= 0.85

    def test_braze_connected_content(self):
        html = "{% connected_content https://api.example.com :save response %}"
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.BRAZE
        assert confidence >= 0.85

    def test_sfmc_ampscript(self):
        html = '%%[SET @name = "World"]%% Hello %%=v(@name)=%%'
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.SFMC
        assert confidence >= 0.90

    def test_adobe_jssp(self):
        html = "<p>Hello <%= recipient.firstName %></p>"
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.ADOBE_CAMPAIGN
        assert confidence >= 0.85

    def test_klaviyo_lookup(self):
        html = '<p>{{ person|lookup:"Custom_Field" }}</p>'
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.KLAVIYO
        assert confidence >= 0.80

    def test_mailchimp_merge(self):
        html = "<p>Hi *|FNAME|*, welcome!</p>"
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.MAILCHIMP
        assert confidence >= 0.90

    def test_hubspot_hubl(self):
        html = '<p>Hi {{ contact.firstname | default("Friend") }}</p>'
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.HUBSPOT
        assert confidence >= 0.80

    def test_iterable_handlebars(self):
        html = "<p>{{#if firstName}}Hi {{firstName}}{{/if}}</p>"
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.ITERABLE
        assert confidence >= 0.80

    def test_no_personalisation(self):
        html = "<p>Hello World</p>"
        platform, confidence = detect_platform(html)
        assert platform == ESPPlatform.UNKNOWN
        assert confidence == 0.0


# ── Delimiter Balance ──


class TestDelimiterBalance:
    def test_balanced_liquid(self):
        html = "{{ name }} {% if cond %}yes{% endif %}"
        errors = check_delimiter_balance(html, ESPPlatform.BRAZE)
        assert errors == []

    def test_unclosed_curly(self):
        html = "{{ name } {% if cond %}yes{% endif %}"
        errors = check_delimiter_balance(html, ESPPlatform.BRAZE)
        assert len(errors) >= 1
        assert "curly" in errors[0].lower()

    def test_unclosed_ampscript(self):
        html = "%%[SET @x = 1 Hello %%=v(@x)=%%"
        errors = check_delimiter_balance(html, ESPPlatform.SFMC)
        assert len(errors) >= 1

    def test_balanced_ampscript(self):
        html = "%%[SET @x = 1]%% Hello %%=v(@x)=%%"
        errors = check_delimiter_balance(html, ESPPlatform.SFMC)
        assert errors == []

    def test_unclosed_merge_tag(self):
        html = "*|FNAME Hello"
        errors = check_delimiter_balance(html, ESPPlatform.MAILCHIMP)
        assert len(errors) >= 1

    def test_balanced_jssp(self):
        html = "<%= recipient.name %>"
        errors = check_delimiter_balance(html, ESPPlatform.ADOBE_CAMPAIGN)
        assert errors == []


# ── Conditional Balance ──


class TestConditionalBalance:
    def test_balanced_liquid_if(self):
        html = "{% if name %}Hello {{ name }}{% endif %}"
        errors = check_conditional_balance(html, ESPPlatform.BRAZE)
        assert errors == []

    def test_unclosed_liquid_if(self):
        html = "{% if name %}Hello {{ name }}"
        errors = check_conditional_balance(html, ESPPlatform.BRAZE)
        assert len(errors) >= 1
        assert "unclosed" in errors[0].lower()

    def test_balanced_ampscript_if(self):
        html = '%%[IF Empty(@name) THEN SET @name = "Friend" ENDIF]%%'
        errors = check_conditional_balance(html, ESPPlatform.SFMC)
        assert errors == []

    def test_balanced_handlebars_if(self):
        html = "{{#if firstName}}Hi {{firstName}}{{/if}}"
        errors = check_conditional_balance(html, ESPPlatform.ITERABLE)
        assert errors == []

    def test_unclosed_handlebars_if(self):
        html = "{{#if firstName}}Hi {{firstName}}"
        errors = check_conditional_balance(html, ESPPlatform.ITERABLE)
        assert len(errors) >= 1

    def test_balanced_mailchimp_if(self):
        html = "*|IF:FNAME|*Hi *|FNAME|**|END:IF|*"
        errors = check_conditional_balance(html, ESPPlatform.MAILCHIMP)
        assert errors == []


# ── Fallback Detection ──


class TestFallbackDetection:
    def test_braze_default_filter(self):
        html = '{{ ${first_name} | default: "Friend" }}'
        tags = extract_tags(html, ESPPlatform.BRAZE)
        assert len(tags) >= 1
        assert tags[0].has_fallback is True

    def test_braze_no_fallback(self):
        html = "{{ ${first_name} }}"
        tags = extract_tags(html, ESPPlatform.BRAZE)
        assert len(tags) >= 1
        assert tags[0].has_fallback is False

    def test_klaviyo_default_filter(self):
        html = "{{ first_name|default:'Friend' }}"
        tags = extract_tags(html, ESPPlatform.KLAVIYO)
        assert len(tags) >= 1
        assert tags[0].has_fallback is True

    def test_hubspot_default_filter(self):
        html = '{{ contact.firstname | default("Friend") }}'
        tags = extract_tags(html, ESPPlatform.HUBSPOT)
        assert len(tags) >= 1
        assert tags[0].has_fallback is True

    def test_iterable_default_helper(self):
        html = '{{defaultIfEmpty firstName "Friend"}}'
        tags = extract_tags(html, ESPPlatform.ITERABLE)
        assert len(tags) >= 1
        assert tags[0].has_fallback is True

    def test_mailchimp_no_conditional_wrapper(self):
        html = "*|FNAME|*"
        tags = extract_tags(html, ESPPlatform.MAILCHIMP)
        assert len(tags) >= 1
        assert tags[0].has_fallback is False


# ── Syntax Validation ──


class TestSyntaxValidation:
    def test_valid_liquid(self):
        html = "{{ name | upcase }} {% if x %}yes{% endif %}"
        errors = validate_liquid_syntax(html)
        assert errors == []

    def test_dangling_pipe_liquid(self):
        html = "{{ name | }}"
        errors = validate_liquid_syntax(html)
        assert len(errors) >= 1
        assert "dangling" in errors[0].lower()

    def test_valid_ampscript(self):
        html = '%%[SET @name = "World"]%% %%=v(@name)=%%'
        errors = validate_ampscript_syntax(html)
        assert errors == []

    def test_set_without_at(self):
        html = '%%[SET name = "World"]%%'
        errors = validate_ampscript_syntax(html)
        assert len(errors) >= 1
        assert "@ prefix" in errors[0]

    def test_unbalanced_parens_ampscript(self):
        html = '%%[SET @x = Lookup("DE", "field", "key", "val"]%%'
        errors = validate_ampscript_syntax(html)
        assert len(errors) >= 1
        assert "parentheses" in errors[0].lower()


# ── Nesting Depth ──


class TestNestingDepth:
    def test_within_limit(self):
        html = "{% if a %}{% if b %}{% if c %}deep{% endif %}{% endif %}{% endif %}"
        violations = check_nesting_depth(html, ESPPlatform.BRAZE, max_depth=3)
        assert violations == []

    def test_exceeds_limit(self):
        html = "{% if a %}{% if b %}{% if c %}{% if d %}too deep{% endif %}{% endif %}{% endif %}{% endif %}"
        violations = check_nesting_depth(html, ESPPlatform.BRAZE, max_depth=3)
        assert len(violations) >= 1
        assert "depth 4" in violations[0]


# ── Mixed Platform ──


class TestMixedPlatform:
    def test_pure_liquid_not_mixed(self):
        html = '{{ name | default: "X" }} {% if cond %}y{% endif %}'
        platforms = detect_all_platforms(html)
        # Pure liquid with Braze-style should not be mixed
        assert len(platforms) <= 1

    def test_liquid_plus_ampscript_is_mixed(self):
        html = "{{ name }} %%[SET @x = 1]%%"
        platforms = detect_all_platforms(html)
        assert len(platforms) >= 2

    def test_no_personalisation(self):
        html = "<p>Hello World</p>"
        platforms = detect_all_platforms(html)
        assert platforms == []


# ── Full Analysis ──


class TestFullAnalysis:
    def test_empty_html(self):
        analysis = analyze_personalisation("")
        assert analysis.has_personalisation is False
        assert analysis.total_tags == 0

    def test_clean_braze_template(self):
        html = (
            '{{ ${first_name} | default: "Friend" }} {% if ${has_offer} %}Special offer!{% endif %}'
        )
        analysis = analyze_personalisation(html)
        assert analysis.has_personalisation is True
        assert analysis.primary_platform == ESPPlatform.BRAZE
        assert analysis.total_tags >= 2
        assert analysis.tags_with_fallback >= 1

    def test_plain_html_no_tags(self):
        html = "<table><tr><td>Hello World</td></tr></table>"
        analysis = analyze_personalisation(html)
        assert analysis.has_personalisation is False

    def test_mixed_platform_detected(self):
        html = "{{ name }} %%[SET @x = 1]%%"
        analysis = analyze_personalisation(html)
        assert analysis.is_mixed_platform is True

    def test_html_entities_not_false_positive(self):
        html = "<p>Price: &lt;$50 &amp; &gt;$10</p>"
        analysis = analyze_personalisation(html)
        assert analysis.has_personalisation is False

    def test_template_in_script_detected(self):
        html = '<script>var name = "{{ user_name }}";</script>'
        analysis = analyze_personalisation(html)
        # Generic template syntax detected
        assert analysis.has_personalisation is True
