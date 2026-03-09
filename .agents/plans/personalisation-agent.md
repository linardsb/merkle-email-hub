# Plan: Personalisation Agent

## Context

Third agent built using the eval-first + skills workflow (Task 4.1 Priority 3). Injects ESP-specific personalisation syntax — Braze Liquid, SFMC AMPscript, Adobe Campaign JavaScript — into email HTML. The SKILL.md and 4 L3 skill files already exist. This plan covers: schemas, prompt loader, service, blueprint node, recovery router wiring, eval infrastructure (synthetic data, judge, dimensions), runner/judge_runner integration, and verification.

Reference implementation: Outlook Fixer agent (same pattern).

## Pre-existing Files (DO NOT recreate)

These files already exist and are complete:
- `app/ai/agents/personalisation/__init__.py`
- `app/ai/agents/personalisation/SKILL.md` — L1 metadata + L2 core instructions
- `app/ai/agents/personalisation/skills/braze_liquid.md` — L3 Braze Liquid reference
- `app/ai/agents/personalisation/skills/sfmc_ampscript.md` — L3 SFMC AMPscript reference
- `app/ai/agents/personalisation/skills/adobe_campaign_js.md` — L3 Adobe Campaign reference
- `app/ai/agents/personalisation/skills/fallback_patterns.md` — L3 universal fallback patterns

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `app/ai/agents/personalisation/schemas.py` | Request/response Pydantic models |
| 2 | `app/ai/agents/personalisation/prompt.py` | SKILL.md loader + progressive disclosure detection |
| 3 | `app/ai/agents/personalisation/service.py` | Agent pipeline: detect skills → LLM → sanitize → QA |
| 4 | `app/ai/blueprints/nodes/personalisation_node.py` | Agentic blueprint node |
| 5 | `app/ai/agents/evals/synthetic_data_personalisation.py` | 12 synthetic test cases |
| 6 | `app/ai/agents/evals/judges/personalisation.py` | 5-criteria binary judge |

## Files to Modify

| # | File | Change |
|---|------|--------|
| 7 | `app/ai/agents/evals/dimensions.py` | Add `PERSONALISATION_DIMENSIONS` |
| 8 | `app/ai/agents/evals/judges/__init__.py` | Register `PersonalisationJudge` |
| 9 | `app/ai/agents/evals/mock_traces.py` | Add `PERSONALISATION_CRITERIA` + register in `AGENT_CRITERIA` |
| 10 | `app/ai/agents/evals/runner.py` | Add `run_personalisation_case()` + import + dispatch |
| 11 | `app/ai/blueprints/nodes/recovery_router_node.py` | Add personalisation failure routing |
| 12 | `app/ai/blueprints/definitions/campaign.py` | Wire `PersonalisationNode` into graph |

## Implementation Steps

### Step 1: Create `schemas.py`

File: `app/ai/agents/personalisation/schemas.py`

```python
"""Request/response schemas for the Personalisation agent."""

from typing import Literal

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult


ESPPlatform = Literal["braze", "sfmc", "adobe_campaign"]


class PersonalisationRequest(BaseModel):
    """Request body for the Personalisation process endpoint.

    Attributes:
        html: Existing email HTML to personalise.
        platform: Target ESP platform for syntax generation.
        requirements: Natural language description of personalisation needs.
        stream: Whether to return SSE streaming response.
        run_qa: Whether to run the 10-point QA gate on the output HTML.
    """

    html: str = Field(min_length=50, max_length=200_000, description="Email HTML to personalise")
    platform: ESPPlatform = Field(description="Target ESP platform")
    requirements: str = Field(
        min_length=5,
        max_length=5_000,
        description="What personalisation to add (e.g., 'Add first name greeting with fallback, show VIP section for premium users')",
    )
    stream: bool = False
    run_qa: bool = False


class PersonalisationResponse(BaseModel):
    """Response from the Personalisation process endpoint.

    Attributes:
        html: Email HTML with ESP-specific personalisation tags injected.
        platform: The ESP platform used.
        tags_injected: List of personalisation tags added.
        qa_results: Individual QA check results (only when run_qa=True).
        qa_passed: Overall QA pass/fail (only when run_qa=True).
        model: The model identifier that processed the HTML.
    """

    html: str
    platform: ESPPlatform
    tags_injected: list[str] = Field(default_factory=list)
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
```

### Step 2: Create `prompt.py`

