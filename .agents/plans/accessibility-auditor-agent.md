# Plan: Accessibility Auditor Agent

## Context

The Accessibility Auditor is the 5th agent (2nd in the eval-first + skills workflow after Outlook Fixer). Scaffolder's `accessibility_baseline` eval dimension has an **8% pass rate** — the second-worst metric after `mso_conditional_correctness` (0%). This agent will fix WCAG 2.1 AA violations in email HTML: alt text, table roles, lang attributes, heading hierarchy, color contrast, and screen reader compatibility.

**Pre-existing assets** (already built — DO NOT recreate):
- `app/ai/agents/accessibility/SKILL.md` — L1 frontmatter + L2 core instructions (120 lines)
- `app/ai/agents/accessibility/skills/wcag_email_mapping.md` — 12 WCAG criteria mapped to email
- `app/ai/agents/accessibility/skills/alt_text_guidelines.md` — Decision tree + 5 rules
- `app/ai/agents/accessibility/skills/color_contrast.md` — Thresholds, formulas, verified pairs
- `app/ai/agents/accessibility/skills/screen_reader_behavior.md` — Client matrix, VML, ARIA

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `app/ai/agents/accessibility/schemas.py` | Request/response Pydantic models |
| 2 | `app/ai/agents/accessibility/prompt.py` | System prompt + progressive disclosure |
| 3 | `app/ai/agents/accessibility/service.py` | Agent service (process + stream_process) |
| 4 | `app/ai/agents/accessibility/__init__.py` | Update docstring (no functional changes) |
| 5 | `app/ai/blueprints/nodes/accessibility_node.py` | Agentic blueprint node |
| 6 | `app/ai/agents/evals/synthetic_data_accessibility.py` | 10+ test cases |
| 7 | `app/ai/agents/evals/judges/accessibility.py` | 5-criteria binary judge |

## Files to Modify

| # | File | Change |
|---|------|--------|
| 8 | `app/ai/agents/evals/dimensions.py` | Add `ACCESSIBILITY_DIMENSIONS` |
| 9 | `app/ai/agents/evals/judges/__init__.py` | Register `AccessibilityJudge` |
| 10 | `app/ai/agents/evals/runner.py` | Add `run_accessibility_case()` + wire into CLI |
| 11 | `app/ai/agents/evals/judge_runner.py` | Add `"accessibility"` to `--agent` choices |
| 12 | `app/ai/agents/evals/mock_traces.py` | Add `ACCESSIBILITY_CRITERIA` + register in `AGENT_CRITERIA` |
| 13 | `app/ai/blueprints/nodes/recovery_router_node.py` | Route `"accessibility"` → `"accessibility"` instead of `"scaffolder"` |
| 14 | `app/ai/blueprints/definitions/campaign.py` | Wire `AccessibilityNode` into blueprint graph |

## Implementation Steps

### Step 1: Schemas (`app/ai/agents/accessibility/schemas.py`)

Follow `outlook_fixer/schemas.py` pattern exactly.

```python
"""Request/response schemas for the Accessibility Auditor agent."""

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult


class AccessibilityRequest(BaseModel):
    """Request body for the Accessibility Auditor process endpoint.

    Attributes:
        html: Email HTML to audit for accessibility issues.
        focus_areas: Optional list of specific audit areas (e.g., 'alt_text', 'contrast').
            When None, the agent audits all accessibility categories.
        stream: Whether to return SSE streaming response.
        run_qa: Whether to run the 10-point QA gate on the fixed HTML.
    """

    html: str = Field(min_length=50, max_length=200_000, description="Email HTML to audit")
    focus_areas: list[str] | None = Field(
        default=None,
        description="Specific audit areas to focus on (all areas if None)",
    )
    stream: bool = False
    run_qa: bool = False


class AccessibilityResponse(BaseModel):
    """Response from the Accessibility Auditor process endpoint.

    Attributes:
        html: The fixed email HTML with accessibility improvements.
        skills_loaded: List of L3 skill files that were loaded.
        qa_results: Individual QA check results (only when run_qa=True).
        qa_passed: Overall QA pass/fail (only when run_qa=True).
        model: The model identifier that processed the HTML.
    """

    html: str
    skills_loaded: list[str] = Field(default_factory=list)
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
```

