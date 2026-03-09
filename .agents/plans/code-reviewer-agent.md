# Plan: Code Reviewer Agent

## Context

The Code Reviewer agent is the 7th of 9 AI agents (task 4.1). It performs static analysis on email HTML: flags redundant code, unsupported CSS per email client, invalid nesting, and file size optimisation opportunities. Unlike other agents that *modify* HTML, the Code Reviewer *analyses and reports* — its output is the original HTML with issues annotated as HTML comments plus a structured JSON review summary.

Follows the established **eval-first + skills workflow**: SKILL.md (L1+L2) + L3 skill files, progressive disclosure, blueprint node, recovery router, eval infrastructure.

## Key Design Decision: Analysis Agent (Not Transform Agent)

Other agents (Scaffolder, Dark Mode, Personalisation) transform HTML → HTML. Code Reviewer is different:
- **Input:** Email HTML + optional focus areas
- **Output:** Original HTML preserved + `<!-- REVIEW: ... -->` inline comments at issue locations + a JSON review summary block in a `<!-- REVIEW_SUMMARY: {...} -->` comment
- **Service response** includes structured `issues: list[CodeReviewIssue]` extracted from the summary
- The agent does NOT rewrite HTML — it annotates issues for the developer to review

This affects schemas (response has `issues` not transformed `html`), the blueprint node (passes HTML through, attaches review as handoff warnings), and judge criteria (evaluates issue quality not HTML transformation).

## Files to Create

### Core Agent (4 files)
1. `app/ai/agents/code_reviewer/__init__.py` — empty
2. `app/ai/agents/code_reviewer/schemas.py` — request/response schemas
3. `app/ai/agents/code_reviewer/prompt.py` — system prompt + progressive disclosure
4. `app/ai/agents/code_reviewer/service.py` — orchestration service

### SKILL.md + L3 Skills (5 files)
5. `app/ai/agents/code_reviewer/SKILL.md` — L1+L2 core instructions
6. `app/ai/agents/code_reviewer/skills/redundant_code.md` — L3: redundant/dead code patterns
7. `app/ai/agents/code_reviewer/skills/css_client_support.md` — L3: CSS property support matrix
8. `app/ai/agents/code_reviewer/skills/nesting_validation.md` — L3: HTML nesting rules for email
9. `app/ai/agents/code_reviewer/skills/file_size_optimization.md` — L3: Gmail 102KB clipping + size reduction

### Blueprint Integration (1 file)
10. `app/ai/blueprints/nodes/code_reviewer_node.py` — agentic blueprint node

### Eval Infrastructure (2 files)
11. `app/ai/agents/evals/synthetic_data_code_reviewer.py` — 12 test cases
12. `app/ai/agents/evals/judges/code_reviewer.py` — 5-criteria binary judge

## Files to Modify

### Eval Registration (5 files)
13. `app/ai/agents/evals/dimensions.py` — add `CODE_REVIEWER_DIMENSIONS`
14. `app/ai/agents/evals/judges/__init__.py` — register `CodeReviewerJudge`
15. `app/ai/agents/evals/runner.py` — add `run_code_reviewer_case()` + CLI option
16. `app/ai/agents/evals/judge_runner.py` — add `CodeReviewerJudge` to type union
17. `app/ai/agents/evals/mock_traces.py` — add `CODE_REVIEWER_CRITERIA` + register in `AGENT_CRITERIA`

### Blueprint Wiring (2 files)
18. `app/ai/blueprints/definitions/campaign.py` — add `CodeReviewerNode` to graph
19. `app/ai/blueprints/nodes/recovery_router_node.py` — add code review routing

### Tests (2 files)
20. `app/ai/agents/tests/test_judges.py` — add `TestCodeReviewerJudge` class + update registry count
21. `app/ai/agents/evals/tests/test_dry_run_pipeline.py` — verify code_reviewer in AGENT_CRITERIA

---

## Implementation Steps

### Step 1: Create `app/ai/agents/code_reviewer/__init__.py`

Empty file.

```python
```

### Step 2: Create `app/ai/agents/code_reviewer/schemas.py`

```python
"""Request/response schemas for the Code Reviewer agent."""

from typing import Literal

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult

ReviewFocus = Literal[
    "redundant_code",
    "css_support",
    "nesting",
    "file_size",
    "all",
]

IssueSeverity = Literal["critical", "warning", "info"]


class CodeReviewIssue(BaseModel):
    """A single code review finding."""

    rule: str = Field(description="Rule identifier (e.g., 'redundant-mso-comment', 'unsupported-css-grid')")
    severity: IssueSeverity
    line_hint: int | None = Field(default=None, description="Approximate line number (best effort)")
    message: str = Field(description="Human-readable description of the issue")
    suggestion: str | None = Field(default=None, description="Actionable fix suggestion")


class CodeReviewRequest(BaseModel):
    """Request body for the Code Reviewer process endpoint."""

    html: str = Field(min_length=50, max_length=200_000, description="Email HTML to review")
    focus: ReviewFocus = Field(default="all", description="Area to focus the review on")
    stream: bool = False
    run_qa: bool = False


class CodeReviewResponse(BaseModel):
    """Response from the Code Reviewer process endpoint."""

    html: str = Field(description="Original HTML (unmodified)")
    issues: list[CodeReviewIssue] = Field(default_factory=list)
    summary: str = Field(description="Brief natural-language review summary")
    skills_loaded: list[str] = Field(default_factory=list)
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
```

### Step 3: Create `app/ai/agents/code_reviewer/SKILL.md`

