# Plan: Agent Quality & Architecture Improvements — COMPLETE (2026-03-09)

## Context

Research conducted 2026-03-09 across all 7 agent service files, blueprint engine, node implementations, eval system, and trace data. Findings: 16.7% overall pass rate, ~80% code duplication across agents, built-but-unused infrastructure (memory recall, handoff_history, confidence scoring), recovery router bug, and prompt gaps causing systematic failures.

**Prerequisites:** Knowledge and Innovation agents must be built first (separate plans). This plan applies to all 7 existing + 2 upcoming agents.

**Key insight:** Current agent failures are prompt engineering and infrastructure wiring problems, not knowledge structure limitations. Phase 8-9 (knowledge graph) is the right direction but premature — fix fundamentals first.

## Completion Summary (2026-03-09)

All 6 phases executed. 544 tests pass. Key outcomes:
- **Phase 1 (BaseAgentService):** 7 agents refactored, ~500 lines removed, `_get_model_tier` + `_should_run_qa` hooks for thread-safe singletons
- **Phase 2 (prompt fixes):** Scaffolder MSO/a11y/dark mode mandatory sections; Content num_alternatives enforcement
- **Phase 3 (infrastructure wiring):** Memory recall in blueprint engine, handoff_history consumption, confidence on all agents
- **Phase 4 (router bug):** "fallback" keyword collision fixed, "merge tag" replacement
- **Phase 5 (eval trace fix):** Dark mode input HTML stored in traces, judge graceful degradation for missing input
- **Phase 6 (response schema):** `confidence` + `skills_loaded` added to all 9 response schemas, `to_handoff()` on BaseAgentService

---

## Phase 1: Extract Shared Agent Base Class

**Problem:** ~80% of each agent's `service.py` is copy-pasted boilerplate. The `stream_*()` method is character-for-character identical across all 7 agents. Adding any new capability (memory recall, confidence scoring) requires editing all 7+ files.

**What to build:**

### 1.1 Define `AgentService` Protocol
File: `app/ai/protocols.py` (extend existing)

```python
class AgentService(Protocol):
    """Standard interface for all agents."""
    async def process(self, request: Any) -> Any: ...
    async def stream_process(self, request: Any) -> AsyncIterator[str]: ...
```

This enables generic agent composition in the blueprint engine.

### 1.2 Extract `BaseAgentService` class
File: `app/ai/agents/base.py` (new)

Extract the shared skeleton into a base class:

```python
class BaseAgentService:
    """Shared agent pipeline: prompt → LLM → post-process → QA."""

    agent_name: str           # e.g. "scaffolder"
    model_tier: str           # "complex" | "standard" | "lightweight"
    max_tokens: int = 8192
    run_qa: bool = True

    def _build_system_prompt(self, relevant_skills: list[str]) -> str
    def _build_user_message(self, request: Any) -> str  # override per agent
    def detect_relevant_skills(self, *args) -> list[str]  # override per agent
    def _post_process(self, raw: str) -> str  # default: extract_html + sanitize_xss
    async def _run_qa(self, html: str) -> tuple[list, bool]  # shared QA loop

    async def process(self, request: Any) -> Any:
        """The shared 10-step pipeline."""
        model = resolve_model(self.model_tier)
        skills = self.detect_relevant_skills(request)
        system_prompt = self._build_system_prompt(skills)
        user_msg = sanitize_prompt(self._build_user_message(request))
        messages = [Message("system", system_prompt), Message("user", user_msg)]
        provider = get_registry().get_llm(settings.ai.provider)
        response = await provider.complete(messages, model_override=model, max_tokens=self.max_tokens)
        output = self._post_process(response.content)
        confidence = extract_confidence(response.content)
        qa_results, qa_passed = await self._run_qa(output) if self.run_qa else ([], True)
        return self._build_response(output, qa_results, qa_passed, model, confidence, skills)

    async def stream_process(self, request: Any) -> AsyncIterator[str]:
        """Shared SSE streaming — currently duplicated 7 times."""
        ...  # extract the identical streaming logic once
```

### 1.3 Refactor each agent to extend `BaseAgentService`
Each agent overrides only what's unique:

