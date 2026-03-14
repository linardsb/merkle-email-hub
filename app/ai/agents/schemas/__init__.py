"""Structured output schemas for agent decisions.

Each agent returns structured JSON (not raw HTML) when in structured mode.
Deterministic code assembles the output from these plans.

Legacy plan schemas (DarkModePlan, AccessibilityPlan, etc.) are retained
for backward compatibility.  New code should use the *Decisions schemas
which operate on EmailBuildPlan fields rather than raw HTML selectors.
"""

from app.ai.agents.schemas.accessibility_decisions import (
    AccessibilityDecisions,
    AltTextDecision,
    HeadingDecision,
)
from app.ai.agents.schemas.accessibility_plan import AccessibilityPlan
from app.ai.agents.schemas.build_plan import EmailBuildPlan
from app.ai.agents.schemas.code_review_decisions import (
    CodeReviewDecisions,
    PlanQualityIssue,
)
from app.ai.agents.schemas.code_review_plan import CodeReviewPlan
from app.ai.agents.schemas.content_decisions import (
    ContentDecisions,
    SlotContentRefinement,
)
from app.ai.agents.schemas.content_plan import ContentPlan
from app.ai.agents.schemas.dark_mode_decisions import (
    DarkColorOverride,
    DarkModeDecisions,
)
from app.ai.agents.schemas.dark_mode_plan import DarkModePlan
from app.ai.agents.schemas.outlook_diagnostic import (
    MSOIssue,
    OutlookDiagnostic,
)
from app.ai.agents.schemas.outlook_plan import OutlookFixPlan
from app.ai.agents.schemas.personalisation_decisions import (
    PersonalisationDecisions,
    VariablePlacement,
)
from app.ai.agents.schemas.personalisation_plan import PersonalisationPlan

__all__ = [
    "AccessibilityDecisions",
    "AccessibilityPlan",
    "AltTextDecision",
    "CodeReviewDecisions",
    "CodeReviewPlan",
    "ContentDecisions",
    "ContentPlan",
    "DarkColorOverride",
    "DarkModeDecisions",
    "DarkModePlan",
    "EmailBuildPlan",
    "HeadingDecision",
    "MSOIssue",
    "OutlookDiagnostic",
    "OutlookFixPlan",
    "PersonalisationDecisions",
    "PersonalisationPlan",
    "PlanQualityIssue",
    "SlotContentRefinement",
    "VariablePlacement",
]
