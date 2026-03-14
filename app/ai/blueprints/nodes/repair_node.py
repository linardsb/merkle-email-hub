"""Repair node — runs cascading auto-repair pipeline before QA gate."""

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.logging import get_logger
from app.qa_engine.repair import RepairPipeline

logger = get_logger(__name__)


class RepairNode:
    """Deterministic node: runs 7-stage repair pipeline on current HTML."""

    @property
    def name(self) -> str:
        return "repair"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Run repair pipeline on current HTML."""
        if not context.html:
            return NodeResult(status="success", details="no_html_to_repair")

        pipeline = RepairPipeline()
        result = pipeline.run(context.html)

        repair_count = len(result.repairs_applied)
        warning_count = len(result.warnings)

        if repair_count > 0:
            logger.info(
                "blueprint.repair_node.applied",
                repair_count=repair_count,
                warning_count=warning_count,
                repairs=result.repairs_applied,
            )
        else:
            logger.info("blueprint.repair_node.no_repairs_needed")

        details_parts: list[str] = []
        if repair_count:
            details_parts.append(f"{repair_count} repair(s) applied")
        if warning_count:
            details_parts.append(f"{warning_count} warning(s)")
        if not details_parts:
            details_parts.append("no repairs needed")

        return NodeResult(
            status="success",
            html=result.html,
            details="; ".join(details_parts),
        )
