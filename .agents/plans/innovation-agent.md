# Plan: Innovation Agent

## Context

The Innovation agent is the 9th and final agent in the V2 roadmap (task 4.1). It prototypes experimental email techniques (CSS checkbox hacks, AMP, animations, progressive enhancement) and provides feasibility assessments with fallback strategies. Unlike HTML-transformer agents (Outlook Fixer, Dark Mode), the Innovation agent is a **generator** — it produces new prototype code from a technique description, similar to the Scaffolder but focused on experimental/bleeding-edge patterns.

**Already exists:** SKILL.md (112 lines), `__init__.py`, 4 L3 skill files (css_checkbox_hacks, amp_email, css_animations, feasibility_framework).
**Missing:** schemas.py, prompt.py, service.py, CLAUDE.md, eval artifacts (dimensions, synthetic data, judge, mock traces, runner integration), blueprint node, tests.

## Files to Create

| File | Purpose |
|------|---------|
| `app/ai/agents/innovation/schemas.py` | `InnovationRequest`, `InnovationResponse` Pydantic models |
| `app/ai/agents/innovation/prompt.py` | Progressive disclosure prompt builder |
| `app/ai/agents/innovation/service.py` | `InnovationService.process()` orchestration |
| `app/ai/agents/innovation/CLAUDE.md` | Agent documentation |
| `app/ai/agents/innovation/skills/CLAUDE.md` | Skills directory documentation |
| `app/ai/agents/evals/synthetic_data_innovation.py` | 10 dimension-based test cases |
| `app/ai/agents/evals/judges/innovation.py` | 5-criteria binary judge |
| `app/ai/blueprints/nodes/innovation_node.py` | Advisory blueprint node |

## Files to Modify

| File | Change |
|------|--------|
| `app/ai/agents/evals/dimensions.py` | Add `INNOVATION_DIMENSIONS` |
| `app/ai/agents/evals/judges/__init__.py` | Register `InnovationJudge` |
| `app/ai/agents/evals/mock_traces.py` | Add `INNOVATION_CRITERIA` + registry entry |
| `app/ai/agents/evals/runner.py` | Add `run_innovation_case()` + wire into `run_agent()` + CLI choices |
| `app/ai/blueprints/definitions/campaign.py` | Register Innovation node (advisory, no edges) |
| `app/ai/blueprints/tests/test_campaign.py` | Assert innovation node exists |
| `app/ai/agents/tests/test_judges.py` | Add Innovation judge tests |
| `app/ai/agents/CLAUDE.md` | Move Innovation from "Planned" to "Implemented" |

## Implementation Steps

### Step 1: Create `app/ai/agents/innovation/schemas.py`

```python
"""Innovation agent request/response schemas."""

from pydantic import BaseModel, Field


class InnovationRequest(BaseModel):
    """Request to the Innovation agent."""

    technique: str = Field(..., min_length=5, max_length=2000)
    category: str | None = None  # interactive, visual_effects, amp, progressive_enhancement, accessibility
    target_clients: list[str] | None = None  # Optional client filter
    stream: bool = False


class InnovationResponse(BaseModel):
    """Response from the Innovation agent."""

    prototype: str  # Working HTML/CSS prototype
    feasibility: str  # Feasibility assessment text
    client_coverage: float  # 0.0-1.0 estimated coverage
    risk_level: str  # low, medium, high
    recommendation: str  # ship, test_further, avoid
    fallback_html: str  # Static fallback for unsupported clients
    confidence: float  # 0.0-1.0
    skills_loaded: list[str]
    model: str
```

### Step 2: Create `app/ai/agents/innovation/prompt.py`