### Step 2: Prompt (`app/ai/agents/accessibility/prompt.py`)

Progressive disclosure with 4 L3 skill files. Detection logic based on HTML content.

```python
"""System prompt for the Accessibility Auditor agent.

Thin prompt — core rules from SKILL.md. Detailed references loaded from
skills/*.md via progressive disclosure based on HTML content analysis.
"""

from pathlib import Path

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
    "wcag_email_mapping": "wcag_email_mapping.md",
    "alt_text_guidelines": "alt_text_guidelines.md",
    "color_contrast": "color_contrast.md",
    "screen_reader_behavior": "screen_reader_behavior.md",
}

ACCESSIBILITY_SYSTEM_PROMPT = f"""\
You are an expert email accessibility auditor specialising in WCAG 2.1 AA
compliance for HTML email. Your sole task is to audit and fix accessibility
issues in email HTML while preserving visual design.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [ACCESSIBILITY_SYSTEM_PROMPT]

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(html: str, focus_areas: list[str] | None = None) -> list[str]:
    """Detect which L3 skill files are relevant based on HTML content.

    Progressive disclosure — only load skill files for detected issues.

    Args:
        html: Input email HTML to analyze.
        focus_areas: Optional explicit list of audit areas.

    Returns:
        List of relevant skill keys.
    """
    html_lower = html.lower()
    skills: list[str] = []

    # Always load WCAG mapping for comprehensive reference
    skills.append("wcag_email_mapping")

    if focus_areas:
        # Explicit focus areas — load matching skills
        area_set = {a.lower() for a in focus_areas}
        if area_set & {"alt_text", "alt", "images", "img"}:
            skills.append("alt_text_guidelines")
        if area_set & {"contrast", "color", "colors", "colour"}:
            skills.append("color_contrast")
        if area_set & {"screen_reader", "aria", "sr", "voiceover", "nvda", "jaws"}:
            skills.append("screen_reader_behavior")
    else:
        # Auto-detect from HTML content
        if "<img" in html_lower:
            skills.append("alt_text_guidelines")

        # Load contrast guide if inline color styles detected
        if "color:" in html_lower or "background-color:" in html_lower:
            skills.append("color_contrast")

        # Load screen reader guide if tables, VML, or ARIA present
        if (
            "<table" in html_lower
            or "<v:" in html_lower
            or "aria-" in html_lower
            or "role=" in html_lower
        ):
            skills.append("screen_reader_behavior")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
```

### Step 3: Service (`app/ai/agents/accessibility/service.py`)

Follow `outlook_fixer/service.py` exactly. Same pipeline: detect skills → build prompt → LLM → validate → extract → sanitize → optional QA.

