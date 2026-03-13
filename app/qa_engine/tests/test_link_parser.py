# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Unit tests for the link parser module."""

from app.qa_engine.link_parser import (
    _check_empty_suspicious,
    _check_encoding,
    _check_phishing_mismatch,
    _check_protocol,
    _detect_template_type,
    _is_template_href,
    _validate_url_format,
    clear_link_cache,
    validate_links,
)

# ── 1. Template Detection ──


class TestDetectTemplateType:
    def test_liquid_variable(self):
        tmpl_type, balanced = _detect_template_type("{{ url }}")
        assert tmpl_type == "liquid"
        assert balanced is True

    def test_ampscript(self):
        tmpl_type, balanced = _detect_template_type("%%[= RequestParameter('url') ]%%")
        assert tmpl_type == "ampscript"
        assert balanced is True

    def test_jssp(self):
        tmpl_type, balanced = _detect_template_type("<%= targetData.url %>")
        assert tmpl_type == "jssp"
        assert balanced is True

    def test_unbalanced_liquid(self):
        tmpl_type, balanced = _detect_template_type("{{ url }")
        assert tmpl_type == "liquid"
        assert balanced is False

    def test_no_template(self):
        tmpl_type, balanced = _detect_template_type("https://example.com")
        assert tmpl_type == ""
        assert balanced is True

    def test_mixed_url_with_liquid(self):
        tmpl_type, balanced = _detect_template_type("https://example.com?id={{ id }}")
        assert tmpl_type == "liquid"
        assert balanced is True

    def test_liquid_tag(self):
        tmpl_type, balanced = _detect_template_type("{% if show %}https://a.com{% endif %}")
        assert tmpl_type == "liquid"
        assert balanced is True


# ── 2. Template Href Detection ──


class TestIsTemplateHref:
    def test_full_template(self):
        assert _is_template_href("{{ url }}") is True

    def test_partial_template(self):
        # Has non-template prefix
        assert _is_template_href("https://example.com/{{ path }}") is False

    def test_no_template(self):
        assert _is_template_href("https://example.com") is False

    def test_ampscript_full(self):
        assert _is_template_href("%%[= url ]%%") is True

    def test_empty(self):
        assert _is_template_href("") is False


# ── 3. URL Format Validation ──


class TestValidateUrlFormat:
    def test_valid_url(self):
        issues = _validate_url_format("https://example.com/page")
        assert len(issues) == 0

    def test_missing_netloc(self):
        issues = _validate_url_format("https:///page")
        assert len(issues) == 1
        assert issues[0].category == "malformed_url"

    def test_path_traversal(self):
        issues = _validate_url_format("https://example.com/../../etc")
        assert len(issues) == 1
        assert "traversal" in issues[0].message.lower()

    def test_valid_with_query_params(self):
        issues = _validate_url_format("https://example.com/page?foo=bar&baz=1")
        assert len(issues) == 0

    def test_valid_with_fragment(self):
        issues = _validate_url_format("https://example.com/page#section")
        assert len(issues) == 0

    def test_valid_with_port(self):
        issues = _validate_url_format("https://example.com:8080/page")
        assert len(issues) == 0


# ── 4. Encoding Checks ──


class TestCheckEncoding:
    def test_clean_url(self):
        issues = _check_encoding("https://example.com/page")
        assert len(issues) == 0

    def test_unencoded_space(self):
        issues = _check_encoding("https://example.com/my page")
        has_space_issue = any(i.category == "unencoded_chars" for i in issues)
        assert has_space_issue

    def test_special_chars(self):
        issues = _check_encoding("https://example.com/<path>")
        has_special_issue = any(i.category == "unencoded_chars" for i in issues)
        assert has_special_issue

    def test_double_encoded(self):
        issues = _check_encoding("https://example.com/%2520path")
        has_double = any(i.category == "double_encoded" for i in issues)
        assert has_double

    def test_already_encoded(self):
        issues = _check_encoding("https://example.com/my%20page")
        # Should not flag already-encoded URLs (no spaces, no double encoding)
        space_issues = [i for i in issues if "space" in i.message.lower()]
        assert len(space_issues) == 0


# ── 5. Protocol Checks ──


class TestCheckProtocol:
    def test_javascript_blocked(self):
        issues = _check_protocol("javascript:alert(1)")
        assert len(issues) == 1
        assert issues[0].category == "suspicious_protocol"

    def test_data_blocked(self):
        issues = _check_protocol("data:text/html,<h1>Hi</h1>")
        assert len(issues) == 1
        assert issues[0].category == "suspicious_protocol"

    def test_https_allowed(self):
        issues = _check_protocol("https://example.com")
        assert len(issues) == 0

    def test_mailto_allowed(self):
        issues = _check_protocol("mailto:user@example.com")
        assert len(issues) == 0

    def test_tel_allowed(self):
        issues = _check_protocol("tel:+15551234567")
        assert len(issues) == 0

    def test_vbscript_blocked(self):
        issues = _check_protocol("vbscript:MsgBox")
        assert len(issues) == 1


# ── 6. Empty/Suspicious Checks ──


class TestCheckEmptySuspicious:
    def test_empty_string(self):
        issues = _check_empty_suspicious("")
        assert len(issues) == 1
        assert issues[0].category == "empty_href"

    def test_hash_only(self):
        issues = _check_empty_suspicious("#")
        assert len(issues) == 1
        assert issues[0].category == "empty_href"

    def test_javascript_void(self):
        issues = _check_empty_suspicious("javascript:void(0)")
        assert len(issues) == 1
        assert issues[0].category == "suspicious_protocol"

    def test_valid_url_no_issue(self):
        issues = _check_empty_suspicious("https://example.com")
        assert len(issues) == 0