```python
"""Progressive disclosure prompt builder for the Innovation agent."""

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_AGENT_DIR = Path(__file__).parent

# L3 skill files loaded on-demand
SKILL_FILES: dict[str, str] = {
    "css_checkbox_hacks": "css_checkbox_hacks.md",
    "amp_email": "amp_email.md",
    "css_animations": "css_animations.md",
    "feasibility_framework": "feasibility_framework.md",
}


def detect_relevant_skills(technique: str) -> list[str]:
    """Detect which L3 skills are relevant to the technique request."""
    t = technique.lower()
    relevant: list[str] = []

    # Always load feasibility framework (core to Innovation agent)
    relevant.append("feasibility_framework")

    # Interactive / checkbox hack techniques
    checkbox_keywords = [
        "tab", "accordion", "carousel", "toggle", "checkbox",
        "hamburger", "menu", "interactive", "collapsible", "drawer",
    ]
    if any(kw in t for kw in checkbox_keywords):
        relevant.append("css_checkbox_hacks")

    # AMP for Email
    amp_keywords = [
        "amp", "dynamic", "form", "real-time", "live",
        "carousel amp", "accordion amp", "interactive form",
    ]
    if any(kw in t for kw in amp_keywords):
        relevant.append("amp_email")

    # Animations and transitions
    animation_keywords = [
        "animation", "animate", "transition", "hover",
        "keyframe", "transform", "fade", "slide", "bounce",
        "spin", "pulse", "shake",
    ]
    if any(kw in t for kw in animation_keywords):
        relevant.append("css_animations")

    return relevant


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt from SKILL.md + relevant L3 files."""
    skill_path = _AGENT_DIR / "SKILL.md"
    base_prompt = skill_path.read_text()

    for skill_name in relevant_skills:
        filename = SKILL_FILES.get(skill_name)
        if not filename:
            continue
        skill_file = _AGENT_DIR / "skills" / filename
        if skill_file.exists():
            content = skill_file.read_text()
            base_prompt += f"\n\n---\n## Reference: {skill_name}\n\n{content}"
            logger.info(
                "agents.innovation.skill_loaded",
                skill=skill_name,
            )

    return base_prompt
```

### Step 3: Create `app/ai/agents/innovation/service.py`

```python
"""Innovation agent service — prototype experimental email techniques."""

from __future__ import annotations

from app.ai.agents.innovation.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.innovation.schemas import InnovationRequest, InnovationResponse
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


class InnovationService:
    """Orchestrates technique prototyping with feasibility assessment."""

    async def process(
        self,
        request: InnovationRequest,
    ) -> InnovationResponse:
        """Process an innovation technique request.

        Args:
            request: The technique description and optional filters.

        Returns:
            Prototype with feasibility assessment and fallback.
        """
        logger.info(
            "agents.innovation.process_started",
            technique_length=len(request.technique),
            category=request.category,
        )

        # 1. Detect skills and build prompt
        relevant_skills = detect_relevant_skills(request.technique)
        system_prompt = build_system_prompt(relevant_skills)

        # 2. Build user message
        user_message = _build_user_message(request)

        # 3. Call LLM (use complex model for creative/experimental work)
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("complex")

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(
                messages, model_override=model, max_tokens=8192
            )
        except Exception as exc:
            logger.error("agents.innovation.llm_failed", error=str(exc))
            raise ServiceUnavailableError(
                "Innovation service temporarily unavailable"
            ) from exc

        # 4. Validate and extract confidence
        raw_output = validate_output(response.content)
        confidence = extract_confidence(raw_output)
        clean_output = strip_confidence_comment(raw_output)

        # 5. Parse structured sections from output
        prototype, feasibility, coverage, risk, recommendation, fallback = (
            _parse_innovation_output(clean_output)
        )

        logger.info(
            "agents.innovation.process_completed",
            confidence=confidence,
            risk_level=risk,
            client_coverage=coverage,
            model=response.model,
        )

        return InnovationResponse(
            prototype=prototype,
            feasibility=feasibility,
            client_coverage=coverage,
            risk_level=risk,
            recommendation=recommendation,
            fallback_html=fallback,
            confidence=confidence or 0.5,
            skills_loaded=relevant_skills,
            model=response.model,
        )


def _build_user_message(request: InnovationRequest) -> str:
    """Build the user message with technique request and constraints."""
    parts = [f"## TECHNIQUE REQUEST\n{request.technique}"]

    if request.category:
        parts.append(f"\n## CATEGORY\n{request.category}")

    if request.target_clients:
        clients = ", ".join(request.target_clients)
        parts.append(f"\n## TARGET CLIENTS\n{clients}")

    parts.append(
        "\n## INSTRUCTIONS\n"
        "Provide your response with these clearly labelled sections:\n"
        "### 1. Prototype\nComplete working HTML/CSS code.\n"
        "### 2. Feasibility Assessment\nClient coverage %, risk level, "
        "file size impact, complexity, recommendation.\n"
        "### 3. Fallback Strategy\nStatic fallback HTML for unsupported clients.\n"
        "### 4. Known Limitations\nClient-specific issues and caveats.\n\n"
        "End with a confidence comment: <!-- CONFIDENCE: 0.XX -->"
    )

    return "\n".join(parts)


def _parse_innovation_output(
    output: str,
) -> tuple[str, str, float, str, str, str]:
    """Parse structured sections from Innovation agent output.

    Returns:
        Tuple of (prototype, feasibility, coverage, risk, recommendation, fallback).
    """
    prototype = ""
    feasibility = ""
    coverage = 0.5
    risk = "medium"
    recommendation = "test_further"
    fallback = ""

    sections = output.split("### ")
    for section in sections:
        lower = section.lower()
        if lower.startswith("1.") or lower.startswith("prototype"):
            prototype = section.split("\n", 1)[-1].strip() if "\n" in section else ""
        elif lower.startswith("2.") or lower.startswith("feasibility"):
            feasibility = section.split("\n", 1)[-1].strip() if "\n" in section else ""
            # Extract coverage percentage
            coverage = _extract_percentage(feasibility)
            # Extract risk level
            risk = _extract_risk(feasibility)
            # Extract recommendation
            recommendation = _extract_recommendation(feasibility)
        elif lower.startswith("3.") or lower.startswith("fallback"):
            fallback = section.split("\n", 1)[-1].strip() if "\n" in section else ""

    return prototype, feasibility, coverage, risk, recommendation, fallback


def _extract_percentage(text: str) -> float:
    """Extract a percentage from text, return as 0.0-1.0."""
    import re

    match = re.search(r"(\d{1,3})%", text)
    if match:
        return min(int(match.group(1)) / 100.0, 1.0)
    return 0.5


def _extract_risk(text: str) -> str:
    """Extract risk level from feasibility text."""
    lower = text.lower()
    if "high risk" in lower or "risk: high" in lower or "risk level: high" in lower:
        return "high"
    if "low risk" in lower or "risk: low" in lower or "risk level: low" in lower:
        return "low"
    return "medium"


def _extract_recommendation(text: str) -> str:
    """Extract recommendation from feasibility text."""
    lower = text.lower()
    if "avoid" in lower:
        return "avoid"
    if "ship" in lower and "test" not in lower:
        return "ship"
    return "test_further"


def get_innovation_service() -> InnovationService:
    """Get singleton Innovation agent service."""
    return InnovationService()
```

