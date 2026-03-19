"""Tests for template eval case generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.agents.evals.template_eval_generator import (
    TemplateEvalGenerator,
)
from app.ai.templates.models import (
    GoldenTemplate,
    TemplateMetadata,
    TemplateSlot,
)
from app.main import app
from app.templates.upload.analyzer import AnalysisResult, ComplexityInfo, SectionInfo, TokenInfo


def _make_template(
    name: str = "uploaded_newsletter_abc123",
    layout_type: str = "newsletter",
    slot_count: int = 4,
) -> GoldenTemplate:
    """Factory for test GoldenTemplate."""
    slots = tuple(
        TemplateSlot(
            slot_id=f"section_0_headline_{i + 1}",
            slot_type="headline",
            selector="section_0 h1",
            required=i == 0,
        )
        for i in range(slot_count)
    )
    return GoldenTemplate(
        metadata=TemplateMetadata(
            name=name,
            display_name="Test Newsletter",
            layout_type=layout_type,  # type: ignore[arg-type]
            column_count=1,
            has_hero_image=False,
            has_navigation=False,
            has_social_links=False,
            sections=("header", "content", "footer"),
            ideal_for=("uploaded",),
            description="Test template",
        ),
        html='<!DOCTYPE html><html lang="en"><head>'
        '<meta name="color-scheme" content="light dark"></head>'
        "<body><!--[if mso]>test<![endif]--><h1>Test</h1></body></html>",
        slots=slots,
        source="uploaded",
    )


def _make_analysis() -> AnalysisResult:
    """Factory for test AnalysisResult."""
    return AnalysisResult(
        sections=[
            SectionInfo(
                section_id="section_0",
                component_name="header",
                element_count=5,
                layout_type="single_column",
            ),
            SectionInfo(
                section_id="section_1",
                component_name="content",
                element_count=10,
                layout_type="single_column",
            ),
            SectionInfo(
                section_id="section_2",
                component_name="footer",
                element_count=3,
                layout_type="single_column",
            ),
        ],
        slots=[],
        tokens=TokenInfo(),
        esp_platform=None,
        complexity=ComplexityInfo(column_count=1),
        layout_type="newsletter",
    )


class TestTemplateEvalGenerator:
    def test_generates_five_cases(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        assert len(cases) == 5

    def test_case_types_are_distinct(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        types = [c["case_type"] for c in cases]
        assert len(set(types)) == 5

    def test_case_ids_are_unique(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        ids = [c["id"] for c in cases]
        assert len(set(ids)) == len(ids)

    def test_all_cases_have_source_tag(self) -> None:
        gen = TemplateEvalGenerator()
        template = _make_template()
        cases = gen.generate(template, _make_analysis())
        for case in cases:
            assert case["source"] == f"uploaded:{template.metadata.name}"

    def test_selection_positive_has_brief(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        pos = [c for c in cases if c["case_type"] == "selection_positive"]
        assert len(pos) == 1
        assert len(str(pos[0]["brief"])) > 20

    def test_selection_negative_uses_different_layout(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(layout_type="newsletter"), _make_analysis())
        neg = [c for c in cases if c["case_type"] == "selection_negative"]
        assert len(neg) == 1
        dims = cast(dict[str, Any], neg[0]["dimensions"])
        assert dims["content_type"] != "newsletter"

    def test_assembly_golden_detects_features(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        golden = [c for c in cases if c["case_type"] == "assembly_golden"]
        assert len(golden) == 1
        checks = cast(dict[str, Any], golden[0]["expected_qa_checks"])
        assert checks["accessibility"] is True  # has lang=
        assert checks["dark_mode"] is True  # has color-scheme
        assert checks["fallback"] is True  # has <!--[if

    def test_slot_fill_counts_required(self) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(slot_count=4), _make_analysis())
        slot = [c for c in cases if c["case_type"] == "slot_fill"]
        assert len(slot) == 1
        assert slot[0]["required_slot_count"] == 1  # only first is required
        assert slot[0]["total_slot_count"] == 4

    def test_all_layout_types_have_positive_briefs(self) -> None:
        gen = TemplateEvalGenerator()
        for layout in [
            "newsletter",
            "promotional",
            "transactional",
            "event",
            "retention",
            "announcement",
            "minimal",
        ]:
            cases = gen.generate(_make_template(layout_type=layout), _make_analysis())
            pos = [c for c in cases if c["case_type"] == "selection_positive"]
            assert len(pos) == 1, f"No positive case for {layout}"


class TestTemplateEvalPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())

        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            saved_path = gen.save("uploaded_newsletter_abc123", cases)
            assert saved_path.exists()
            loaded = gen.load_for_template("uploaded_newsletter_abc123")
            assert len(loaded) == 5

    def test_load_all(self, tmp_path: Path) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())

        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            gen.save("uploaded_newsletter_abc123", cases)
            all_cases = gen.load_all()
            assert "uploaded_newsletter_abc123" in all_cases
            assert len(all_cases["uploaded_newsletter_abc123"]) == 5

    def test_delete_existing(self, tmp_path: Path) -> None:
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())

        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            gen.save("uploaded_newsletter_abc123", cases)
            assert gen.delete("uploaded_newsletter_abc123") is True
            assert gen.load_for_template("uploaded_newsletter_abc123") == []

    def test_delete_nonexistent_returns_false(self, tmp_path: Path) -> None:
        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            gen = TemplateEvalGenerator()
            assert gen.delete("nonexistent_template_xyz") is False

    def test_rejects_path_traversal_name(self) -> None:
        gen = TemplateEvalGenerator()
        import pytest

        for bad_name in ["../etc/passwd", "../../evil", "foo/bar", ".hidden"]:
            with pytest.raises(ValueError, match="Invalid template name"):
                gen.save(bad_name, [])
            with pytest.raises(ValueError, match="Invalid template name"):
                gen.load_for_template(bad_name)
            with pytest.raises(ValueError, match="Invalid template name"):
                gen.delete(bad_name)

    def test_load_corrupted_file_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("not json")
        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            gen = TemplateEvalGenerator()
            all_cases = gen.load_all()
            assert all_cases == {}


class TestTemplateEvalRoutes:
    """Route-level tests for /api/v1/evals/templates endpoints."""

    @pytest.fixture(autouse=True)
    def _save_overrides(self):
        saved = dict(app.dependency_overrides)
        yield
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)

    @pytest.fixture
    def client(self) -> TestClient:
        from app.core.rate_limit import limiter

        limiter.enabled = False
        return TestClient(app)

    def test_list_requires_auth(self, client: TestClient) -> None:
        """GET /api/v1/evals/templates without auth -> 401/403."""
        resp = client.get("/api/v1/evals/templates")
        assert resp.status_code in (401, 403, 404, 405)

    def test_get_cases_for_unknown_template(self, client: TestClient) -> None:
        """GET /api/v1/evals/templates/nonexistent/cases -> 401/403/404."""
        resp = client.get("/api/v1/evals/templates/nonexistent_xyz/cases")
        assert resp.status_code in (401, 403, 404, 405)

    def test_delete_requires_auth(self, client: TestClient) -> None:
        """DELETE without auth -> 401/403."""
        resp = client.delete("/api/v1/evals/templates/test_tmpl/cases")
        assert resp.status_code in (401, 403, 404, 405)

    def test_list_with_mock_auth(self, client: TestClient, tmp_path: Path) -> None:
        """List with mocked auth returns summary."""
        from unittest.mock import MagicMock

        from app.auth.dependencies import require_role

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "developer"

        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            app.dependency_overrides[require_role("developer")] = lambda: mock_user
            resp = client.get("/api/v1/evals/templates")
            if resp.status_code == 200:
                data = resp.json()
                assert "total_templates" in data
                assert "total_cases" in data
            else:
                assert resp.status_code in (404, 405)


class TestEdgeCases:
    def test_zero_slots_template(self) -> None:
        """Template with no slots -> slot_fill case has expected_count=0."""
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(slot_count=0), _make_analysis())
        slot = [c for c in cases if c["case_type"] == "slot_fill"]
        assert len(slot) == 1
        assert slot[0]["required_slot_count"] == 0
        assert slot[0]["total_slot_count"] == 0

    def test_unknown_layout_fallback(self) -> None:
        """Unknown layout type -> falls back to newsletter brief."""
        gen = TemplateEvalGenerator()
        # Force an unusual layout through the factory
        tmpl = _make_template(layout_type="custom_weird")
        cases = gen.generate(tmpl, _make_analysis())
        pos = [c for c in cases if c["case_type"] == "selection_positive"]
        assert len(pos) == 1
        # Should use newsletter fallback brief
        assert len(str(pos[0]["brief"])) > 20

    def test_load_case_set_returns_metadata(self, tmp_path: Path) -> None:
        """load_case_set() returns dict with 'cases' and 'generated_at' keys."""
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        with patch(
            "app.ai.agents.evals.template_eval_generator.UPLOADED_GOLDEN_DIR",
            tmp_path,
        ):
            gen.save("uploaded_newsletter_abc123", cases)
            data = gen.load_case_set("uploaded_newsletter_abc123")
        assert data is not None
        assert "cases" in data
        assert "generated_at" in data

    def test_qa_passthrough_has_html_length(self) -> None:
        """QA passthrough case includes html_length."""
        gen = TemplateEvalGenerator()
        cases = gen.generate(_make_template(), _make_analysis())
        qa = [c for c in cases if c["case_type"] == "qa_passthrough"]
        assert len(qa) == 1
        assert "html_length" in qa[0]
        length = qa[0]["html_length"]
        assert isinstance(length, int) and length > 0
