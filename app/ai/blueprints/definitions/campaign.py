"""Campaign blueprint — full email generation pipeline with self-correction.

Graph:
  scaffolder → qa_gate → (success) → maizzle_build → export
                       → (qa_fail) → recovery_router → dark_mode → qa_gate (loop)
                                                      → outlook_fixer → qa_gate (loop)
                                                      → scaffolder (loop)
"""

from app.ai.blueprints.engine import BlueprintDefinition, Edge
from app.ai.blueprints.nodes.dark_mode_node import DarkModeNode
from app.ai.blueprints.nodes.export_node import ExportNode
from app.ai.blueprints.nodes.maizzle_build_node import MaizzleBuildNode
from app.ai.blueprints.nodes.outlook_fixer_node import OutlookFixerNode
from app.ai.blueprints.nodes.qa_gate_node import QAGateNode
from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
from app.ai.blueprints.nodes.scaffolder_node import ScaffolderNode
from app.ai.blueprints.protocols import BlueprintNode


def build_campaign_blueprint() -> BlueprintDefinition:
    """Construct the campaign email generation blueprint."""
    scaffolder = ScaffolderNode()
    qa_gate = QAGateNode()
    maizzle_build = MaizzleBuildNode()
    export = ExportNode()
    recovery_router = RecoveryRouterNode()
    dark_mode = DarkModeNode()
    outlook_fixer = OutlookFixerNode()

    nodes: dict[str, BlueprintNode] = {
        scaffolder.name: scaffolder,
        qa_gate.name: qa_gate,
        maizzle_build.name: maizzle_build,
        export.name: export,
        recovery_router.name: recovery_router,
        dark_mode.name: dark_mode,
        outlook_fixer.name: outlook_fixer,
    }

    edges = [
        # scaffolder always feeds into QA
        Edge(from_node="scaffolder", to_node="qa_gate", condition="always"),
        # QA pass → build
        Edge(from_node="qa_gate", to_node="maizzle_build", condition="success"),
        # QA fail → recovery router
        Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
        # Recovery router routes to specific fixer
        Edge(
            from_node="recovery_router",
            to_node="dark_mode",
            condition="route_to",
            route_value="dark_mode",
        ),
        Edge(
            from_node="recovery_router",
            to_node="outlook_fixer",
            condition="route_to",
            route_value="outlook_fixer",
        ),
        Edge(
            from_node="recovery_router",
            to_node="scaffolder",
            condition="route_to",
            route_value="scaffolder",
        ),
        # Dark mode fix loops back to QA
        Edge(from_node="dark_mode", to_node="qa_gate", condition="always"),
        # Outlook fixer loops back to QA
        Edge(from_node="outlook_fixer", to_node="qa_gate", condition="always"),
        # Build → export
        Edge(from_node="maizzle_build", to_node="export", condition="always"),
    ]

    return BlueprintDefinition(
        name="campaign",
        nodes=nodes,
        edges=edges,
        entry_node="scaffolder",
    )