| Agent | Overrides |
|-------|-----------|
| Scaffolder | `model_tier="complex"`, `_build_user_message()`, `detect_relevant_skills()` |
| Dark Mode | `_build_user_message()` (color overrides), `_run_qa()` (DarkModeCheck first), `detect_relevant_skills()` |
| Content | `_post_process()` (extract_content + spam check), `run_qa=False`, `max_tokens=2048`, per-operation model tier |
| Outlook Fixer | `_build_user_message()`, `detect_relevant_skills()` |
| Accessibility | `_build_user_message()`, `detect_relevant_skills()` |
| Personalisation | `_build_user_message()`, `detect_relevant_skills()` |
| Code Reviewer | `_post_process()` (JSON extraction), `_run_qa()` (QA on input, not output) |

**Estimated reduction:** ~500 lines removed across 7 files. New base class ~150 lines.

### 1.4 Remove singleton pattern duplication
Replace the 7x duplicated `_service: T | None = None` / `get_*_service()` with a shared `get_agent_service(name)` factory or keep per-agent but move to a one-liner using the base class.

**Verify:**
- `make test` — all existing agent tests pass
- `make types` — no type errors
- `make lint` — clean
- Each agent still produces identical output (regression test against existing traces)

---

## Phase 2: Fix Prompt Gaps (Immediate Quality Wins)

**Problem:** 16.7% overall pass rate. Root causes are specific prompt gaps, not architectural issues.

### 2.1 Fix Scaffolder MSO Conditionals (0% pass rate)

File: `app/ai/agents/scaffolder/SKILL.md` and/or `app/ai/agents/scaffolder/skills/mso_vml_quick_ref.md`

The scaffolder never includes `xmlns:v="urn:schemas-microsoft-com:vml"` and `xmlns:o="urn:schemas-microsoft-com:office:office"` namespace declarations. Add these to the template skeleton in the SKILL.md L2 instructions as a **mandatory** boilerplate requirement, not just a reference.

Add to L2 core instructions:
```
## Required HTML Skeleton (ALWAYS include)
Every generated email MUST include these namespace declarations in the <html> tag:
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
```

### 2.2 Fix Scaffolder Accessibility Baseline (8% pass rate)

File: `app/ai/agents/scaffolder/SKILL.md`

Add to L2 core instructions:
```
## Required Accessibility (ALWAYS include)
- <html lang="en"> (or appropriate language code from brief)
- role="article" on the main content wrapper
- Heading hierarchy: exactly one <h1>, use <h2>/<h3> for sections
- alt="" on decorative images, descriptive alt on content images
```

### 2.3 Fix Scaffolder Dark Mode Readiness (25% pass rate)

File: `app/ai/agents/scaffolder/SKILL.md`

Add to L2 core instructions:
```
## Required Dark Mode Foundation (ALWAYS include)
- <meta name="color-scheme" content="light dark">
- <meta name="supported-color-schemes" content="light dark">
- [data-ogsb] selectors in <style> for Outlook dark mode
```

### 2.4 Fix Content Agent Operation Compliance (57% pass rate)

File: `app/ai/agents/content/SKILL.md` or `app/ai/agents/content/service.py` prompt

When `num_alternatives=1` or operation expects single output, add explicit instruction:
```
Return EXACTLY ONE result. Do not provide alternatives or variations unless explicitly asked.
```

**Verify:**
- Run `make eval-run --agent scaffolder` against the same 12 synthetic cases
- Run `make eval-run --agent content` against the same 14 cases
- Compare pass rates against baseline (scaffolder should jump from 0%/8%/25% on those criteria)

---

## Phase 3: Wire Built-But-Unused Infrastructure

**Problem:** Phase 7 infrastructure was built but never connected to agent execution. Memory recall, handoff_history, confidence scoring, and brief context exist but aren't used where they matter.

### 3.1 Wire Memory Recall into Blueprint Nodes

File: `app/ai/blueprints/engine.py` — `_build_node_context()` method

Before each agentic node executes, recall relevant memories from the project's memory store and inject them into `context.metadata["recalled_memories"]`.

```python
# In _build_node_context():
if self._memory_service and context.brief:
    memories = await self._memory_service.recall(
        context.brief,
        project_id=run.project_id,
        limit=5,
    )
    context.metadata["recalled_memories"] = [
        {"content": m.content, "agent": m.source_agent, "type": m.memory_type}
        for m, score in memories
        if score > 0.3  # relevance threshold
    ]
```