```python
# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Accessibility Auditor agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.accessibility.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.accessibility.schemas import (
    AccessibilityRequest,
    AccessibilityResponse,
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


def _build_user_message(request: AccessibilityRequest) -> str:
    """Build the user message from the request fields."""
    parts: list[str] = [
        "Audit and fix the following email HTML for WCAG 2.1 AA accessibility:\n",
        request.html,
    ]

    if request.focus_areas:
        areas_str = ", ".join(request.focus_areas)
        parts.append(f"\n\nFocus on these areas: {areas_str}")

    return "\n".join(parts)


class AccessibilityService:
    """Orchestrates the Accessibility Auditor agent pipeline.

    Pipeline: detect skills → build prompt → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def process(self, request: AccessibilityRequest) -> AccessibilityResponse:
        """Audit and fix accessibility issues in email HTML (non-streaming).

        Args:
            request: The accessibility audit request with HTML and options.

        Returns:
            AccessibilityResponse with fixed HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure — load only relevant skill files
        relevant_skills = detect_relevant_skills(request.html, request.focus_areas)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.accessibility.process_started",
            provider=provider_name,
            model=model,
            html_length=len(request.html),
            skills_loaded=relevant_skills,
            has_focus_areas=request.focus_areas is not None,
            run_qa=request.run_qa,
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.accessibility.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Accessibility audit processing failed") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.accessibility.process_completed",
            model=model_id,
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
                "agents.accessibility.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return AccessibilityResponse(
            html=html,
            skills_loaded=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: AccessibilityRequest) -> AsyncIterator[str]:
        """Stream accessibility fix as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The accessibility audit request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"a11y-fix-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.html, request.focus_areas)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.accessibility.stream_started",
            provider=provider_name,
            model=model,
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
                "agents.accessibility.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Accessibility audit streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.accessibility.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_accessibility_service: AccessibilityService | None = None


def get_accessibility_service() -> AccessibilityService:
    """Get or create the Accessibility service singleton.

    Returns:
        Singleton AccessibilityService instance.
    """
    global _accessibility_service
    if _accessibility_service is None:
        _accessibility_service = AccessibilityService()
    return _accessibility_service
```

### Step 4: Update `__init__.py`

```python
"""Accessibility Auditor agent — WCAG 2.1 AA compliance for email HTML."""
```

No functional changes — the docstring is already correct.

### Step 5: Blueprint Node (`app/ai/blueprints/nodes/accessibility_node.py`)

Follow `outlook_fixer_node.py` exactly. Filter QA failures to accessibility-specific ones on retry.

```python
"""Accessibility Auditor agentic node — fixes WCAG AA issues in email HTML."""

from app.ai.agents.accessibility.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
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


class AccessibilityNode:
    """Agentic node that audits and fixes accessibility issues in email HTML.

    Receives context.html from recovery router (when QA detects accessibility failures).
    Uses progressive disclosure to load only relevant skill files.
    On retry: injects accessibility-specific QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "accessibility"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Fix accessibility issues in HTML via LLM with progressive skill loading."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(context.html)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.accessibility_node.llm_failed", error=str(exc))
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
            agent_name="accessibility",
            artifact=html,
            decisions=(
                f"Fixed accessibility issues in {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.accessibility_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Accessibility fixes applied to {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            "Audit and fix the following email HTML for WCAG 2.1 AA accessibility:\n\n"
            + context.html[:12000]
        ]

        if context.iteration > 0 and context.qa_failures:
            a11y_failures = [
                f
                for f in context.qa_failures
                if any(
                    kw in f.lower()
                    for kw in ("accessibility", "alt", "lang", "role", "contrast", "heading", "wcag")
                )
            ]
            if a11y_failures:
                parts.append(
                    "\n\n--- ACCESSIBILITY QA FAILURES (fix these) ---\n"
                    + "\n".join(f"- {f}" for f in a11y_failures)
                )

        progress = context.metadata.get("progress_anchor", "")
        if progress:
            parts.append(f"\n\n{progress}")

        # Read upstream handoff warnings
        upstream = context.metadata.get("upstream_handoff")
        if isinstance(upstream, AgentHandoff) and upstream.warnings:
            parts.append(
                "\n\n--- UPSTREAM WARNINGS ---\n" + "\n".join(f"- {w}" for w in upstream.warnings)
            )

        component_ctx = context.metadata.get("component_context", "")
        if component_ctx:
            parts.append(f"\n\n{component_ctx}")

        return "\n".join(parts)
```

### Step 6: Eval Dimensions (`app/ai/agents/evals/dimensions.py`)

Append at the end of the file:

