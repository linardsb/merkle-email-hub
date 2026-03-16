# mypy: disable-error-code="no-untyped-def"
"""Tests for the Visual QA agent service and blueprint node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.visual_qa.decisions import DetectedDefect, VisualQADecisions
from app.ai.agents.visual_qa.schemas import VisualDefect, VisualQARequest, VisualQAResponse
from app.ai.agents.visual_qa.service import _MAX_SCREENSHOT_B64_LEN, VisualQAService
from app.ai.blueprints.nodes.visual_qa_node import VisualQANode
from app.ai.blueprints.protocols import NodeContext

# ── Fixtures ──


@pytest.fixture
def service():
    return VisualQAService()


@pytest.fixture
def node():
    return VisualQANode()


@pytest.fixture
def sample_html():
    return "<html><body><table><tr><td>Hello</td></tr></table></body></html>" + "x" * 50


@pytest.fixture
def sample_screenshots():
    """Minimal valid base64 PNG data for testing."""
    # 1x1 transparent PNG (smallest valid PNG)
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
        "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    return {
        "gmail_web": tiny_png_b64,
        "outlook_2019": tiny_png_b64,
        "apple_mail": tiny_png_b64,
    }


# ── Schema tests ──


class TestVisualQASchemas:
    def test_request_requires_screenshots(self):
        with pytest.raises(ValueError):
            VisualQARequest(screenshots={}, html="x" * 50)

    def test_request_validates_html_min_length(self):
        with pytest.raises(ValueError):
            VisualQARequest(screenshots={"gmail": "abc"}, html="short")

    def test_request_valid(self, sample_screenshots: dict[str, str], sample_html: str):
        req = VisualQARequest(screenshots=sample_screenshots, html=sample_html)
        assert len(req.screenshots) == 3

    def test_response_defaults(self):
        resp = VisualQAResponse()
        assert resp.defects == []
        assert resp.overall_rendering_score == 1.0
        assert resp.auto_fixable is False

    def test_visual_defect_fields(self):
        defect = VisualDefect(
            region="CTA button",
            description="Button clipped",
            severity="critical",
            affected_clients=["outlook_2019"],
            suggested_fix="Use VML roundrect",
            css_property="border-radius",
        )
        assert defect.severity == "critical"
        assert defect.css_property == "border-radius"

    def test_request_output_mode_default(
        self, sample_screenshots: dict[str, str], sample_html: str
    ):
        req = VisualQARequest(screenshots=sample_screenshots, html=sample_html)
        assert req.output_mode == "structured"

    def test_request_with_baseline_diffs(
        self, sample_screenshots: dict[str, str], sample_html: str
    ):
        req = VisualQARequest(
            screenshots=sample_screenshots,
            html=sample_html,
            baseline_diffs=[{"client": "outlook_2019", "diff_percentage": 4.2}],
        )
        assert req.baseline_diffs is not None
        assert len(req.baseline_diffs) == 1


# ── Decisions tests ──


class TestVisualQADecisions:
    def test_decisions_defaults(self):
        d = VisualQADecisions()
        assert d.defects == ()
        assert d.overall_rendering_score == 1.0
        assert d.confidence == 0.0

    def test_decisions_with_defects(self):
        defect = DetectedDefect(
            region="header",
            description="Layout collapsed",
            severity="critical",
            affected_clients=("outlook_2019",),
            suggested_fix="Use table layout",
            css_property="display",
        )
        d = VisualQADecisions(defects=(defect,), confidence=0.9)
        assert len(d.defects) == 1
        assert d.defects[0].severity == "critical"

    def test_decisions_frozen(self):
        d = VisualQADecisions()
        with pytest.raises(AttributeError):
            d.confidence = 0.5  # type: ignore[misc]

    def test_detected_defect_frozen(self):
        defect = DetectedDefect(
            region="test",
            description="test",
            severity="info",
            affected_clients=(),
            suggested_fix="fix",
            css_property="",
        )
        with pytest.raises(AttributeError):
            defect.region = "changed"  # type: ignore[misc]

    def test_decisions_multiple_defects(self):
        defects = (
            DetectedDefect(
                region="header",
                description="broken",
                severity="critical",
                affected_clients=("outlook",),
                suggested_fix="fix1",
                css_property="display",
            ),
            DetectedDefect(
                region="footer",
                description="misaligned",
                severity="warning",
                affected_clients=("gmail",),
                suggested_fix="fix2",
                css_property="padding",
            ),
        )
        d = VisualQADecisions(
            defects=defects,
            critical_clients=("outlook",),
            overall_rendering_score=0.5,
        )
        assert len(d.defects) == 2
        assert d.critical_clients == ("outlook",)


# ── Service tests ──


class TestVisualQAService:
    def test_agent_name(self, service: VisualQAService):
        assert service.agent_name == "visual_qa"

    def test_build_user_message(
        self, service: VisualQAService, sample_screenshots: dict[str, str], sample_html: str
    ):
        req = VisualQARequest(screenshots=sample_screenshots, html=sample_html)
        msg = service._build_user_message(req)
        assert "gmail_web" in msg
        assert "outlook_2019" in msg
        assert "apple_mail" in msg

    def test_build_user_message_with_diffs(
        self, service: VisualQAService, sample_screenshots: dict[str, str], sample_html: str
    ):
        req = VisualQARequest(
            screenshots=sample_screenshots,
            html=sample_html,
            baseline_diffs=[
                {"client": "outlook_2019", "diff_percentage": 4.2, "changed_pixels": 1500}
            ],
        )
        msg = service._build_user_message(req)
        assert "4.2%" in msg

    def test_parse_decisions_valid_json(self, service: VisualQAService):
        raw = '{"defects": [{"region": "header", "description": "broken", "severity": "critical", "affected_clients": ["outlook"], "suggested_fix": "fix it", "css_property": "display"}], "overall_rendering_score": 0.7, "critical_clients": ["outlook"], "summary": "Issues found", "confidence": 0.85, "auto_fixable": true}'
        decisions = service.parse_decisions(raw)
        assert len(decisions.defects) == 1
        assert decisions.overall_rendering_score == 0.7
        assert decisions.confidence == 0.85
        assert decisions.auto_fixable is True

    def test_parse_decisions_json_in_code_fence(self, service: VisualQAService):
        raw = '```json\n{"defects": [], "overall_rendering_score": 1.0, "critical_clients": [], "summary": "Perfect", "confidence": 0.95, "auto_fixable": false}\n```'
        decisions = service.parse_decisions(raw)
        assert decisions.overall_rendering_score == 1.0
        assert decisions.summary == "Perfect"

    def test_parse_decisions_invalid_json(self, service: VisualQAService):
        decisions = service.parse_decisions("not json at all")
        assert decisions.confidence == 0.0
        assert "Failed to parse" in decisions.summary

    def test_parse_decisions_malformed_defects(self, service: VisualQAService):
        raw = '{"defects": ["not_a_dict", {"region": "ok"}], "confidence": 0.5}'
        decisions = service.parse_decisions(raw)
        # Only dict entries become defects
        assert len(decisions.defects) == 1

    def test_parse_decisions_generic_code_fence(self, service: VisualQAService):
        raw = '```\n{"defects": [], "summary": "Clean", "confidence": 0.8}\n```'
        decisions = service.parse_decisions(raw)
        assert decisions.summary == "Clean"

    def test_parse_decisions_empty_json(self, service: VisualQAService):
        decisions = service.parse_decisions("{}")
        assert len(decisions.defects) == 0
        assert decisions.overall_rendering_score == 1.0

    @pytest.mark.asyncio
    async def test_process_screenshot_too_large(self, service: VisualQAService, sample_html: str):
        huge = "A" * (_MAX_SCREENSHOT_B64_LEN + 1)
        req = VisualQARequest(screenshots={"gmail": huge}, html=sample_html)
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai=MagicMock(visual_qa_model="", provider="mock")
            )
            resp = await service.process(req)
        assert "exceeds size limit" in resp.summary

    def test_enrich_with_ontology_no_ontology(self, service: VisualQAService):
        decisions = VisualQADecisions(
            defects=(
                DetectedDefect(
                    region="test",
                    description="test",
                    severity="info",
                    affected_clients=(),
                    suggested_fix="fix",
                    css_property="display",
                ),
            ),
        )
        with patch("app.knowledge.ontology.get_ontology", side_effect=ImportError):
            result = service.enrich_with_ontology(decisions)
        assert len(result.defects) == 1  # Unchanged

    def test_enrich_with_ontology_no_css_property(self, service: VisualQAService):
        decisions = VisualQADecisions(
            defects=(
                DetectedDefect(
                    region="test",
                    description="test",
                    severity="info",
                    affected_clients=(),
                    suggested_fix="fix",
                    css_property="",
                ),
            ),
        )
        result = service.enrich_with_ontology(decisions)
        assert result.defects[0].suggested_fix == "fix"  # Unchanged

    def test_enrich_with_ontology_property_not_found(self, service: VisualQAService):
        decisions = VisualQADecisions(
            defects=(
                DetectedDefect(
                    region="test",
                    description="test",
                    severity="info",
                    affected_clients=(),
                    suggested_fix="fix",
                    css_property="nonexistent-property",
                ),
            ),
        )
        mock_ontology = MagicMock()
        mock_ontology.find_property_by_name.return_value = None
        with patch("app.knowledge.ontology.get_ontology", return_value=mock_ontology):
            result = service.enrich_with_ontology(decisions)
        assert result.defects[0].suggested_fix == "fix"  # Unchanged

    def test_model_tier(self, service: VisualQAService):
        assert service.model_tier == "standard"

    def test_parse_decisions_non_numeric_score(self, service: VisualQAService):
        """CRITICAL 3: float() on non-numeric VLM output should not crash."""
        raw = '{"defects": [], "overall_rendering_score": "high", "confidence": "very confident"}'
        decisions = service.parse_decisions(raw)
        assert decisions.overall_rendering_score == 1.0  # Falls back to default
        assert decisions.confidence == 0.0  # Falls back to default


# ── Node tests ──


class TestVisualQANode:
    def test_node_name(self, node: VisualQANode):
        assert node.name == "visual_qa"

    def test_node_type(self, node: VisualQANode):
        assert node.node_type == "agentic"

    @pytest.mark.asyncio
    async def test_node_skipped_when_disabled(self, node: VisualQANode):
        ctx = NodeContext(html="<html>test</html>")
        with patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock:
            mock.return_value = MagicMock(ai=MagicMock(visual_qa_enabled=False))
            result = await node.execute(ctx)
        assert result.status == "skipped"
        assert "disabled" in result.details

    @pytest.mark.asyncio
    async def test_node_skipped_when_no_screenshots(self, node: VisualQANode):
        ctx = NodeContext(html="<html>test</html>", metadata={})
        with patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock:
            mock.return_value = MagicMock(ai=MagicMock(visual_qa_enabled=True))
            result = await node.execute(ctx)
        assert result.status == "skipped"
        assert "No screenshots" in result.details

    @pytest.mark.asyncio
    async def test_node_rejects_oversized_screenshot(self, node: VisualQANode, sample_html: str):
        """CRITICAL 1: Node must validate screenshot sizes."""
        huge = "A" * (_MAX_SCREENSHOT_B64_LEN + 1)
        ctx = NodeContext(html=sample_html, metadata={"screenshots": {"gmail": huge}})
        with patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock:
            mock.return_value = MagicMock(ai=MagicMock(visual_qa_enabled=True))
            result = await node.execute(ctx)
        assert result.status == "failed"
        assert "exceeds size limit" in result.error

    @pytest.mark.asyncio
    async def test_node_llm_failure(
        self, node: VisualQANode, sample_screenshots: dict[str, str], sample_html: str
    ):
        ctx = NodeContext(html=sample_html, metadata={"screenshots": sample_screenshots})
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("VLM down")

        with (
            patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
            patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
            patch(
                "app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="test-model"
            ),
        ):
            mock_settings.return_value = MagicMock(
                ai=MagicMock(visual_qa_enabled=True, visual_qa_model="", provider="mock")
            )
            mock_reg.return_value.get_llm.return_value = mock_provider
            result = await node.execute(ctx)

        assert result.status == "failed"
        assert "VLM" in result.error
        # Error message should NOT leak internal exception details
        assert "VLM down" not in result.error

    @pytest.mark.asyncio
    async def test_node_success(
        self, node: VisualQANode, sample_screenshots: dict[str, str], sample_html: str
    ):
        ctx = NodeContext(html=sample_html, metadata={"screenshots": sample_screenshots})

        mock_response = MagicMock()
        mock_response.content = '{"defects": [], "overall_rendering_score": 1.0, "critical_clients": [], "summary": "No issues", "confidence": 0.95, "auto_fixable": false}'
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50}

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response

        with (
            patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
            patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
            patch(
                "app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="test-model"
            ),
            patch("app.knowledge.ontology.get_ontology", side_effect=ImportError),
        ):
            mock_settings.return_value = MagicMock(
                ai=MagicMock(visual_qa_enabled=True, visual_qa_model="test-vlm", provider="mock")
            )
            mock_reg.return_value.get_llm.return_value = mock_provider
            result = await node.execute(ctx)

        assert result.status == "success"
        assert result.html == sample_html  # Pass-through
        assert result.handoff is not None
        assert result.handoff.agent_name == "visual_qa"
        assert len(result.handoff.warnings) == 0  # No defects

    @pytest.mark.asyncio
    async def test_node_with_defects(
        self, node: VisualQANode, sample_screenshots: dict[str, str], sample_html: str
    ):
        ctx = NodeContext(html=sample_html, metadata={"screenshots": sample_screenshots})

        mock_response = MagicMock()
        mock_response.content = '{"defects": [{"region": "CTA", "description": "Button clipped", "severity": "critical", "affected_clients": ["outlook_2019"], "suggested_fix": "Use VML", "css_property": "border-radius"}], "overall_rendering_score": 0.6, "critical_clients": ["outlook_2019"], "summary": "Outlook issues", "confidence": 0.9, "auto_fixable": true}'
        mock_response.usage = None

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response

        with (
            patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
            patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
            patch(
                "app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="test-model"
            ),
            patch("app.knowledge.ontology.get_ontology", side_effect=ImportError),
        ):
            mock_settings.return_value = MagicMock(
                ai=MagicMock(visual_qa_enabled=True, visual_qa_model="", provider="mock")
            )
            mock_reg.return_value.get_llm.return_value = mock_provider
            result = await node.execute(ctx)

        assert result.status == "success"
        assert result.handoff is not None
        assert len(result.handoff.warnings) == 1
        assert "critical" in result.handoff.warnings[0]
        assert "CTA" in result.handoff.warnings[0]

    def test_service_parse_decisions_from_node(self):
        """Node delegates to service.parse_decisions — verify via service."""
        from app.ai.agents.visual_qa.service import get_visual_qa_service

        service = get_visual_qa_service()
        decisions = service.parse_decisions("{}")
        assert len(decisions.defects) == 0
        assert decisions.overall_rendering_score == 1.0

    def test_node_build_user_message(
        self, node: VisualQANode, sample_screenshots: dict[str, str], sample_html: str
    ):
        ctx = NodeContext(html=sample_html, metadata={})
        msg = node._build_user_message(ctx, sample_screenshots)
        assert "gmail_web" in msg
        assert "3" in msg  # "3 email screenshots"

    def test_node_build_user_message_with_diffs(
        self, node: VisualQANode, sample_screenshots: dict[str, str], sample_html: str
    ):
        ctx = NodeContext(
            html=sample_html,
            metadata={"baseline_diffs": [{"client": "outlook_2019", "diff_percentage": 3.5}]},
        )
        msg = node._build_user_message(ctx, sample_screenshots)
        assert "3.5%" in msg


# ── Handoff tests ──


class TestVisualQAHandoff:
    def test_handoff_import(self):
        from app.ai.blueprints.handoff import VisualQAHandoff

        h = VisualQAHandoff(
            defects_found=3,
            overall_score=0.7,
            critical_clients=("outlook_2019",),
            auto_fixable=True,
            screenshotted_clients=("gmail_web", "outlook_2019", "apple_mail"),
        )
        assert h.defects_found == 3
        assert h.overall_score == 0.7

    def test_handoff_defaults(self):
        from app.ai.blueprints.handoff import VisualQAHandoff

        h = VisualQAHandoff()
        assert h.defects_found == 0
        assert h.overall_score == 1.0
        assert h.auto_fixable is False

    def test_handoff_in_registry(self):
        from app.ai.blueprints.handoff import HANDOFF_PAYLOAD_TYPES, VisualQAHandoff

        assert "visual_qa" in HANDOFF_PAYLOAD_TYPES
        assert HANDOFF_PAYLOAD_TYPES["visual_qa"] is VisualQAHandoff

    def test_format_upstream_constraints(self):
        from app.ai.blueprints.handoff import VisualQAHandoff, format_upstream_constraints
        from app.ai.blueprints.protocols import AgentHandoff

        handoff = AgentHandoff(
            agent_name="visual_qa",
            artifact="",
            decisions=(),
            warnings=(),
            confidence=0.9,
            typed_payload=VisualQAHandoff(
                defects_found=2,
                overall_score=0.7,
                critical_clients=("outlook_2019",),
                auto_fixable=True,
            ),
        )
        result = format_upstream_constraints(handoff)
        assert "Defects found: 2" in result
        assert "Rendering score: 0.70" in result
        assert "outlook_2019" in result
        assert "Auto-fixable: True" in result


# ── Prompt tests ──


class TestVisualQAPrompt:
    def test_build_system_prompt(self):
        from app.ai.agents.visual_qa.prompt import build_system_prompt

        prompt = build_system_prompt([], output_mode="structured")
        assert "Visual QA" in prompt
        assert "rendering defects" in prompt
        assert "JSON" in prompt

    def test_detect_relevant_skills_mso(self):
        from app.ai.agents.visual_qa.prompt import detect_relevant_skills

        html = "<html><!--[if mso]>test<![endif]--></html>" + "x" * 50
        skills = detect_relevant_skills(html)
        # No skill files exist yet, so empty list is expected
        assert isinstance(skills, list)

    def test_detect_relevant_skills_dark_mode(self):
        from app.ai.agents.visual_qa.prompt import detect_relevant_skills

        html = "<html><style>@media (prefers-color-scheme: dark) {}</style></html>" + "x" * 50
        skills = detect_relevant_skills(html)
        assert isinstance(skills, list)
