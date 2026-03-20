"""Unit tests for import annotator service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.import_annotator.exceptions import ImportAnnotationError
from app.ai.agents.import_annotator.schemas import AnnotationDecision, ImportAnnotationResult
from app.ai.agents.import_annotator.service import ImportAnnotatorService


class TestImportAnnotatorService:
    def setup_method(self) -> None:
        self.service = ImportAnnotatorService()

    @pytest.mark.asyncio
    async def test_already_annotated_html_returns_unchanged(self) -> None:
        html = '<div data-section-id="abc">content</div>'
        result = await self.service.annotate(html)
        assert result["annotated_html"] == html
        assert len(result["warnings"]) == 1
        assert "already contains" in result["warnings"][0]
        assert result["sections"] == []

    @pytest.mark.asyncio
    async def test_oversized_html_raises_error(self) -> None:
        html = "x" * (2 * 1024 * 1024 + 1)
        with pytest.raises(ImportAnnotationError, match="2MB"):
            await self.service.annotate(html)

    def test_parse_annotation_result_valid_json(self) -> None:
        raw = (
            '{"annotations": [{"section_id": "s1", "component_name": "Header",'
            ' "element_selector": "body > table", "layout_type": "single",'
            ' "confidence": 0.9, "reasoning": "top section"}],'
            ' "warnings": [], "overall_confidence": 0.9, "reasoning": "clear layout"}'
        )
        result = self.service._parse_annotation_result(raw)
        assert len(result.annotations) == 1
        assert result.annotations[0].component_name == "Header"
        assert result.annotations[0].section_id == "s1"
        assert result.overall_confidence == 0.9

    def test_parse_annotation_result_code_fences(self) -> None:
        raw = '```json\n{"annotations": [], "warnings": [], "overall_confidence": 0.5, "reasoning": ""}\n```'
        result = self.service._parse_annotation_result(raw)
        assert len(result.annotations) == 0
        assert result.overall_confidence == 0.5

    def test_parse_annotation_result_invalid_json(self) -> None:
        with pytest.raises(ImportAnnotationError, match="Failed to parse"):
            self.service._parse_annotation_result("not json at all")

    def test_apply_annotations_sets_data_attributes(self) -> None:
        html = "<html><body><table><tr><td>Hello</td></tr></table></body></html>"
        annotations = (
            AnnotationDecision(
                section_id="sec-1",
                component_name="Content",
                element_selector="table",
                layout_type="single",
                confidence=0.9,
                reasoning="test",
            ),
        )
        result_obj = ImportAnnotationResult(
            annotations=annotations,
            overall_confidence=0.9,
            reasoning="test",
        )
        result_html = self.service._apply_annotations(html, result_obj)
        assert 'data-section-id="sec-1"' in result_html
        assert 'data-component-name="Content"' in result_html

    def test_apply_annotations_columns_layout(self) -> None:
        html = "<html><body><table><tr><td>A</td><td>B</td></tr></table></body></html>"
        annotations = (
            AnnotationDecision(
                section_id="col-1",
                component_name="Columns",
                element_selector="tr",
                layout_type="columns",
                confidence=0.8,
                reasoning="multi-column",
            ),
        )
        result_obj = ImportAnnotationResult(annotations=annotations, overall_confidence=0.8)
        result_html = self.service._apply_annotations(html, result_obj)
        assert 'data-section-layout="columns"' in result_html

    def test_apply_annotations_preserves_esp_tokens(self) -> None:
        """ESP tokens must survive lxml parse/serialize roundtrip."""
        html = (
            "<html><body><table><tbody>"
            "<tr><td>{{ name }}</td></tr>"
            "<tr><td>%%=v(@var)=%%</td></tr>"
            "</tbody></table></body></html>"
        )
        annotations = (
            AnnotationDecision(
                section_id="esp-1",
                component_name="Content",
                element_selector="table",
                layout_type="single",
                confidence=0.9,
                reasoning="test",
            ),
        )
        result_obj = ImportAnnotationResult(annotations=annotations, overall_confidence=0.9)
        result_html = self.service._apply_annotations(html, result_obj)
        assert "{{ name }}" in result_html
        assert "%%=v(@var)=%%" in result_html
        assert 'data-section-id="esp-1"' in result_html

    def test_apply_annotations_returns_original_when_none_applied(self) -> None:
        html = "<html><body><p>Simple</p></body></html>"
        annotations = (
            AnnotationDecision(
                section_id="missing",
                component_name="Content",
                element_selector=".nonexistent-class",
                layout_type="single",
                confidence=0.5,
                reasoning="test",
            ),
        )
        result_obj = ImportAnnotationResult(annotations=annotations, overall_confidence=0.5)
        result_html = self.service._apply_annotations(html, result_obj)
        assert result_html == html  # Original returned unchanged

    @pytest.mark.asyncio
    async def test_fallback_on_provider_failure(self) -> None:
        """If LLM call fails, return original HTML unchanged."""
        html = "<html><body><table><tr><td>Hello</td></tr></table></body></html>"
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value.complete = AsyncMock(side_effect=Exception("LLM down"))
        with (
            patch(
                "app.ai.agents.import_annotator.service.get_registry", return_value=mock_registry
            ),
            patch("app.ai.agents.import_annotator.service.get_fallback_chain", return_value=None),
            patch("app.ai.agents.import_annotator.service.get_settings"),
            patch(
                "app.ai.agents.import_annotator.service.resolve_model", return_value="test-model"
            ),
        ):
            result = await self.service.annotate(html)
            assert result["annotated_html"] == html
            assert len(result["warnings"]) > 0
            assert "failed" in result["warnings"][0].lower()


class TestDetectRelevantSkills:
    def test_detects_table_layouts(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        skills = detect_relevant_skills("<table><tr><td>Hello</td></tr></table>")
        assert "table_layouts" in skills

    def test_detects_esp_tokens(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        skills = detect_relevant_skills("<p>{{ name }}</p>")
        assert "esp_tokens" in skills

    def test_detects_div_layouts(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        skills = detect_relevant_skills('<div class="mj-column">Content</div>')
        assert "div_layouts" in skills

    def test_detects_column_patterns(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        skills = detect_relevant_skills('<div style="display:inline-block;width:50%">Col</div>')
        assert "column_patterns" in skills

    def test_esp_platform_forces_esp_tokens(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        skills = detect_relevant_skills("<p>No tokens</p>", esp_platform="braze")
        assert "esp_tokens" in skills

    def test_large_html_loads_all_skills(self) -> None:
        from app.ai.agents.import_annotator.prompt import detect_relevant_skills

        html = "x" * 51_000
        skills = detect_relevant_skills(html)
        assert len(skills) == 4  # All skills loaded


class TestImportAnnotationSchemas:
    def test_annotation_decision_frozen(self) -> None:
        decision = AnnotationDecision(
            section_id="test",
            component_name="Header",
            element_selector="body > table",
            layout_type="single",
            confidence=0.9,
            reasoning="test",
        )
        with pytest.raises(AttributeError):
            decision.section_id = "changed"  # type: ignore[misc]

    def test_import_annotation_result_defaults(self) -> None:
        result = ImportAnnotationResult()
        assert result.annotations == ()
        assert result.warnings == ()
        assert result.overall_confidence == 0.0
        assert result.reasoning == ""