```markdown
---
name: code_reviewer
version: "1.0"
description: >
  Static analysis of email HTML: redundant code, unsupported CSS properties
  per email client, invalid HTML nesting, and file size optimisation. Reports
  issues with severity, location, and actionable suggestions. Does not modify
  the source HTML — annotation only.
input: Email HTML with optional focus area
output: JSON array of issues with rule, severity, line_hint, message, suggestion
eval_criteria:
  - issue_genuineness
  - suggestion_actionability
  - severity_accuracy
  - coverage_completeness
  - no_false_positives
confidence_rules:
  high: "0.9+ — Clear-cut violations (missing DOCTYPE, display:flex, >102KB)"
  medium: "0.5-0.7 — Context-dependent issues (redundancy judgement, nesting edge cases)"
  low: "Below 0.5 — Ambiguous patterns, client-specific quirks with limited data"
references:
  - skills/redundant_code.md
  - skills/css_client_support.md
  - skills/nesting_validation.md
  - skills/file_size_optimization.md
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: ".claude/hooks/block-dangerous.sh"
          statusMessage: "Checking command safety..."
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            The Code Reviewer agent just completed. Evaluate its output:

            $ARGUMENTS

            Verify:
            1. Output is valid JSON array of issues (or empty array for clean code)
            2. Each issue has rule, severity (critical/warning/info), message
            3. No false positives for standard email patterns (tables, inline styles, MSO)
            4. Severity assignments match impact (critical = breaks rendering, warning = poor practice, info = optimisation)
            5. A <!-- CONFIDENCE: X.XX --> comment is present
            6. Original HTML was NOT modified — analysis only

            Return {"ok": true} if all checks pass.
            Return {"ok": false, "reason": "..."} describing which check(s) failed.
          statusMessage: "Validating code review output..."
---

# Code Reviewer Agent — Core Instructions

## Input/Output Contract

You receive email HTML and produce a structured review. You NEVER modify the HTML.

**Input:** Email HTML + optional focus area (redundant_code, css_support, nesting, file_size, all)
**Output:** A JSON block containing an array of issues, wrapped in a code fence:

```json
{
  "issues": [
    {
      "rule": "rule-id",
      "severity": "critical|warning|info",
      "line_hint": 42,
      "message": "Description of the problem",
      "suggestion": "How to fix it"
    }
  ],
  "summary": "Brief overview of findings"
}
```

## Review Categories

1. **Redundant Code** — Duplicate styles, unused CSS classes, dead MSO conditionals, repeated table attributes
2. **CSS Client Support** — Properties unsupported in major email clients (Outlook, Gmail, Yahoo, Apple Mail)
3. **Nesting Validation** — Invalid HTML nesting for email (div inside span, incorrect table structure, unclosed tags)
4. **File Size** — Gmail 102KB clipping risk, bloated inline styles, unnecessary whitespace, oversized images without dimensions

## Severity Classification

- **critical** — Breaks rendering in major clients (Outlook, Gmail). Must fix before send.
- **warning** — Poor practice that degrades experience for some users. Should fix.
- **info** — Optimisation opportunity. Nice to fix but not blocking.

## Core Rules

1. **Never modify HTML** — You are an analyst, not an editor
2. **No false positives for email patterns** — Tables for layout, inline styles, MSO conditionals, VML are EXPECTED in email HTML. Do not flag them.
3. **Be specific** — Include the exact CSS property, HTML element, or pattern that's problematic
4. **Be actionable** — Every issue must have a concrete suggestion, not generic advice
5. **Severity must match impact** — Don't over-classify optimisations as critical

## Email-Specific Allowlist (DO NOT FLAG)

These are standard email patterns, NOT issues:
- `<table>` for layout with `role="presentation"`
- Inline styles on every element
- `<!--[if mso]>...<![endif]-->` conditional comments
- VML elements (`<v:rect>`, `<v:roundrect>`, etc.)
- `xmlns:v="urn:schemas-microsoft-com:vml"` namespace
- `@media (prefers-color-scheme: dark)` media queries
- `[data-ogsc]` / `[data-ogsb]` Outlook selectors
- `mso-` prefixed CSS properties
- `width` and `height` HTML attributes on images and tables
- `cellpadding`, `cellspacing`, `border` table attributes

## Confidence Assessment

`<!-- CONFIDENCE: 0.XX -->`

## Security Rules (ABSOLUTE)

- NEVER include `<script>` tags or inline JavaScript
- NEVER use `on*` event handlers
- NEVER use `javascript:` protocol
- Report findings only — never inject executable code
```

### Step 4: Create L3 Skill Files

#### `app/ai/agents/code_reviewer/skills/redundant_code.md`

```markdown
# Redundant Code Detection — L3 Reference

## Patterns to Detect

### Duplicate Inline Styles
- Same `style` attribute value repeated on adjacent/sibling elements
- Identical `background-color` + `color` pairs that could use a CSS class
- Rule: `redundant-duplicate-style`

### Unused CSS Classes
- Classes defined in `<style>` block but never referenced in HTML body
- Rule: `redundant-unused-class`

### Dead MSO Conditionals
- `<!--[if mso]>` blocks with empty content or only whitespace
- Nested MSO conditionals that target the same version (e.g., nested `[if gte mso 9]`)
- Rule: `redundant-dead-mso`

### Repeated Table Attributes
- `cellpadding="0" cellspacing="0" border="0"` on every nested table — only needed on outermost
- `role="presentation"` repeated on layout tables already inside a presentation table (though not wrong, it's redundant at inner levels if outer already has it — classify as `info`)
- Rule: `redundant-table-attrs`

### Empty Elements
- `<td>&nbsp;</td>` spacers that could use `height` on `<td>` (info only)
- Empty `<style>` blocks
- Rule: `redundant-empty-element`

## False Positive Prevention
- Multiple inline styles are NORMAL in email — only flag when truly identical on siblings
- MSO conditionals with different version targeting are NOT redundant
- Tables with `cellpadding="0"` at every level is defensive and often intentional — severity: info
```

#### `app/ai/agents/code_reviewer/skills/css_client_support.md`