```python
# ---------------------------------------------------------------------------
# Accessibility Auditor Agent Dimensions
# ---------------------------------------------------------------------------
ACCESSIBILITY_DIMENSIONS = {
    "violation_category": {
        "description": "Category of WCAG violation present in the input HTML",
        "values": [
            "missing_alt_text",
            "decorative_img_no_empty_alt",
            "missing_lang_attribute",
            "layout_table_no_role",
            "low_contrast_text",
            "skipped_heading_levels",
            "non_descriptive_links",
            "missing_table_role",
            "color_only_information",
            "missing_document_title",
        ],
    },
    "html_complexity": {
        "description": "Structural complexity of the email HTML being audited",
        "values": [
            "simple_single_column",
            "multi_column_tables",
            "nested_layout_tables",
            "mso_conditional_heavy",
            "vml_elements_present",
            "mixed_layout_and_data_tables",
        ],
    },
    "image_scenario": {
        "description": "Type of image accessibility challenge",
        "values": [
            "informative_no_alt",
            "decorative_missing_empty_alt",
            "functional_link_image",
            "complex_infographic",
            "logo_with_text",
            "no_images",
        ],
    },
    "severity": {
        "description": "Mix of violation severity levels in the input",
        "values": [
            "single_critical",
            "multiple_moderate",
            "mixed_severity",
            "many_minor",
        ],
    },
}
```

### Step 7: Synthetic Test Data (`app/ai/agents/evals/synthetic_data_accessibility.py`)

Create 10 test cases covering all dimension axes. Each case has realistic email HTML with specific accessibility violations for the agent to fix.

Use the same `_BASE_HTML` pattern as `synthetic_data_outlook_fixer.py`:
- Define `_BASE_HTML` with `{body_content}` placeholder
- Create 10+ fixture strings with specific violations
- Each test case: `id` (a11y-001 to a11y-010), `dimensions` dict, `html_input`, `expected_challenges` list