File: `app/ai/agents/personalisation/prompt.py`

Follow the exact pattern from `app/ai/agents/outlook_fixer/prompt.py`:

```python
"""System prompt for the Personalisation agent.

Thin prompt — core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.personalisation.schemas import ESPPlatform

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""


def _load_skill_file(name: str) -> str:
    """Load an L3 skill reference file by name."""
    path = _SKILL_DIR / "skills" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# L3 reference files — loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "braze_liquid": "braze_liquid.md",
    "sfmc_ampscript": "sfmc_ampscript.md",
    "adobe_campaign_js": "adobe_campaign_js.md",
    "fallback_patterns": "fallback_patterns.md",
}

PERSONALISATION_SYSTEM_PROMPT = f"""\
You are an expert email personalisation engineer. Your sole task is to
inject ESP-specific dynamic content syntax into email HTML.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [PERSONALISATION_SYSTEM_PROMPT]

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(platform: ESPPlatform, requirements: str) -> list[str]:
    """Detect which L3 skill files are relevant based on platform and requirements.

    Progressive disclosure — load the platform-specific file + fallback patterns.

    Args:
        platform: Target ESP platform.
        requirements: Natural language personalisation requirements.

    Returns:
        List of relevant skill keys.
    """
    skills: list[str] = []

    # Always load fallback patterns
    skills.append("fallback_patterns")

    # Load platform-specific skill
    platform_map: dict[ESPPlatform, str] = {
        "braze": "braze_liquid",
        "sfmc": "sfmc_ampscript",
        "adobe_campaign": "adobe_campaign_js",
    }
    platform_skill = platform_map.get(platform)
    if platform_skill:
        skills.append(platform_skill)

    # Cross-platform references only if requirements mention another platform
    req_lower = requirements.lower()
    if platform != "braze" and ("liquid" in req_lower or "braze" in req_lower):
        skills.append("braze_liquid")
    if platform != "sfmc" and ("ampscript" in req_lower or "sfmc" in req_lower):
        skills.append("sfmc_ampscript")
    if platform != "adobe_campaign" and ("adobe" in req_lower or "jssp" in req_lower):
        skills.append("adobe_campaign_js")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
```

### Step 3: Create `service.py`

File: `app/ai/agents/personalisation/service.py`

Follow exact pattern from `app/ai/agents/outlook_fixer/service.py`:

```python
# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Personalisation agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.personalisation.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import (
    PersonalisationRequest,
    PersonalisationResponse,
)
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _build_user_message(request: PersonalisationRequest) -> str:
    """Build the user message from the request fields."""
    return (
        f"Add personalisation to the following email HTML for the {request.platform} platform.\n\n"
        f"Requirements:\n{request.requirements}\n\n"
        f"Email HTML:\n{request.html}"
    )


class PersonalisationService:
    """Orchestrates the Personalisation agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def process(self, request: PersonalisationRequest) -> PersonalisationResponse:
        """Inject ESP personalisation syntax into email HTML (non-streaming).

        Args:
            request: The Personalisation request with HTML, platform, and requirements.

        Returns:
            PersonalisationResponse with personalised HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure — load only relevant skill files
        relevant_skills = detect_relevant_skills(request.platform, request.requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.personalisation.process_started",
            provider=provider_name,
            model=model,
            platform=request.platform,
            html_length=len(request.html),
            requirements_length=len(request.requirements),
            skills_loaded=relevant_skills,
            run_qa=request.run_qa,
        )

        # Resolve provider and call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.personalisation.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Personalisation processing failed") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.personalisation.process_completed",
            model=model_id,
            platform=request.platform,
            html_length=len(html),
            usage=result.usage,
        )

        # Optional QA checks
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []
            for check in ALL_CHECKS:
                check_result = await check.run(html)
                qa_results.append(check_result)
            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.personalisation.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return PersonalisationResponse(
            html=html,
            platform=request.platform,
            tags_injected=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: PersonalisationRequest) -> AsyncIterator[str]:
        """Stream personalisation as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The Personalisation request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"personalise-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.platform, request.requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.personalisation.stream_started",
            provider=provider_name,
            model=model,
            platform=request.platform,
            html_length=len(request.html),
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            async for chunk in provider.stream(messages, model_override=model, max_tokens=8192):  # type: ignore[attr-defined]
                sse_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

        except Exception as e:
            logger.error(
                "agents.personalisation.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Personalisation streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.personalisation.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_personalisation_service: PersonalisationService | None = None


def get_personalisation_service() -> PersonalisationService:
    """Get or create the Personalisation service singleton.

    Returns:
        Singleton PersonalisationService instance.
    """
    global _personalisation_service
    if _personalisation_service is None:
        _personalisation_service = PersonalisationService()
    return _personalisation_service
```