```markdown
# CSS Client Support — L3 Reference

## Critical (Breaks Rendering)

| CSS Property | Unsupported In | Rule ID |
|---|---|---|
| `display: flex` | Outlook (all), Gmail (partial) | `css-unsupported-flex` |
| `display: grid` | Outlook (all), Gmail, Yahoo | `css-unsupported-grid` |
| `position: fixed` | All email clients | `css-unsupported-position-fixed` |
| `position: sticky` | All email clients | `css-unsupported-position-sticky` |
| `position: absolute` | Outlook, many webmail | `css-unsupported-position-absolute` |
| `float` | Outlook (all versions) | `css-unsupported-float` |
| `calc()` | Outlook, Gmail (partial) | `css-unsupported-calc` |
| `var()` / CSS custom properties | Outlook, Gmail | `css-unsupported-custom-props` |

## Warning (Degraded Experience)

| CSS Property | Unsupported In | Rule ID |
|---|---|---|
| `border-radius` | Outlook (Windows) | `css-partial-border-radius` |
| `box-shadow` | Outlook (Windows) | `css-partial-box-shadow` |
| `background-image` (CSS) | Outlook (use VML) | `css-partial-bg-image` |
| `max-width` without MSO fallback | Outlook | `css-needs-mso-fallback` |
| `gap` | Most email clients | `css-unsupported-gap` |
| `object-fit` | Outlook | `css-partial-object-fit` |
| `clip-path` | Most email clients | `css-unsupported-clip-path` |

## Info (Minor Compatibility)

| CSS Property | Note | Rule ID |
|---|---|---|
| `margin: auto` for centering | Outlook needs `align="center"` | `css-info-margin-auto` |
| `line-height` as unitless | Some clients need px value | `css-info-unitless-line-height` |

## Detection Notes
- Only flag CSS in `style` attributes and `<style>` blocks — ignore CSS in MSO conditionals
- `mso-` prefixed properties are Outlook-specific and VALID — never flag
- Check both shorthand and longhand (e.g., `display:flex` and `display: flex`)
```

#### `app/ai/agents/code_reviewer/skills/nesting_validation.md`

```markdown
# HTML Nesting Validation — L3 Reference

## Critical Nesting Violations (Email Context)

### Table Structure
- `<tr>` directly inside `<table>` without `<tbody>` — OK in email (not a violation)
- `<td>` outside `<tr>` — always invalid. Rule: `nesting-td-outside-tr`
- `<tr>` outside `<table>` — always invalid. Rule: `nesting-tr-outside-table`
- Nested `<table>` directly inside `<tr>` (must be inside `<td>`). Rule: `nesting-table-in-tr`

### Block-in-Inline
- `<div>` inside `<span>` — invalid. Rule: `nesting-block-in-inline`
- `<table>` inside `<a>` — invalid in most clients. Rule: `nesting-table-in-link`
- `<p>` inside `<p>` — auto-closed by parser, causes unexpected layout. Rule: `nesting-p-in-p`

### Unclosed Tags
- Unclosed `<td>`, `<tr>`, `<table>` — critical rendering issue. Rule: `nesting-unclosed-tag`
- Note: self-closing tags like `<br/>`, `<img/>`, `<hr/>` are valid

### Excessive Depth
- Table nesting depth > 6 levels — Outlook rendering degrades. Rule: `nesting-excessive-depth`
- More than 15 nested `<table>` elements total — Gmail performance. Rule: `nesting-too-many-tables`

## False Positive Prevention
- `<div>` inside `<td>` is VALID and common
- `<a>` wrapping inline content is VALID
- Multiple `<table>` elements (not deeply nested) is NORMAL for email layout
- MSO conditional comments may contain apparent nesting violations — skip content inside `<!--[if mso]>...<![endif]-->`
```

#### `app/ai/agents/code_reviewer/skills/file_size_optimization.md`

```markdown
# File Size Optimisation — L3 Reference

## Gmail Clipping Threshold
Gmail clips emails at **102KB** (102,400 bytes). After clipping, a "View entire message" link appears and tracking pixels may not load.

### Size Calculation
- Measure the **rendered HTML** size in bytes (UTF-8 encoded)
- Include inline styles, embedded CSS, MSO conditionals
- Exclude external resources (images loaded via `src`)

### Rule: `filesize-gmail-clip-risk`
- **critical** if HTML > 102KB
- **warning** if HTML > 80KB (approaching limit)
- **info** if HTML > 60KB (monitor)

## Common Bloat Sources

### Inline Style Repetition
- Same `font-family: Arial, Helvetica, sans-serif` on 50+ elements
- Same `color: #333333; font-size: 14px; line-height: 1.5` block repeated
- Rule: `filesize-style-bloat` (severity: warning)
- Suggestion: Use embedded CSS class where client support allows, or extract to `<style>` block with `!important`

### Unnecessary Whitespace
- Excessive indentation (4+ levels of nested indentation in production)
- Multiple blank lines between elements
- Rule: `filesize-whitespace` (severity: info)
- Suggestion: Minify for production builds (Maizzle handles this via `purgeCSS` + `minify`)

### Oversized MSO Blocks
- VML backgrounds/buttons can add 2-5KB each
- Multiple VML elements for same visual effect
- Rule: `filesize-heavy-mso` (severity: info)

### Embedded Images (Base64)
- Base64-encoded images in `src="data:image/..."` dramatically increase size
- A 50KB image becomes ~67KB when base64-encoded
- Rule: `filesize-base64-image` (severity: critical)
- Suggestion: Host images externally and reference via URL

## Size Reporting
Always include current file size in the review summary:
- `"HTML size: 45,230 bytes (44% of Gmail clip limit)"`
```

### Step 5: Create `app/ai/agents/code_reviewer/prompt.py`

```python
"""System prompt for the Code Reviewer agent.

Thin prompt -- core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.code_reviewer.schemas import ReviewFocus

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


# L3 reference files -- loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "redundant_code": "redundant_code.md",
    "css_client_support": "css_client_support.md",
    "nesting_validation": "nesting_validation.md",
    "file_size_optimization": "file_size_optimization.md",
}

CODE_REVIEWER_SYSTEM_PROMPT = f"""\
You are an expert email HTML code reviewer. Your sole task is to
analyse email HTML and report issues — you NEVER modify the source HTML.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [CODE_REVIEWER_SYSTEM_PROMPT]

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(focus: ReviewFocus) -> list[str]:
    """Detect which L3 skill files are relevant based on review focus.

    Args:
        focus: Review focus area.

    Returns:
        List of relevant skill keys.
    """
    if focus == "all":
        return list(SKILL_FILES.keys())

    focus_map: dict[ReviewFocus, list[str]] = {
        "redundant_code": ["redundant_code"],
        "css_support": ["css_client_support"],
        "nesting": ["nesting_validation"],
        "file_size": ["file_size_optimization"],
    }
    return focus_map.get(focus, list(SKILL_FILES.keys()))
```

### Step 6: Create `app/ai/agents/code_reviewer/service.py`

```python
# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Code Reviewer agent service -- orchestrates LLM -> parse issues -> optional QA."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.code_reviewer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.code_reviewer.schemas import (
    CodeReviewIssue,
    CodeReviewRequest,
    CodeReviewResponse,
)
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