### Step 4: Create `app/ai/agents/innovation/CLAUDE.md`

```markdown
# Innovation Agent

Prototypes experimental email techniques and assesses their feasibility. Handles CSS checkbox hacks (tabs, accordions, carousels), AMP for Email, CSS animations, and progressive enhancement patterns.

## Architecture
- **Generator agent** — Produces new prototype code from technique descriptions
- **No DB dependency** — Pure LLM generation (no RAG, no DB session)
- **Progressive disclosure** — SKILL.md (L1+L2) + 4 L3 skill files loaded on-demand
- **Uses complex model** — Creative work benefits from stronger reasoning

## Files
- `schemas.py` — `InnovationRequest`, `InnovationResponse`
- `prompt.py` — `detect_relevant_skills()`, `build_system_prompt()`
- `service.py` — `InnovationService.process()` (build prompt → LLM → parse sections)
- `SKILL.md` — Core instructions (categories, rules, output structure, confidence)
- `skills/` — 4 L3 files (css_checkbox_hacks, amp_email, css_animations, feasibility_framework)

## Eval
- 10 synthetic test cases in `evals/synthetic_data_innovation.py`
- 5-criteria judge in `evals/judges/innovation.py` (technique_correctness, fallback_quality, client_coverage_accuracy, feasibility_assessment, innovation_value)
```

### Step 5: Create `app/ai/agents/innovation/skills/CLAUDE.md`

