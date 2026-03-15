"""Tests for SectionAdapter — component -> section bridge."""

from unittest.mock import MagicMock

import pytest

from app.ai.templates.composer import SectionBlock
from app.ai.templates.models import TemplateSlot
from app.components.section_adapter import (
    AdaptationError,
    SectionAdapter,
    SlotHint,
    _inject_slot_markers,
)
from app.qa_engine.schemas import QACheckResult


def _make_version(
    *,
    component_id: int = 1,
    version_id: int = 10,
    version_number: int = 1,
    html_source: str = '<div class="header"><h1>Title</h1></div>',
) -> MagicMock:
    """Create a mock ComponentVersion."""
    v = MagicMock()
    v.id = version_id
    v.component_id = component_id
    v.version_number = version_number
    v.html_source = html_source
    return v


def _make_slot_hint(
    slot_id: str = "main_headline",
    slot_type: str = "headline",
    selector: str = "h1",
) -> SlotHint:
    return SlotHint(
        slot_id=slot_id,
        slot_type=slot_type,  # type: ignore[arg-type]
        selector=selector,
        required=True,
        max_chars=80,
    )


class TestSectionAdapterAdapt:
    """Tests for SectionAdapter.adapt()."""

    def test_happy_path_returns_section_block(self) -> None:
        adapter = SectionAdapter()
        version = _make_version()
        hints = [_make_slot_hint()]

        block = adapter.adapt(version, hints)

        assert isinstance(block, SectionBlock)
        assert block.block_id == "component_1_v1"
        assert block.display_name == "Component #1 v1"
        assert len(block.slot_definitions) == 1
        assert block.slot_definitions[0].slot_id == "main_headline"

    def test_data_slot_marker_injected(self) -> None:
        adapter = SectionAdapter()
        version = _make_version()
        hints = [_make_slot_hint()]

        block = adapter.adapt(version, hints)

        assert 'data-slot="main_headline"' in block.html

    def test_slot_definitions_become_template_slots(self) -> None:
        adapter = SectionAdapter()
        version = _make_version()
        hints = [_make_slot_hint()]

        block = adapter.adapt(version, hints)

        slot = block.slot_definitions[0]
        assert isinstance(slot, TemplateSlot)
        assert slot.slot_type == "headline"
        assert slot.required is True
        assert slot.max_chars == 80

    def test_script_tags_stripped(self) -> None:
        adapter = SectionAdapter()
        version = _make_version(
            html_source='<div><h1>Title</h1><script>alert("xss")</script></div>'
        )
        hints = [_make_slot_hint()]

        block = adapter.adapt(version, hints)

        assert "<script>" not in block.html
        assert "alert" not in block.html

    def test_selector_miss_logs_warning_no_crash(self) -> None:
        adapter = SectionAdapter()
        version = _make_version()
        hints = [_make_slot_hint(selector=".nonexistent-class")]

        block = adapter.adapt(version, hints)

        assert isinstance(block, SectionBlock)
        assert "data-slot" not in block.html

    def test_multiple_slots(self) -> None:
        html = '<div><h1>Title</h1><p class="body">Body text</p></div>'
        adapter = SectionAdapter()
        version = _make_version(html_source=html)
        hints = [
            _make_slot_hint(slot_id="title", selector="h1"),
            _make_slot_hint(slot_id="body_text", slot_type="body", selector="p.body"),
        ]

        block = adapter.adapt(version, hints)

        assert len(block.slot_definitions) == 2
        assert 'data-slot="title"' in block.html
        assert 'data-slot="body_text"' in block.html


class TestValidateForComposition:
    """Tests for SectionAdapter.validate_for_composition()."""

    def test_passes_with_high_scores(self) -> None:
        adapter = SectionAdapter()
        block = SectionBlock(
            block_id="test",
            display_name="Test",
            html="<div></div>",
            slot_definitions=(),
        )
        results = [
            QACheckResult(check_name="html_validation", passed=True, score=0.95),
            QACheckResult(check_name="accessibility", passed=True, score=0.85),
        ]

        returned = adapter.validate_for_composition(block, results)
        assert returned == results

    def test_raises_on_low_score(self) -> None:
        adapter = SectionAdapter()
        block = SectionBlock(
            block_id="test",
            display_name="Test",
            html="<div></div>",
            slot_definitions=(),
        )
        results = [
            QACheckResult(check_name="html_validation", passed=False, score=0.5),
            QACheckResult(check_name="accessibility", passed=False, score=0.6),
        ]

        with pytest.raises(AdaptationError, match=r"QA score 0\.55"):
            adapter.validate_for_composition(block, results)

    def test_raises_on_empty_results(self) -> None:
        adapter = SectionAdapter()
        block = SectionBlock(
            block_id="test",
            display_name="Test",
            html="<div></div>",
            slot_definitions=(),
        )

        with pytest.raises(AdaptationError, match="No QA results"):
            adapter.validate_for_composition(block, [])


class TestInjectSlotMarkers:
    """Tests for _inject_slot_markers helper."""

    def test_injects_data_slot_attribute(self) -> None:
        html = "<div><h1>Hello</h1></div>"
        hints = [_make_slot_hint(selector="h1")]

        result = _inject_slot_markers(html, hints)

        assert 'data-slot="main_headline"' in result

    def test_empty_hints_returns_unchanged(self) -> None:
        html = "<div><h1>Hello</h1></div>"

        result = _inject_slot_markers(html, [])

        assert result == html

    def test_invalid_html_returns_unchanged(self) -> None:
        html = ""
        hints = [_make_slot_hint()]

        result = _inject_slot_markers(html, hints)
        assert isinstance(result, str)
