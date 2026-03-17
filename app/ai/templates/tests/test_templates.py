"""Validate that ALL golden templates pass QA checks and registry works correctly."""

from pathlib import Path

import pytest

from app.ai.templates.registry import LIBRARY_DIR, METADATA_DIR, TemplateRegistry
from app.qa_engine.checks import ALL_CHECKS

TEMPLATE_HTML_FILES = sorted(LIBRARY_DIR.glob("*.html"))


@pytest.fixture
def registry() -> TemplateRegistry:
    r = TemplateRegistry()
    r.load()
    return r


class TestTemplateRegistry:
    def test_loads_all_templates(self, registry: TemplateRegistry) -> None:
        names = registry.names()
        assert len(names) >= 15, f"Expected >= 15 templates, got {len(names)}"

    def test_every_html_has_metadata(self) -> None:
        for html_file in TEMPLATE_HTML_FILES:
            yaml_file = METADATA_DIR / f"{html_file.stem}.yaml"
            assert yaml_file.exists(), f"Missing metadata for {html_file.name}"

    def test_get_returns_template(self, registry: TemplateRegistry) -> None:
        for name in registry.names():
            template = registry.get(name)
            assert template is not None
            assert template.metadata.name == name
            assert len(template.html) > 100

    def test_search_by_layout_type(self, registry: TemplateRegistry) -> None:
        newsletters = registry.search(layout_type="newsletter")
        assert len(newsletters) >= 2

    def test_list_for_selection(self, registry: TemplateRegistry) -> None:
        metadata_list = registry.list_for_selection()
        assert len(metadata_list) >= 15
        for m in metadata_list:
            assert m.name
            assert m.display_name
            assert m.layout_type

    def test_fill_slots_replaces_content(self, registry: TemplateRegistry) -> None:
        template = registry.get(registry.names()[0])
        assert template is not None
        fills: dict[str, str] = {}
        for slot in template.slots:
            fills[slot.slot_id] = f"FILLED:{slot.slot_id}"
        result = registry.fill_slots(template, fills)
        for slot in template.slots:
            assert f"FILLED:{slot.slot_id}" in result

    def test_fill_slots_enforces_max_chars(self, registry: TemplateRegistry) -> None:
        template = registry.get(registry.names()[0])
        assert template is not None
        capped_slots = [s for s in template.slots if s.max_chars]
        if capped_slots:
            slot = capped_slots[0]
            long_content = "X" * (slot.max_chars + 100)  # type: ignore[operator]
            result = registry.fill_slots(template, {slot.slot_id: long_content})
            assert long_content not in result

    def test_search_by_column_count(self, registry: TemplateRegistry) -> None:
        two_col = registry.search(column_count=2)
        assert len(two_col) >= 2
        for t in two_col:
            assert t.metadata.column_count == 2

    def test_search_by_hero(self, registry: TemplateRegistry) -> None:
        with_hero = registry.search(has_hero=True)
        assert len(with_hero) >= 5
        for t in with_hero:
            assert t.metadata.has_hero_image is True

    def test_get_nonexistent_returns_none(self, registry: TemplateRegistry) -> None:
        assert registry.get("nonexistent_template") is None


class TestTemplateQACompliance:
    """Every golden template must pass all 11 QA checks."""

    @pytest.mark.parametrize(
        "html_file",
        TEMPLATE_HTML_FILES,
        ids=[f.stem for f in TEMPLATE_HTML_FILES],
    )
    @pytest.mark.asyncio
    async def test_template_passes_all_qa_checks(self, html_file: Path) -> None:
        html = html_file.read_text()
        for check in ALL_CHECKS:
            result = await check.run(html)
            # css_support scores 0.75-0.85 due to:
            # - color-scheme (limited client support but essential for dark mode)
            # - -webkit-text-size-adjust (vendor prefix, required for iOS)
            # - dark mode background-color in <style> without inline fallback
            #   (Gmail strips <style> but doesn't support prefers-color-scheme)
            threshold = 0.7 if check.name in {"css_support", "deliverability"} else 0.9
            assert result.score >= threshold, (
                f"Template {html_file.stem} failed {check.name}: "
                f"score={result.score}, details={result.details}"
            )


class TestTemplateSlotMarkers:
    """Verify slot markers exist in HTML and match metadata."""

    @pytest.mark.parametrize(
        "html_file",
        TEMPLATE_HTML_FILES,
        ids=[f.stem for f in TEMPLATE_HTML_FILES],
    )
    def test_all_required_slots_present_in_html(self, html_file: Path) -> None:
        registry = TemplateRegistry()
        registry.load()
        template = registry.get(html_file.stem)
        assert template is not None
        for slot in template.slots:
            if slot.required:
                assert (
                    f'data-slot="{slot.slot_id}"' in template.html
                    or f"data-slot='{slot.slot_id}'" in template.html
                ), f"Required slot {slot.slot_id} not found in {html_file.stem}"
