"""Bridge between component versions and QA engine — runs checks, extracts compatibility."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models import ComponentQAResult, ComponentVersion
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.knowledge.ontology.query import unsupported_css_in_html
from app.knowledge.ontology.registry import load_ontology
from app.qa_engine.schemas import QARunRequest
from app.qa_engine.service import QAEngineService

logger = get_logger(__name__)


def extract_compatibility(html: str) -> dict[str, str]:
    """Analyse component HTML against ontology and return per-client compatibility.

    Returns dict mapping client_id → "full" | "partial" | "none".
    A client is:
    - "full" if zero CSS issues affect it
    - "partial" if only warnings (market_share ≤ 20%) affect it
    - "none" if errors (market_share > 20%) affect it
    """
    onto = load_ontology()
    issues = unsupported_css_in_html(html)

    # Build name → client_id lookup for O(1) resolution
    name_to_id: dict[str, str] = {c.name: c.id for c in onto.clients}

    # Build per-client issue severity
    client_severity: dict[str, str] = {}
    for issue in issues:
        unsupported_clients: list[str] = issue["unsupported_clients"]  # type: ignore[assignment]
        severity = str(issue["severity"])
        for client_name in unsupported_clients:
            client_id = name_to_id.get(client_name)
            if not client_id:
                continue
            current = client_severity.get(client_id, "full")
            if severity == "error" or current == "none":
                client_severity[client_id] = "none"
            elif severity == "warning" and current != "none":
                client_severity[client_id] = "partial"

    # Build complete compatibility map — all clients
    compatibility: dict[str, str] = {}
    for client in onto.clients:
        compatibility[client.id] = client_severity.get(client.id, "full")

    return compatibility


async def run_component_qa(
    db: AsyncSession,
    version: ComponentVersion,
) -> ComponentQAResult:
    """Run QA checks on a component version and store compatibility result.

    1. Runs the full 10-point QA gate on the component HTML
    2. Extracts per-client compatibility from css_support results
    3. Creates a ComponentQAResult linking version → QA result + compatibility
    """
    logger.info(
        "components.qa_started",
        component_id=version.component_id,
        version_number=version.version_number,
    )

    # Run QA engine
    qa_service = QAEngineService(db)
    try:
        qa_response = await qa_service.run_checks(
            QARunRequest(html=version.html_source),  # pyright: ignore[reportCallIssue]
        )
    except Exception as exc:
        logger.error(
            "components.qa_engine_failed",
            component_id=version.component_id,
            version_number=version.version_number,
            error=str(exc),
        )
        raise AppError("QA engine failed for component version") from exc

    # Extract compatibility from ontology analysis
    try:
        compatibility = extract_compatibility(version.html_source)
    except Exception as exc:
        logger.error(
            "components.compatibility_extraction_failed",
            component_id=version.component_id,
            error=str(exc),
        )
        raise AppError("Compatibility extraction failed") from exc

    # Store link + update version compatibility in a single transaction
    cqa = ComponentQAResult(
        component_version_id=version.id,
        qa_result_id=qa_response.id,
        compatibility=compatibility,
    )
    db.add(cqa)
    version.compatibility = compatibility
    await db.commit()
    await db.refresh(cqa)

    logger.info(
        "components.qa_completed",
        component_id=version.component_id,
        version_number=version.version_number,
        qa_result_id=qa_response.id,
        full_clients=sum(1 for v in compatibility.values() if v == "full"),
        partial_clients=sum(1 for v in compatibility.values() if v == "partial"),
        none_clients=sum(1 for v in compatibility.values() if v == "none"),
    )

    return cqa