```markdown
# Innovation Agent — L3 Skill Files

Progressive disclosure reference files loaded on-demand based on technique request keywords.

## Files
- `css_checkbox_hacks.md` — CSS-only interactive patterns (tabs, accordions, carousels, menus)
- `amp_email.md` — AMP for Email components, forms, dynamic content
- `css_animations.md` — CSS animations, transitions, hover effects, keyframes
- `feasibility_framework.md` — Client coverage scoring, risk assessment, fallback strategy framework

## Loading Rules
- `feasibility_framework` always loaded (core to Innovation agent)
- Others loaded based on keyword detection in technique request
```

### Step 6: Add `INNOVATION_DIMENSIONS` to `app/ai/agents/evals/dimensions.py`

Append after `KNOWLEDGE_DIMENSIONS`:

```python
# ---------------------------------------------------------------------------
# Innovation Agent Dimensions
# ---------------------------------------------------------------------------
INNOVATION_DIMENSIONS = {
    "technique_category": {
        "description": "Type of experimental email technique being prototyped",
        "values": [
            "css_checkbox_interactive",
            "css_animation_transition",
            "amp_for_email",
            "progressive_enhancement",
            "accessibility_innovation",
        ],
    },
    "client_coverage_challenge": {
        "description": "How widely the technique is supported across email clients",
        "values": [
            "broad_support",
            "modern_only",
            "single_engine",
            "near_zero_support",
        ],
    },
    "fallback_complexity": {
        "description": "Difficulty of providing a graceful fallback",
        "values": [
            "simple_static",
            "degraded_but_functional",
            "requires_conditional",
            "no_graceful_fallback",
        ],
    },
    "implementation_risk": {
        "description": "Risk level based on technique maturity and edge cases",
        "values": [
            "production_proven",
            "tested_limited",
            "experimental_untested",
            "bleeding_edge",
        ],
    },
}
```

### Step 7: Create `app/ai/agents/evals/synthetic_data_innovation.py`

