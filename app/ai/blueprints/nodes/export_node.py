"""Export deterministic node — packages HTML as a Braze Content Block."""

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.logging import get_logger

logger = get_logger(__name__)

_BRAZE_CONTENT_BLOCK_TEMPLATE = """{{% content_block name='{name}' %}}
{html}
{{% /content_block %}}"""


class ExportNode:
    """Deterministic node that packages HTML for Braze Content Block export.

    No external API calls or DB access — just Liquid formatting.
    Returns the packaged content in NodeResult.html.
    """

    @property
    def name(self) -> str:
        return "export"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Wrap HTML in Braze Content Block Liquid syntax."""
        if not context.html:
            return NodeResult(
                status="failed",
                error="No HTML to export",
            )

        block_name = "blueprint_email"
        packaged = _BRAZE_CONTENT_BLOCK_TEMPLATE.format(
            name=block_name,
            html=context.html,
        )

        logger.info(
            "blueprint.export.completed",
            format="braze_content_block",
            output_length=len(packaged),
        )

        return NodeResult(
            status="success",
            html=packaged,
            details=f"Packaged as Braze Content Block '{block_name}' ({len(packaged)} chars)",
        )
