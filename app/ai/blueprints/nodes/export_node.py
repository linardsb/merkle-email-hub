"""Export deterministic node — passes through compiled HTML for downstream delivery."""

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExportNode:
    """Deterministic node that validates and passes through compiled HTML.

    ESP-specific formatting (Braze Content Blocks, SFMC Content Areas, etc.)
    is handled by the sync layer (ConnectorSyncService / ConnectorService),
    not here. The pipeline produces clean HTML.
    """

    @property
    def name(self) -> str:
        return "export"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Pass through HTML unchanged — ESP formatting belongs in sync layer."""
        if not context.html:
            return NodeResult(
                status="failed",
                error="No HTML to export",
            )

        logger.info(
            "blueprint.export.completed",
            format="raw_html",
            output_length=len(context.html),
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"Export ready ({len(context.html)} chars)",
        )