```python
"""Synthetic test data for the Innovation agent evaluation.

10 dimension-based test cases covering CSS checkbox hacks, AMP for Email,
CSS animations, progressive enhancement, and accessibility innovations.
"""

from typing import Any

INNOVATION_TEST_CASES: list[dict[str, Any]] = [
    # --- CSS Checkbox Interactive ---
    {
        "id": "inn-001",
        "technique": "Create a CSS-only tabbed content section for email where users can click tabs to show/hide different product categories without JavaScript.",
        "category": "interactive",
        "dimensions": {
            "technique_category": "css_checkbox_interactive",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use hidden checkbox + label + sibling selector pattern",
            "Provide static fallback showing all content stacked",
            "Note Apple Mail, iOS Mail support; Outlook/Gmail do NOT",
            "Coverage should be ~40-50% (WebKit clients only)",
        ],
    },
    {
        "id": "inn-002",
        "technique": "Build a CSS-only accordion FAQ section for email. Each question should expand/collapse when clicked.",
        "category": "interactive",
        "dimensions": {
            "technique_category": "css_checkbox_interactive",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "degraded_but_functional",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use radio input + label pattern for mutual exclusion",
            "Fallback: all answers visible (stacked)",
            "Correct client coverage estimate (Apple Mail yes, Gmail no)",
            "Note file size impact of repeated checkbox patterns",
        ],
    },
    # --- CSS Animations ---
    {
        "id": "inn-003",
        "technique": "Add a subtle fade-in animation to the hero image and CTA button when the email is opened.",
        "category": "visual_effects",
        "dimensions": {
            "technique_category": "css_animation_transition",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use @keyframes with opacity transition",
            "Fallback: elements visible immediately (no animation)",
            "Note Apple Mail supports, Outlook/Gmail strip @keyframes",
            "Reduced motion media query for accessibility",
        ],
    },
    {
        "id": "inn-004",
        "technique": "Create a countdown timer animation in CSS that counts down from 10 to 0 for a flash sale email.",
        "category": "visual_effects",
        "dimensions": {
            "technique_category": "css_animation_transition",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "experimental_untested",
        },
        "expected_challenges": [
            "Acknowledge CSS-only countdown has severe limitations",
            "High risk / avoid recommendation (timing unreliable)",
            "Suggest server-side image countdown as better alternative",
            "Very low coverage (~20% at best)",
        ],
    },
    # --- AMP for Email ---
    {
        "id": "inn-005",
        "technique": "Build an interactive product carousel using AMP for Email that users can swipe through directly in their inbox.",
        "category": "amp",
        "dimensions": {
            "technique_category": "amp_for_email",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use amp-carousel component with proper AMP boilerplate",
            "MIME multipart fallback (HTML version for non-AMP clients)",
            "Coverage: Gmail only (~30%), must be sender-verified",
            "Note AMP sender registration requirement",
        ],
    },
    {
        "id": "inn-006",
        "technique": "Create an in-email survey form using AMP for Email where users can submit responses without leaving the inbox.",
        "category": "amp",
        "dimensions": {
            "technique_category": "amp_for_email",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use amp-form with proper action-xhr endpoint",
            "Fallback: link to external survey form",
            "Note CORS requirements for AMP form endpoints",
            "Gmail-only coverage, sender registration needed",
        ],
    },
    # --- Progressive Enhancement ---
    {
        "id": "inn-007",
        "technique": "Use CSS Grid for a product grid layout that falls back to table-based layout for Outlook.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "broad_support",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "CSS Grid in style block for modern clients",
            "MSO conditional table-based fallback for Outlook",
            "Coverage: ~70% see Grid, 30% see table fallback",
            "Both versions must look professional",
        ],
    },
    {
        "id": "inn-008",
        "technique": "Implement CSS custom properties (variables) for theming an email with a single color change point.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "degraded_but_functional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Define --brand-color in style block",
            "Inline style fallback values for Outlook/Gmail",
            "Note Gmail strips custom properties",
            "Coverage ~45% (Apple Mail, iOS yes; Gmail, Outlook no)",
        ],
    },
    # --- Accessibility Innovation ---
    {
        "id": "inn-009",
        "technique": "Add prefers-reduced-motion support to all animations in an email, with a static fallback for users who prefer reduced motion.",
        "category": "accessibility",
        "dimensions": {
            "technique_category": "accessibility_innovation",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use @media (prefers-reduced-motion: reduce) query",
            "Disable all animations and transitions inside the query",
            "Note: only clients that support @media support this",
            "Recommend as best practice alongside any animation technique",
        ],
    },
    # --- Edge Case / Near-Zero Support ---
    {
        "id": "inn-010",
        "technique": "Create an email with CSS Scroll Snap for a horizontal scrollable gallery of product images.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "near_zero_support",
            "fallback_complexity": "no_graceful_fallback",
            "implementation_risk": "bleeding_edge",
        },
        "expected_challenges": [
            "Acknowledge scroll-snap has near-zero email client support",
            "Recommend 'avoid' — technique not viable for email",
            "Suggest alternative: linked image grid or AMP carousel",
            "Risk level should be 'high'",
        ],
    },
]
```

### Step 8: Create `app/ai/agents/evals/judges/innovation.py`