### Step 4: Create `personalisation_node.py`

File: `app/ai/blueprints/nodes/personalisation_node.py`

Follow exact pattern from `app/ai/blueprints/nodes/outlook_fixer_node.py`:

```python
"""Personalisation agentic node — injects ESP dynamic content into email HTML."""

from app.ai.agents.personalisation.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import ESPPlatform
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import (
    extract_confidence,
    extract_html,
    sanitize_html_xss,
    strip_confidence_comment,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PersonalisationNode:
    """Agentic node that injects ESP personalisation syntax into email HTML.

    Receives context.html (email) + platform/requirements from metadata.
    Uses progressive disclosure to load only the platform-specific skill file.
    On retry: injects personalisation-related QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "personalisation"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Inject ESP personalisation via LLM with progressive skill loading."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Read platform from metadata (default to braze if not specified)
        platform: ESPPlatform = context.metadata.get("esp_platform", "braze")  # type: ignore[assignment]
        requirements: str = str(context.metadata.get("personalisation_requirements", ""))

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(platform, requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context, platform, requirements)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.personalisation_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"LLM call failed: {exc}",
            )

        validated = validate_output(response.content)
        html = extract_html(validated)
        confidence = extract_confidence(html)
        html = strip_confidence_comment(html)
        html = sanitize_html_xss(html)

        usage = dict(response.usage) if response.usage else None

        handoff = AgentHandoff(
            agent_name="personalisation",
            artifact=html,
            decisions=(
                f"Injected {platform} personalisation into {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.personalisation_node.completed",
            iteration=context.iteration,
            platform=platform,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Personalisation ({platform}) applied to {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(
        self, context: NodeContext, platform: ESPPlatform, requirements: str
    ) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            f"Add {platform} personalisation to the following email HTML:\n\n"
            + context.html[:12000]
        ]

        if requirements:
            parts.append(f"\n\nPersonalisation requirements:\n{requirements}")

        if context.iteration > 0 and context.qa_failures:
            relevant_failures = [
                f
                for f in context.qa_failures
                if any(
                    kw in f.lower()
                    for kw in ("personalisation", "personalization", "liquid", "ampscript",
                               "variable", "fallback", "dynamic", "tag")
                )
            ]
            if relevant_failures:
                parts.append(
                    "\n\n--- PERSONALISATION QA FAILURES (fix these) ---\n"
                    + "\n".join(f"- {f}" for f in relevant_failures)
                )

        # Read upstream handoff warnings
        upstream = context.metadata.get("upstream_handoff")
        if isinstance(upstream, AgentHandoff) and upstream.warnings:
            parts.append(
                "\n\n--- UPSTREAM WARNINGS ---\n"
                + "\n".join(f"- {w}" for w in upstream.warnings)
            )

        component_ctx = context.metadata.get("component_context", "")
        if component_ctx:
            parts.append(f"\n\n{component_ctx}")

        return "\n".join(parts)
```

### Step 5: Add `PERSONALISATION_DIMENSIONS` to `dimensions.py`

File: `app/ai/agents/evals/dimensions.py`

Append after `ACCESSIBILITY_DIMENSIONS`:

```python
# ---------------------------------------------------------------------------
# Personalisation Agent Dimensions
# ---------------------------------------------------------------------------
PERSONALISATION_DIMENSIONS = {
    "esp_platform": {
        "description": "Target ESP platform for personalisation syntax",
        "values": [
            "braze",
            "sfmc",
            "adobe_campaign",
        ],
    },
    "variable_complexity": {
        "description": "Complexity of variables and data references",
        "values": [
            "basic_field",
            "custom_attribute",
            "connected_content",
            "data_extension_lookup",
            "nested_object",
            "content_block",
        ],
    },
    "conditional_complexity": {
        "description": "Complexity of conditional logic required",
        "values": [
            "simple_if_else",
            "nested_conditional",
            "loop_iteration",
            "multi_condition_chain",
            "filter_chain",
        ],
    },
    "fallback_challenge": {
        "description": "Type of fallback/edge case handling needed",
        "values": [
            "simple_default",
            "section_hiding",
            "conditional_fallback",
            "null_handling",
            "empty_array",
            "type_mismatch",
        ],
    },
}
```