def _build_user_message(request: CodeReviewRequest) -> str:
    """Build the user message from the request fields."""
    focus_label = "all areas" if request.focus == "all" else request.focus
    return (
        f"Review the following email HTML. Focus on: {focus_label}.\n\n"
        f"Email HTML:\n{request.html}"
    )


def _extract_issues(raw_content: str) -> tuple[list[CodeReviewIssue], str]:
    """Extract structured issues from LLM response.

    Looks for a JSON block with 'issues' array and 'summary' field.

    Returns:
        Tuple of (issues list, summary string).
    """
    # Try to find JSON in code fence
    content = raw_content
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

    # Strip confidence comment if present
    content = strip_confidence_comment(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: return raw content as summary with no structured issues
        return [], raw_content.strip()

    issues: list[CodeReviewIssue] = []
    raw_issues = data.get("issues", [])
    for item in raw_issues:
        if isinstance(item, dict):
            issues.append(
                CodeReviewIssue(
                    rule=str(item.get("rule", "unknown")),
                    severity=item.get("severity", "info"),
                    line_hint=item.get("line_hint"),
                    message=str(item.get("message", "")),
                    suggestion=item.get("suggestion"),
                )
            )

    summary = str(data.get("summary", f"Found {len(issues)} issue(s)."))
    return issues, summary


class CodeReviewService:
    """Orchestrates the Code Reviewer agent pipeline.

    Pipeline: detect skills -> build prompt -> LLM call -> validate output ->
    parse issues -> optional QA checks.
    """

    async def process(self, request: CodeReviewRequest) -> CodeReviewResponse:
        """Review email HTML and return structured issues (non-streaming).

        Args:
            request: The Code Review request with HTML and focus area.

        Returns:
            CodeReviewResponse with issues, summary, and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"

        # Progressive disclosure -- load only relevant skill files
        relevant_skills = detect_relevant_skills(request.focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.code_reviewer.process_started",
            provider=provider_name,
            model=model,
            focus=request.focus,
            html_length=len(request.html),
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
                "agents.code_reviewer.process_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Code review processing failed") from e

        # Process output: validate -> extract issues
        raw_content = validate_output(result.content)
        confidence = extract_confidence(raw_content)
        issues, summary = _extract_issues(raw_content)

        logger.info(
            "agents.code_reviewer.process_completed",
            model=model_id,
            focus=request.focus,
            issue_count=len(issues),
            confidence=confidence,
            usage=result.usage,
        )

        # Optional QA checks on the input HTML
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []
            for check in ALL_CHECKS:
                check_result = await check.run(request.html)
                qa_results.append(check_result)
            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.code_reviewer.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return CodeReviewResponse(
            html=request.html,  # Return original HTML unmodified
            issues=issues,
            summary=summary,
            skills_loaded=relevant_skills,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_process(self, request: CodeReviewRequest) -> AsyncIterator[str]:
        """Stream code review as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete output).

        Args:
            request: The Code Review request with HTML.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("standard")
        model_id = f"{provider_name}:{model}"
        response_id = f"review-{uuid.uuid4().hex[:12]}"

        relevant_skills = detect_relevant_skills(request.focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_message = _build_user_message(request)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        logger.info(
            "agents.code_reviewer.stream_started",
            provider=provider_name,
            model=model,
            focus=request.focus,
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
                "agents.code_reviewer.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError("Code review streaming failed") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.code_reviewer.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# -- Module-level singleton --

_code_review_service: CodeReviewService | None = None


def get_code_review_service() -> CodeReviewService:
    """Get or create the Code Review service singleton.

    Returns:
        Singleton CodeReviewService instance.
    """
    global _code_review_service
    if _code_review_service is None:
        _code_review_service = CodeReviewService()
    return _code_review_service
```

### Step 7: Create `app/ai/blueprints/nodes/code_reviewer_node.py`

```python
"""Code Reviewer agentic node -- analyses email HTML and reports issues."""

import json

from app.ai.agents.code_reviewer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.code_reviewer.schemas import ReviewFocus
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CodeReviewerNode:
    """Agentic node that reviews email HTML for issues.

    Receives context.html (email) + optional review focus from metadata.
    On retry: injects code-review-related QA failures into the prompt.
    Unlike other nodes, passes HTML through unchanged — issues go into handoff warnings.
    """

    @property
    def name(self) -> str:
        return "code_reviewer"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Review email HTML via LLM and return issues as handoff warnings."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Read focus from metadata (default to "all")
        focus: ReviewFocus = context.metadata.get("review_focus", "all")  # type: ignore[assignment]

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context, focus)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.code_reviewer_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"LLM call failed: {exc}",
            )

        validated = validate_output(response.content)
        confidence = extract_confidence(validated)
        clean_content = strip_confidence_comment(validated)

        # Parse issues from response
        issues_as_warnings: tuple[str, ...] = ()
        try:
            # Extract JSON from code fence
            content = clean_content
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                content = content[start:end].strip()

            data = json.loads(content)
            raw_issues = data.get("issues", [])
            issues_as_warnings = tuple(
                f"code_review: [{item.get('severity', 'info')}] {item.get('rule', 'unknown')}: {item.get('message', '')}"
                for item in raw_issues
                if isinstance(item, dict)
            )
        except (json.JSONDecodeError, ValueError):
            issues_as_warnings = (f"code_review: raw output: {clean_content[:200]}",)

        usage = dict(response.usage) if response.usage else None

        # Code reviewer passes HTML through unchanged; issues go into warnings
        handoff = AgentHandoff(
            agent_name="code_reviewer",
            artifact=context.html,  # HTML unchanged
            decisions=(
                f"Reviewed {len(context.html)} chars with focus={focus}",
                f"Found {len(issues_as_warnings)} issue(s)",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=issues_as_warnings,
            component_refs=tuple(detect_component_refs(context.html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.code_reviewer_node.completed",
            iteration=context.iteration,
            focus=focus,
            issue_count=len(issues_as_warnings),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through unchanged
            details=f"Code review completed: {len(issues_as_warnings)} issue(s) found (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext, focus: ReviewFocus) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        focus_label = "all areas" if focus == "all" else focus
        parts = [
            f"Review the following email HTML. Focus on: {focus_label}.\n\n"
            + context.html[:12000]
        ]

        if context.iteration > 0 and context.qa_failures:
            relevant_failures = [
                f
                for f in context.qa_failures
                if any(
                    kw in f.lower()
                    for kw in (
                        "code_review",
                        "redundant",
                        "css_support",
                        "nesting",
                        "file_size",
                        "unsupported",
                    )
                )
            ]
            if relevant_failures:
                parts.append(
                    "\n\n--- CODE REVIEW QA FAILURES (address these) ---\n"
                    + "\n".join(f"- {f}" for f in relevant_failures)
                )

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

### Step 8: Add `CODE_REVIEWER_DIMENSIONS` to `app/ai/agents/evals/dimensions.py`

Append after `PERSONALISATION_DIMENSIONS`:

```python
# ---------------------------------------------------------------------------
# Code Reviewer Agent Dimensions
# ---------------------------------------------------------------------------
CODE_REVIEWER_DIMENSIONS = {
    "issue_category": {
        "description": "Category of code issue present in the email HTML",
        "values": [
            "redundant_inline_styles",
            "unused_css_class",
            "dead_mso_conditional",
            "unsupported_css_property",
            "invalid_nesting",
            "gmail_clip_risk",
            "base64_embedded_image",
            "excessive_table_depth",
            "mixed_issues",
        ],
    },
    "html_complexity": {
        "description": "Structural complexity of the email HTML being reviewed",
        "values": [
            "simple_single_column",
            "multi_column_tables",
            "heavy_mso_conditionals",
            "vml_elements_present",
            "mixed_layout",
            "production_template",
        ],
    },
    "expected_severity": {
        "description": "Expected severity level of the most significant issue",
        "values": [
            "critical_only",
            "warning_dominant",
            "info_only",
            "mixed_severity",
            "clean_no_issues",
        ],
    },
    "file_size_scenario": {
        "description": "File size challenge in the email HTML",
        "values": [
            "under_60kb",
            "near_threshold_80kb",
            "over_102kb_clipping",
            "bloated_base64",
            "minimal",
        ],
    },
}
```

### Step 9: Create `app/ai/agents/evals/synthetic_data_code_reviewer.py`

Create 12 test cases covering the dimension axes. Each case has email HTML with specific issues to detect.

```python
"""Synthetic test data for Code Reviewer agent evaluation.

12 test cases covering: redundant code, unsupported CSS, invalid nesting,
file size issues, and clean HTML (false positive testing).
"""

# -- Base HTML fragments (reused across cases) --

_VALID_HEAD = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<title>Test Email</title>
</head>"""

_VALID_BODY_OPEN = '<body style="margin:0; padding:0; background-color:#ffffff;">'
_VALID_BODY_CLOSE = "</body></html>"


def _wrap(body_content: str, head: str = _VALID_HEAD) -> str:
    return f"{head}\n{_VALID_BODY_OPEN}\n{body_content}\n{_VALID_BODY_CLOSE}"


# -- Test Cases --

CODE_REVIEWER_TEST_CASES: list[dict] = [
    # --- Redundant Code Cases ---
    {
        "id": "cr-001",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "redundant_inline_styles",
            "html_complexity": "multi_column_tables",
            "expected_severity": "warning_dominant",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5; padding:20px;">
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">First paragraph</p>
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">Second paragraph</p>
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">Third paragraph</p>
    </td>
  </tr>
  <tr>
    <td style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5; padding:20px;">
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">More repeated styles</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Detect repeated inline style blocks across siblings"],
    },
    {
        "id": "cr-002",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "dead_mso_conditional",
            "html_complexity": "heavy_mso_conditionals",
            "expected_severity": "info_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<!--[if mso]>
<table role="presentation" width="600"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px;">
  <tr><td style="padding:20px;">Content here</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->

<!--[if mso]>

<![endif]-->

<!--[if gte mso 9]>
  <!--[if gte mso 9]>
    <table><tr><td>Nested same-version MSO</td></tr></table>
  <![endif]-->
<![endif]-->
"""),
        "expected_challenges": ["Detect empty MSO conditional", "Detect nested same-version MSO"],
    },
    {
        "id": "cr-003",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "unused_css_class",
            "html_complexity": "simple_single_column",
            "expected_severity": "info_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": f"""{_VALID_HEAD.replace('</head>', '')}\
<style>
  .hero-title {{ font-size: 24px; }}
  .hero-subtitle {{ font-size: 16px; }}
  .cta-button {{ background-color: #007bff; }}
  .unused-class-a {{ color: red; }}
  .unused-class-b {{ margin: 10px; }}
</style>
</head>
{_VALID_BODY_OPEN}
<table role="presentation">
  <tr><td class="hero-title">Welcome</td></tr>
  <tr><td><a href="https://example.com" class="cta-button">Click</a></td></tr>
</table>
{_VALID_BODY_CLOSE}""",
        "expected_challenges": ["Detect unused CSS classes (unused-class-a, unused-class-b, hero-subtitle)"],
    },

    # --- CSS Support Cases ---
    {
        "id": "cr-004",
        "focus": "css_support",
        "dimensions": {
            "issue_category": "unsupported_css_property",
            "html_complexity": "simple_single_column",
            "expected_severity": "critical_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <tr>
    <td style="display:flex; justify-content:space-between; align-items:center;">
      <div style="flex:1; padding:10px;">Column 1</div>
      <div style="flex:1; padding:10px;">Column 2</div>
    </td>
  </tr>
  <tr>
    <td style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
      <div>Grid item 1</div>
      <div>Grid item 2</div>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Flag display:flex", "Flag display:grid", "Flag gap property"],
    },
    {
        "id": "cr-005",
        "focus": "css_support",
        "dimensions": {
            "issue_category": "unsupported_css_property",
            "html_complexity": "mixed_layout",
            "expected_severity": "mixed_severity",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <tr>
    <td style="border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); position:relative;">
      <img src="https://placehold.co/600x200" alt="Banner" width="600" height="200"
           style="display:block; object-fit:cover; clip-path:circle(50%);">
      <div style="position:absolute; top:10px; left:10px; background:var(--brand-color);">
        Overlay text with CSS custom property
      </div>
    </td>
  </tr>
  <tr>
    <td style="max-width:600px; margin:0 auto;">
      <p style="line-height:1.5">Text with unitless line-height</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Flag position:absolute", "Flag object-fit", "Flag clip-path",
            "Flag var(--brand-color)", "Note border-radius partial support",
            "Note box-shadow partial support", "Note max-width needs MSO fallback",
        ],
    },

    # --- Nesting Cases ---
    {
        "id": "cr-006",
        "focus": "nesting",
        "dimensions": {
            "issue_category": "invalid_nesting",
            "html_complexity": "multi_column_tables",
            "expected_severity": "critical_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <td style="padding:20px;">Content without tr</td>
  <tr>
    <table role="presentation"><tr><td>Table directly in tr</td></tr></table>
  </tr>
  <tr>
    <td>
      <span><div>Block inside inline</div></span>
      <p>First paragraph<p>Nested paragraph (invalid)</p></p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Detect td outside tr", "Detect table directly in tr",
            "Detect div inside span", "Detect p inside p",
        ],
    },
    {
        "id": "cr-007",
        "focus": "nesting",
        "dimensions": {
            "issue_category": "excessive_table_depth",
            "html_complexity": "heavy_mso_conditionals",
            "expected_severity": "warning_dominant",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation"><tr><td>
  <table role="presentation"><tr><td>
    <table role="presentation"><tr><td>
      <table role="presentation"><tr><td>
        <table role="presentation"><tr><td>
          <table role="presentation"><tr><td>
            <table role="presentation"><tr><td>
              Deeply nested content (7 levels)
            </td></tr></table>
          </td></tr></table>
        </td></tr></table>
      </td></tr></table>
    </td></tr></table>
  </td></tr></table>
</td></tr></table>"""),
        "expected_challenges": ["Detect excessive table nesting depth (>6)"],
    },

    # --- File Size Cases ---
    {
        "id": "cr-008",
        "focus": "file_size",
        "dimensions": {
            "issue_category": "gmail_clip_risk",
            "html_complexity": "production_template",
            "expected_severity": "critical_only",
            "file_size_scenario": "over_102kb_clipping",
        },
        "html_input": _wrap(
            '<table role="presentation">'
            + "\n".join(
                f'<tr><td style="font-family:Arial,sans-serif; font-size:14px; color:#333; '
                f'line-height:1.5; padding:10px 20px;">Row {i} with enough content to bulk up the '
                f"file size past the Gmail clipping threshold. This is test content repeated to "
                f"create a realistically large email template. Lorem ipsum dolor sit amet.</td></tr>"
                for i in range(350)
            )
            + "</table>"
        ),
        "expected_challenges": ["Detect file size >102KB", "Suggest minification"],
    },
    {
        "id": "cr-009",
        "focus": "file_size",
        "dimensions": {
            "issue_category": "base64_embedded_image",
            "html_complexity": "simple_single_column",
            "expected_severity": "critical_only",
            "file_size_scenario": "bloated_base64",
        },
        "html_input": _wrap(f"""
<table role="presentation" width="600">
  <tr>
    <td>
      <img src="data:image/png;base64,{'A' * 5000}" alt="Embedded image" width="200" height="200">
      <p>Email with base64 embedded image</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Detect base64 embedded image", "Suggest external hosting"],
    },

    # --- Mixed Issues Cases ---
    {
        "id": "cr-010",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "production_template",
            "expected_severity": "mixed_severity",
            "file_size_scenario": "near_threshold_80kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="display:flex; padding:20px; font-family:Arial,sans-serif;">
      <div style="font-family:Arial,sans-serif; color:#333;">
        <span><div>Nested block in inline</div></span>
      </div>
    </td>
  </tr>
  <tr>
    <td style="font-family:Arial,sans-serif; color:#333; padding:20px;">
      <p style="font-family:Arial,sans-serif; color:#333;">Repeated styles</p>
      <p style="font-family:Arial,sans-serif; color:#333;">Same styles again</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Flag display:flex (critical)",
            "Detect div inside span (critical)",
            "Detect repeated inline styles (warning)",
        ],
    },

    # --- Clean HTML (False Positive Testing) ---
    {
        "id": "cr-011",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "production_template",
            "expected_severity": "clean_no_issues",
            "file_size_scenario": "under_60kb",
        },
        "html_input": f"""{_VALID_HEAD.replace('</head>', '')}\
<style>
  @media (prefers-color-scheme: dark) {{
    .dark-bg {{ background-color: #1a1a2e !important; }}
  }}
  [data-ogsc] .dark-text {{ color: #ffffff !important; }}
</style>
</head>
{_VALID_BODY_OPEN}
<!--[if mso]>
<table role="presentation" width="600" align="center"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px; margin:0 auto;">
  <tr>
    <td style="padding:20px; font-family:Arial,Helvetica,sans-serif; color:#333333;">
      <img src="https://placehold.co/600x200" alt="Spring collection banner showing new arrivals"
           width="600" height="200" style="display:block; width:100%; height:auto;">
      <h1 style="font-size:24px; margin:20px 0 10px;">Welcome to Our Store</h1>
      <p style="font-size:14px; line-height:22px;">Quality email template content.</p>
      <a href="https://example.com/shop" style="display:inline-block; padding:12px 24px;
         background-color:#007bff; color:#ffffff; text-decoration:none;
         mso-padding-alt:12px 24px;">Shop Now</a>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
{_VALID_BODY_CLOSE}""",
        "expected_challenges": ["Clean HTML — should report zero or minimal issues (info only)"],
    },
    {
        "id": "cr-012",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "vml_elements_present",
            "expected_severity": "clean_no_issues",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
        style="width:600px; height:300px;">
  <v:fill type="frame" src="https://placehold.co/600x300" />
  <v:textbox inset="0,0,0,0">
<![endif]-->
<table role="presentation" width="600" style="background-image:url('https://placehold.co/600x300'); background-size:cover;">
  <tr>
    <td style="padding:40px; font-family:Arial,sans-serif; color:#ffffff;">
      <h1 style="font-size:28px; margin:0 0 10px;">VML Background Hero</h1>
      <p style="font-size:16px; line-height:24px;">Content over background image with Outlook VML fallback.</p>
    </td>
  </tr>
</table>
<!--[if mso]>
  </v:textbox>
</v:rect>
<![endif]-->"""),
        "expected_challenges": ["VML elements and MSO comments are valid — should NOT be flagged"],
    },
]
```

### Step 10: Create `app/ai/agents/evals/judges/code_reviewer.py`

```python
"""Binary pass/fail judge for the Code Reviewer agent."""

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

CODE_REVIEWER_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="issue_genuineness",
        description=(
            "Are all flagged issues real problems? Each reported issue must be a "
            "genuine code quality problem in email HTML context. Standard email patterns "
            "(table layouts, inline styles, MSO conditionals, VML, mso-* CSS properties, "
            "cellpadding/cellspacing/border attributes) must NOT be flagged as issues. "
            "A false positive is any issue that flags normal, expected email HTML patterns."
        ),
    ),
    JudgeCriteria(
        name="suggestion_actionability",
        description=(
            "Does every issue include a concrete, actionable fix suggestion? Generic "
            "advice like 'consider improving' or 'review this code' is insufficient. "
            "Suggestions must specify what to change (e.g., 'Replace display:flex with "
            "table-based layout', 'Move repeated font-family to <style> class', "
            "'Host image externally instead of base64 encoding'). Severity:info issues "
            "may have lighter suggestions but must still be specific."
        ),
    ),
    JudgeCriteria(
        name="severity_accuracy",
        description=(
            "Is the severity classification correct for each issue? Critical = breaks "
            "rendering in major email clients (Outlook, Gmail). Warning = degrades "
            "experience or poor practice. Info = optimisation opportunity. Examples: "
            "display:flex should be critical (breaks Outlook). Redundant styles should "
            "be warning or info. Unused CSS class should be info. File size >102KB "
            "should be critical. Over-classifying info issues as critical is a failure."
        ),
    ),
    JudgeCriteria(
        name="coverage_completeness",
        description=(
            "Does the review catch all significant issues in the HTML? Compare the "
            "expected_challenges from the test case against the reported issues. "
            "Missing a critical issue (unsupported CSS, invalid nesting, size threshold) "
            "is a coverage failure. Missing an info-level optimisation is acceptable "
            "if the major issues are caught."
        ),
    ),
    JudgeCriteria(
        name="output_format",
        description=(
            "Is the output valid JSON with the expected structure? Must contain an "
            "'issues' array where each issue has 'rule' (string), 'severity' "
            "(critical/warning/info), 'message' (string), and optionally 'line_hint' "
            "(integer) and 'suggestion' (string). Must also contain a 'summary' string. "
            "If the output is not parseable JSON or is missing required fields, this "
            "criterion fails."
        ),
    ),
]


class CodeReviewerJudge:
    """Binary judge for Code Reviewer agent outputs."""

    agent_name: str = "code_reviewer"
    criteria: list[JudgeCriteria] = CODE_REVIEWER_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with input HTML and review output."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        html_input = ""
        focus = "all"
        if judge_input.input_data:
            html_input = str(judge_input.input_data.get("html_input", ""))
            if not html_input:
                html_input = str(judge_input.input_data.get("html_length", ""))
            focus = str(judge_input.input_data.get("focus", "all"))

        review_output = ""
        if judge_input.output_data:
            # Output includes issues and summary
            issues = judge_input.output_data.get("issues", [])
            summary = judge_input.output_data.get("summary", "")
            review_output = f"Summary: {summary}\n\nIssues:\n"
            for issue in issues:
                if isinstance(issue, dict):
                    review_output += (
                        f"- [{issue.get('severity', '?')}] {issue.get('rule', '?')}: "
                        f"{issue.get('message', '')} "
                        f"(suggestion: {issue.get('suggestion', 'none')})\n"
                    )

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## REVIEW FOCUS\n{focus}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT INPUT (Email HTML)\n```html\n{html_input}\n```\n\n"
            f"## AGENT OUTPUT (Code Review)\n{review_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
```

### Step 11: Modify `app/ai/agents/evals/judges/__init__.py`

Add `CodeReviewerJudge` import and registration:

```python
# Add import
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge

# Add to JUDGE_REGISTRY type union and dict
# Type union becomes: ScaffolderJudge | DarkModeJudge | ContentJudge | OutlookFixerJudge | AccessibilityJudge | PersonalisationJudge | CodeReviewerJudge

# Add entry:
#     "code_reviewer": CodeReviewerJudge,

# Add to __all__:
#     "CodeReviewerJudge",
```

### Step 12: Modify `app/ai/agents/evals/runner.py`

Add `run_code_reviewer_case()` function and register in CLI choices:

```python
# Add import at top:
from app.ai.agents.evals.synthetic_data_code_reviewer import CODE_REVIEWER_TEST_CASES

# Add runner function (after run_personalisation_case):
async def run_code_reviewer_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single code reviewer test case and return the trace."""
    from app.ai.agents.code_reviewer.schemas import CodeReviewRequest
    from app.ai.agents.code_reviewer.service import CodeReviewService

    service = CodeReviewService()
    html_input: str = str(case["html_input"])
    focus: str = str(case.get("focus", "all"))
    request = CodeReviewRequest(
        html=html_input,
        focus=focus,  # pyright: ignore[reportArgumentType]
        stream=False,
        run_qa=True,
    )

    start = time.monotonic()
    try:
        response = await service.process(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "code_reviewer",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
                "focus": focus,
            },
            "output": {
                "html": response.html,
                "issues": [i.model_dump() for i in response.issues],
                "summary": response.summary,
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
            "agent": "code_reviewer",
            "dimensions": case["dimensions"],
            "input": {
                "html_input": html_input,
                "html_length": len(html_input),
                "focus": focus,
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }

# In run_agent(): add elif branch:
#     elif agent == "code_reviewer":
#         cases = CODE_REVIEWER_TEST_CASES
#         runner = run_code_reviewer_case

# In main(): add "code_reviewer" to choices list and "all" agents list
```

### Step 13: Modify `app/ai/agents/evals/judge_runner.py`

```python
# Add import:
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge

# Update judge_trace type union to include CodeReviewerJudge:
# judge: ScaffolderJudge | ... | PersonalisationJudge | CodeReviewerJudge

# Add "code_reviewer" to CLI choices and "all" agents list
```

### Step 14: Modify `app/ai/agents/evals/mock_traces.py`

Add Code Reviewer criteria and register:

```python
# Add after PERSONALISATION_CRITERIA:
CODE_REVIEWER_CRITERIA: list[dict[str, str]] = [
    {"criterion": "issue_genuineness", "description": "Flagged issues are real problems"},
    {"criterion": "suggestion_actionability", "description": "Suggestions are specific and actionable"},
    {"criterion": "severity_accuracy", "description": "Severity matches impact"},
    {"criterion": "coverage_completeness", "description": "All significant issues caught"},
    {"criterion": "output_format", "description": "Valid JSON with required fields"},
]

# Add to AGENT_CRITERIA dict:
#     "code_reviewer": CODE_REVIEWER_CRITERIA,
```

### Step 15: Modify `app/ai/blueprints/definitions/campaign.py`

Add `CodeReviewerNode` to the campaign blueprint graph. Code Reviewer runs after the main scaffolder QA pass, before the build step:

```python
# Add import:
from app.ai.blueprints.nodes.code_reviewer_node import CodeReviewerNode

# In build_campaign_blueprint():
#   code_reviewer = CodeReviewerNode()
#   Add to nodes dict: code_reviewer.name: code_reviewer

# Add edges:
#   Edge(from_node="recovery_router", to_node="code_reviewer", condition="route_to", route_value="code_reviewer"),
#   Edge(from_node="code_reviewer", to_node="qa_gate", condition="always"),
```

### Step 16: Modify `app/ai/blueprints/nodes/recovery_router_node.py`

Add Code Reviewer routing logic:

```python
# Add to _FAILURE_ROUTING dict:
#   "css_support": "code_reviewer",  # Override from "scaffolder"
#   "file_size": "code_reviewer",    # Override from "scaffolder"

# Add detection block (after personalisation detection):
has_code_review_failure = any(
    any(
        kw in f.lower()
        for kw in (
            "code_review",
            "redundant",
            "css_support",
            "nesting",
            "file_size",
            "unsupported css",
        )
    )
    for f in context.qa_failures
)

# Also check upstream handoff warnings:
if not has_code_review_failure:
    has_code_review_failure = any(
        any(
            kw in w.lower()
            for kw in ("code_review", "redundant", "unsupported css", "file_size")
        )
        for w in upstream.warnings
    )

# Add routing priority (after personalisation, before default scaffolder):
elif has_code_review_failure:
    target = "code_reviewer"
```

### Step 17: Update Tests

#### `app/ai/agents/tests/test_judges.py`

Add:
```python
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge

def _make_code_reviewer_input() -> JudgeInput:
    return JudgeInput(
        trace_id="cr-001",
        agent="code_reviewer",
        input_data={
            "html_input": '<td style="display:flex">Bad CSS</td>',
            "focus": "css_support",
        },
        output_data={
            "issues": [
                {
                    "rule": "css-unsupported-flex",
                    "severity": "critical",
                    "message": "display:flex is unsupported in Outlook",
                    "suggestion": "Replace with table-based layout",
                }
            ],
            "summary": "Found 1 critical issue",
        },
        expected_challenges=["Flag display:flex"],
    )

CODE_REVIEWER_CRITERIA_NAMES = [
    "issue_genuineness",
    "suggestion_actionability",
    "severity_accuracy",
    "coverage_completeness",
    "output_format",
]


class TestCodeReviewerJudge:
    def test_build_prompt_contains_criteria_and_input(self) -> None:
        judge = CodeReviewerJudge()
        prompt = judge.build_prompt(_make_code_reviewer_input())

        assert "issue_genuineness" in prompt
        assert "suggestion_actionability" in prompt
        assert "severity_accuracy" in prompt
        assert "display:flex" in prompt
        assert "css_support" in prompt

    def test_parse_valid_response(self) -> None:
        judge = CodeReviewerJudge()
        raw = _make_valid_response(CODE_REVIEWER_CRITERIA_NAMES)
        verdict = judge.parse_response(raw, _make_code_reviewer_input())

        assert verdict.overall_pass is True
        assert len(verdict.criteria_results) == 5
        assert verdict.error is None
        assert verdict.trace_id == "cr-001"
        assert verdict.agent == "code_reviewer"


# Update TestJudgeRegistry:
#   assert "code_reviewer" in JUDGE_REGISTRY
#   assert len(JUDGE_REGISTRY) == 7  # was 6
```

### Step 18: Verify

After implementation:

```bash
# Run all quality checks
make check

# Verify dry-run pipeline includes code_reviewer
python -m app.ai.agents.evals.runner --agent code_reviewer --output traces/ --dry-run

# Verify judge dry-run
python -m app.ai.agents.evals.judge_runner --agent code_reviewer --traces traces/code_reviewer_traces.jsonl --output traces/code_reviewer_verdicts.jsonl --dry-run
```

---

## Security Checklist

No new HTTP endpoints are added by this plan (the Code Reviewer agent is accessed via the existing AI chat pipeline and blueprint engine). Security considerations:

- [x] Agent output goes through `validate_output()` — standard LLM output validation
- [x] Input HTML goes through `sanitize_prompt()` before LLM call
- [x] No new routes = no new auth/rate-limit requirements
- [x] Error responses use `AIExecutionError` (auto-sanitized via `get_safe_error_message`)
- [x] No secrets/credentials in logs (structured logging with field extraction only)
- [x] Code Reviewer does NOT modify HTML — analysis only, eliminating XSS injection risk
- [x] Blueprint node uses `detect_component_refs()` safely (read-only)

## Verification

- [x] `make check` passes (lint, types, tests, frontend, security-check)
- [x] `test_judges.py::TestJudgeRegistry::test_registry_has_all_agents` passes with 7 agents
- [x] `test_dry_run_pipeline.py::test_pipeline_with_all_agents` includes code_reviewer
- [x] Dry-run generates 12 traces + 12 verdicts for code_reviewer
- [x] `CodeReviewerNode` correctly passes HTML through (artifact == input)
- [x] Recovery router routes `css_support` and `file_size` failures to code_reviewer
- [x] Campaign blueprint graph includes code_reviewer node