```python
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Innovation agent."""

from app.ai.agents.evals.judges.base import (
    SYSTEM_PROMPT_TEMPLATE,
    build_criteria_block,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

INNOVATION_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="technique_correctness",
        description=(
            "Is the prototype code technically correct for the requested technique? "
            "CSS checkbox hacks must use the hidden-input + label + sibling-selector "
            "pattern. AMP components must include proper boilerplate. Animations must "
            "use valid @keyframes. Code must be HTML/CSS only (no JavaScript). "
            "Prototype with syntax errors or wrong patterns is a failure."
        ),
    ),
    JudgeCriteria(
        name="fallback_quality",
        description=(
            "Does the response include a production-quality fallback for unsupported "
            "clients? The fallback must be static HTML that displays meaningful content "
            "(not blank or broken). AMP techniques need MIME fallback mention. "
            "Missing fallback or a fallback that renders broken is a failure."
        ),
    ),
    JudgeCriteria(
        name="client_coverage_accuracy",
        description=(
            "Is the stated client coverage percentage realistic? Apple Mail/iOS support "
            "most CSS; Gmail strips most advanced CSS; Outlook uses Word renderer. "
            "Overstating coverage (e.g., claiming 80% for checkbox hacks) is a failure. "
            "Understating by >20 percentage points is also a failure."
        ),
    ),
    JudgeCriteria(
        name="feasibility_assessment",
        description=(
            "Does the feasibility assessment include risk level, file size impact, "
            "and a clear recommendation (ship/test_further/avoid)? The recommendation "
            "must be appropriate — bleeding-edge techniques should not recommend 'ship'. "
            "Well-proven patterns should not recommend 'avoid'. Missing any of "
            "risk/recommendation/coverage is a failure."
        ),
    ),
    JudgeCriteria(
        name="innovation_value",
        description=(
            "Does the response demonstrate genuine knowledge of the technique's "
            "trade-offs and provide actionable guidance? A response that only shows "
            "generic code without email-specific context (client quirks, limitations, "
            "workarounds) is a failure. The response should help a developer make an "
            "informed decision about whether to use this technique."
        ),
    ),
]


class InnovationJudge:
    """Binary judge for Innovation agent outputs."""

    agent_name: str = "innovation"
    criteria: list[JudgeCriteria] = INNOVATION_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with technique request and prototype output."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        technique = ""
        category = "any"
        if judge_input.input_data:
            technique = str(judge_input.input_data.get("technique", ""))
            category = str(judge_input.input_data.get("category", "any"))

        prototype_output = ""
        feasibility_output = ""
        fallback_output = ""
        if judge_input.output_data:
            prototype_output = str(judge_input.output_data.get("prototype", ""))
            feasibility_output = str(judge_input.output_data.get("feasibility", ""))
            fallback_output = str(judge_input.output_data.get("fallback_html", ""))

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## TECHNIQUE REQUEST\n{technique}\n\n"
            f"## CATEGORY\n{category}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT OUTPUT (Prototype)\n{prototype_output}\n\n"
            f"## AGENT OUTPUT (Feasibility)\n{feasibility_output}\n\n"
            f"## AGENT OUTPUT (Fallback)\n{fallback_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
```

### Step 9: Modify `app/ai/agents/evals/judges/__init__.py`

Add import and registry entry:

```python
# Add import
from app.ai.agents.evals.judges.innovation import InnovationJudge

# Add to JUDGE_REGISTRY type union: | InnovationJudge
# Add entry: "innovation": InnovationJudge,

# Add to __all__: "InnovationJudge",
```

Full updated file:

```python
"""LLM judge modules for agent evaluation."""

from app.ai.agents.evals.judges.accessibility import AccessibilityJudge
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge
from app.ai.agents.evals.judges.content import ContentJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.innovation import InnovationJudge
from app.ai.agents.evals.judges.knowledge import KnowledgeJudge
from app.ai.agents.evals.judges.outlook_fixer import OutlookFixerJudge
from app.ai.agents.evals.judges.personalisation import PersonalisationJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import (
    CriterionResult,
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

JUDGE_REGISTRY: dict[
    str,
    type[
        ScaffolderJudge
        | DarkModeJudge
        | ContentJudge
        | OutlookFixerJudge
        | AccessibilityJudge
        | PersonalisationJudge
        | CodeReviewerJudge
        | KnowledgeJudge
        | InnovationJudge
    ],
] = {
    "scaffolder": ScaffolderJudge,
    "dark_mode": DarkModeJudge,
    "content": ContentJudge,
    "outlook_fixer": OutlookFixerJudge,
    "accessibility": AccessibilityJudge,
    "personalisation": PersonalisationJudge,
    "code_reviewer": CodeReviewerJudge,
    "knowledge": KnowledgeJudge,
    "innovation": InnovationJudge,
}

__all__ = [
    "JUDGE_REGISTRY",
    "AccessibilityJudge",
    "CodeReviewerJudge",
    "ContentJudge",
    "CriterionResult",
    "DarkModeJudge",
    "InnovationJudge",
    "JudgeCriteria",
    "JudgeInput",
    "JudgeVerdict",
    "KnowledgeJudge",
    "OutlookFixerJudge",
    "PersonalisationJudge",
    "ScaffolderJudge",
]
```

### Step 10: Modify `app/ai/agents/evals/mock_traces.py`

Add after `KNOWLEDGE_CRITERIA`:

```python
INNOVATION_CRITERIA: list[dict[str, str]] = [
    {"criterion": "technique_correctness", "description": "Prototype code technically correct"},
    {"criterion": "fallback_quality", "description": "Production-quality fallback provided"},
    {"criterion": "client_coverage_accuracy", "description": "Coverage percentage realistic"},
    {"criterion": "feasibility_assessment", "description": "Risk, recommendation, and coverage present"},
    {"criterion": "innovation_value", "description": "Actionable email-specific guidance"},
]
```