### Step 6: Create `synthetic_data_personalisation.py`

File: `app/ai/agents/evals/synthetic_data_personalisation.py`

Create 12 test cases: 4 per ESP platform × varying complexity. Each test case has:
- `id`: `"pers-001"` through `"pers-012"`
- `dimensions`: dict mapping dimension names to values
- `html_input`: Real email HTML (use `_BASE_HTML` template with `{body_content}` slot)
- `requirements`: Natural language personalisation requirements
- `platform`: Target ESP
- `expected_challenges`: List of expected agent challenges

**Base HTML template** — reuse the same structural pattern as `synthetic_data_outlook_fixer.py`:

```python
_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<title>Email</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #f5f5f5; }}
  .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
</style>
</head>
<body>
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" class="container" width="100%">
{body_content}
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""
```

**12 test cases covering:**

| ID | Platform | Variable | Conditional | Fallback | Scenario |
|----|----------|----------|-------------|----------|----------|
| pers-001 | braze | basic_field | simple_if_else | simple_default | First name greeting + fallback |
| pers-002 | braze | custom_attribute | nested_conditional | section_hiding | VIP tier-based content sections |
| pers-003 | braze | connected_content | multi_condition_chain | conditional_fallback | API-fetched product recommendations |
| pers-004 | braze | content_block | filter_chain | null_handling | Content block with date filters |
| pers-005 | sfmc | basic_field | simple_if_else | simple_default | Subscriber name + default |
| pers-006 | sfmc | data_extension_lookup | nested_conditional | section_hiding | Segment-based product showcase |
| pers-007 | sfmc | nested_object | loop_iteration | empty_array | Row iteration over purchase history |
| pers-008 | sfmc | custom_attribute | multi_condition_chain | type_mismatch | Multi-tier loyalty status |
| pers-009 | adobe_campaign | basic_field | simple_if_else | simple_default | Recipient greeting + fallback |
| pers-010 | adobe_campaign | nested_object | nested_conditional | conditional_fallback | Profile-based dynamic images |
| pers-011 | adobe_campaign | custom_attribute | loop_iteration | null_handling | Collection iteration with null guard |
| pers-012 | braze | basic_field | simple_if_else | simple_default | Mixed: static + dynamic CTA with abort |

Each case body_content should be a realistic email section (greeting row, product grid, CTA row, etc.) with static placeholder text that the agent should replace with dynamic tags.

**Requirements examples:**
- `"pers-001"`: `"Add first name greeting with 'there' as fallback. Show 'Hi {{first_name}}' or 'Hi there' if missing."`
- `"pers-005"`: `"Add subscriber first name using AMPscript SET and output. Default to 'Valued Customer' if empty."`
- `"pers-009"`: `"Add recipient first name greeting using Adobe Campaign recipient fields. Default to 'Friend' if missing."`

Export as `PERSONALISATION_TEST_CASES: list[dict[str, Any]]`.

### Step 7: Create `judges/personalisation.py`

File: `app/ai/agents/evals/judges/personalisation.py`

Follow exact pattern from `judges/outlook_fixer.py`:

