"""QA Gate deterministic node — runs 11-point quality checks against HTML."""

from typing import Any, cast

from app.ai.blueprints.nodes.recovery_router_node import CHECK_PRIORITY, CHECK_TO_AGENT
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType, StructuredFailure
from app.core.logging import get_logger
from app.qa_engine.check_config import load_defaults
from app.qa_engine.checks import ALL_CHECKS

logger = get_logger(__name__)


class QAGateNode:
    """Deterministic node that runs all QA checks against the current HTML.

    Returns success if all checks pass, failed with details if any fail.
    Produces StructuredFailure objects for the recovery router.
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
        structured_failures: list[StructuredFailure] = []
        passed_count = 0

        # Merge visual precheck failures (set by VisualPrecheckNode upstream)
        _raw_precheck = (context.metadata or {}).get("visual_precheck_failures", [])
        visual_precheck_data: list[Any] = (
            list(cast(list[Any], _raw_precheck))  # type: ignore[redundant-cast]
            if isinstance(_raw_precheck, list)
            else []
        )
        for vpf_raw in visual_precheck_data:
            if isinstance(vpf_raw, dict):
                vpf = cast(dict[str, Any], vpf_raw)
                detail = str(vpf.get("details", "visual defect"))
                check_name = str(vpf.get("check_name", "visual_defect"))
                failures.append(f"{check_name}: {detail}")
                structured_failures.append(
                    StructuredFailure(
                        check_name=check_name,
                        score=float(vpf.get("score", 0.0)),
                        details=detail,
                        suggested_agent=str(vpf.get("suggested_agent", "scaffolder")),
                        priority=int(vpf.get("priority", 0)),
                        severity=str(vpf.get("severity", "high")),
                    )
                )

        profile = load_defaults()
        for check in ALL_CHECKS:
            check_config = profile.get_check_config(check.name)
            if check_config and not check_config.enabled:
                passed_count += 1
                continue
            result = await check.run(context.html, check_config)
            if result.passed:
                passed_count += 1
            else:
                detail = result.details or "no details"
                failures.append(f"{result.check_name}: {detail} (score={result.score:.2f})")
                structured_failures.append(
                    StructuredFailure(
                        check_name=result.check_name,
                        score=result.score,
                        details=detail,
                        suggested_agent=CHECK_TO_AGENT.get(result.check_name, "scaffolder"),
                        priority=CHECK_PRIORITY.get(result.check_name, 99),
                        severity=result.severity,
                    )
                )

        # Sort by priority (lower = higher priority)
        structured_failures.sort(key=lambda f: f.priority)

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
            structured_failures=tuple(structured_failures),
        )