Add to `AGENT_CRITERIA` dict:

```python
    "innovation": INNOVATION_CRITERIA,
```

### Step 11: Modify `app/ai/agents/evals/runner.py`

1. Add import at top:
```python
from app.ai.agents.evals.synthetic_data_innovation import INNOVATION_TEST_CASES
```

2. Add `run_innovation_case()` function (after `run_knowledge_case`):
```python
async def run_innovation_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single innovation test case and return the trace."""
    from app.ai.agents.innovation.schemas import InnovationRequest
    from app.ai.agents.innovation.service import InnovationService

    service = InnovationService()
    technique: str = str(case["technique"])
    category: str | None = case.get("category")
    request = InnovationRequest(technique=technique, category=category)

    start = time.monotonic()
    try:
        response = await service.process(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "innovation",
            "dimensions": case["dimensions"],
            "input": {
                "technique": technique,
                "category": category,
            },
            "output": {
                "prototype": response.prototype,
                "feasibility": response.feasibility,
                "client_coverage": response.client_coverage,
                "risk_level": response.risk_level,
                "recommendation": response.recommendation,
                "fallback_html": response.fallback_html,
                "confidence": response.confidence,
                "skills_loaded": response.skills_loaded,
                "model": response.model,
            },
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "innovation",
            "dimensions": case["dimensions"],
            "input": {
                "technique": technique,
                "category": category,
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
```

3. Add `"innovation"` branch in `run_agent()` function (after the `"knowledge"` elif):
```python
    elif agent == "innovation":
        cases = INNOVATION_TEST_CASES
        runner = run_innovation_case
```

4. Add `"innovation"` to CLI choices and `"all"` list in `main()`.

### Step 12: Create `app/ai/blueprints/nodes/innovation_node.py`

Advisory node (like Knowledge — not in QA→recovery loop):

```python
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Innovation node — experimental technique prototyping for blueprint context.

Advisory node: provides technique feasibility assessment to downstream agents.
Not part of the QA → recovery router loop.
"""

from app.ai.agents.innovation.prompt import build_system_prompt, detect_relevant_skills
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class InnovationNode:
    """Advisory blueprint node for experimental technique prototyping."""

    @property
    def name(self) -> str:
        return "innovation"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Execute innovation prototyping for the current brief/context.

        Reads the brief as the technique request. Returns prototype and
        feasibility in AgentHandoff.decisions for downstream agents.
        """
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("complex")

        technique = context.brief or context.metadata.get("innovation_request", "")
        if not technique:
            return NodeResult(
                status="skipped",
                html=context.html,
                details="No technique request provided for innovation prototyping",
            )

        # Build prompt
        relevant_skills = detect_relevant_skills(str(technique))
        system_prompt = build_system_prompt(relevant_skills)

        user_message = (
            f"## TECHNIQUE REQUEST\n{technique}\n\n"
            "Provide a working prototype, feasibility assessment with client coverage %, "
            "risk level, and recommendation, plus a static fallback.\n"
            "End with <!-- CONFIDENCE: 0.XX -->"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("agents.innovation.node_failed", error=str(exc))
            return NodeResult(
                status="failed",
                html=context.html,
                error=f"Innovation prototyping failed: {exc}",
            )

        raw_output = validate_output(response.content)
        confidence = extract_confidence(raw_output)
        clean_output = strip_confidence_comment(raw_output)

        handoff = AgentHandoff(
            status=HandoffStatus.OK,
            agent_name="innovation",
            artifact=clean_output,
            decisions=(f"innovation_prototype: {clean_output[:200]}",),
            warnings=(),
            component_refs=(),
            confidence=confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through unchanged
            handoff=handoff,
            usage=response.usage,
        )
```

### Step 13: Modify `app/ai/blueprints/definitions/campaign.py`

Add import and node registration:

```python
# Add import
from app.ai.blueprints.nodes.innovation_node import InnovationNode

# In build_campaign_blueprint(), add after knowledge = KnowledgeNode():
    innovation = InnovationNode()

# Add to nodes dict:
    innovation.name: innovation,

# No edges needed — advisory node like knowledge
```

