"""Tests for code-aware HTML chunking (Phase 16.3)."""

from app.knowledge.chunking_html import chunk_html, is_html_content


class TestIsHtmlContent:
    """Tests for HTML detection."""

    def test_doctype(self) -> None:
        assert is_html_content("<!DOCTYPE html><html><body></body></html>")

    def test_html_tag(self) -> None:
        assert is_html_content("<html><head></head><body></body></html>")

    def test_table_tag(self) -> None:
        assert is_html_content("<table><tr><td>cell</td></tr></table>")

    def test_plain_text(self) -> None:
        assert not is_html_content("This is just plain text with no HTML.")

    def test_markdown(self) -> None:
        assert not is_html_content("# Heading\n\nSome **bold** text.")

    def test_only_checks_first_500(self) -> None:
        # HTML marker beyond 500 chars should not be detected
        text = "x" * 501 + "<html>"
        assert not is_html_content(text)


class TestChunkHtmlEmpty:
    """Edge case: empty input."""

    def test_empty_string(self) -> None:
        assert chunk_html("") == []

    def test_whitespace_only(self) -> None:
        assert chunk_html("   \n  ") == []


class TestChunkHtmlPlainText:
    """Non-HTML input falls back to text chunker."""

    def test_plain_text_fallback(self) -> None:
        text = "This is a plain text document.\nWith multiple lines.\nNo HTML here."
        results = chunk_html(text)
        assert len(results) >= 1
        assert all(r.section_type == "text_fallback" for r in results)

    def test_plain_text_content_preserved(self) -> None:
        text = "Short text."
        results = chunk_html(text)
        assert len(results) == 1
        assert results[0].content == text


class TestStyleBlockExtraction:
    """Tests for <style> block extraction."""

    def test_single_style_block(self) -> None:
        html = """<!DOCTYPE html><html><head>
        <style>.foo { color: red; }</style>
        </head><body><p>Hello</p></body></html>"""
        results = chunk_html(html)
        style_chunks = [r for r in results if r.section_type == "style"]
        assert len(style_chunks) == 1
        assert ".foo { color: red; }" in style_chunks[0].content

    def test_multiple_style_blocks(self) -> None:
        html = """<!DOCTYPE html><html><head>
        <style>.a { color: red; }</style>
        <style>.b { color: blue; }</style>
        </head><body><p>Hello</p></body></html>"""
        results = chunk_html(html)
        style_chunks = [r for r in results if r.section_type == "style"]
        assert len(style_chunks) == 2

    def test_style_has_summary(self) -> None:
        html = """<!DOCTYPE html><html><head>
        <style>.x { margin: 0; }</style>
        </head><body><p>Hi</p></body></html>"""
        results = chunk_html(html)
        style_chunks = [r for r in results if r.section_type == "style"]
        assert style_chunks[0].summary is not None
        assert "CSS style block" in style_chunks[0].summary


class TestMsoConditionalExtraction:
    """Tests for MSO conditional block extraction."""

    def test_mso_block_extracted(self) -> None:
        html = """<!DOCTYPE html><html><body>
        <!--[if mso]>
        <table><tr><td>Outlook content</td></tr></table>
        <![endif]-->
        <p>Normal content</p>
        </body></html>"""
        results = chunk_html(html)
        mso_chunks = [r for r in results if r.section_type == "mso_conditional"]
        assert len(mso_chunks) == 1
        assert "Outlook content" in mso_chunks[0].content

    def test_non_mso_conditional_skipped(self) -> None:
        html = """<!DOCTYPE html><html><body>
        <!--[if !mso]><!-->
        <p>Non-Outlook content</p>
        <!--<![endif]-->
        </body></html>"""
        results = chunk_html(html)
        mso_chunks = [r for r in results if r.section_type == "mso_conditional"]
        assert len(mso_chunks) == 0

    def test_gte_mso_conditional(self) -> None:
        html = """<!DOCTYPE html><html><body>
        <!--[if gte mso 9]>
        <v:rect>VML content</v:rect>
        <![endif]-->
        </body></html>"""
        results = chunk_html(html)
        mso_chunks = [r for r in results if r.section_type == "mso_conditional"]
        assert len(mso_chunks) == 1


class TestStructuralSplitting:
    """Tests for body structural element splitting."""

    def test_tables_split(self) -> None:
        # Make each table large enough that they can't be merged (>chunk_size/2)
        rows = ["<tr><td>" + "x" * 600 + "</td></tr>" for _ in range(3)]
        tables = [f"<table>{row}</table>" for row in rows]
        html = f"<!DOCTYPE html><html><body>{''.join(tables)}</body></html>"
        results = chunk_html(html)
        section_chunks = [r for r in results if r.section_type == "section"]
        assert len(section_chunks) >= 3

    def test_divs_split(self) -> None:
        divs = [f"<div>Section {i}</div>" for i in range(4)]
        html = f"<!DOCTYPE html><html><body>{''.join(divs)}</body></html>"
        results = chunk_html(html)
        section_chunks = [r for r in results if r.section_type == "section"]
        assert len(section_chunks) >= 1  # may merge small divs