The `BlueprintService` already has access to `MemoryService` via `handoff_memory.py` — extend the wiring.

Each agent's `_build_user_message()` (or the base class) appends recalled memories to the prompt when present.

### 3.2 Have Fixer Nodes Read the Brief

File: All fixer node `_build_user_message()` methods (or handle in `BaseAgentService`)

Currently fixer nodes (dark_mode, outlook_fixer, accessibility, personalisation, code_reviewer) receive `context.brief` but never use it. Their prompts only show the HTML + QA failures.

Add to fixer prompts:
```
## Original Campaign Intent
{context.brief}

Keep this intent in mind while fixing. Do not alter the design direction or content meaning.
```

This prevents fixers from "undoing" scaffolder decisions without understanding why they were made.

### 3.3 Enable Confidence Scoring on All Agents

Files: `BaseAgentService._post_process()` (if Phase 1 is done) or each `service.py`

Currently only Code Reviewer extracts confidence via `extract_confidence()`. Add to all agents:
1. Append to system prompt: `"End your response with <!-- CONFIDENCE: X.XX --> where X.XX is your confidence (0.00-1.00) in the output quality."`
2. Extract confidence in post-processing
3. Include in response and handoff

The blueprint engine already checks `confidence < 0.5` → `needs_review` status. This gate is built but only triggered by one agent.

### 3.4 Have Recovery Router Consume `handoff_history`

File: `app/ai/blueprints/nodes/recovery_router_node.py`

Currently the router only reads the most recent `upstream_handoff.warnings`. Extend to read `handoff_history` to:
- Track which agents have already run → avoid redundant routing
- Accumulate all warnings from all prior nodes → better routing decisions
- Detect cycles: if dark_mode already ran and the same QA failure persists, escalate rather than re-route

```python
# In execute():
history = context.metadata.get("handoff_history", [])
agents_already_run = {h.agent_name for h in history}
all_warnings = [w for h in history for w in h.warnings]

# Don't re-route to an agent that already tried and failed
if target in agents_already_run and iteration > 0:
    target = self._next_fallback(target, agents_already_run)
```

**Verify:**
- `make test` — all blueprint tests pass
- Blueprint eval: run `make eval-blueprint` and confirm 5/5 still pass
- Manual test: run a blueprint where dark_mode fails → verify memory is recalled in context

---

## Phase 4: Fix Recovery Router Bug

**Problem:** The `has_personalisation_failure` check matches on the keyword `"fallback"`, which also matches Outlook MSO fallback failures. This can misroute QA failures.

### 4.1 Fix "fallback" keyword collision

File: `app/ai/blueprints/nodes/recovery_router_node.py`

The personalisation failure detection includes `"fallback"` in its keyword list. MSO fallback checks (e.g., `"fallback: No MSO conditional comments"`) also contain this word.

Fix: Make personalisation keywords more specific — use `"liquid"`, `"ampscript"`, `"dynamic content"`, `"personalisation"`, `"personalization"` instead of generic `"fallback"`. Or check that the QA failure source is the personalisation-specific check, not substring matching.

### 4.2 Add Multi-Target Recovery Routing (Optional Enhancement)

Currently: if QA flags both dark_mode AND accessibility failures, only dark_mode gets routed to (first match wins). The accessibility issue waits for the next QA cycle.

Improvement: return a priority-ordered list of targets. The engine runs them sequentially before the next QA gate. This reduces self-correction rounds needed for multi-domain failures.

**Verify:**
- Add a test case: QA failure string contains both "mso" and "liquid" → verify correct routing
- Existing blueprint tests still pass

---

## Phase 5: Fix Eval Trace Collection Bug

**Problem:** Dark mode's 10% html_preservation pass rate is a trace collection bug, not an agent bug. The trace stores empty input HTML, so the judge can't verify HTML was preserved.

### 5.1 Fix Dark Mode Trace Input Storage

File: `app/ai/agents/evals/runner.py`

When generating traces, ensure the input HTML is stored in the trace data (truncated if needed for token budget). The judge needs to compare input vs output to evaluate preservation.