**Test case coverage:**
1. `a11y-001` — Missing alt text on multiple images (informative + decorative)
2. `a11y-002` — Layout tables without `role="presentation"`
3. `a11y-003` — Missing `lang` attribute on `<html>` + no `<title>`
4. `a11y-004` — Low contrast text (#999 on #fff = ~2.8:1, below 4.5:1)
5. `a11y-005` — Skipped heading levels (h1 → h3 → h5)
6. `a11y-006` — Non-descriptive links ("click here", "read more")
7. `a11y-007` — Complex multi-column with MSO conditionals, all issues combined
8. `a11y-008` — Functional images (linked images with no alt)
9. `a11y-009` — VML elements present, tables mixed layout+data, ARIA missing
10. `a11y-010` — Color-only information (red/green status indicators)

### Step 8: Judge (`app/ai/agents/evals/judges/accessibility.py`)

Follow `judges/outlook_fixer.py` pattern. 5 criteria matching SKILL.md `eval_criteria`.

```python
"""Binary pass/fail judge for the Accessibility Auditor agent."""

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

ACCESSIBILITY_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="wcag_aa_compliance",
        description=(
            "Does the output HTML meet WCAG 2.1 AA standards for email? "
            "Check: <html> has lang attribute; all layout tables have role='presentation'; "
            "<title> element present in <head>; role='article' on outer wrapper; "
            "<meta charset='utf-8'> present. Missing any of these is a failure."
        ),
    ),
    JudgeCriteria(
        name="alt_text_quality",
        description=(
            "Do all images have appropriate alt text? Informative images must have "
            "descriptive alt text (max ~125 chars, no 'image of' prefix). Decorative "
            "images must have alt='' (empty string, not missing). Functional images "
            "(inside links) must describe the action/destination. Missing alt attributes "
            "or generic alt text like 'image' or 'photo' is a failure."
        ),
    ),
    JudgeCriteria(
        name="contrast_ratio_accuracy",
        description=(
            "Are color contrast issues identified and fixed? Normal text requires "
            "minimum 4.5:1 contrast ratio against its background. Large text (>=18px or "
            ">=14px bold) requires minimum 3:1. If the input has low-contrast text, the "
            "output must either fix the colors or flag them. Introducing new low-contrast "
            "text is a failure."
        ),
    ),
    JudgeCriteria(
        name="semantic_structure",
        description=(
            "Is the heading hierarchy sequential with no skipped levels? There should "
            "be at most one <h1>, and headings must proceed h1→h2→h3 without gaps. "
            "Link text must be descriptive (never 'click here', 'read more', 'here' "
            "alone). Layout tables must not use <th>, <caption>, or <thead> (those are "
            "for data tables only)."
        ),
    ),
    JudgeCriteria(
        name="screen_reader_compatibility",
        description=(
            "Is the output compatible with major screen readers in email clients? "
            "Layout tables must have role='presentation' (prevents column/row announcement). "
            "VML elements must be inside MSO conditionals (screen readers should skip them). "
            "Reading order must follow DOM order. ARIA attributes must be valid and not "
            "conflict with native semantics. Original content must be preserved — the "
            "agent must not remove or alter text, links, or images."
        ),
    ),
]


class AccessibilityJudge:
    """Binary judge for Accessibility Auditor agent outputs."""

    agent_name: str = "accessibility"
    criteria: list[JudgeCriteria] = ACCESSIBILITY_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML and fixed output HTML."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))

        html_output = ""
        if judge_input.output_data:
            html_output = str(judge_input.output_data.get("html", ""))

        user_content = (
            f"## AGENT INPUT (Email HTML with accessibility issues)\n```html\n{html_input}\n```\n\n"
            f"## AGENT OUTPUT (Fixed HTML with accessibility improvements)\n```html\n{html_output}\n```"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
```

### Step 9: Register Judge (`app/ai/agents/evals/judges/__init__.py`)

Add `AccessibilityJudge` import and register in `JUDGE_REGISTRY`:

```python
from app.ai.agents.evals.judges.accessibility import AccessibilityJudge

JUDGE_REGISTRY: dict[
    str, type[ScaffolderJudge | DarkModeJudge | ContentJudge | OutlookFixerJudge | AccessibilityJudge]
] = {
    "scaffolder": ScaffolderJudge,
    "dark_mode": DarkModeJudge,
    "content": ContentJudge,
    "outlook_fixer": OutlookFixerJudge,
    "accessibility": AccessibilityJudge,
}

# Add to __all__
```

### Step 10: Wire into Eval Runner (`app/ai/agents/evals/runner.py`)

Add import:
```python
from app.ai.agents.evals.synthetic_data_accessibility import ACCESSIBILITY_TEST_CASES
```

Add `run_accessibility_case()` function (follow `run_outlook_fixer_case` pattern):
```python
async def run_accessibility_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single accessibility test case and return the trace."""
    from app.ai.agents.accessibility.schemas import AccessibilityRequest
    from app.ai.agents.accessibility.service import AccessibilityService

    service = AccessibilityService()
    html_input: str = str(case["html_input"])
    request = AccessibilityRequest(
        html=html_input,
        focus_areas=None,
        stream=False,
        run_qa=True,
    )

    start = time.monotonic()
    try:
        response = await service.process(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "accessibility",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
            },
            "output": {
                "html": response.html,
                "skills_loaded": response.skills_loaded,
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
            "agent": "accessibility",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
```

Add to `run_agent()` dispatch:
```python
elif agent == "accessibility":
    cases = ACCESSIBILITY_TEST_CASES
    runner = run_accessibility_case
```

Update `--agent` choices: add `"accessibility"`.
Update `"all"` list: add `"accessibility"`.

### Step 11: Wire into Judge Runner (`app/ai/agents/evals/judge_runner.py`)

Add `AccessibilityJudge` to imports and type union on line 56:
```python
from app.ai.agents.evals.judges.accessibility import AccessibilityJudge
```

Update `judge_trace()` type hint to include `AccessibilityJudge`.

Update `--agent` choices on line 230: add `"accessibility"`.
Update `"all"` list on line 254: add `"accessibility"`.

### Step 12: Update Mock Traces (`app/ai/agents/evals/mock_traces.py`)

Add:
```python
ACCESSIBILITY_CRITERIA: list[dict[str, str]] = [
    {"criterion": "wcag_aa_compliance", "description": "WCAG 2.1 AA structure met"},
    {"criterion": "alt_text_quality", "description": "Image alt text appropriate"},
    {"criterion": "contrast_ratio_accuracy", "description": "Contrast ratios sufficient"},
    {"criterion": "semantic_structure", "description": "Heading hierarchy and link text correct"},
    {"criterion": "screen_reader_compatibility", "description": "Screen reader compatible"},
]
```

Add to `AGENT_CRITERIA`:
```python
"accessibility": ACCESSIBILITY_CRITERIA,
```

### Step 13: Update Recovery Router (`app/ai/blueprints/nodes/recovery_router_node.py`)

Change line 13:
```python
# Before:
"accessibility": "scaffolder",

# After:
"accessibility": "accessibility",
```

Also add accessibility keyword detection in the `execute()` method, after the `has_outlook_failure` block (around line 58):

```python
has_accessibility_failure = any(
    f.startswith("accessibility:") for f in context.qa_failures
)

# Also check upstream handoff warnings
if isinstance(upstream, AgentHandoff) and upstream.warnings:
    if not has_accessibility_failure:
        has_accessibility_failure = any(
            kw in w.lower()
            for w in upstream.warnings
            for kw in ("accessibility", "wcag", "alt text", "contrast")
        )
```

Update the routing logic:
```python
if has_dark_mode_failure:
    target = "dark_mode"
elif has_outlook_failure:
    target = "outlook_fixer"
elif has_accessibility_failure:
    target = "accessibility"
else:
    target = "scaffolder"
```

### Step 14: Wire into Blueprint (`app/ai/blueprints/definitions/campaign.py`)

Add import:
```python
from app.ai.blueprints.nodes.accessibility_node import AccessibilityNode
```

Add node creation:
```python
accessibility = AccessibilityNode()
```

Add to `nodes` dict:
```python
accessibility.name: accessibility,
```

Add edge from recovery router:
```python
Edge(
    from_node="recovery_router",
    to_node="accessibility",
    condition="route_to",
    route_value="accessibility",
),
```

Add loop-back edge:
```python
Edge(from_node="accessibility", to_node="qa_gate", condition="always"),
```

Update the module docstring to include the accessibility route.

## Security Checklist

This agent has NO new HTTP endpoints — it's invoked via the existing blueprint endpoint (`POST /api/v1/blueprints/run`) and the existing eval CLI tools. Security is inherited from existing infrastructure:

- [x] Auth: Blueprint endpoint already requires `get_current_user` + admin/developer RBAC
- [x] Rate limiting: Blueprint endpoint already rate-limited (3/min)
- [x] Input validation: `AccessibilityRequest` uses Pydantic `Field(min_length=50, max_length=200_000)`
- [x] Output sanitization: `sanitize_html_xss()` on every agent output
- [x] Input sanitization: `sanitize_prompt()` on every user message
- [x] Error handling: `AIExecutionError` hierarchy (auto-sanitized via `get_safe_error_message`)
- [x] No secrets in logs: Only token counts, model names, and timing logged
- [x] Blueprint node: Errors produce `NodeResult(status="failed")`, never crash engine

## Verification

- [x] `make check` passes (lint + types + tests + security-check) — 540 tests, mypy clean, ruff clean
- [x] `make eval-dry-run` passes with `--agent accessibility` — 10/10 traces
- [x] `make eval-run --agent accessibility --dry-run` generates mock traces — 10/10
- [x] Judge dry-run produces verdicts for all 10 test cases — 5 criteria per case
- [x] Blueprint dry-run routes accessibility QA failures to AccessibilityNode
- [x] Recovery router correctly routes `accessibility:` prefixed failures

## Post-Implementation

After agent is implemented and verified:
1. Run live evals: `make eval-run --agent accessibility`
2. Run judge: `make eval-analysis` on accessibility traces
3. Iterate SKILL.md based on failure clusters
4. Update `app/ai/agents/CLAUDE.md` — move Accessibility to "Implemented" section
5. Update `CLAUDE.md` agent table — mark Accessibility as Done
6. Update `TODO.md` task 4.1 — check off Accessibility Auditor
