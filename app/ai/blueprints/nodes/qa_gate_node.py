"""QA Gate deterministic node — runs 10-point quality checks against HTML."""

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS

logger = get_logger(__name__)


class QAGateNode:
    """Deterministic node that runs all QA checks against the current HTML.

    Returns success if all checks pass, failed with details if any fail.
    The failure details are consumed by the recovery router.
    """

    @property
    def name(self) -> str:
        return "qa_gate"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Run all QA checks and aggregate results."""
        if not context.html:
            return NodeResult(
                status="failed",
                error="No HTML to validate",
                details="no_html",
            )

        failures: list[str] = []
        passed_count = 0

        for check in ALL_CHECKS:
            result = await check.run(context.html)
            if result.passed:
                passed_count += 1
            else:
                detail = result.details or "no details"
                failures.append(f"{result.check_name}: {detail} (score={result.score:.2f})")

        total = len(ALL_CHECKS)

        if not failures:
            logger.info("blueprint.qa_gate.all_passed", checks=total)
            return NodeResult(
                status="success",
                html=context.html,
                details=f"All {total} checks passed",
            )

        summary = "\n".join(failures)
        logger.info(
            "blueprint.qa_gate.failures",
            passed=passed_count,
            failed=len(failures),
        )
        return NodeResult(
            status="failed",
            html=context.html,
            details=summary,
        )
