"""Tests for the export node."""

import pytest

from app.ai.blueprints.nodes.export_node import ExportNode
from app.ai.blueprints.protocols import NodeContext


class TestExportNode:
    """Tests for ExportNode raw HTML passthrough."""

    @pytest.mark.asyncio()
    async def test_export_returns_raw_html_no_wrapping(self) -> None:
        node = ExportNode()
        html = "<html><body><p>Hello World</p></body></html>"
        context = NodeContext(html=html, brief="test", iteration=0)

        result = await node.execute(context)

        assert result.status == "success"
        assert result.html == html
        assert "content_block" not in (result.html or "")
        assert "braze" not in (result.details or "").lower()

    @pytest.mark.asyncio()
    async def test_export_fails_on_empty_html(self) -> None:
        node = ExportNode()
        context = NodeContext(html="", brief="test", iteration=0)

        result = await node.execute(context)

        assert result.status == "failed"
        assert result.error == "No HTML to export"

    def test_export_node_metadata(self) -> None:
        node = ExportNode()
        assert node.name == "export"
        assert node.node_type == "deterministic"