### Step 14: Modify `app/ai/blueprints/tests/test_campaign.py`

Add assertion for innovation node:

```python
    assert "innovation" in definition.nodes
    assert definition.nodes["innovation"].node_type == "agentic"
```

Update edge count assertion if it exists (should remain the same — no new edges).

### Step 15: Add Innovation judge tests to `app/ai/agents/tests/test_judges.py`

Add after Code Reviewer tests:

```python
# --- Innovation Judge Tests ---

from app.ai.agents.evals.judges.innovation import InnovationJudge


def _make_innovation_input() -> JudgeInput:
    return JudgeInput(
        trace_id="inn-001",
        agent="innovation",
        input_data={
            "technique": "Create a CSS-only tabbed content section for email",
            "category": "interactive",
        },
        output_data={
            "prototype": "<input type='checkbox' id='tab1'><label for='tab1'>Tab 1</label>",
            "feasibility": "Client coverage: 45%. Risk level: medium. Recommendation: test_further.",
            "fallback_html": "<table><tr><td>All content stacked</td></tr></table>",
        },
        expected_challenges=["checkbox pattern", "static fallback"],
    )


INNOVATION_CRITERIA_NAMES = [
    "technique_correctness",
    "fallback_quality",
    "client_coverage_accuracy",
    "feasibility_assessment",
    "innovation_value",
]


class TestInnovationJudge:
    def test_build_prompt_contains_criteria_and_input(self) -> None:
        judge = InnovationJudge()
        prompt = judge.build_prompt(_make_innovation_input())

        assert "technique_correctness" in prompt
        assert "fallback_quality" in prompt
        assert "client_coverage_accuracy" in prompt
        assert "CSS-only tabbed content" in prompt
        assert "interactive" in prompt

    def test_parse_valid_response(self) -> None:
        judge = InnovationJudge()
        raw = _make_valid_response(INNOVATION_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_innovation_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.error is None
        assert verdict.trace_id == "inn-001"
        assert verdict.agent == "innovation"
```

Update `TestJudgeRegistry`:

```python
    def test_registry_has_all_agents(self) -> None:
        # ... existing assertions ...
        assert "innovation" in JUDGE_REGISTRY
        assert len(JUDGE_REGISTRY) == 9
```

### Step 16: Update `app/ai/agents/CLAUDE.md`

Move Innovation from "Planned Agents" to "Implemented Agents (V2)":

```markdown
## Implemented Agents (V2 — task 4.1, eval-first + skills workflow, continued)
- **Innovation** (`innovation/`) — Prototypes experimental email techniques: CSS checkbox hacks (tabs, accordions, carousels), AMP for Email, CSS animations, progressive enhancement. **Generator agent** (produces new prototype code, not an HTML transformer). Provides feasibility assessment (risk level, client coverage %, recommendation), static fallback HTML, and known limitations. Progressive disclosure: SKILL.md (L1+L2) + 4 L3 skill files (css_checkbox_hacks, amp_email, css_animations, feasibility_framework). Blueprint node is advisory (not in QA→recovery loop).
```

Remove "Planned Agents" section (no agents remaining).

Update eval status table to add Innovation row and update registry count from 8 to 9.

## Security Checklist

The Innovation agent has NO HTTP routes (it's called via blueprint node or internal service). No endpoints to secure.

- [x] Auth dependency — N/A (no routes)
- [x] Authorization check — N/A (no routes)
- [x] Rate limiting — N/A (no routes; blueprint pipeline has its own token cap)
- [x] Input validation — Pydantic `InnovationRequest` with min/max length
- [x] Error responses — Uses `ServiceUnavailableError` from AppError hierarchy
- [x] No secrets in logs — Only logs technique_length, category, confidence, risk_level

## Verification — COMPLETED (2026-03-09)

- [x] `make check` — 191 AI tests pass, pyright 0 errors, ruff security clean
- [x] `make eval-dry-run` — innovation agent 10/10 traces generated
- [x] Innovation judge tests pass (prompt building + response parsing) — 2 tests
- [x] Blueprint test confirms innovation node exists and is agentic
- [x] Judge registry count is 9 (all agents)
- [x] `python -m app.ai.agents.evals.runner --agent innovation --dry-run --output traces/` — 10/10 succeeded
