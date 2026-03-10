"""Generate client-specific onboarding subgraph for a project."""

from __future__ import annotations

from app.core.logging import get_logger
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import EmailClient

logger = get_logger(__name__)


def generate_onboarding_documents(
    project_id: int,
    project_name: str,
    client_ids: list[str],
) -> list[tuple[str, str]]:
    """Generate scoped ontology documents for a project's target clients.

    Returns list of (dataset_name, document_text) tuples.
    Dataset name is scoped: "project_onboarding_{project_id}".

    Documents include:
    1. Compatibility Brief — executive summary of constraints
    2. Per-client profiles — unsupported CSS with fallbacks
    3. Cross-client risk matrix — properties risky across ALL targets
    """
    onto = load_ontology()
    dataset = f"project_onboarding_{project_id}"
    documents: list[tuple[str, str]] = []

    # Resolve clients — skip unknown IDs gracefully
    clients: list[EmailClient] = []
    for cid in client_ids:
        client = onto.get_client(cid)
        if client:
            clients.append(client)
        else:
            logger.warning("onboarding.unknown_client_id", client_id=cid, project_id=project_id)

    if not clients:
        logger.info("onboarding.no_valid_clients", project_id=project_id)
        return []

    # Document 1: Compatibility Brief (executive summary)
    documents.append((dataset, _build_compatibility_brief(onto, clients, project_name)))

    # Document 2: Per-client constraint profiles
    for client in clients:
        documents.append((dataset, _build_client_profile(onto, client)))

    # Document 3: Cross-client risk matrix
    documents.append((dataset, _build_risk_matrix(onto, clients)))

    logger.info(
        "onboarding.documents_generated",
        project_id=project_id,
        document_count=len(documents),
        client_count=len(clients),
    )

    return documents


def _build_compatibility_brief(
    onto: OntologyRegistry,
    clients: list[EmailClient],
    project_name: str,
) -> str:
    """Executive summary of constraints across target audience."""
    lines = [
        f"# Compatibility Brief: {project_name}",
        "",
        "## Target Audience",
    ]

    for c in clients:
        lines.append(f"- **{c.name}** ({c.platform}, {c.engine.value}, {c.market_share}% share)")

    # Count unsupported properties per client
    lines.append("")
    lines.append("## Constraint Summary")

    total_risky: set[str] = set()
    for c in clients:
        unsupported = onto.properties_unsupported_by(c.id)
        lines.append(f"- {c.name}: {len(unsupported)} unsupported CSS properties")
        total_risky.update(p.id for p in unsupported)

    lines.append(f"- **Total unique risky properties**: {len(total_risky)}")

    # Dark mode awareness
    dark_mode_engines = {"word"}  # Outlook's Word engine has worst dark mode support
    needs_dark_mode_care = any(c.engine.value.lower() in dark_mode_engines for c in clients)
    if needs_dark_mode_care:
        lines.append("")
        lines.append("## Dark Mode Warning")
        lines.append(
            "Target audience includes Outlook (Word engine) — "
            "requires explicit dark mode overrides via MSO conditionals and color-scheme meta."
        )

    lines.append("")
    return "\n".join(lines)


def _build_client_profile(onto: OntologyRegistry, client: EmailClient) -> str:
    """Detailed constraint profile for a single client."""
    lines = [
        f"# Email Client Profile: {client.name}",
        f"- Platform: {client.platform}",
        f"- Engine: {client.engine.value}",
        f"- Market Share: {client.market_share}%",
    ]
    if client.notes:
        lines.append(f"- Notes: {client.notes}")
    lines.append("")

    unsupported = onto.properties_unsupported_by(client.id)
    if unsupported:
        lines.append(f"## Unsupported CSS ({len(unsupported)} properties)")
        for prop in unsupported:
            css_decl = f"{prop.property_name}: {prop.value}" if prop.value else prop.property_name
            fallbacks = onto.fallbacks_for(prop.id)
            # Only include fallbacks relevant to this client
            relevant_fallbacks = [fb for fb in fallbacks if client.id in fb.client_ids]
            if relevant_fallbacks:
                fb = relevant_fallbacks[0]
                target = onto.get_property(fb.target_property_id)
                target_name = (
                    f"{target.property_name}: {target.value}" if target else fb.target_property_id
                )
                lines.append(f"- `{css_decl}` → fallback: `{target_name}` ({fb.technique})")
            else:
                lines.append(f"- `{css_decl}` — no fallback available")
    else:
        lines.append("## Full CSS Support")
        lines.append("This client supports all tracked CSS properties.")

    lines.append("")
    return "\n".join(lines)


def _build_risk_matrix(onto: OntologyRegistry, clients: list[EmailClient]) -> str:
    """Properties that are unsupported across multiple target clients."""
    lines = [
        "# Cross-Client CSS Risk Matrix",
        "",
        "Properties unsupported by 2+ target clients (highest risk).",
        "",
    ]

    # Count how many target clients lack each property
    prop_fail_count: dict[str, list[str]] = {}  # prop_id → [client_names]
    for c in clients:
        for prop in onto.properties_unsupported_by(c.id):
            prop_fail_count.setdefault(prop.id, []).append(c.name)

    # Filter to multi-client failures, sort by count desc
    multi_fail = {pid: names for pid, names in prop_fail_count.items() if len(names) >= 2}

    if not multi_fail:
        lines.append("No CSS properties are unsupported across multiple target clients.")
        return "\n".join(lines)

    lines.append("| CSS Property | Unsupported In | Fallback |")
    lines.append("|-------------|---------------|----------|")

    for pid in sorted(multi_fail, key=lambda p: len(multi_fail[p]), reverse=True):
        risk_prop = onto.get_property(pid)
        if not risk_prop:
            continue
        css_decl = (
            f"{risk_prop.property_name}: {risk_prop.value}"
            if risk_prop.value
            else risk_prop.property_name
        )
        client_names = ", ".join(multi_fail[pid])
        fallbacks = onto.fallbacks_for(pid)
        fb_text = fallbacks[0].technique if fallbacks else "none"
        lines.append(f"| `{css_decl}` | {client_names} | {fb_text} |")

    lines.append("")
    return "\n".join(lines)


async def generate_and_store_subgraph(
    project_id: int,
    project_name: str,
    client_ids: list[str],
) -> None:
    """Generate onboarding documents and store in Cognee graph.

    Fire-and-forget — exceptions are logged but not raised.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.cognee.enabled:
            logger.debug("onboarding.cognee_disabled", project_id=project_id)
            return

        documents = generate_onboarding_documents(project_id, project_name, client_ids)
        if not documents:
            return

        from app.knowledge.graph.cognee_provider import CogneeGraphProvider

        provider = CogneeGraphProvider(settings)

        # Group texts by dataset
        texts = [text for _, text in documents]
        dataset = documents[0][0]  # All share same dataset name

        await provider.add_documents(texts, dataset_name=dataset)
        await provider.build_graph(dataset_name=dataset, background=True)

        logger.info(
            "onboarding.subgraph_stored",
            project_id=project_id,
            document_count=len(documents),
        )
    except Exception:
        logger.warning(
            "onboarding.subgraph_generation_failed",
            project_id=project_id,
            exc_info=True,
        )
