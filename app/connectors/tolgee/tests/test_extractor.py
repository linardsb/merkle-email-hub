"""Unit tests for Tolgee translation key extraction."""

from __future__ import annotations

from app.connectors.tolgee.extractor import extract_keys


class TestExtractKeys:
    """Tests for extract_keys function."""

    def test_basic_extraction(self) -> None:
        """Extracts keys from common email elements."""
        html = """
        <html><body>
            <h1>Welcome to our newsletter</h1>
            <p>Check out our latest deals</p>
            <td>Free shipping on orders over $50</td>
            <a href="https://example.com">Shop Now</a>
        </body></html>
        """
        keys = extract_keys(html, template_id=42)
        assert len(keys) >= 4
        key_names = [k.key for k in keys]
        assert any("h1" in k for k in key_names)
        assert any("p" in k for k in key_names)
        assert any("td" in k for k in key_names)
        assert any("a" in k for k in key_names)

    def test_attribute_extraction(self) -> None:
        """Extracts translatable attributes (alt, title)."""
        html = '<html><body><img alt="Product image" title="Click to view"></body></html>'
        keys = extract_keys(html, template_id=1)
        texts = [k.source_text for k in keys]
        assert "Product image" in texts
        assert "Click to view" in texts

    def test_skip_urls(self) -> None:
        """URLs are skipped."""
        html = "<html><body><td>https://example.com/page</td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 0

    def test_skip_email_addresses(self) -> None:
        """Email addresses are skipped."""
        html = "<html><body><td>user@example.com</td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 0

    def test_skip_template_tokens(self) -> None:
        """ESP template tokens (Liquid, Handlebars) are skipped."""
        html = "<html><body><td>{{ user.name }}</td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 0

    def test_skip_whitespace_only(self) -> None:
        """Whitespace-only content is skipped."""
        html = "<html><body><td>   </td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 0

    def test_skip_numbers(self) -> None:
        """Pure numbers/percentages are skipped."""
        html = "<html><body><td>42</td><td>99.9%</td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 0

    def test_icu_preservation(self) -> None:
        """ICU message format is extracted with context hint."""
        html = "<html><body><td>{count, plural, one {# item} other {# items}}</td></body></html>"
        keys = extract_keys(html, template_id=1)
        assert len(keys) == 1
        assert keys[0].context is not None
        assert "ICU" in keys[0].context

    def test_subject_and_preheader(self) -> None:
        """Subject and preheader are extracted as meta keys."""
        html = "<html><body><td>Content</td></body></html>"
        keys = extract_keys(
            html,
            template_id=5,
            subject="Welcome aboard!",
            preheader="Your journey starts here",
        )
        meta_keys = [k for k in keys if ".meta." in k.key]
        assert len(meta_keys) == 2
        subjects = [k for k in meta_keys if "subject" in k.key]
        assert len(subjects) == 1
        assert subjects[0].source_text == "Welcome aboard!"

    def test_section_tracking(self) -> None:
        """data-section attributes update key prefixes."""
        html = """
        <html><body>
            <div data-section="hero"><td>Hero text</td></div>
            <div data-section="footer"><td>Footer text</td></div>
        </body></html>
        """
        keys = extract_keys(html, template_id=1)
        key_names = [k.key for k in keys]
        assert any("hero" in k for k in key_names)
        assert any("footer" in k for k in key_names)

    def test_deduplication(self) -> None:
        """Multiple elements generate unique keys."""
        html = """
        <html><body>
            <td>First cell</td>
            <td>Second cell</td>
        </body></html>
        """
        keys = extract_keys(html, template_id=1)
        key_names = [k.key for k in keys]
        assert len(key_names) == len(set(key_names)), "Keys should be unique"

    def test_non_visible_elements_skipped(self) -> None:
        """Content in style, script, head elements is skipped."""
        html = """
        <html>
        <head><title>Do not extract</title></head>
        <body>
            <style>body { color: red; }</style>
            <script>alert('test')</script>
            <td>Visible content</td>
        </body></html>
        """
        keys = extract_keys(html, template_id=1)
        texts = [k.source_text for k in keys]
        assert "Visible content" in texts
        assert "Do not extract" not in texts
        assert "body { color: red; }" not in texts

    def test_empty_html(self) -> None:
        """Empty or minimal HTML returns empty list."""
        assert extract_keys("", template_id=1) == []
        assert extract_keys("<html><body></body></html>", template_id=1) == []

    def test_namespace_propagation(self) -> None:
        """Custom namespace propagates to all keys."""
        html = "<html><body><td>Hello</td></body></html>"
        keys = extract_keys(html, template_id=1, namespace="marketing")
        assert all(k.namespace == "marketing" for k in keys)

    def test_real_email_template(self) -> None:
        """Extracts multiple keys from a representative email HTML."""
        html = """
        <html><body>
        <table>
            <tr><td data-section="header">
                <h1>Spring Sale Event</h1>
                <p>Save up to 50% on selected items</p>
            </td></tr>
            <tr><td data-section="hero">
                <h2>New Arrivals</h2>
                <p>Discover our latest collection of premium products</p>
                <a href="https://example.com">Shop the Collection</a>
            </td></tr>
            <tr><td data-section="products">
                <td>Premium Wireless Headphones</td>
                <td>Ultra-Slim Laptop Stand</td>
                <td>Ergonomic Mouse Pad</td>
                <span>Starting from $29.99</span>
            </td></tr>
            <tr><td data-section="footer">
                <p>Unsubscribe from our mailing list</p>
                <span>123 Commerce Street, NY 10001</span>
            </td></tr>
        </table>
        </body></html>
        """
        keys = extract_keys(
            html,
            template_id=99,
            subject="Spring Sale — Up to 50% Off!",
            preheader="Don't miss our biggest sale of the season",
        )
        # Should have subject + preheader + multiple content keys
        assert len(keys) >= 10
