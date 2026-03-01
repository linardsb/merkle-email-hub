"""Unit tests for component HTML sanitization."""

from app.components.sanitize import sanitize_component_html


def test_strips_script_tags() -> None:
    html = '<table><tr><td><script>alert("xss")</script>Safe</td></tr></table>'
    result = sanitize_component_html(html)
    assert "<script>" not in result
    assert "alert" not in result
    assert "Safe" in result


def test_strips_event_handlers() -> None:
    html = '<table onclick="steal()" onmouseover="bad()"><tr><td>Content</td></tr></table>'
    result = sanitize_component_html(html)
    assert "onclick" not in result
    assert "onmouseover" not in result
    assert "Content" in result


def test_strips_javascript_protocol() -> None:
    html = '<a href="javascript:alert(1)">Link</a>'
    result = sanitize_component_html(html)
    assert "javascript:" not in result
    assert "Link" in result


def test_strips_iframe_tags() -> None:
    html = '<table><tr><td>Before</td></tr></table><iframe src="evil.com"></iframe><p>After</p>'
    result = sanitize_component_html(html)
    assert "<iframe" not in result
    assert "Before" in result
    assert "After" in result


def test_strips_data_uris() -> None:
    html = '<img src="data:text/html,<script>alert(1)</script>" />'
    result = sanitize_component_html(html)
    assert "data:" not in result


def test_preserves_mso_conditionals() -> None:
    html = """\
<!--[if mso]>
<table role="presentation" width="600"><tr><td>
<![endif]-->
<table><tr><td>Content</td></tr></table>
<!--[if mso]>
</td></tr></table>
<![endif]-->"""
    result = sanitize_component_html(html)
    assert "<!--[if mso]>" in result
    assert "<![endif]-->" in result
    assert "Content" in result


def test_preserves_dark_mode_css() -> None:
    html = """\
<style>
  @media (prefers-color-scheme: dark) {
    .header { background-color: #1a1a2e !important; }
  }
  [data-ogsc] .header { background-color: #1a1a2e !important; }
</style>
<table><tr><td>Content</td></tr></table>"""
    result = sanitize_component_html(html)
    assert "prefers-color-scheme: dark" in result
    assert "[data-ogsc]" in result
    assert "#1a1a2e" in result


def test_preserves_inline_styles() -> None:
    html = '<td style="padding: 20px; background-color: #ffffff; font-family: Arial, sans-serif;">Text</td>'
    result = sanitize_component_html(html)
    assert (
        'style="padding: 20px; background-color: #ffffff; font-family: Arial, sans-serif;"'
        in result
    )


def test_passthrough_clean_html() -> None:
    clean = '<table role="presentation"><tr><td style="padding: 10px;">Hello</td></tr></table>'
    result = sanitize_component_html(clean)
    assert result == clean
