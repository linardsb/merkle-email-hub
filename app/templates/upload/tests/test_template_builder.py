"""Tests for GoldenTemplate builder (Phase 25.10)."""

from __future__ import annotations

from app.ai.templates.models import DefaultTokens, TemplateSlot
from app.templates.upload.template_builder import TemplateBuilder


class TestTemplateBuilder:
    def _make_slots(self) -> tuple[TemplateSlot, ...]:
        return (
            TemplateSlot(
                slot_id="hero_heading",
                slot_type="headline",
                selector="h1",
                required=True,
                placeholder="Heading",
            ),
            TemplateSlot(
                slot_id="hero_image",
                slot_type="image",
                selector="img.hero",
                required=True,
                placeholder="",
            ),
            TemplateSlot(
                slot_id="body_text",
                slot_type="body",
                selector="p.body",
                required=False,
                placeholder="Body",
            ),
        )

    def _make_tokens(self) -> DefaultTokens:
        return DefaultTokens(
            colors={"background": "#ffffff", "text": "#333333", "cta": "#0066cc"},
            fonts={"heading": "Arial", "body": "Georgia"},
        )

    def test_uploaded_prefix(self) -> None:
        """Template name gets 'uploaded_' prefix."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Test</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
            name="my_promo",
        )
        assert tmpl.metadata.name.startswith("uploaded_")

    def test_source_is_uploaded(self) -> None:
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Test</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="newsletter",
            column_count=2,
            sections=["hero", "body"],
        )
        assert tmpl.source == "uploaded"

    def test_auto_name_generation(self) -> None:
        """When name=None, generates hash-based name."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Auto named</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="transactional",
            column_count=1,
            sections=["hero"],
        )
        assert tmpl.metadata.name.startswith("uploaded_")
        assert len(tmpl.metadata.name) > len("uploaded_")

    def test_hero_image_detection(self) -> None:
        """Required image slot -> has_hero_image=True."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Hero</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
        )
        assert tmpl.metadata.has_hero_image is True

    def test_no_hero_without_image_slot(self) -> None:
        """No required image slot -> has_hero_image=False."""
        slots = (
            TemplateSlot(
                slot_id="heading",
                slot_type="headline",
                selector="h1",
                required=True,
                placeholder="Hi",
            ),
        )
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>No hero</body></html>",
            slots=slots,
            tokens=self._make_tokens(),
            layout_type="transactional",
            column_count=1,
            sections=["main"],
        )
        assert tmpl.metadata.has_hero_image is False

    def test_empty_slots_allowed(self) -> None:
        """Builder handles templates with no detected slots."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Minimal</body></html>",
            slots=(),
            tokens=self._make_tokens(),
            layout_type="minimal",
            column_count=1,
            sections=["body"],
        )
        assert len(tmpl.slots) == 0

    def test_description_override(self) -> None:
        """Custom description is preserved."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Desc</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
            description="My custom description",
        )
        assert tmpl.metadata.description == "My custom description"

    def test_wrapper_metadata_stored(self) -> None:
        """Wrapper metadata is persisted on GoldenTemplate."""
        from app.templates.upload.analyzer import WrapperInfo

        wrapper = WrapperInfo(
            tag="table",
            width="600",
            align="center",
            bgcolor="#ffffff",
        )
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body><table width='600'><tr><td>Hi</td></tr></table></body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
            wrapper=wrapper,
        )
        assert tmpl.wrapper_metadata is not None
        assert tmpl.wrapper_metadata["width"] == "600"
        assert tmpl.wrapper_metadata["align"] == "center"
        assert tmpl.wrapper_metadata["bgcolor"] == "#ffffff"

    def test_no_wrapper_metadata_when_none(self) -> None:
        """No wrapper -> wrapper_metadata is None."""
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body>Test</body></html>",
            slots=self._make_slots(),
            tokens=self._make_tokens(),
            layout_type="newsletter",
            column_count=1,
            sections=["body"],
        )
        assert tmpl.wrapper_metadata is None

    def test_ensure_wrapper_adds_centering(self) -> None:
        """HTML without centering gets wrapper injected."""
        from app.templates.upload.analyzer import WrapperInfo

        wrapper = WrapperInfo(tag="table", width="600", align="center")
        html = "<html><body><table width='600'><tr><td>Content</td></tr></table></body></html>"
        tmpl = TemplateBuilder().build(
            sanitized_html=html,
            slots=(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["content"],
            wrapper=wrapper,
        )
        assert "max-width: 600px" in tmpl.html
        assert "margin: 0 auto" in tmpl.html

    def test_ensure_wrapper_no_double_wrap(self) -> None:
        """HTML that already has centering is not double-wrapped."""
        from app.templates.upload.analyzer import WrapperInfo

        wrapper = WrapperInfo(tag="table", width="600", align="center")
        html = (
            "<html><body>"
            '<table width="600" align="center"><tr><td>'
            '<table width="600"><tr><td>Content</td></tr></table>'
            "</td></tr></table>"
            "</body></html>"
        )
        tmpl = TemplateBuilder().build(
            sanitized_html=html,
            slots=(),
            tokens=self._make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["content"],
            wrapper=wrapper,
        )
        # Should not add a second wrapper
        assert tmpl.html.count("margin: 0 auto") <= 1