# ── 7. Phishing Mismatch ──


class TestCheckPhishingMismatch:
    def test_action_text_no_issue(self):
        issues = _check_phishing_mismatch("https://example.com", "Shop now")
        assert len(issues) == 0

    def test_same_domain_no_issue(self):
        issues = _check_phishing_mismatch("https://example.com/sale", "https://example.com")
        assert len(issues) == 0

    def test_different_domain_phishing(self):
        issues = _check_phishing_mismatch("https://evil.com", "https://paypal.com")
        assert len(issues) == 1
        assert issues[0].category == "phishing_mismatch"

    def test_no_text_no_issue(self):
        issues = _check_phishing_mismatch("https://example.com", "")
        assert len(issues) == 0

    def test_www_stripped(self):
        """www. prefix should be stripped for comparison."""
        issues = _check_phishing_mismatch("https://www.example.com/page", "https://example.com")
        assert len(issues) == 0


# ── 8. Validate Links (Integration) ──


class TestValidateLinks:
    def test_valid_https_links(self):
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        result = validate_links(html)
        assert result.total_links == 1
        assert result.https_links == 1
        assert len(result.issues) == 0

    def test_http_link_flagged(self):
        html = '<html><body><a href="http://example.com">Link</a></body></html>'
        result = validate_links(html)
        assert result.http_links == 1
        non_https = [i for i in result.issues if i.category == "non_https"]
        assert len(non_https) == 1

    def test_empty_href(self):
        html = '<html><body><a href="">Link</a></body></html>'
        result = validate_links(html)
        assert result.empty_hrefs == 1
        empty = [i for i in result.issues if i.category == "empty_href"]
        assert len(empty) == 1

    def test_template_balanced_not_flagged(self):
        html = '<html><body><a href="{{ url }}">Link</a></body></html>'
        result = validate_links(html)
        assert result.template_links == 1
        assert len(result.issues) == 0

    def test_template_unbalanced_flagged(self):
        html = '<html><body><a href="{{ url }">Link</a></body></html>'
        result = validate_links(html)
        template_issues = [i for i in result.issues if i.category == "template_syntax"]
        assert len(template_issues) == 1

    def test_mixed_valid_and_invalid(self):
        html = """<html><body>
            <a href="https://good.com">Good</a>
            <a href="http://bad.com">Bad</a>
            <a href="">Empty</a>
        </body></html>"""
        result = validate_links(html)
        assert result.total_links == 3
        assert result.https_links == 1
        assert result.http_links == 1
        assert result.empty_hrefs == 1
        assert len(result.issues) >= 2  # non_https + empty_href

    def test_no_links(self):
        html = "<html><body><p>No links</p></body></html>"
        result = validate_links(html)
        assert result.total_links == 0

    def test_malformed_html_graceful(self):
        html = "<html><body><a href='https://example.com'>Link<a></body></html>"
        result = validate_links(html)
        # Should still parse without crashing
        assert result.total_links >= 1

    def test_link_with_image(self):
        html = '<html><body><a href="https://example.com"><img src="logo.png" alt="Logo"></a></body></html>'
        result = validate_links(html)
        assert result.links[0].has_img_child is True

    def test_javascript_href_blocked(self):
        html = '<html><body><a href="javascript:alert(1)">Click</a></body></html>'
        result = validate_links(html)
        blocked = [i for i in result.issues if i.category == "suspicious_protocol"]
        assert len(blocked) == 1

    def test_mailto_counted(self):
        html = '<html><body><a href="mailto:user@example.com">Email</a></body></html>'
        result = validate_links(html)
        assert result.mailto_links == 1
        assert len(result.issues) == 0

    def test_tel_counted(self):
        html = '<html><body><a href="tel:+15551234567">Call</a></body></html>'
        result = validate_links(html)
        assert result.tel_links == 1
        assert len(result.issues) == 0

    def test_empty_html(self):
        result = validate_links("")
        assert result.total_links == 0

    def test_localhost_http_not_flagged(self):
        html = '<html><body><a href="http://localhost:3000">Dev</a></body></html>'
        result = validate_links(html)
        non_https = [i for i in result.issues if i.category == "non_https"]
        assert len(non_https) == 0


# ── 9. Caching ──


class TestCaching:
    def test_cache_returns_same_result(self):
        from app.qa_engine.link_parser import get_cached_link_result

        clear_link_cache()
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        r1 = get_cached_link_result(html)
        r2 = get_cached_link_result(html)
        assert r1 is r2

    def test_clear_cache_forces_recompute(self):
        from app.qa_engine.link_parser import get_cached_link_result

        clear_link_cache()
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        r1 = get_cached_link_result(html)
        clear_link_cache()
        r2 = get_cached_link_result(html)
        assert r1 is not r2

    def test_different_html_different_results(self):
        from app.qa_engine.link_parser import get_cached_link_result

        clear_link_cache()
        html1 = '<html><body><a href="https://a.com">A</a></body></html>'
        html2 = '<html><body><a href="https://b.com">B</a></body></html>'
        r1 = get_cached_link_result(html1)
        r2 = get_cached_link_result(html2)
        assert r1 is not r2