```python
"""Binary pass/fail judge for the Personalisation agent."""

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

PERSONALISATION_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="syntax_correctness",
        description=(
            "Is the ESP-specific syntax valid? For Braze: all {{ }} and {% %} tags are "
            "properly opened and closed, filters use | pipe syntax, connected_content uses "
            "correct :save parameter. For SFMC: %%[...]%% blocks are matched, %%=...=%% "
            "inline output is well-formed, functions use correct case (Lookup not lookup). "
            "For Adobe Campaign: <%= %> output tags and <% %> logic blocks are matched, "
            "recipient fields use correct dot notation. No mixed platform syntax."
        ),
    ),
    JudgeCriteria(
        name="fallback_completeness",
        description=(
            "Does every dynamic variable have a fallback/default value? For Braze: "
            "{{ variable | default: 'value' }} pattern. For SFMC: IIF or IF/ELSE around "
            "every variable reference. For Adobe Campaign: ternary or if-block fallback. "
            "Section-level hiding (conditional wrapping of entire content blocks) counts as "
            "valid fallback. Variables without any fallback mechanism fail this criterion."
        ),
    ),
    JudgeCriteria(
        name="html_preservation",
        description=(
            "Is the original HTML structure, content, and styling preserved? All existing "
            "elements (tables, images, links, text), inline styles, CSS, MSO conditionals, "
            "VML, dark mode support, and accessibility attributes must remain intact. Only "
            "personalisation tag insertions are acceptable changes. No removal of existing "
            "content, no structural modifications, no style alterations."
        ),
    ),
    JudgeCriteria(
        name="platform_accuracy",
        description=(
            "Is the output using the correct ESP platform's syntax exclusively? If the "
            "target platform is Braze, there must be zero AMPscript or Adobe JSSP tags. "
            "If SFMC, there must be zero Liquid or JSSP tags. If Adobe Campaign, there "
            "must be zero Liquid or AMPscript tags. Platform-specific best practices must "
            "be followed (e.g., Braze content blocks via {% content_blocks.${name} %}, "
            "SFMC data extension via Lookup(), Adobe via recipient.field notation)."
        ),
    ),
    JudgeCriteria(
        name="logic_match",
        description=(
            "Does the personalisation logic match the natural language requirements? "
            "If requirements say 'show VIP section only for premium users', the output "
            "must contain a conditional that checks user tier/status and wraps the VIP "
            "section. If requirements say 'loop through products', the output must contain "
            "an iteration construct. The logic structure must faithfully implement the "
            "stated intent — not just add surface-level variable substitution."
        ),
    ),
]


class PersonalisationJudge:
    """Binary judge for Personalisation agent outputs."""

    agent_name: str = "personalisation"
    criteria: list[JudgeCriteria] = PERSONALISATION_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML, requirements, and output HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        requirements = ""
        platform = ""
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))
            requirements = str(judge_input.input_data.get("requirements", ""))
            platform = str(judge_input.input_data.get("platform", ""))

        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        user_content = (
            f"## TARGET PLATFORM\n{platform}\n\n"
            f"## PERSONALISATION REQUIREMENTS\n{requirements}\n\n"
            f"## AGENT INPUT (Original HTML)\n```html\n{html_input}\n```\n\n"
            f"## AGENT OUTPUT (Personalised HTML)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
```

### Step 8: Register judge in `judges/__init__.py`

File: `app/ai/agents/evals/judges/__init__.py`

Add import and registry entry:

```python
from app.ai.agents.evals.judges.personalisation import PersonalisationJudge

# In JUDGE_REGISTRY dict, add:
"personalisation": PersonalisationJudge,

# In __all__ list, add:
"PersonalisationJudge",
```

Update the type annotation on `JUDGE_REGISTRY` to include `PersonalisationJudge` in the union.

### Step 9: Add mock criteria to `mock_traces.py`

File: `app/ai/agents/evals/mock_traces.py`

Add after `ACCESSIBILITY_CRITERIA`:

```python
PERSONALISATION_CRITERIA: list[dict[str, str]] = [
    {"criterion": "syntax_correctness", "description": "ESP syntax valid and well-formed"},
    {"criterion": "fallback_completeness", "description": "All variables have fallbacks"},
    {"criterion": "html_preservation", "description": "Original HTML preserved"},
    {"criterion": "platform_accuracy", "description": "Correct platform syntax only"},
    {"criterion": "logic_match", "description": "Logic matches requirements"},
]
```

Add to `AGENT_CRITERIA` dict:

```python
"personalisation": PERSONALISATION_CRITERIA,
```

### Step 10: Add runner dispatch in `runner.py`

File: `app/ai/agents/evals/runner.py`

**Import** — add at top:

```python
from app.ai.agents.evals.synthetic_data_personalisation import PERSONALISATION_TEST_CASES
```

**Add runner function** — after `run_accessibility_case`:

```python
async def run_personalisation_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single personalisation test case and return the trace."""
    from app.ai.agents.personalisation.schemas import PersonalisationRequest
    from app.ai.agents.personalisation.service import PersonalisationService

    service = PersonalisationService()
    html_input: str = str(case["html_input"])
    platform: str = str(case["platform"])
    requirements: str = str(case["requirements"])
    request = PersonalisationRequest(
        html=html_input,
        platform=platform,  # type: ignore[arg-type]
        requirements=requirements,
        stream=False,
        run_qa=True,
    )

    start = time.monotonic()
    try:
        response = await service.process(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "personalisation",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
                "platform": platform,
                "requirements": requirements,
            },
            "output": {
                "html": response.html,
                "platform": response.platform,
                "tags_injected": response.tags_injected,
                "qa_results": [r.model_dump() for r in (response.qa_results or [])],
                "qa_passed": response.qa_passed,
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
            "agent": "personalisation",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
                "platform": platform,
                "requirements": requirements,
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
```

