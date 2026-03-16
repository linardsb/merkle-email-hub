"""Tests for HTML context offloading (Phase 1)."""

from app.ai.agents.html_summarizer import (
    extract_section,
    prepare_html_context,
    summarize_html,
)


class TestSummarizeHtml:
    def test_detects_mso_conditionals(self) -> None:
        html = "<html><!--[if gte mso 9]><table><![endif]--></html>"
        summary = summarize_html(html)
        assert "mso_conditionals" in summary.detected_patterns

    def test_detects_vml(self) -> None:
        html = "<html><v:roundrect>test</v:roundrect></html>"
        summary = summarize_html(html)
        assert "vml" in summary.detected_patterns

    def test_detects_dark_mode(self) -> None:
        html = "<style>@media (prefers-color-scheme: dark) { body { background: #000; } }</style>"
        summary = summarize_html(html)
        assert "dark_mode" in summary.detected_patterns

    def test_detects_personalization(self) -> None:
        html = "<html>Hello {{first_name}}</html>"
        summary = summarize_html(html)
        assert "personalization" in summary.detected_patterns

    def test_counts_lines_and_bytes(self) -> None:
        html = "line1\nline2\nline3"
        summary = summarize_html(html)
        assert summary.line_count == 3
        assert summary.byte_size == len(html.encode("utf-8"))

    def test_detects_section_boundaries(self) -> None:
        html = "<!-- START header --><div>...</div><!-- START footer --><div>...</div>"
        summary = summarize_html(html)
        assert summary.section_count >= 2
        assert len(summary.section_boundaries) >= 2


class TestPrepareHtmlContext:
    def test_short_html_returned_in_full(self) -> None:
        html = "<html><body>short</body></html>"
        result = prepare_html_context(html, max_chars=8000)
        assert result == html

    def test_long_html_gets_summary(self) -> None:
        html = "<html>" + "x" * 10000 + "</html>"
        result = prepare_html_context(html, max_chars=5000)
        assert "[HTML Summary:" in result
        assert "FIRST SECTION" in result
        assert "LAST SECTION" in result

    def test_summary_preserves_end_of_html(self) -> None:
        footer = "<!-- FOOTER CONTENT -->"
        html = "<html>" + "x" * 10000 + footer + "</html>"
        result = prepare_html_context(html, max_chars=5000)
        assert footer in result

    def test_exact_threshold_returns_full(self) -> None:
        html = "x" * 8000
        result = prepare_html_context(html, max_chars=8000)
        assert result == html

    def test_patterns_included_in_summary(self) -> None:
        html = "<!--[if gte mso 9]>" + "x" * 10000 + "<![endif]-->"
        result = prepare_html_context(html, max_chars=5000)
        assert "mso_conditionals" in result


class TestExtractSection:
    def test_extracts_by_index(self) -> None:
        html = "<!-- START header --><div>header</div><!-- START footer --><div>footer</div>"
        section = extract_section(html, 0)
        assert "header" in section

    def test_out_of_range_returns_empty(self) -> None:
        html = "<!-- START header --><div>only one</div>"
        assert extract_section(html, 99) == ""

    def test_negative_index_returns_empty(self) -> None:
        assert extract_section("<html>test</html>", -1) == ""

    def test_no_boundaries_returns_empty(self) -> None:
        assert extract_section("<html>no sections</html>", 0) == ""
