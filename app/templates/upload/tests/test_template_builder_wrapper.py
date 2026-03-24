"""Template builder wrapper reconstruction tests (Phase 31.8)."""

from __future__ import annotations

from app.ai.templates.models import DefaultTokens, TemplateSlot
from app.templates.upload.analyzer import WrapperInfo
from app.templates.upload.template_builder import TemplateBuilder


def _make_slots() -> tuple[TemplateSlot, ...]:
    return (
        TemplateSlot(
            slot_id="heading",
            slot_type="headline",
            selector="h1",
            required=True,
            placeholder="Heading",
        ),
    )


def _make_tokens() -> DefaultTokens:
    return DefaultTokens(
        colors={"background": "#ffffff", "text": "#333333"},
        fonts={"heading": "Arial"},
    )


class TestBuildWithWrapper:
    def test_wrapper_preserves_centering(self) -> None:
        """build() with wrapper metadata -> ensure_wrapper() adds centering."""
        wrapper = WrapperInfo(tag="table", width="600", align="center")
        html = "<html><body><table width='600'><tr><td>Content</td></tr></table></body></html>"
        tmpl = TemplateBuilder().build(
            sanitized_html=html,
            slots=_make_slots(),
            tokens=_make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
            wrapper=wrapper,
        )
        assert "max-width: 600px" in tmpl.html
        assert "margin: 0 auto" in tmpl.html

    def test_wrapper_metadata_dict_stored(self) -> None:
        wrapper = WrapperInfo(
            tag="table",
            width="600",
            align="center",
            cellpadding="0",
            cellspacing="0",
        )
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body><table><tr><td>X</td></tr></table></body></html>",
            slots=_make_slots(),
            tokens=_make_tokens(),
            layout_type="newsletter",
            column_count=1,
            sections=["body"],
            wrapper=wrapper,
        )
        assert tmpl.wrapper_metadata is not None
        assert tmpl.wrapper_metadata["width"] == "600"
        assert tmpl.wrapper_metadata["cellpadding"] == "0"

    def test_mso_wrapper_preserved(self) -> None:
        mso = '<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->'
        wrapper = WrapperInfo(tag="table", width="600", align="center", mso_wrapper=mso)
        tmpl = TemplateBuilder().build(
            sanitized_html="<html><body><table><tr><td>X</td></tr></table></body></html>",
            slots=_make_slots(),
            tokens=_make_tokens(),
            layout_type="promotional",
            column_count=1,
            sections=["hero"],
            wrapper=wrapper,
        )
        assert tmpl.wrapper_metadata is not None
        assert tmpl.wrapper_metadata.get("mso_wrapper") == mso


class TestBuildWithoutWrapper:
    def test_no_wrapper_html_stored_as_is(self) -> None:
        html = "<html><body><table><tr><td>Plain</td></tr></table></body></html>"
        tmpl = TemplateBuilder().build(
            sanitized_html=html,
            slots=_make_slots(),
            tokens=_make_tokens(),
            layout_type="minimal",
            column_count=1,
            sections=["body"],
        )
        assert tmpl.wrapper_metadata is None
        # HTML should not have centering injected
        assert "margin: 0 auto" not in tmpl.html