**Add dispatch** — in `run_agent()` function, add before `else: raise ValueError`:

```python
    elif agent == "personalisation":
        cases = PERSONALISATION_TEST_CASES
        runner = run_personalisation_case
```

**Update docstring** — add `personalisation` to the usage examples at top of file.

**Update `--agent all`** — if there's a list of all agents, add `"personalisation"` to it.

### Step 11: Wire recovery router for personalisation failures

File: `app/ai/blueprints/nodes/recovery_router_node.py`

**In `_FAILURE_ROUTING` dict**, there's no direct personalisation QA check (since the 10-point QA gate doesn't have a personalisation-specific check). However, the recovery router should be able to route to personalisation when explicitly requested via handoff warnings.

**In the `execute()` method**, add detection after `has_accessibility_failure`:

```python
        # Determine if any failures are personalisation-specific
        has_personalisation_failure = any(
            any(kw in f.lower() for kw in ("personalisation", "personalization", "liquid",
                                            "ampscript", "dynamic content", "variable", "fallback"))
            for f in context.qa_failures
        )
```

**In handoff warning checks**, add:

```python
            if not has_personalisation_failure:
                has_personalisation_failure = any(
                    any(kw in w.lower() for kw in ("personalisation", "personalization",
                                                    "liquid", "ampscript", "dynamic"))
                    for w in upstream.warnings
                )
```

**In routing priority**, add before the `else` clause:

```python
        elif has_personalisation_failure:
            target = "personalisation"
```

### Step 12: Wire `PersonalisationNode` into campaign blueprint

File: `app/ai/blueprints/definitions/campaign.py`

**Add import:**

```python
from app.ai.blueprints.nodes.personalisation_node import PersonalisationNode
```

**In `build_campaign_blueprint()`:**

Instantiate:
```python
    personalisation = PersonalisationNode()
```

Add to nodes dict:
```python
    personalisation.name: personalisation,
```

Add edges:
```python
        # Recovery router routes to personalisation fixer
        Edge(
            from_node="recovery_router",
            to_node="personalisation",
            condition="route_to",
            route_value="personalisation",
        ),
        # Personalisation fix loops back to QA
        Edge(from_node="personalisation", to_node="qa_gate", condition="always"),
```

Update the docstring graph comment to include the personalisation path.

## Security Checklist

This agent does NOT add any new API endpoints (it follows the pattern of being called via the existing `/api/v1/blueprints/run` endpoint and the existing AI chat routes). Security concerns scoped to the agent itself:

- [x] No new routes — uses existing blueprint/chat infrastructure with auth + rate limiting
- [x] XSS sanitization via `sanitize_html_xss()` on all LLM output
- [x] Input sanitization via `sanitize_prompt()` on user messages
- [x] Output validation via `validate_output()` before HTML extraction
- [x] No secrets/credentials in logs (only token counts, model names, timing)
- [x] SKILL.md security rules: no `<script>`, no `on*` handlers, no `javascript:` protocol
- [x] Platform isolation: one ESP syntax per template (prevents syntax confusion attacks)
- [x] Fallback enforcement: every variable requires a default (prevents data leakage of internal field names)
- [x] Adobe Campaign JSSP `<% %>` is server-side only — sanitizer strips client-side script tags
- [x] Error handling via `AIExecutionError` (inherits `AppError` → auto-sanitized responses)

## Verification

- [x] `make lint` passes (ruff format + lint) — 0 new errors
- [x] `make types` passes (mypy + pyright) — 0 errors, 0 warnings
- [x] `make test` passes (all existing tests + new ones) — 540 passed
- [x] `make eval-dry-run` passes (exercises full pipeline including personalisation) — 12/12 cases
- [ ] `PersonalisationService().process()` returns valid HTML with ESP tags (manual test or unit test with mocked LLM)
- [x] Blueprint engine routes personalisation failures correctly (recovery_router → personalisation → qa_gate loop)
- [x] 12 synthetic test cases load without errors
- [x] Judge produces 5-criterion verdicts on mock traces
- [x] No mixed ESP syntax in any test case output
- [x] Total test count: 540 (updated judge registry + campaign structure tests)
