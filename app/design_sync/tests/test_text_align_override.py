"""Tests for Gap 11 / Phase 50.6 — text-align override from text-node attribute."""

from __future__ import annotations

from app.design_sync.component_matcher import (
    TokenOverride,
    _build_token_overrides,
)
from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    EmailSection,
    EmailSectionType,
    TextBlock,
)


def _section(*, texts: list[TextBlock]) -> EmailSection:
    return EmailSection(
        section_type=EmailSectionType.CONTENT,
        node_id="s1",
        node_name="section",
        column_layout=ColumnLayout.SINGLE,
        column_count=1,
        texts=texts,
    )


def test_heading_left_align() -> None:
    section = _section(
        texts=[TextBlock(node_id="t1", content="Hello", is_heading=True, text_align="LEFT")]
    )
    overrides = _build_token_overrides(section)
    assert TokenOverride("text-align", "_heading", "left") in overrides


def test_heading_right_align() -> None:
    section = _section(
        texts=[TextBlock(node_id="t1", content="Hello", is_heading=True, text_align="RIGHT")]
    )
    overrides = _build_token_overrides(section)
    assert TokenOverride("text-align", "_heading", "right") in overrides


def test_heading_center_align() -> None:
    section = _section(
        texts=[TextBlock(node_id="t1", content="Hello", is_heading=True, text_align="CENTER")]
    )
    overrides = _build_token_overrides(section)
    assert TokenOverride("text-align", "_heading", "center") in overrides


def test_body_align_emitted() -> None:
    section = _section(
        texts=[TextBlock(node_id="t1", content="Body copy", is_heading=False, text_align="LEFT")]
    )
    overrides = _build_token_overrides(section)
    assert TokenOverride("text-align", "_body", "left") in overrides


def test_no_emission_when_unset() -> None:
    section = _section(
        texts=[TextBlock(node_id="t1", content="Hello", is_heading=True, text_align=None)]
    )
    overrides = _build_token_overrides(section)
    assert not any(o.css_property == "text-align" for o in overrides)


def test_unknown_align_value_skipped() -> None:
    section = _section(
        texts=[
            TextBlock(node_id="t1", content="Hello", is_heading=True, text_align="JUSTIFY-FOOBAR")
        ]
    )
    overrides = _build_token_overrides(section)
    assert not any(o.css_property == "text-align" for o in overrides)