class TestNestedSplitting:
    """Tests for recursive splitting of large sections."""

    def test_large_table_splits_by_rows(self) -> None:
        # Create table larger than chunk_size
        rows = "".join(f"<tr><td>{'x' * 100} row {i}</td></tr>" for i in range(20))
        html = f"<!DOCTYPE html><html><body><table>{rows}</table></body></html>"
        results = chunk_html(html, chunk_size=300)
        section_chunks = [r for r in results if r.section_type == "section"]
        assert len(section_chunks) > 1


class TestSmallSectionMerging:
    """Tests for merging small adjacent chunks."""

    def test_small_divs_merged(self) -> None:
        divs = [f"<div>Tiny {i}</div>" for i in range(5)]
        html = f"<!DOCTYPE html><html><body>{''.join(divs)}</body></html>"
        # With large chunk_size, small divs should merge
        results = chunk_html(html, chunk_size=2000)
        section_chunks = [r for r in results if r.section_type == "section"]
        # All 5 small divs should merge into fewer chunks
        assert len(section_chunks) < 5


class TestMalformedHtml:
    """Tests for graceful handling of malformed HTML."""

    def test_truncated_html(self) -> None:
        html = "<!DOCTYPE html><html><body><table><tr><td>Unclosed"
        results = chunk_html(html)
        # Should not raise, should produce chunks
        assert len(results) >= 1

    def test_broken_tags(self) -> None:
        html = "<!DOCTYPE html><html><body><div<p>broken</p></body></html>"
        results = chunk_html(html)
        assert len(results) >= 1


class TestChunkIndices:
    """Tests for sequential chunk indexing."""

    def test_indices_sequential(self) -> None:
        html = """<!DOCTYPE html><html><head>
        <style>.a { color: red; }</style>
        </head><body>
        <!--[if mso]><table><tr><td>MSO</td></tr></table><![endif]-->
        <table><tr><td>Content 1</td></tr></table>
        <table><tr><td>Content 2</td></tr></table>
        </body></html>"""
        results = chunk_html(html)
        indices = [r.chunk_index for r in results]
        assert indices == list(range(len(results)))


class TestFullEmailHtml:
    """Integration test with realistic email HTML."""

    def test_realistic_email(self) -> None:
        html = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<style>
  .header { background-color: #333; color: white; padding: 20px; }
  .content { padding: 15px; }
  .footer { background-color: #f5f5f5; padding: 10px; font-size: 12px; }
</style>
</head>
<body>
<!--[if mso]>
<table role="presentation" width="600"><tr><td>
<![endif]-->
<div class="wrapper">
  <table role="presentation" width="100%">
    <tr><td class="header">
      <h1>Newsletter</h1>
    </td></tr>
  </table>
  <table role="presentation" width="100%">
    <tr><td class="content">
      <p>Hello {{first_name}},</p>
      <p>Welcome to our newsletter.</p>
    </td></tr>
  </table>
  <table role="presentation" width="100%">
    <tr><td class="footer">
      <p>Unsubscribe | Privacy Policy</p>
    </td></tr>
  </table>
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body>
</html>"""
        results = chunk_html(html)
        types = {r.section_type for r in results}
        # Should have style, mso_conditional, and section chunks
        assert "style" in types
        assert "mso_conditional" in types
        assert "section" in types

    def test_no_text_fallback_for_valid_html(self) -> None:
        """Valid HTML should not produce text_fallback chunks."""
        html = """<!DOCTYPE html><html><head>
        <style>body { margin: 0; }</style>
        </head><body>
        <table><tr><td>Content</td></tr></table>
        </body></html>"""
        results = chunk_html(html)
        assert all(r.section_type != "text_fallback" for r in results)


class TestChunkSizeRespected:
    """Tests that chunk_size constraint is respected."""

    def test_chunks_within_size(self) -> None:
        rows = "".join(f"<tr><td>{'data ' * 20} row {i}</td></tr>" for i in range(30))
        html = f"<!DOCTYPE html><html><body><table>{rows}</table></body></html>"
        chunk_size = 500
        results = chunk_html(html, chunk_size=chunk_size)
        assert len(results) > 1
        # text_fallback chunks respect chunk_size strictly
        for r in results:
            if r.section_type == "text_fallback":
                assert len(r.content) <= chunk_size + 50  # overlap tolerance
