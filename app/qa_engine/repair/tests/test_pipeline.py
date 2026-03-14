"""Unit tests for RepairPipeline orchestrator."""

from app.qa_engine.repair.pipeline import RepairPipeline, RepairResult


class _FailingStage:
    """Test helper: stage that always raises."""

    @property
    def name(self) -> str:
        return "failing"

    def repair(self, html: str) -> RepairResult:
        raise RuntimeError("boom")


class _NoOpStage:
    """Test helper: stage that does nothing."""

    @property
    def name(self) -> str:
        return "noop"

    def repair(self, html: str) -> RepairResult:
        return RepairResult(html=html)


class TestRepairPipeline:
    def test_runs_default_stages(self) -> None:
        pipeline = RepairPipeline()
        result = pipeline.run("<html><body>content</body></html>")
        assert result.html
        assert isinstance(result.repairs_applied, list)

    def test_stage_failure_does_not_crash(self) -> None:
        pipeline = RepairPipeline(stages=[_FailingStage(), _NoOpStage()])
        result = pipeline.run("<html><body>test</body></html>")
        assert result.html == "<html><body>test</body></html>"
        assert any("failed" in w for w in result.warnings)

    def test_idempotency(self) -> None:
        pipeline = RepairPipeline()
        html = (
            "<!DOCTYPE html><html><head></head><body>"
            '<!-- comment --><a href="">link</a>'
            "</body></html>"
        )
        result1 = pipeline.run(html)
        result2 = pipeline.run(result1.html)
        assert result1.html == result2.html

    def test_custom_stages(self) -> None:
        pipeline = RepairPipeline(stages=[_NoOpStage()])
        result = pipeline.run("anything")
        assert result.html == "anything"
        assert result.repairs_applied == []

    def test_aggregates_repairs_and_warnings(self) -> None:
        from app.qa_engine.repair.links import LinkRepair
        from app.qa_engine.repair.structure import StructureRepair

        pipeline = RepairPipeline(stages=[StructureRepair(), LinkRepair()])
        result = pipeline.run('<a href="">link</a>')
        # Structure adds doctype/html/head/body; links fixes empty href
        assert len(result.repairs_applied) > 1

    def test_stages_run_in_order(self) -> None:
        """Verify stages receive the output of the previous stage."""
        from app.qa_engine.repair.links import LinkRepair
        from app.qa_engine.repair.structure import StructureRepair

        pipeline = RepairPipeline(stages=[StructureRepair(), LinkRepair()])
        result = pipeline.run('<a href="">link</a>')
        # Structure should have added DOCTYPE before links stage runs
        assert "<!DOCTYPE html>" in result.html
        # Links should have fixed empty href
        assert 'href="#"' in result.html


class TestRepairNode:
    """Integration test for RepairNode blueprint protocol conformance."""

    async def test_execute_repairs_html(self) -> None:
        from app.ai.blueprints.nodes.repair_node import RepairNode
        from app.ai.blueprints.protocols import NodeContext

        node = RepairNode()
        assert node.name == "repair"
        assert node.node_type == "deterministic"

        context = NodeContext(html='<html><body><a href="">link</a></body></html>')
        result = await node.execute(context)

        assert result.status == "success"
        assert result.html
        assert 'href="#"' in result.html
        assert "repair(s) applied" in result.details

    async def test_execute_no_html(self) -> None:
        from app.ai.blueprints.nodes.repair_node import RepairNode
        from app.ai.blueprints.protocols import NodeContext

        node = RepairNode()
        result = await node.execute(NodeContext())

        assert result.status == "success"
        assert result.details == "no_html_to_repair"

    async def test_execute_clean_html(self) -> None:
        from app.ai.blueprints.nodes.repair_node import RepairNode
        from app.ai.blueprints.protocols import NodeContext

        html = (
            '<!DOCTYPE html>\n<html lang="en"><head>'
            '<meta name="color-scheme" content="light dark">'
            '<meta name="supported-color-schemes" content="light dark">'
            "<style>@media (prefers-color-scheme: dark) { body {} }</style>"
            "</head><body><p>clean</p></body></html>"
        )
        node = RepairNode()
        result = await node.execute(NodeContext(html=html))

        assert result.status == "success"
        assert "no repairs needed" in result.details