```python
# In trace generation:
trace["input_html"] = request.html[:5000]  # truncated for token budget
trace["input_html_length"] = len(request.html)
```

### 5.2 Update html_preservation Judge

File: `app/ai/agents/evals/judges/__init__.py` (DarkModeJudge criteria)

Update the judge prompt to reference the stored `input_html` field instead of expecting it in the output. If `input_html` is empty/missing, mark as `"skip"` not `"fail"`.

### 5.3 Re-run Real Eval Traces for All 7 Agents

After prompt fixes (Phase 2) and trace fix (5.1-5.2):
```bash
make eval-run        # Generate real traces for all agents
make eval-analysis   # Analyze verdicts
make eval-baseline   # Establish new baseline
```

**Verify:**
- Dark mode html_preservation pass rate should increase significantly
- Scaffolder MSO/accessibility/dark_mode criteria should improve from Phase 2 fixes
- New baseline reflects actual agent quality

---

## Phase 6: Standardise Agent Response Schema

**Problem:** Three distinct response patterns exist with no shared structure. Blueprint nodes have to handle each differently.

### 6.1 Create Shared Response Fields

All agent responses should include:
```python
@dataclass
class AgentResponseBase:
    html: str
    model: str
    confidence: float          # 0.0-1.0 from <!-- CONFIDENCE -->
    skills_loaded: list[str]   # which L3 skills were used
    qa_results: list[dict]     # QA check results (empty if not run)
    qa_passed: bool            # True if all checks passed
```

Content agent extends with `content: list[str]`, `operation: str`, `spam_warnings`.
Code Reviewer extends with `issues: list[CodeReviewIssue]`, `summary: str`.

### 6.2 Standardise Handoff Emission

Currently each node manually constructs `AgentHandoff`. With `BaseAgentService`, the base class can emit a standardised handoff from any response:

```python
def to_handoff(self, response: AgentResponseBase) -> AgentHandoff:
    return AgentHandoff(
        status="ok" if response.qa_passed else "warning",
        agent_name=self.agent_name,
        artifact=response.html,
        decisions=tuple(self._extract_decisions(response)),
        warnings=tuple(self._extract_warnings(response)),
        confidence=response.confidence,
    )
```

**Verify:**
- Blueprint API response still includes all fields
- Handoff memory bridge still persists correctly
- `make test` passes

---

## Execution Order

| Step | Phase | Risk | Dependencies |
|------|-------|------|-------------|
| 1 | Phase 2 (prompt fixes) | Low — markdown edits only | None |
| 2 | Phase 4.1 (router bug fix) | Low — small code change | None |
| 3 | Phase 5 (trace bug fix) | Low — eval infra only | None |
| 4 | Phase 1 (base class extraction) | Medium — refactor | None, but do after prompt fixes so eval baseline is stable |
| 5 | Phase 3 (wire infrastructure) | Medium — engine changes | Phase 1 makes this easier but not required |
| 6 | Phase 6 (response schema) | Medium — cross-cutting | Phase 1 (base class) |
| 7 | Re-run evals | Low | Phases 2, 5 |

**Total estimated scope:** ~800 lines changed, ~500 lines removed (dedup), ~200 lines added (base class + wiring).

---

## What This Plan Does NOT Cover (Intentionally Kept)

- **Phase 8-9 (Knowledge Graph / Cognee)** — genuine capability improvements, do AFTER this plan
- **7.6 DCG Cross-Agent Memory** — separate repo work, complementary to this
- **Knowledge / Innovation agents** — separate build plans
- **LMCache infrastructure patterns** — independent improvements
- **Autoresearch patterns** — future optimization loop
- **Human label calibration** — blocked on real eval traces (Phase 5.3 unblocks this)

---

## Success Criteria

After implementing this plan:
1. Agent service files are ~60% smaller (shared base class)
2. Scaffolder pass rate jumps from 0%/8%/25% to >60% on MSO/accessibility/dark_mode criteria
3. Dark mode html_preservation pass rate reflects actual quality (not trace bug)
4. Content operation_compliance >80%
5. All agents emit confidence scores
6. Blueprint runs benefit from recalled memories from prior runs
7. Recovery router doesn't misroute personalisation vs MSO fallback failures
8. Adding a new agent requires ~50 lines (overrides only) instead of ~300 lines (full copy-paste)
