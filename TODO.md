# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–47):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA). Phase 18 (rendering resilience & property-based testing). Phase 19 (Outlook transition advisor & email CSS compiler). Phase 20 (Gmail AI intelligence & deliverability). Phase 21 (real-time ontology sync & competitive intelligence). Phase 22 (AI evolution infrastructure). Phase 23 (multimodal protocol & MCP agent interface — 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks). Phase 26 (email build pipeline performance & CSS optimization — 5 subtasks). Phase 27 (email client rendering fidelity & pre-send testing — 6 subtasks). Phase 28 (export quality gates & approval workflow — 3 subtasks). Phase 29 (design import enhancements — 2 subtasks). Phase 30 (end-to-end testing & CI quality — 3 subtasks). Phase 31 (HTML import fidelity & preview accuracy — 8 subtasks). Phase 32 (agent email rendering intelligence — 12 subtasks: centralized client matrix, content rendering awareness, import annotator skills, knowledge lookup tool, cross-agent insight propagation, eval-driven skill updates, visual QA feedback loop, MCP agent tools, skill versioning, per-client skill overlays). Phase 33 (design token pipeline overhaul — 12 subtasks). Phase 34 (CRAG accept/reject gate — 3 subtasks). Phase 35 (next-gen design-to-email pipeline — 11 subtasks: MJML compilation, tree normalizer, MJML generation, section templates, AI layout intelligence, visual fidelity scoring, correction learning loop, W3C design tokens, Figma webhooks, section caching). Phase 36 (universal email design document & multi-format import hub — 7 subtasks: EmailDesignDocument JSON Schema, converter refactor, Figma/Penpot adapters, MJML import, HTML reverse engineering, Klaviyo + HubSpot ESP export). Phase 37 (golden reference library for AI judge calibration — 5 subtasks: expand golden component library with VML/MSO/ESP/innovation templates, reference loader & criterion mapping, wire into judge prompts, re-run pipeline & measure improvement, complete human labeling). Phase 38 (pipeline fidelity fix — 8 subtasks). Phase 39 (pipeline hardening — 7 subtasks). Phase 40 (converter snapshot & visual regression testing — 7 subtasks). Phase 41 (converter bgcolor continuity + VLM classification — 7 subtasks). Phase 42 (HTTP caching, smart polling & data fetching hardening — 7 subtasks). Phase 43 (judge feedback loop & self-improving calibration). Phase 44 (workflow hardening, CI gaps & operational maturity — 12 subtasks). Phase 45 (scheduling, notifications & build debounce — 6 subtasks). Phase 46 (provider resilience & connector extensibility — 5 subtasks: credential pool with rotation/cooldowns, LLM key rotation, ESP key rotation, credential health dashboard, dynamic ESP connector discovery via plugin system). Phase 47 (VLM visual verification loop & component library expansion — 10 subtasks: section screenshot cropping, VLM section-by-section diff, deterministic correction applicator, verification loop orchestrator, pipeline integration, component gap analysis 89→150+, extended matcher scoring, custom component generation AI fallback, verification tests, diagnostic trace enhancement; fidelity ladder: 85%→93%→97%→99%).

---

## Phase 48 — Agent Pipeline DAG, Adversarial Quality Loops & Cross-Repo Pattern Adoption

> **The agent pipeline is sequential and self-evaluating.** Today, a blueprint run fires agents one-by-one (Scaffolder → DarkMode → Accessibility → Personalisation → Content → CodeReviewer → VisualQA). Independent agents that *could* run in parallel (DarkMode, Accessibility, Personalisation) wait for each other. Inter-agent context flows through loose `AgentHandoff` objects with no schema enforcement. The same LLM that generates output also evaluates it — inherent self-evaluation bias. Meanwhile, the Scaffolder generates free-form HTML with no structural guarantee that the output maps to existing components, causing reliability variance across runs.
>
> **This phase adopts proven patterns from 6 open-source projects** scanned in `repos_to_scan/`:
> - **agent-teams-lite** → DAG-based pipeline with parallel execution and typed artifact passing
> - **adversarial-dev** → Separate evaluator agent eliminates self-evaluation bias; quality contracts between pipeline stages
> - **json-render** → Scaffolder emits a constrained component tree (JSON) instead of free-form HTML, compiled deterministically
> - **evals-skills** → Meta-evaluation of QA checks (FP/FN rates), synthetic adversarial email generation for calibration
> - **mcp2cli** → Response caching and schema compression for MCP tool calls (96-99% token overhead reduction)
> - **cognee** → Knowledge graph proactive QA: "component X broke in client Y" → auto-warn before agent runs
>
> **Infrastructure reuse:** `BaseAgentService` (base.py:47) provides `process()`, `to_handoff()`. `ScaffolderPipeline` (pipeline.py:53) has 3-pass structured output. `call_with_fallback()` (fallback.py:164) handles provider cascading. `AgentHandoff` carries inter-agent state. Blueprint run system orchestrates agent sequences. Eval framework (`app/ai/agents/evals/`) has judges, synthetic data, calibration. MCP server (`app/mcp/`) has 17 tools. Knowledge graph (`app/knowledge/graph/`) has Cognee provider. QA engine (`app/qa_engine/`) has 11 checks + chaos engine.
>
> **Why now:** Phases 0–47 built the vertical capabilities. Phase 48 transforms *how* those capabilities compose — making the platform faster (parallel execution), more reliable (adversarial evaluation + component-tree generation), and self-improving (meta-evaluation + proactive knowledge).

- [x] ~~48.1 Pipeline DAG schema and template registry~~ DONE
- [x] ~~48.2 Parallel agent executor with topological ordering~~ DONE
- [x] 48.3 Typed artifact protocol for inter-agent data flow
- [x] ~~48.4 Adversarial evaluator agent~~ DONE
- [x] ~~48.5 Quality contracts and stage gates~~ DONE
- [x] ~~48.6 Email component tree JSON schema~~ DONE
- [x] ~~48.7 Scaffolder component-tree generation mode~~ DONE
- [x] ~~48.8 Component tree deterministic compiler~~ DONE
- [x] ~~48.9 QA check meta-evaluation framework~~ DONE
- [x] ~~48.10 Synthetic adversarial email generator~~ DONE
- [x] ~~48.11 MCP response caching and schema compression~~ DONE
- [x] ~~48.12 Knowledge graph proactive QA pipeline~~ DONE
- [x] ~~48.13 Agent execution hook system with profiles~~ DONE

- [ ] **Phase 49 — Design-Sync Converter Structural Fidelity** (see below)

---

### ~~48.1 Pipeline DAG Schema and Template Registry~~ `[Backend]` DONE

**What:** Define agent pipelines as directed acyclic graphs (DAGs) where nodes are agents and edges are data dependencies. Store named pipeline templates in a registry with YAML definitions. Replace the current hard-coded sequential agent list in blueprint runs.
**Why:** The sequential pipeline wastes time — DarkMode, Accessibility, and Personalisation are independent and should run concurrently. A DAG makes dependencies explicit and enables automatic parallelism. Borrowed from **agent-teams-lite** which uses DAG-based phase orchestration with pluggable agents.
**Implementation:**
- Create `app/ai/pipeline/` package with `__init__.py`
- `app/ai/pipeline/dag.py`:
  - `PipelineNode(agent_name: str, tier: TaskTier, inputs: list[str], outputs: list[str], contract: str | None)` — frozen dataclass. `inputs`/`outputs` reference artifact names (e.g., `"html"`, `"qa_results"`, `"corrections"`)
  - `PipelineDag(name: str, nodes: dict[str, PipelineNode], description: str)` — validates acyclicity via Kahn's algorithm at construction time, raises `CyclicDependencyError` if edges form a cycle
  - `topological_levels() -> list[list[str]]` — returns nodes grouped by execution level (nodes in the same level have no inter-dependencies → safe to parallelize)
  - `validate() -> list[str]` — checks all input artifacts are produced by upstream nodes, all agent names exist in agent registry
- `app/ai/pipeline/registry.py`:
  - `PipelineRegistry` — singleton, loads YAML definitions from `app/ai/pipeline/templates/`
  - `get(name: str) -> PipelineDag` — retrieve by name
  - `register(dag: PipelineDag)` — add at runtime (for plugin-defined pipelines)
  - `list_all() -> list[str]` — available pipeline names
- Built-in pipeline templates (`app/ai/pipeline/templates/`):
  ```yaml
  # full-build.yaml
  name: full-build
  description: Complete email build with all agents
  nodes:
    scaffolder:
      agent: scaffolder
      tier: expensive
      inputs: []
      outputs: [html, build_plan]
      contract: html_valid
    dark_mode:
      agent: dark_mode
      tier: standard
      inputs: [html]
      outputs: [html]
    accessibility:
      agent: accessibility
      tier: standard
      inputs: [html]
      outputs: [html]
    personalisation:
      agent: personalisation
      tier: standard
      inputs: [html]
      outputs: [html]
    content:
      agent: content
      tier: standard
      inputs: [html]
      outputs: [html]
    code_reviewer:
      agent: code_reviewer
      tier: fast
      inputs: [html]
      outputs: [qa_results]
      contract: no_critical_issues
    visual_qa:
      agent: visual_qa
      tier: standard
      inputs: [html]
      outputs: [qa_results, corrections]
      contract: fidelity_above_threshold
  ```
  - Additional templates: `quick-fix.yaml` (dark_mode + outlook_fixer only), `qa-only.yaml` (code_reviewer + visual_qa), `design-import.yaml` (import_annotator → scaffolder → full pipeline)
- Config: `PIPELINE__DEFAULT_TEMPLATE` (default `"full-build"`), `PIPELINE__CUSTOM_DIR` (for user-defined YAML pipelines)
**Verify:** Parse `full-build.yaml` → 7 nodes, acyclic. `topological_levels()` returns `[[scaffolder], [dark_mode, accessibility, personalisation, content], [code_reviewer, visual_qa]]`. Cyclic edge → `CyclicDependencyError`. Unknown agent name → validation error. Registry loads all templates at startup. 14 tests.

---

### ~~48.2 Parallel Agent Executor with Topological Ordering~~ `[Backend]` DONE

**What:** Add `PipelineExecutor` that takes a `PipelineDag`, resolves execution order via `topological_levels()`, and runs agents at the same level concurrently with `asyncio.gather()`. Replaces the current sequential blueprint run loop.
**Why:** With 7 agents, the sequential pipeline takes ~7× single-agent latency. The DAG reveals that agents at the same topological level are independent — running them concurrently via `asyncio.gather()` reduces wall-clock time to ~3× (3 levels in full-build). Borrowed from **agent-teams-lite** fresh-context sub-agent model.
**Implementation:**
- `app/ai/pipeline/executor.py`:
  - `PipelineExecutor(dag: PipelineDag, artifact_store: ArtifactStore, settings: PipelineConfig)`:
    - `async execute(initial_artifacts: dict[str, Any], run_id: str) -> PipelineResult`
    - For each topological level:
      1. Collect nodes at this level
      2. For each node, resolve input artifacts from `ArtifactStore`
      3. `asyncio.gather(*[_run_node(node, inputs) for node in level_nodes])` — concurrent execution
      4. Store output artifacts in `ArtifactStore`
      5. If node has `contract`, validate via `ContractValidator` (48.5) — fail-fast on violation
    - `_run_node(node: PipelineNode, inputs: dict[str, Any]) -> dict[str, Any]`:
      - Resolve agent service from agent registry (`get_scaffolder_service()`, etc.)
      - Build request from artifacts (adapter per agent type)
      - Call `agent.process(request)` or `agent.process(request, context_blocks)`
      - Extract outputs via `agent.to_handoff()` → map to artifact names
      - Report to Cost Governor
    - Progress reporting: emit `pipeline.level.start`, `pipeline.node.start`, `pipeline.node.complete`, `pipeline.level.complete` structured log events
  - `PipelineResult(artifacts: dict[str, Any], trace: list[NodeTrace], total_duration_ms: int, levels_executed: int, nodes_executed: int, cost_tokens: int)`
  - `NodeTrace(agent_name: str, duration_ms: int, model_id: str, tokens_used: int, contract_passed: bool | None, error: str | None)`
- **Merge strategy for parallel HTML modifications:** When multiple agents at the same level produce `html` output (e.g., dark_mode + accessibility + personalisation all modify HTML):
  - Sequential merge: apply diffs in deterministic order (alphabetical by agent name)
  - Each agent receives the *same* input HTML (from previous level) and produces a *full* modified copy
  - `_merge_html_outputs(base_html: str, outputs: dict[str, str]) -> str` — unified diff3 merge. On conflict: last-writer-wins with structured log warning
- **Checkpoint integration:** After each level completes, fire checkpoint via existing `PipelineCheckpointCallback` (pipeline.py:213). On resume, skip completed levels.
- Wire into `app/email_engine/blueprints/` — `BlueprintRunner` gets new `use_dag: bool` flag (default `False`, feature-flagged). When `True`, delegates to `PipelineExecutor` instead of sequential loop.
- Config: `PIPELINE__ENABLED` (default `false`), `PIPELINE__MAX_CONCURRENT_AGENTS` (default `5`, caps `asyncio.gather` semaphore), `PIPELINE__MERGE_STRATEGY` (`"sequential"` | `"diff3"`, default `"sequential"`)
**Verify:** Execute `full-build` DAG with mock agents → 3 levels, 7 nodes. Level 2 runs 4 agents concurrently (verify via timing). Checkpoint after level 1 → resume skips scaffolder. HTML merge with 3 parallel agents produces valid combined output. Semaphore caps concurrent agents. Node failure → `PipelineResult` includes error trace, remaining nodes at that level still complete. 16 tests.

---

### ~~48.3 Typed Artifact Protocol for Inter-Agent Data Flow~~ `[Backend]` DONE

**What:** Replace loose `AgentHandoff` dict passing with a typed artifact system. Each artifact has a schema, validation, and lifecycle. An `ArtifactStore` manages artifacts during a pipeline run.
**Why:** Current `AgentHandoff` carries `html`, `confidence`, `qa_passed`, `decisions`, `warnings`, `component_refs` as untyped fields. Agents access whatever they want with no contract enforcement. Typed artifacts make data dependencies explicit and enable the DAG executor to validate artifact availability before running a node. Borrowed from **agent-teams-lite** pluggable artifact persistence (engram/openspec/hybrid).
**Implementation:**
- `app/ai/pipeline/artifacts.py`:
  - `Artifact(name: str, data: Any, produced_by: str, produced_at: datetime, schema_version: str)` — frozen dataclass
  - Concrete artifact types (all frozen dataclasses):
    - `HtmlArtifact(html: str, sections: list[str] | None = None)` — the email HTML
    - `BuildPlanArtifact(plan: EmailBuildPlan)` — scaffolder structured output
    - `QaResultArtifact(results: list[QACheckResult], passed: bool, score: float)` — QA check output
    - `CorrectionArtifact(corrections: list[SectionCorrection], applied: int, skipped: int)` — VLM corrections
    - `DesignTokenArtifact(tokens: DesignTokens)` — design system tokens
    - `ScreenshotArtifact(screenshots: dict[str, bytes])` — rendered screenshots
    - `EvalArtifact(verdict: str, feedback: str, score: float)` — adversarial eval output (48.4)
  - `ArtifactStore`:
    - In-memory `dict[str, Artifact]` during pipeline run
    - `put(name: str, artifact: Artifact)` — stores artifact, validates against expected type
    - `get(name: str, expected_type: type[T]) -> T` — retrieves with type check, raises `ArtifactNotFoundError`
    - `get_optional(name: str, expected_type: type[T]) -> T | None` — graceful miss
    - `snapshot() -> dict[str, str]` — serializable summary for checkpoint persistence
    - Optional Redis persistence: `async persist(run_id: str)` / `async restore(run_id: str)` for cross-process resume
  - `ArtifactAdapter` protocol — each agent implements adapter that converts `ArtifactStore` inputs → agent request and agent response → artifacts:
    - `adapt_inputs(store: ArtifactStore) -> AgentRequest`
    - `adapt_outputs(response: AgentResponse, store: ArtifactStore) -> None`
  - Built-in adapters for all 10 agents in `app/ai/pipeline/adapters/` (one file per agent)
- **Migration:** `AgentHandoff.to_artifacts() -> dict[str, Artifact]` bridge method for backward compat. `Artifact.to_handoff() -> AgentHandoff` reverse bridge. Both deprecated — new code uses artifacts directly.
**Verify:** Store `HtmlArtifact` → retrieve with type check → correct. Wrong type → `TypeError`. `ArtifactNotFoundError` on missing. Adapter for scaffolder converts `ScaffolderResponse` → `HtmlArtifact` + `BuildPlanArtifact`. Adapter for code_reviewer converts `HtmlArtifact` → `CodeReviewRequest`. Snapshot → restore roundtrip. 18 tests.

---

### ~~48.4 Adversarial Evaluator Agent `[Backend]`~~ DONE

**What:** New `EvaluatorAgentService` extending `BaseAgentService` that evaluates another agent's output against the original brief and quality criteria. Returns accept/revise/reject verdict with structured feedback. Uses a *different* model from the generator to eliminate self-evaluation bias.
**Why:** Currently, the Code Reviewer and Visual QA agents evaluate the platform's own output using the same model family. This creates self-evaluation bias — the same model that generated a pattern is more likely to approve it. Borrowed from **adversarial-dev** which uses a Planner/Generator/Evaluator triad where the Evaluator is structurally separated from the Generator. Research shows adversarial evaluation catches 30-40% more issues than self-evaluation.
**Implementation:**
- `app/ai/agents/evaluator/`:
  - `service.py` — `EvaluatorAgentService(BaseAgentService)`:
    - `agent_name = "evaluator"`, `default_tier = TaskTier.STANDARD`
    - Override `_get_model_tier()` to *always* use a different provider than the generator. If generator used `anthropic:claude-sonnet`, evaluator uses `openai:gpt-4o` (configurable via `AI__EVALUATOR_PROVIDER`). If same provider, use different model tier.
    - `async evaluate(original_brief: str, agent_name: str, agent_output: str, quality_criteria: list[str]) -> EvalVerdict`
    - Pipeline: build prompt with brief + agent output + criteria → LLM call → parse structured JSON response
  - `prompt.py` — System prompt: "You are a critical email quality evaluator. You did NOT generate this HTML. Your role is to find defects the generator missed. Evaluate against the criteria and original brief."
  - `schemas.py`:
    - `EvalVerdict(verdict: Literal["accept", "revise", "reject"], score: float, issues: list[EvalIssue], feedback: str, suggested_corrections: list[str])`
    - `EvalIssue(severity: Literal["critical", "major", "minor"], category: str, description: str, location: str | None)`
  - `skill-versions.yaml` — initial skill version
- **Integration with DAG:**
  - Evaluator is an optional node in pipeline DAGs. `full-build-adversarial.yaml` adds evaluator after scaffolder and after the parallel agent level
  - On `"revise"` verdict: re-run the failing agent with evaluator feedback injected as prompt amendment (up to `PIPELINE__MAX_REVISIONS`, default 2)
  - On `"reject"` verdict: pipeline fails with structured error
  - On `"accept"`: proceed to next level
- **Eval criteria per agent** (loaded from `app/ai/agents/evaluator/criteria/`):
  - `scaffolder.yaml`: structural completeness, table-based layout, slot coverage, design token application
  - `dark_mode.yaml`: media query presence, color contrast, prefers-color-scheme support
  - `accessibility.yaml`: WCAG 2.1 AA compliance, alt text quality, semantic structure
  - Generic fallback: HTML validity, no XSS vectors, no console errors
- Config: `AI__EVALUATOR_ENABLED` (default `false`), `AI__EVALUATOR_PROVIDER` (default `""` = auto-select different provider), `AI__EVALUATOR_CRITERIA_DIR` (default `app/ai/agents/evaluator/criteria/`), `PIPELINE__MAX_REVISIONS` (default `2`)
**Verify:** Mock evaluator returns `"revise"` with 2 issues → agent re-runs with feedback injected. Second pass returns `"accept"` → pipeline proceeds. `"reject"` → pipeline fails with `EvalVerdict` in error. Different-provider enforcement: generator=anthropic → evaluator≠anthropic. Criteria loading from YAML. No evaluator configured → pipeline unchanged. 14 tests.

---

### ~~48.5 Quality Contracts and Stage Gates~~ `[Backend]` DONE

**What:** Define quality contracts that run between pipeline stages. A contract is a set of assertions (check name, threshold, required patterns) that an agent's output must pass before artifacts propagate to the next DAG level.
**Why:** Without contracts, a broken output (e.g., Scaffolder emitting invalid HTML or DarkMode stripping all colors) propagates through the entire pipeline, wasting tokens on agents that process garbage. Stage gates catch failures early. Borrowed from **adversarial-dev** sprint contracts which enforce acceptance criteria between agent phases with file-based communication.
**Implementation:**
- `app/ai/pipeline/contracts.py`:
  - `Contract(name: str, assertions: list[Assertion])` — frozen dataclass
  - `Assertion(check: str, operator: Literal[">=", "<=", "==", "contains", "not_contains"], threshold: Any)`
    - Built-in checks: `html_valid` (parseable HTML), `min_size` (bytes), `max_size` (bytes), `has_table_layout` (no div/p layout), `dark_mode_present` (prefers-color-scheme media query), `no_critical_qa` (no critical QA issues), `fidelity_above` (float), `no_xss` (sanitization check)
  - `ContractValidator`:
    - `async validate(contract: Contract, artifacts: ArtifactStore) -> ContractResult`
    - `ContractResult(passed: bool, failures: list[AssertionFailure], duration_ms: int)`
    - `AssertionFailure(assertion: Assertion, actual_value: Any, message: str)`
  - Contract definitions stored in pipeline YAML (see 48.1 `contract` field on nodes)
  - Predefined contract library (`app/ai/pipeline/contracts/`):
    - `html_valid.yaml`: parseable, min 100 bytes, max 102400 bytes, has `<table>` root
    - `no_critical_issues.yaml`: QA results have zero `severity=critical` findings
    - `fidelity_above_threshold.yaml`: visual QA fidelity score >= 0.85 (configurable)
- **Integration:** `PipelineExecutor` (48.2) checks contract after each node. On failure:
  1. If `PIPELINE__CONTRACT_RETRY` enabled: re-run agent (up to 1 retry)
  2. If retry fails or disabled: emit `pipeline.contract.failed` event, mark node as failed, skip downstream dependents
  3. `PipelineResult` includes `contract_failures: list[ContractFailure]`
- Config: `PIPELINE__CONTRACT_RETRY` (default `true`), `PIPELINE__CONTRACT_STRICT` (default `false` — when `true`, any contract failure aborts entire pipeline)
**Verify:** `html_valid` contract passes on valid email HTML. `html_valid` fails on `<p>broken` fragment. `no_critical_issues` fails when QA results contain critical finding. Contract retry: first attempt fails → re-run → second attempt passes → proceeds. Strict mode: failure → pipeline aborts. Assertion operators: `>=`, `<=`, `contains` all work. 12 tests.

---

### 48.6 Email Component Tree JSON Schema `[Backend]`

**What:** Define a formal JSON Schema for representing an email as a tree of component references. Root `EmailTree` contains metadata + ordered `sections[]`. Each section references a component slug from the manifest and provides slot fills + style overrides.
**Why:** The Scaffolder currently generates free-form HTML — every run can produce structurally different output for the same brief. A component tree constrains output to existing, tested components, making generation deterministic and reliable. Borrowed from **json-render** which generates UI from prompts constrained to predefined components, achieving guardrailed generative output.
**Implementation:**
- `app/components/tree_schema.py`:
  - `EmailTree(metadata: TreeMetadata, sections: list[TreeSection])` — Pydantic model
  - `TreeMetadata(subject: str, preheader: str, design_tokens: DesignTokens, template_id: str | None)`
  - `TreeSection(component_slug: str, slot_fills: dict[str, SlotValue], style_overrides: dict[str, str], children: list[TreeSection] | None = None, custom_html: str | None = None)`
  - `SlotValue` = union of `TextSlot(text: str, tag: str)`, `ImageSlot(src: str, alt: str, width: int, height: int)`, `ButtonSlot(text: str, href: str, bg_color: str, text_color: str)`, `HtmlSlot(html: str)`
  - Validation:
    - `component_slug` must exist in `component_manifest.yaml` (cross-reference validation)
    - `slot_fills` keys must match slot definitions for that component
    - `style_overrides` values must be valid CSS property:value pairs (regex check, not full CSS parser)
    - `custom_html` only allowed when `component_slug == "__custom__"` (fallback for unmatched sections)
  - JSON Schema export: `EmailTree.model_json_schema()` → published as MCP resource (`email-tree-schema`)
- `app/components/schemas/email-tree.json` — generated JSON Schema file for external tooling
- Wire into MCP resources (`app/mcp/resources.py`): add `email_tree_schema` resource alongside existing `css_ontology` and `hub_capabilities`
**Verify:** Valid tree with 5 sections → passes validation. Unknown `component_slug` → `ValidationError`. Wrong slot name → `ValidationError`. `custom_html` without `__custom__` slug → error. JSON Schema export matches Pydantic model. MCP resource returns schema. 10 tests.

---

### ~~48.7 Scaffolder Component-Tree Generation Mode~~ `[Backend]` DONE

**What:** Add a `"tree"` output mode to `ScaffolderService` where the 3-pass pipeline produces an `EmailTree` JSON structure instead of raw HTML. The layout pass selects components, the content pass fills slots, the design pass applies tokens.
**Why:** Free-form HTML generation has ~85-95% structural reliability. Component-tree mode constrains the LLM to selecting from 150+ tested components and filling typed slots — bringing structural reliability to ~99%. The tree is then compiled deterministically (48.8). Borrowed from **json-render** guardrailed generation pattern.
**Implementation:**
- Modify `app/ai/agents/scaffolder/pipeline.py`:
  - `ScaffolderPipeline.__init__()` gains `output_mode: Literal["html", "tree"] = "html"` parameter
  - **Layout pass (tree mode):** System prompt includes full component manifest as JSON (slug, category, slot definitions). LLM returns `{"sections": [{"component_slug": "hero-full-width", "visibility": true}, ...]}` instead of `TemplateSelection`
  - **Content pass (tree mode):** For each section, LLM fills slots constrained to the component's slot definitions. System prompt: "Fill these slots for component `{slug}`. Available slots: {slot_defs}. Return JSON: {slot_name: slot_value}."
  - **Design pass:** Unchanged — returns `DesignTokens` which become `TreeMetadata.design_tokens`
  - New method: `async execute_tree(brief: str, brand_config: dict | None = None) -> EmailTree` — calls the 3 passes in tree mode, assembles `EmailTree`
  - **Confidence scoring:** If LLM picks a component with `< custom_component_confidence_threshold` match score (from matcher), flag section for `__custom__` fallback
- Modify `app/ai/agents/scaffolder/service.py`:
  - `ScaffolderService._process_structured()` checks `request.output_mode`. If `"tree"`: call `pipeline.execute_tree()` → compile via `TreeCompiler` (48.8) → QA → return
  - `ScaffolderRequest` schema gains `output_mode: Literal["html", "tree"] = "html"` field
  - `ScaffolderResponse` gains `tree: dict | None = None` field (serialized `EmailTree` when tree mode used)
- **Component manifest injection:** `_build_component_manifest_prompt() -> str` — reads `component_manifest.yaml`, formats as JSON array of `{slug, category, slots: [{name, type, required}]}`. Estimated ~8K tokens for 150 components — fits within scaffolder budget.
- Config: `AI__SCAFFOLDER_TREE_MODE` (default `false`), `AI__SCAFFOLDER_TREE_MANIFEST_BUDGET` (default `8000` tokens)
**Verify:** Tree mode produces valid `EmailTree` with sections referencing real component slugs. Slot fills match component definitions. Unknown component from LLM → validation error caught, falls back to `__custom__`. HTML mode unchanged (regression). Design tokens propagated to `TreeMetadata`. 12 tests.

---

### ~~48.8 Component Tree Deterministic Compiler `[Backend]`~~ DONE

**What:** Add `TreeCompiler` that walks an `EmailTree` and produces complete email HTML by resolving each section to its component template, filling slots, applying style overrides, and wrapping in the email document structure.
**Why:** The tree-to-HTML compilation is 100% deterministic — no LLM involved. This means identical `EmailTree` input always produces identical HTML output, enabling caching, diffing, and reliable regression testing. The LLM's job is reduced to *what to build* (component selection + content), not *how to build it* (HTML structure).
**Implementation:**
- `app/components/tree_compiler.py`:
  - `TreeCompiler(manifest: ComponentManifest, template_dir: Path)`:
    - `compile(tree: EmailTree) -> CompiledEmail`
    - Per section:
      1. Load component HTML template from `email-templates/components/{slug}.html`
      2. Parse `data-slot` attributes in template
      3. Fill each slot: `TextSlot` → HTML-escaped text in appropriate tag, `ImageSlot` → `<img>` with attributes, `ButtonSlot` → `<a>` with inline styles, `HtmlSlot` → raw injection (sanitized)
      4. Apply `style_overrides` as inline CSS on the component's root element
      5. Apply `DesignTokens` from metadata (colors, fonts, spacing) as CSS variable replacement
    - For `__custom__` sections: use `custom_html` field directly (already generated by 47.8 `CustomComponentGenerator`)
    - Wrap sections in email document boilerplate: `<!DOCTYPE>`, `<html>`, `<head>` (with preheader, viewport meta), `<body>`, outer table wrapper
    - MSO conditional injection: add `<!--[if mso]>` wrappers per platform requirements
    - Dark mode: inject `prefers-color-scheme` media query block from `DesignTokens.dark_palette`
  - `CompiledEmail(html: str, sections_compiled: int, custom_sections: int, compilation_ms: int)`
  - **Slot sanitization:** `TextSlot` content is HTML-entity-escaped. `HtmlSlot` runs through existing `_post_process()` XSS sanitizer. `ButtonSlot.href` validated as safe URL scheme (`http`, `https`, `mailto`, `tel`).
- **Caching:** Compiled templates are cached in-memory per `(slug, slot_hash, override_hash)` tuple. Cache invalidated on component template file change (file mtime check).
**Verify:** Compile tree with 5 sections → valid email HTML with all slots filled. `hero-full-width` component has correct `<img>` from `ImageSlot`. Style override `{"background-color": "#FF0000"}` applied to root element. `__custom__` section uses provided HTML. XSS in `HtmlSlot` → sanitized. Dark mode media query present when `dark_palette` set. Cache hit on second identical compilation. 14 tests.

---

### 48.9 QA Check Meta-Evaluation Framework `[Backend]`

**What:** Run each of the 11 QA checks against the golden reference library (Phase 37) and synthetic adversarial emails (48.10) to measure false positive rate, false negative rate, precision, and recall per check. Output threshold tuning recommendations.
**Why:** The QA engine has 11 checks but no systematic way to know if they're calibrated correctly. A file_size check with a 100KB threshold might flag 20% of valid emails (high FP) while missing actually oversized ones with inlined images (FN). Meta-evaluation quantifies check quality so thresholds can be tuned empirically. Borrowed from **evals-skills** eval-audit and evaluator-validation patterns.
**Implementation:**
- `app/qa_engine/meta_eval.py`:
  - `MetaEvaluator(qa_service: QAService, golden_loader: GoldenReferenceLoader)`:
    - `async evaluate_all_checks() -> MetaEvalReport`
    - `async evaluate_check(check_name: str) -> CheckEvalResult`
    - Per check:
      1. Load golden reference library (Phase 37: 14+ templates with known-good labels)
      2. Load synthetic adversarial emails (48.10: emails designed to trigger specific check failures)
      3. Run QA check on both sets
      4. Compare QA results against ground-truth labels
      5. Compute: TP, FP, TN, FN, precision, recall, F1, specificity
  - `MetaEvalReport(checks: dict[str, CheckEvalResult], overall_f1: float, timestamp: datetime, recommendations: list[ThresholdRecommendation])`
  - `CheckEvalResult(check_name: str, tp: int, fp: int, tn: int, fn: int, precision: float, recall: float, f1: float, current_threshold: Any, recommended_threshold: Any | None)`
  - `ThresholdRecommendation(check_name: str, current: Any, recommended: Any, improvement_f1: float, reasoning: str)` — when FP > 10% or FN > 5%, suggest threshold adjustment
  - **Ground-truth labels:** Extend golden reference YAML files with per-check expected results:
    ```yaml
    # golden/mammut-duvet-day.yaml (existing + new section)
    expected_qa:
      file_size: pass
      accessibility: fail  # known: missing alt text on decorative image
      dark_mode: pass
      link_validation: pass
      ...
    ```
- `app/qa_engine/meta_eval_routes.py`:
  - `POST /api/v1/qa/meta-eval` — admin-only, triggers full meta-evaluation run
  - `GET /api/v1/qa/meta-eval/latest` — retrieve most recent report
- Integrate with existing `app/ai/agents/evals/qa_calibration.py` — feed `MetaEvalReport` into calibration loop
- Config: `QA__META_EVAL_ENABLED` (default `true`), `QA__META_EVAL_FP_THRESHOLD` (default `0.10`), `QA__META_EVAL_FN_THRESHOLD` (default `0.05`)
**Verify:** Run meta-eval on golden library with 14 templates → per-check precision/recall scores. File size check with intentionally low threshold → high FP rate detected → recommendation emitted. Accessibility check on template missing alt text → correctly labeled FN/TP. Admin-only endpoint enforced. Latest report retrieval. 10 tests.

---

### 48.10 Synthetic Adversarial Email Generator `[Backend]`

**What:** Generate emails specifically designed to trigger edge cases and failure modes in each QA check. These adversarial emails serve as the negative test set for meta-evaluation (48.9) and strengthen the chaos engine calibration.
**Why:** The golden reference library contains real-world "good" emails. To measure false negatives, we need emails with *known* defects — not random corruption (that's chaos engine's job), but targeted, realistic defects that a human reviewer would catch but automated checks might miss. Borrowed from **evals-skills** synthetic data generation patterns which generate targeted test cases per evaluation dimension.
**Implementation:**
- `app/qa_engine/synthetic_generator.py`:
  - `SyntheticEmailGenerator(base_templates: list[str])`:
    - `generate_adversarial_set() -> list[SyntheticEmail]` — produces ~50 emails across all check categories
    - `generate_for_check(check_name: str, count: int = 5) -> list[SyntheticEmail]`
  - `SyntheticEmail(html: str, expected_failures: dict[str, bool], defect_category: str, defect_description: str, difficulty: Literal["easy", "medium", "hard"])`
  - **Defect injection strategies per check:**

    | Check | Defect Strategy |
    |-------|----------------|
    | `file_size` | Inline base64 images pushing to 101KB, 102KB, 103KB boundary |
    | `accessibility` | Remove alt text from one image, set `color: #777` on `#fff` bg (1.9:1 contrast) |
    | `link_validation` | Insert `javascript:` href, broken tracking URL, mailto with injection |
    | `dark_mode` | Hardcode `color: #000` without `@media (prefers-color-scheme: dark)` override |
    | `image_optimization` | 2000×2000px image, missing width/height, non-retina hero |
    | `liquid_syntax` | Unclosed `{% if %}`, nested `{{ }}` in wrong context, Braze/SFMC syntax mix |
    | `personalisation` | Unescaped `%%first_name%%` in href, AMPscript in subject line |
    | `css_support` | `display: flex` (no fallback), `gap` property, `clip-path` |
    | `spam_score` | ALL CAPS subject, multiple exclamation marks, hidden text (font-size:0) |
    | `brand_compliance` | Off-brand hex color (#FF0000 instead of brand #E31937), wrong font |
    | `rendering_resilience` | No MSO conditionals, CSS Grid layout, SVG images |

  - **Base template mutation:** Start from golden templates (known-good), apply targeted mutations. This ensures defects are realistic (not garbage HTML).
  - Each generated email includes ground-truth labels (`expected_failures`) for meta-eval scoring
  - Output saved to `data/synthetic-adversarial/` as JSON manifest + HTML files
- Config: `QA__SYNTHETIC_COUNT_PER_CHECK` (default `5`), `QA__SYNTHETIC_OUTPUT_DIR` (default `data/synthetic-adversarial/`)
**Verify:** Generate for `accessibility` → 5 emails, each with specific a11y defect, `expected_failures["accessibility"] == True`. Base template is recognizable (not garbage). File size boundary email is exactly 101-103KB. Liquid syntax email has unclosed tag. All 11 checks have adversarial coverage. Total set ~55 emails. 12 tests.

---

### 48.11 MCP Response Caching and Schema Compression `[Backend]`

**What:** Add a response cache and schema compression layer to the MCP server. Cache responses for identical tool calls within a session. Compress frequently-used tool schemas to reduce per-call token overhead.
**Why:** MCP tool calls send full schemas with every invocation (~500-2000 tokens per tool). With 17 tools, that's up to 34K tokens of schema overhead per session. Repeated calls to `qa_check` on the same HTML waste additional tokens. Borrowed from **mcp2cli** which achieves 96-99% token overhead reduction through schema compression and response caching.
**Implementation:**
- `app/mcp/optimization.py`:
  - **Response cache:**
    - `MCPResponseCache(max_size: int = 100, ttl_seconds: int = 300)`
    - Cache key: `blake2b(tool_name + sorted(json(params)))` — deterministic hash of tool + params
    - Skip cache for tools with side effects: `run_agent`, `scaffolder_generate`, `dark_mode_apply` (write tools)
    - Cache-eligible tools: `qa_check`, `qa_full_run`, `search_knowledge`, `search_components`, `search_css_property`, `rendering_confidence`, `rendering_fidelity_report`, `template_search`, `estimate_cost` (read-only tools)
    - LRU eviction when `max_size` exceeded. TTL-based expiry for freshness.
    - Response includes `_cached: true` metadata flag
  - **Schema compression:**
    - `compress_schema(schema: dict) -> dict` — remove `description` fields from nested properties (keep top-level), collapse `anyOf` single-types, inline `$ref` to avoid repeated definitions
    - `SchemaRegistry` — pre-compressed schemas loaded at server startup. Original schemas available via `GET /mcp/schemas/{tool_name}` for clients that need full docs
    - Estimated savings: 500-2000 tokens → 100-400 tokens per tool = 60-80% reduction
  - **Batch tool calls:**
    - `batch_execute(calls: list[ToolCall]) -> list[ToolResult]` — execute multiple tool calls in one round-trip. Parallel execution for independent calls. Already-cached results returned immediately.
- Modify `app/mcp/server.py`:
  - Wrap `@server.tool()` handlers with cache decorator for eligible tools
  - Register compressed schemas as primary, full schemas as fallback
  - Add `batch_execute` tool
- Config: `MCP__CACHE_ENABLED` (default `true`), `MCP__CACHE_MAX_SIZE` (default `100`), `MCP__CACHE_TTL` (default `300`), `MCP__COMPRESS_SCHEMAS` (default `true`)
**Verify:** Call `qa_check` twice with same HTML → second call returns cached result with `_cached: true`. Different HTML → cache miss. TTL expiry → cache miss after 300s. Write tools (`run_agent`) never cached. Schema compression reduces `qa_check` schema from ~800 to ~200 tokens. `batch_execute` with 3 calls → 3 results in one round-trip. Cache eviction at max_size. 12 tests.

---

### 48.12 Knowledge Graph Proactive QA Pipeline `[Backend]`

**What:** Automatically extract email-specific failure patterns from QA runs into the knowledge graph as relationships. Before agent pipeline runs, traverse the graph for relevant warnings and auto-inject them into agent prompts as context amendments.
**Why:** The knowledge graph stores documents but doesn't capture *failure patterns* as structured relationships. When "component hero-full-width breaks in Outlook 2019 due to missing VML wrapper" is discovered during QA, that knowledge stays in the QA report. Next time an agent uses hero-full-width, it has no warning. Proactive QA turns past failures into future prevention. Borrowed from **cognee** ECL pipeline (Extract, Cognify, Load) for transforming unstructured data into actionable graph relationships.
**Implementation:**
- `app/knowledge/proactive_qa.py`:
  - **Extract phase** — `FailureExtractor`:
    - Listens to `qa_engine.check.failed` events (structured log hook)
    - Extracts: `(component_slug, email_client, failure_type, severity, description)` tuples
    - Deduplication: `blake2b(component + client + failure_type)` → skip if already in graph
  - **Cognify phase** — `FailureRelationshipBuilder`:
    - Creates graph edges: `Component --[FAILS_IN]--> EmailClient` with properties `{failure_type, severity, description, first_seen, last_seen, occurrence_count}`
    - Creates graph edges: `CSSProperty --[UNSUPPORTED_BY]--> EmailClient` (from CSS support check failures)
    - Updates `occurrence_count` and `last_seen` on repeated failures
    - Uses existing `app/knowledge/graph/cognee_provider.py` `GraphKnowledgeProvider.add_relationship()`
  - **Load phase** — `ProactiveWarningInjector`:
    - Before agent pipeline runs, query graph: "What known failures exist for the components and clients in this build?"
    - Input: list of component slugs (from EmailTree or build plan) + target email clients (from project config)
    - Query: `MATCH (c:Component)-[r:FAILS_IN]->(ec:EmailClient) WHERE c.slug IN $slugs AND ec.name IN $clients RETURN c, r, ec`
    - Output: `list[ProactiveWarning(component: str, client: str, failure: str, severity: str, suggestion: str)]`
    - Inject warnings into agent system prompts via existing prompt amendment mechanism (`app/ai/agents/knowledge_prefetch.py` pattern)
  - **Auto-suggestion generation:** For each warning, generate a 1-line suggestion: "Use VML wrapper for hero-full-width in Outlook" → extracted from past successful fixes in knowledge base
- `app/knowledge/proactive_qa_routes.py`:
  - `GET /api/v1/knowledge/proactive-warnings?components=hero-full-width,card-grid&clients=outlook-2019,gmail-web` — preview warnings for given components/clients
  - `GET /api/v1/knowledge/failure-graph?component=hero-full-width` — visualize failure relationships for a component
- Wire into `PipelineExecutor` (48.2): before executing level 1, query proactive warnings and inject into artifact store as `ProactiveWarningsArtifact`. Agent adapters (48.3) include warnings in system prompt.
- Config: `KNOWLEDGE__PROACTIVE_QA_ENABLED` (default `false`), `KNOWLEDGE__PROACTIVE_MAX_WARNINGS` (default `10`), `KNOWLEDGE__FAILURE_MIN_OCCURRENCES` (default `2` — only warn after pattern seen twice)
**Verify:** QA failure on `hero-full-width` in Outlook → relationship created in graph. Second failure → `occurrence_count` incremented. Query with matching component+client → warning returned. Query with non-matching → empty. Warning injected into scaffolder prompt amendment. Deduplication prevents duplicate graph edges. API endpoints return correct data. 12 tests.

---

### 48.13 Agent Execution Hook System with Profiles `[Backend]`

**What:** Add a hook system for agent pipeline execution with pre/post-agent hooks and configurable profiles (minimal, standard, strict). Hooks enable cost tracking, quality gates, pattern extraction, and observability without modifying agent code.
**Why:** The current pipeline has no extension points between agents. Adding observability, cost tracking, or custom validation requires modifying `BaseAgentService`. Hooks decouple cross-cutting concerns from agent logic. Borrowed from **everything-claude-code** which has 112 hook scripts with profile-based activation (minimal/standard/strict) and lifecycle events.
**Implementation:**
- `app/ai/hooks/`:
  - `registry.py` — `HookRegistry`:
    - `register(event: HookEvent, hook: HookFn, profile: HookProfile = "standard")` — register a hook for an event
    - `async fire(event: HookEvent, context: HookContext) -> list[HookResult]` — execute all hooks for event at current profile level
    - Events: `pre_agent`, `post_agent`, `pre_pipeline`, `post_pipeline`, `pre_level`, `post_level`, `contract_failed`, `artifact_stored`
    - `HookContext(agent_name: str | None, run_id: str, artifacts: ArtifactStore, pipeline_name: str, level: int | None, node_trace: NodeTrace | None, cost_tokens: int)`
    - `HookResult(hook_name: str, duration_ms: int, output: Any | None, error: str | None)`
  - `profiles.py` — `HookProfile = Literal["minimal", "standard", "strict"]`:
    - `minimal`: cost tracking only (fastest, ~0ms overhead per agent)
    - `standard`: cost tracking + structured logging + progress reporting (default)
    - `strict`: all of standard + adversarial evaluation (48.4) + contract enforcement + pattern extraction
  - **Built-in hooks** (`app/ai/hooks/builtin/`):
    - `cost_tracker.py` (`minimal`): Accumulates per-agent and per-pipeline token costs. Integrates with Cost Governor. Emits `pipeline.cost.update` event. At pipeline end: total cost, per-agent breakdown, budget remaining.
    - `structured_logger.py` (`standard`): Emits structured JSON logs for every hook event. Fields: `run_id`, `agent_name`, `event`, `duration_ms`, `tokens_used`, `model_id`. Compatible with existing `get_logger()` infrastructure.
    - `progress_reporter.py` (`standard`): Updates `ProgressTracker` (`app/core/progress.py`) with pipeline stage progress. Frontend polling picks this up via existing `use-progress.ts` hook.
    - `adversarial_gate.py` (`strict`): Triggers evaluator agent (48.4) as a `post_agent` hook. If verdict is `"reject"`, raises `HookAbortError` that stops the pipeline.
    - `pattern_extractor.py` (`strict`): After pipeline completes, analyzes agent traces for recurring patterns (same component always needs dark mode fixes, same CSS property always fails QA). Stores patterns in knowledge base for future proactive warnings (48.12).
  - `config.py`:
    - `HookConfig` Pydantic model: `profile: HookProfile = "standard"`, `custom_hook_dir: str = ""`, `disabled_hooks: list[str] = []`
- Wire into `PipelineExecutor` (48.2): `fire(pre_pipeline)` at start, `fire(pre_agent)`/`fire(post_agent)` around each agent call, `fire(post_pipeline)` at end.
- Config: `PIPELINE__HOOK_PROFILE` (default `"standard"`), `PIPELINE__DISABLED_HOOKS` (comma-separated list), `PIPELINE__CUSTOM_HOOK_DIR` (default `""`)
**Verify:** `minimal` profile: only cost_tracker runs. `standard`: cost + logging + progress. `strict`: all hooks including adversarial gate. Custom hook registered → fires on correct event. Disabled hook → skipped. `HookAbortError` in strict mode → pipeline stops. Cost tracker accumulates correctly across 3 agents. Pattern extractor identifies repeated dark mode failures. 14 tests.

---

### Phase 48 — Summary

| Subtask | Scope | Dependencies | Track | Status |
|---------|-------|--------------|-------|--------|
| 48.1 Pipeline DAG schema & registry | `app/ai/pipeline/dag.py`, `registry.py` | None | A | DONE |
| 48.2 Parallel agent executor | `app/ai/pipeline/executor.py` | 48.1, 48.3, 48.5 | A | DONE |
| 48.3 Typed artifact protocol | `app/ai/pipeline/artifacts.py`, `adapters/` | None | A | DONE |
| 48.4 Adversarial evaluator agent | `app/ai/agents/evaluator/` | 48.3 | A | DONE |
| 48.5 Quality contracts & stage gates | `app/ai/pipeline/contracts.py` | 48.1 | A | DONE |
| 48.6 Component tree JSON schema | `app/components/tree_schema.py` | None | B | DONE |
| 48.7 Scaffolder component-tree mode | `app/ai/agents/scaffolder/` | 48.6 | B | DONE |
| 48.8 Component tree compiler | `app/components/tree_compiler.py` | 48.6 | B | DONE |
| 48.9 QA check meta-evaluation | `app/qa_engine/meta_eval.py` | 48.10 | C | DONE |
| 48.10 Synthetic adversarial generator | `app/qa_engine/synthetic_generator.py` | None | C | DONE |
| 48.11 MCP response cache & compression | `app/mcp/optimization.py` | None | D | DONE |
| 48.12 Knowledge graph proactive QA | `app/knowledge/proactive_qa.py` | None | D | DONE |
| 48.13 Agent execution hook system | `app/ai/hooks/` | 48.2 | E | DONE |

> **Execution:** Five independent tracks, three with internal sequencing.
>
> **Track A (DAG pipeline + adversarial):** 48.1 + 48.3 + 48.5 (parallel, no inter-deps) → 48.2 (needs 48.1 + 48.3 + 48.5) → 48.4 (needs 48.3 for artifact protocol).
> **Track B (component tree):** 48.6 → 48.7 + 48.8 (parallel after schema).
> **Track C (meta-evaluation):** 48.10 → 48.9 (needs synthetic data for scoring).
> **Track D (infrastructure):** 48.11 + 48.12 (fully parallel, no deps).
> **Track E (hooks):** 48.13 (after 48.2 for pipeline integration points).
>
> Tracks A-D can all proceed in parallel. Track E starts after Track A completes 48.2.
>
> **Total new code:** ~3500 LOC Python + ~500 LOC YAML configs + ~200 LOC test fixtures. One new agent (evaluator). One new package (`app/ai/pipeline/`). No database migrations. All behind feature flags — zero behavior change when disabled.
>
> **Impact ladder:**
> - 48.1 + 48.2 alone → **~40% pipeline speedup** (parallel agent execution)
> - 48.4 + 48.5 → **~30% fewer post-pipeline defects** (early failure detection)
> - 48.6 + 48.7 + 48.8 → **~99% structural reliability** (constrained generation)
> - 48.9 + 48.10 → **quantified QA check quality** (no more guessing if thresholds are right)
> - 48.11 → **60-80% MCP token reduction** (cost savings at scale)
> - 48.12 → **proactive defect prevention** (learn from past failures)
> - 48.13 → **extensible pipeline observability** (hooks instead of code changes)

---

## Phase 49 — Design-Sync Converter Structural Fidelity

> **The converter pipeline produces structurally wrong HTML.** Despite 155 components, 47 phases of improvements, and VLM verification loops, converting a real Figma design (REFRAME 2025 — 12 logical sections) yields: 5 missing sections, 6 wrong component selections, placeholder text instead of actual content, wrong fonts/colors/sizes, and zero support for repeated-content patterns. The "5 reasons" list (5 identical icon+heading+body blocks inside one `#F1F4F9` container) is the canonical failure — the pipeline treats each as independent, loses 4 of 5, and matches the survivor to the wrong component.
>
> **Root causes identified via end-to-end audit:**
> 1. **No sibling pattern detection** — `layout_analyzer.py` classifies each section in isolation. `match_all()` matches each independently. No code anywhere detects that N consecutive sections share identical structure.
> 2. **No repeating-group rendering** — `component_renderer.py` renders exactly one template instance per `ComponentMatch`. No wrapper, no repetition, no container bgcolor.
> 3. **Token override regex targets only `<h[1-3]>` and `<p>` elements** — but ~50% of component templates use `<td>` for headings/body text. Those keep hardcoded defaults (`Arial`, `#333333`, `#555555`) regardless of what Figma extracted.
> 4. **Slot fill extraction loses content** — when N child sections are flattened into one `EmailSection`, texts/images pile up unordered. The slot filler grabs the first few and ignores the rest.
> 5. **File-level tokens include ALL emails in a shared Figma file** — `ExtractedTokens` has 254 colors and 25 font families from the entire design system, not scoped to the target email.
>
> **Infrastructure reuse:** `layout_analyzer.py:358` `_get_section_candidates()` already unwraps single-child wrappers. `component_matcher.py:1115` `_build_token_overrides()` already creates `TokenOverride` objects from `TextBlock` data. `component_renderer.py:296` `_apply_token_overrides()` does regex-based inline style replacement. `converter_service.py:696` rendering loop iterates `ComponentMatch` objects sequentially. `COMPONENT_SEEDS` has 151 components with slot definitions. Phase 48 Track B (`EmailTree` schema + `TreeCompiler`) provides the eventual deterministic compilation target.
>
> **Test data:** `data/debug/reframe/raw_figma.json` — Figma API response for REFRAME 2025 (node `2833:1491`, 124KB, 11 wrappers, 3608px total height). Reference HTML: `email-templates/reframe-2025.html`. Converter output: `/Users/Berzins/Desktop/test.html`. Validator results: `email-templates/training_HTML/for_converter_engine/reframe_jason.txt`. Pipeline audit: `docs/design-to-html-pipeline-audit.md`.
>
> **Can be executed before Phase 48.** Only 49.8 (EmailTree bridge) depends on 48.6. Subtasks 49.1–49.7 + 49.9 are fully independent.
>
> **Why now:** Phase 48 improves how agents compose downstream. But the design-sync converter is upstream — it produces the initial HTML that agents then refine. If the initial conversion is 40% wrong (missing sections, wrong components, placeholder text), no amount of downstream agent orchestration can recover. This phase fixes the foundation.

- [x] ~~49.1 Sibling pattern detector — repeated-content grouping~~ DONE
- [ ] 49.2 Repeating-group renderer — multi-instance template rendering
- [ ] 49.3 Section-to-component classification improvements
- [ ] 49.4 Token override element-type expansion
- [ ] 49.5 Per-node slot content extraction fidelity
- [ ] 49.6 Per-email token scoping from shared Figma files
- [ ] 49.7 CTA fidelity — button color/shape extraction
- [ ] 49.8 Design-sync → EmailTree bridge (connects to 48.6/48.8)
- [x] ~~49.9 Data-driven converter regression framework~~ DONE

---

### 49.1 Sibling Pattern Detector — Repeated-Content Grouping `[Backend]`

**What:** Add a new analysis pass between section extraction and component matching that detects N structurally similar consecutive sections and merges them into a single `RepeatingGroup`. This is the highest-impact single change — it fixes the "5 reasons" pattern and all similar repeated-content layouts (product grids, feature lists, testimonial rows, pricing columns).
**Why:** `layout_analyzer.py:358` `_get_section_candidates()` returns flat section lists. `match_all()` at `component_matcher.py:89` processes each independently. When Figma has 5 identical icon+heading+body child frames inside a wrapper, they either become 5 independent sections (if top-level) or get flattened into one section with 5 images + 10 texts (if inside a wrapper). Neither produces correct HTML. The reference email puts all 5 inside ONE `<table bgcolor="#F1F4F9">` using the `col-icon` component pattern.
**Figma structure (confirmed from `data/debug/reframe/raw_figma.json`):**
```
Wrapper [2] = 2833:1507 (mj-wrapper, 640x669, bg=#ffffff, 5 children)
  ├── 2833:1508 mj-section (576x135, bg=#f1f4f9)
  │     ├── mj-column (60x50) → mj-image 40x40 (icon)
  │     └── mj-column (452x111) → "Reason 1" (Helvetica/20) + body (Helvetica/18)
  ├── 2833:1517 mj-section (576x135, bg=#f1f4f9) → "Reason 2" + body
  ├── 2833:1526 mj-section (576x135, bg=#f1f4f9) → "Reason 3" + body
  ├── 2833:1535 mj-section (576x114, bg=#f1f4f9) → "Reason 4" + body
  └── 2833:1544 mj-section (576x130, bg=#f1f4f9) → "Reason 5" + body
```
All 5 are **direct siblings** inside 1 wrapper. Each has identical structure: 2 columns (icon 40x40 + text column with Subhead + body), same `#f1f4f9` bg, same fonts. Heights vary slightly (114-135px) — use 20px bucketing to tolerate this.
**Implementation:**
- `app/design_sync/sibling_detector.py` (new file, ~250 lines):
  - `SiblingSignature(image_count: int, text_count: int, button_count: int, has_heading: bool, column_layout: ColumnLayout, approx_height_bucket: int)` — frozen dataclass. Height bucketed to 20px granularity to tolerate minor size differences.
  - `RepeatingGroup(sections: list[EmailSection], container_bgcolor: str | None, container_padding: tuple[float, float, float, float] | None, pattern_component: str | None, repeat_count: int, group_confidence: float)` — frozen dataclass. `pattern_component` is a hint (e.g., `"col-icon"`) when all items match the same component type.
  - `detect_repeating_groups(sections: list[EmailSection], *, min_group_size: int = 2, max_gap_px: float = 40.0, similarity_threshold: float = 0.8) -> list[EmailSection | RepeatingGroup]`:
    1. Compute `SiblingSignature` for each section
    2. Sliding window: compare adjacent sections' signatures. If `_signature_similarity(a, b) >= threshold`, extend the current run.
    3. When a run of `>= min_group_size` similar sections is found, merge into `RepeatingGroup`. The container bgcolor comes from the parent frame's `fill_color` if available (from `DesignNode.fill_color` on the wrapper), or from the first section's `bg_color`.
    4. Return mixed list of `EmailSection` (unchanged singles) and `RepeatingGroup` (merged runs).
  - `_signature_similarity(a: SiblingSignature, b: SiblingSignature) -> float` — weighted Jaccard: image_count match (0.3), text_count match (0.25), button_count match (0.15), has_heading match (0.15), column_layout match (0.1), height_bucket match (0.05). Score 1.0 = identical structure.
  - Edge cases: skip DIVIDER/SPACER sections (don't merge separators). Allow one non-matching section inside a run if surrounded by ≥2 matching (gap tolerance). Sections with `classification_confidence < 0.3` are wildcards (match anything).
- Wire into `converter_service.py:_convert_with_components()` after `match_all()` call and before the rendering loop (~line 696):
  - Call `detect_repeating_groups(layout.sections)` to produce grouped section list
  - Pass `RepeatingGroup` objects through to the renderer (49.2)
- Add `RepeatingGroup` to `app/design_sync/figma/layout_analyzer.py` exports for type-checking
- Config: `DESIGN_SYNC__SIBLING_DETECTION_ENABLED` (default `true`), `DESIGN_SYNC__SIBLING_MIN_GROUP` (default `2`), `DESIGN_SYNC__SIBLING_SIMILARITY_THRESHOLD` (default `0.8`)
**Verify:** 5 identical icon+heading+body sections → grouped into 1 `RepeatingGroup(repeat_count=5)`. 3 product cards → `RepeatingGroup(repeat_count=3)`. Mixed sections (hero, text, 5 reasons, footer) → only the 5 reasons get grouped. DIVIDER between similar sections breaks the run. Single section → no grouping. Configurable thresholds respected. 14 tests.

---

### 49.2 Repeating-Group Renderer — Multi-Instance Template Rendering `[Backend]`

**What:** Extend `ComponentRenderer` to handle `RepeatingGroup` objects by rendering the inner component template N times and wrapping all instances in a container `<table>` with the group's background color and padding.
**Why:** `render_section()` at `component_renderer.py:85` takes exactly one `ComponentMatch` and produces one `RenderedSection`. There is no mechanism to render a template multiple times inside a wrapper. The "5 reasons" pattern requires rendering `col-icon.html` 5 times inside `<table bgcolor="#F1F4F9">`.
**Reference HTML target (from `email-templates/reframe-2025.html`):**
```html
<table role="presentation" class="reason-bg resptab" width="576" cellpadding="0"
       cellspacing="0" border="0" style="width: 576px; background-color: #f1f4f9"
       bgcolor="#f1f4f9">
  <!-- Reason 1 -->
  <tr><td style="padding: 20px 24px 0">
    <table>...<td width="40" valign="top"><!-- 40x40 icon --></td>
               <td valign="top"><!-- "Reason 1" heading + body --></td>...</table>
  </td></tr>
  <!-- Reason 2 --><tr><td style="padding: 16px 24px 0">...same pattern...</td></tr>
  <!-- Reasons 3-5 same -->
</table>
```
Each inner section is `<tr><td style="padding: 16px 24px 0">` (first item uses `20px` top). Container uses `width="576"` (not 640 — inset by 32px padding on each side).
**Implementation:**
- `app/design_sync/component_renderer.py`:
  - New method: `render_repeating_group(self, group: RepeatingGroup, matches: list[ComponentMatch]) -> RenderedSection`:
    1. For each `ComponentMatch` in `matches`, call existing `render_section(match)` to get individual `RenderedSection` objects
    2. Build container wrapper:
       ```html
       <!--[if mso]>
       <table role="presentation" width="{container_width}" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
       <![endif]-->
       <table role="presentation" class="{dark_mode_class}" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{group.container_bgcolor};">
         {rendered_sections joined with spacing rows}
       </table>
       <!--[if mso]>
       </td></tr></table>
       <![endif]-->
       ```
    3. Each inner rendered section's HTML is wrapped in `<tr><td style="padding:{item_padding}">...</td></tr>`
    4. `item_padding` derived from `group.sections[0].item_spacing` or default `16px 24px 0`
    5. Dark mode class auto-generated from bgcolor (e.g., `bgcolor_F1F4F9` → `reason-bg`) following the pattern in existing dark mode CSS generation
  - Return combined `RenderedSection(html=wrapped, component_slug="repeating-group", section_idx=group.sections[0].section_idx)`
- Modify rendering loop in `converter_service.py:_convert_with_components()` (~line 696):
  - When iterating the grouped section list from 49.1, check if item is `RepeatingGroup`
  - If yes: match each inner section via `match_section()`, then call `render_repeating_group(group, inner_matches)`
  - If no: existing `render_section(match)` path unchanged
- Handle component matching for group members: `match_section()` is called per-group-member individually, but with a hint from `RepeatingGroup.pattern_component` that biases matching toward the same component for all members (consistency).
**Verify:** 5-section `RepeatingGroup` with `col-icon` matches → single wrapped HTML with 5 `col-icon` instances inside `#F1F4F9` container. Container has MSO ghost table wrapper. Individual section slots filled correctly (each with its own text/image). Spacing between items matches `item_spacing`. Dark mode class generated for container bgcolor. Empty group (0 sections) → no output. Single-section group → rendered without extra wrapper. 12 tests.

---

### 49.3 Section-to-Component Classification Improvements `[Backend]`

**What:** Improve section classification and component matching to reduce wrong-component selection from ~60% to <15% on real designs. Add heuristics for distinguishing text-block from editorial, col-icon from article-card, full-width-image from image-block, and event-card from text-block.
**Why:** The converter matched 6/12 sections to the wrong component on the REFRAME 2025 test. Key confusions: intro text (1-col) classified as editorial-2 (2-col) because a nearby image got included; icon+text blocks classified as article-card instead of col-icon; full-width images falling to image-block (which adds spurious captions); event details missing the event-card extended matcher.
**REFRAME section-by-section mapping (Figma → correct component):**
```
[0] 2833:1492 hero image (640x419, no text)           → full-width-image (NOT image-block)
[1] 2833:1497 intro text + CTA (576x150, 1 col)       → text-block + button-filled (NOT editorial-2)
[2] 2833:1507 5 reasons (5× mj-section siblings)      → col-icon ×5 in RepeatingGroup (NOT col-2/article)
[3] 2833:1553 CTA "Grab your spot" (#ffbaf3)           → button-filled
[4] 2833:1561 speaker image (640x394, no text)         → full-width-image (NOT image-block)
[5] 2833:1566 event details (4 short texts, #f1f4f9)   → event-card (NOT text-block)
[6] 2833:1577 venue image (640x349, no text)           → full-width-image (NOT image-block)
[7] 2833:1582 "Can't make it live?" (2 texts)          → text-block
[8] 2833:1589 CTA "Register for livestream" (#06d5ff)  → button-filled
[9] 2833:1597 sponsors image (640x429, no text)        → full-width-image (NOT image-block)
[10] 2833:1602 footer (legal + social, bg=#f1f4f9)     → email-footer + social-icons
```
**Key heuristic fixes needed:**
- `col-icon`: image ≤60x60 + 1-3 texts → score 0.92 (beats article-card 0.9)
- `full-width-image`: 1 image + 0 texts + width ≥80% container → score 1.0 (beats image-block 0.7)
- `event-card`: 3+ short texts with date/time/location keywords → score 0.85
- `text-block` vs `editorial-2`: single-column layout + no side-by-side image → force text-block
**Reference component list** (from `reframe-2025.html` line 2): `email-shell, full-width-image, text-block, cta/button-filled, col-icon, event-card, social-icons, email-footer`
**Event-card reference HTML pattern** (from `reframe-2025.html:1068-1148`):
```html
<!-- 7. EVENT DETAILS — event-card component -->
<table class="reason-bg" width="100%" style="background-color: #f1f4f9">
  <tr><td class="dark-bg" style="padding: 30px 46px">
    <table>
      <tr><td data-slot="event_name" style="padding: 0 0 16px; font-size: 24px;">
        Join us at Vimeo REFRAME 2025</td></tr>
      <tr><td style="padding: 0 0 6px; font-size: 18px;">
        <strong>Date:</strong> October 23, 2025</td></tr>
      <tr><td style="padding: 0 0 6px; font-size: 18px;">
        <strong>Time:</strong> 9:30am – 6:30pm ET</td></tr>
      <tr><td style="font-size: 18px;">
        <strong>Location:</strong> Center 415, New York City</td></tr>
    </table>
  </td></tr>
</table>
```
Note: uses `<td>` with `data-slot="event_name"` (not `<h2>`), each detail in its own `<tr>` with `<strong>` labels, inside `#f1f4f9` card with `padding: 30px 46px`.
**Implementation:**
- `app/design_sync/component_matcher.py`:
  - Fix editorial-2 false positive (~line 305): add guard — only match `editorial-2` when column_groups >= 2 AND at least one column has both image AND text. Currently matches when `img_count >= 1 and text_count >= 2 and len(col_groups) >= 2`, but `col_groups` detection is too aggressive (adjacent image + text at different X positions = 2 groups).
  - New `col-icon` detector in `_score_extended_candidates()` (~line 356): match when `img_count == 1 AND image.width <= 60 AND image.height <= 60 AND text_count >= 1 AND text_count <= 3`. Score 0.92. Currently these fall through to `article-card` at 0.9 (which has no icon size check).
  - Fix `image-block` vs `full-width-image` (~line 250): when section has exactly 1 image, 0 texts, 0 buttons, and `image.width >= 0.8 * container_width`, prefer `full-width-image` (score 1.0) over `image-block` (score 0.7). `image-block` should only be used when caption text is present in the section.
  - Improve `event-card` extended matcher (~line 356): relax date pattern requirement — currently needs `_DATE_PATTERN` regex match which requires "Month DD" or "DD/MM" format. Add detection for structured event data: 3+ short text lines (< 50 chars each) containing keywords like "date", "time", "location", "where", "when", or containing time patterns like `\d{1,2}:\d{2}` or `\d{1,2}(am|pm)`.
  - Add `text-block` vs `editorial` disambiguation: if section has column_layout == `SINGLE` and all content is left-aligned text (no side-by-side image), force `text-block` regardless of image presence. Images inside single-column text sections are inline illustrations, not editorial columns.
- `app/design_sync/figma/layout_analyzer.py`:
  - Fix `_classify_section()` (~line 419): add `CONTENT` subtype hints in `EmailSection.content_roles` tuple — `("text-only",)`, `("text-with-icon",)`, `("editorial",)`, `("event-info",)` based on content analysis. These hints flow to the matcher as soft signals.
**Verify:** Single-column intro text with nearby image → `text-block` (not `editorial-2`). 40x40 icon + heading + body → `col-icon` (not `article-card`). Full-width image with no text → `full-width-image` (not `image-block`). Event details with "Date:", "Time:", "Location:" lines → `event-card`. Existing editorial-2 matches (real 2-col with image+text per column) unchanged. Existing article-card matches (large image + text) unchanged. 16 tests.

---

### 49.4 Token Override Element-Type Expansion `[Backend]`

**What:** Fix the token override regex system to target ALL elements carrying heading/body styles, not just `<h[1-3]>` and `<p>`. The override system must match `<td>`, `<a>`, `<span>`, and any element with semantic CSS classes like `hero-title`, `textblock-heading`, `product-title`.
**Why:** `_apply_token_overrides()` at `component_renderer.py:296` uses `_replace_heading_font()` (line 334) with regex `r"(<h[1-3]\b[^>]*style=\"[^\"]*?)font-family:\s*[^;\"]+\"`. This only matches `<h1>`, `<h2>`, `<h3>`. But ~50% of component templates use `<td class="hero-title" style="font-family: Arial...">` for headings. Same issue for body text — regex targets `<p>` only but templates use `<td class="textblock-body">`, `<td class="hero-subtitle">`, etc. Result: hardcoded template defaults (`Arial, sans-serif`, `#333333`, `#555555`) survive in the output.
**Confirmed from Figma data:** All REFRAME text nodes use `font=Helvetica/18` (body) and `font=Helvetica/20` (subheads) with `color=#000000`. The converter output has `font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` and `color: #333333` / `#555555` — these are the component template defaults from `editorial-2.html` and `text-block.html`, never overridden because the regex only targets `<h>` and `<p>` elements.
**Bug location:** `component_renderer.py:334` `_replace_heading_font()` pattern `r"(<h[1-3]\b..."` and `:340` `_replace_body_font()` pattern `r"(<p\b..."`. The fix must also cover `<td>`, `<th>`, `<a>`, `<span>` elements with semantic classes.
**Reference CSS classes used in `reframe-2025.html`** (all on `<td>` elements, NOT `<h>` or `<p>`):
- `class="dark-text"` — heading + body text elements (Helvetica/18-24px, color:#000000)
- `class="dark-bg"` — containers with background
- `class="footer-text"` / `class="footer-link"` — footer elements
- `class="cta-btn"` — CTA button table
- `class="reason-bg"` — #f1f4f9 containers
No component-specific classes like `textblock-heading` / `textblock-body` appear in the reference — the reference uses generic dark-mode classes directly on `<td>` elements with fully inline styles. The override regex must match `<td>` elements by either class OR by presence of `font-family`/`color` in their inline style.
**Implementation:**
- `app/design_sync/component_renderer.py`:
  - Define heading class patterns: `HEADING_CLASSES = {"hero-title", "textblock-heading", "artcard-heading", "product-title", "col-icon-heading", "event-name"}` (~10 classes across 155 components)
  - Define body class patterns: `BODY_CLASSES = {"hero-subtitle", "textblock-body", "artcard-body", "product-desc", "col-icon-body", "event-detail", "imgblock-caption"}` (~10 classes)
  - Rewrite `_replace_heading_font()` (line 334): two-pass replacement:
    1. Original `<h[1-6]>` regex (keep for components that do use heading elements)
    2. New: `r'(<(?:td|th|a|span|div)\b[^>]*class="[^"]*(?:HEADING_CLASS_PATTERN)[^"]*"[^>]*style="[^"]*?)font-family:\s*[^;"]+` where `HEADING_CLASS_PATTERN` is alternation of `HEADING_CLASSES`
  - Same two-pass approach for `_replace_heading_color()` (line 349), `_replace_body_font()` (line 340), `_replace_body_color()` (line 358)
  - Also replace font-size when a `font_size` token override is present (currently not handled at all — no `_replace_heading_size()` exists). Add `_replace_font_size(html, target_classes, new_size)` for both heading and body.
  - Add `_replace_bgcolor()` for section container background color — currently `bg_color` token override exists but is only applied as a `bgcolor` attribute. Add inline `style="background-color:..."` replacement for CSS-based backgrounds.
- Compile all regex patterns at module level (not per-call) for performance
**Verify:** Component with `<td class="hero-title" style="font-family: Arial">` + heading font override `Helvetica` → output has `font-family: Helvetica`. Component with `<p style="font-family: Arial">` still works (regression). Component with `<td class="textblock-body" style="color: #555555">` + body color override `#000000` → output has `color: #000000`. Component with no matching classes → unchanged. Font-size override applied when present. Bgcolor override applied to container. 14 tests.

---

### 49.5 Per-Node Slot Content Extraction Fidelity `[Backend]`

**What:** Fix text/image content extraction from Figma nodes so that all section content reaches the slot filler — no more "Section Heading" or "Image caption — describe the content for context." defaults when actual content exists in the design.
**Why:** The converter output has placeholder text in multiple sections. This happens because: (a) `_get_section_candidates()` at `layout_analyzer.py:358` flattens child frames into `EmailSection.texts` and `.images` lists, losing parent-child relationships; (b) `_build_slot_fills()` at `component_matcher.py` takes the first N items from these flat lists for slot filling, silently dropping extras; (c) when text extraction fails (empty `characters` field, or text inside nested groups), the slot gets the component template's default placeholder.
**Figma text extraction evidence (from `raw_figma.json`):** Text is in `node.characters` field, nested 4-5 levels deep. Example for Reason 1:
```
mj-wrapper > mj-section > mj-column > mj-text-Frame > Subhead (TEXT)
  characters: "Reason 1", style: {fontFamily: "Helvetica", fontSize: 20}
mj-wrapper > mj-section > mj-column > mj-text-Frame > text (TEXT)
  characters: "Learn how AI-powered workflows...", style: {fontFamily: "Helvetica", fontSize: 18}
```
Text extraction at `figma/service.py:1217` uses `node_data.get("characters")` — this works. The loss happens when `_get_section_candidates()` flattens the wrapper's 5 mj-sections into one EmailSection, dumping all 10 text nodes (5 headings + 5 bodies) into a single `texts` list. The slot filler grabs texts[0] and texts[1] for the first template instance and ignores texts[2..9].
**Reference slot fills (from `reframe-2025.html`)** — what correctly filled slots look like:
- `data-slot="body"`: "From bold ideas to big connections, REFRAME 2025 is where the future of video takes shape..." (not "Editorial heading" default)
- `data-slot="cta_text"`: "Register now" / "Grab your spot" / "Register for livestream" (not generic "CTA")
- `data-slot="event_name"`: "Join us at Vimeo REFRAME 2025" (not "Section Heading")
- `data-slot="image_alt"`: "5 reasons you don't want to miss REFRAME — Vimeo" (not "Full width image")
- `data-slot="icon_1_url"` through `data-slot="icon_5_url"`: each reason's 40x40 icon image
All text content exists in Figma `characters` fields — the issue is purely in extraction/assignment, not source data.
**Implementation:**
- `app/design_sync/figma/layout_analyzer.py`:
  - Enhance `_extract_text_blocks()` to walk child nodes recursively (currently stops at depth 1 in some cases). Track the parent-child hierarchy so texts maintain their grouping context.
  - Add `TextBlock.source_node_id: str` field — links each text back to its Figma node for debugging
  - Add `TextBlock.role_hint: str | None` — `"heading"`, `"body"`, `"label"`, `"cta"` based on font size relative to siblings (heading = largest font in group, body = second largest, label = smallest, cta = inside button-like container)
  - When extracting from a section with multiple child groups (like the 5 "reason" blocks), preserve the grouping: `EmailSection.content_groups: list[ContentGroup]` where `ContentGroup(texts: list[TextBlock], images: list[ImagePlaceholder], buttons: list[ButtonElement])`. Each content group corresponds to one visually distinct block within the section.
- `app/design_sync/component_matcher.py`:
  - `_build_slot_fills()` (~line 1050): use `content_groups` when available. For `col-icon` component: `groups[0].images[0]` → icon slot, `groups[0].texts[0]` → heading slot, `groups[0].texts[1]` → body slot. For repeating groups (49.1/49.2): each group maps to one template instance.
  - When `content_groups` is empty, fall back to current flat-list behavior
  - Log warning when slot fill falls back to template default (structured log: `design_sync.slot_fill.default_used`, fields: `section_idx`, `slot_name`, `component_slug`)
- `app/design_sync/component_renderer.py`:
  - In `_fill_slots()` (~line 143): when a `SlotFill.value` is empty string or matches known placeholder patterns (`"Section Heading"`, `"Image caption"`, `"Editorial heading"`, `"Lorem ipsum"`), log warning instead of silently using it
**Verify:** Figma section with heading "Join us at REFRAME 2025" → slot fill uses actual text (not "Section Heading"). Section with 5 child groups → `content_groups` has 5 entries. Deeply nested text (3 levels) still extracted. `role_hint` correctly assigns "heading" to largest font. Empty text node skipped. Slot fill default usage logged. 14 tests.

---

### 49.6 Per-Email Token Scoping from Shared Figma Files `[Backend]`

**What:** Scope extracted tokens to the target email frame instead of the entire Figma file. When a file contains multiple email designs (common in design system files), only extract colors/typography/spacing used within the target frame's subtree.
**Why:** `sync_tokens_and_structure()` at `figma/service.py:415` extracts tokens from the entire Figma file. The test file "The Ultimate Email Design System (Community)" has 254 colors and 25 font families across dozens of email designs. When the converter tries to pick the "right" font family for the REFRAME email, it sees `Inter`, `Helvetica`, `Courier New`, `Roboto`, `Open Sans`, etc. The global `convert_typography()` may pick the most-frequent font (Inter) instead of the one actually used in the target email (Helvetica).
**Confirmed from `data/debug/5/tokens.json`:** 254 colors, 234 typography entries across **25 font families** (Arial, Commissioner, Courier New, GT America Trial, Geist Mono, Georgia, Helvetica, Inter, Lucida Sans, Monument Grotesk, Noto Sans, Nunito Sans, Open Sans, Roboto, etc.). The REFRAME email uses **only Helvetica** (sizes 18 and 20). All other fonts are noise from other emails in the shared Figma file. Key design colors ARE present (`#C6FC6A` green CTA, `#F1F4F9` gray bg, `#000000` text) but buried among 254 entries. Scoping to the target frame subtree would reduce this to ~3 colors and 1 font family.
**Implementation:**
- `app/design_sync/figma/service.py`:
  - New method: `_scope_tokens_to_frame(tokens: ExtractedTokens, frame_node_ids: set[str], file_data: dict) -> ExtractedTokens`:
    1. Walk the target frame's subtree, collecting all `style` references (fill colors, text styles, effects)
    2. Filter `tokens.colors` to only those used in the subtree
    3. Filter `tokens.typography` to only those used in the subtree
    4. Filter `tokens.spacing` to only those used in the subtree
    5. Return scoped `ExtractedTokens`
  - Call `_scope_tokens_to_frame()` after global extraction when a specific `node_id` target is provided (which it always is for design-sync imports)
  - Preserve unscoped tokens as `ExtractedTokens.global_tokens: ExtractedTokens | None` for fallback
- `app/design_sync/converter_service.py`:
  - In `_convert_with_components()`: use scoped tokens for per-section overrides, fall back to global for design system variables (brand colors, etc.)
  - `_select_primary_font()` (~line 770): when scoped tokens have ≤ 3 font families, use the most-frequent one. When > 3, fall back to global most-frequent. This handles the common case where an email uses 1-2 fonts.
- Config: `DESIGN_SYNC__TOKEN_SCOPING_ENABLED` (default `true`)
**Verify:** Shared Figma file with 2 emails (Email A uses Helvetica, Email B uses Inter) → scoping to Email A produces tokens with Helvetica only. Single-email file → scoped tokens = global tokens. Scoped tokens preserve all colors used in target frame. Font frequency correctly identifies primary font. Fallback to global when scoping disabled. 10 tests.

---

### 49.7 CTA Fidelity — Button Color/Shape Extraction `[Backend]`

**What:** Extract button visual properties (background color, border radius, text color, border) from Figma nodes and apply them as token overrides to CTA components. Support multiple distinct CTAs per email with different styles.
**Why:** The REFRAME 2025 reference has 3 CTAs with distinct colors (`#c6fc6a` green, `#ffbaf3` pink, `#06d5ff` cyan), `border-radius: 6px`, and arrow icons. The converter produced 1 CTA with hardcoded `#e84e0f` orange, `border-radius: 25px` — all from the `button-filled.html` template defaults. Button node properties exist in Figma (`fills`, `cornerRadius`) but don't reach the rendered HTML.
**Figma CTA structure (from `raw_figma.json`):**
```
Wrapper [1] 2833:1497 — intro + CTA
  └── mj-button 2833:1503 (FRAME 576x48, fills=[{color: r=0.776 g=0.988 b=0.416}] = #c6fc6a)
        ├── mj-button-text 2833:1504 "Register now" (Helvetica/18, color=#000000)
        └── afterIcon-Frame 2833:1505 → afterIcon (RECTANGLE 17x17, arrow icon)

Wrapper [3] 2833:1553 — standalone CTA
  └── mj-button 2833:1557 (FRAME 576x48, fills=[{color}] = #ffbaf3)
        ├── mj-button-text 2833:1558 "Grab your spot" (Helvetica/18, color=#000000)
        └── afterIcon-Frame 2833:1559 → afterIcon (RECTANGLE 17x17)

Wrapper [8] 2833:1589 — standalone CTA
  └── mj-button (FRAME 576x48, fills=[{color}] = #06d5ff)
        ├── mj-button-text "Register for livestream" (Helvetica/18, color=#000000)
        └── afterIcon-Frame → afterIcon (RECTANGLE 17x17)
```
Button bg color is in `node.fills[0].color` (RGBA floats, convert to hex). Arrow icon is a child RECTANGLE node named `afterIcon` inside `afterIcon-Frame`. Each CTA is its own wrapper/section — the matcher needs to extract per-section button properties.
**Reference CTA HTML pattern** (from `reframe-2025.html:314-411`):
```html
<!--[if mso]>
  <v:roundrect href="..." style="height:48px;v-text-anchor:middle;width:200px;"
    arcsize="10%" fillcolor="#c6fc6a">
    <w:anchorlock/><center style="color:#000;font-family:Helvetica,Arial,sans-serif;font-size:18px">
      Register now &#9654;</center>
  </v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<table class="cta-btn" width="100%" style="background-color:#c6fc6a;border-radius:6px;">
  <tr>
    <td style="padding:13px 24px"><a data-slot="cta_url" href="..."
      style="color:#000;font-family:Helvetica,Arial,sans-serif;font-size:18px;font-weight:400;">
      <span data-slot="cta_text">Register now</span></a></td>
    <td align="right" style="padding:13px 24px 13px 0">
      <a href="..."><img src="reframe-assets/cta_arrow.png" alt="" width="17" height="17"/></a></td>
  </tr>
</table>
<!--<![endif]-->
```
Key patterns: VML `v:roundrect` with `fillcolor` for Outlook, `border-radius:6px` (not 25px), arrow icon in separate `<td align="right">`, `font-weight:400` (not bold). Same structure for all 3 CTAs, only `fillcolor`/`background-color` and text differ.
**Implementation:**
- `app/design_sync/figma/layout_analyzer.py`:
  - Enhance `ButtonElement` dataclass (~line 80): add `bg_color: str | None`, `text_color: str | None`, `border_radius: float | None`, `border_color: str | None`, `border_width: float | None`, `icon_url: str | None`
  - In `_extract_buttons()` (~line 600): read `fills[0].color` for bg_color, `cornerRadius` for border_radius, child text node's `fills[0].color` for text_color, `strokes` for border. Export any child image nodes as `icon_url`.
- `app/design_sync/component_matcher.py`:
  - In `_build_slot_fills()` for CTA-type sections: create `SlotFill` objects for `cta_bg_color`, `cta_text_color`, `cta_border_radius` from `ButtonElement` properties
  - In `_build_token_overrides()`: add `TokenOverride("background-color", ".cta-btn", button.bg_color)`, `TokenOverride("border-radius", ".cta-btn", f"{button.border_radius}px")`, `TokenOverride("color", ".cta-btn a", button.text_color)`
- `app/design_sync/component_renderer.py`:
  - In `_apply_token_overrides()`: handle CTA-specific overrides — replace `background-color`, `border-radius`, `color` on elements with class `cta-btn` and nested `<a>` tags
  - Handle VML roundrect: when `button.bg_color` is set, update `fillcolor` attribute on `<v:roundrect>` MSO conditional block
- Support multiple CTAs: each CTA section gets its own `ButtonElement` with its own colors. The component matcher creates per-section token overrides, so different CTAs naturally get different styles.
**Verify:** Button with Figma fill `#c6fc6a` → rendered `button-filled.html` has `background-color: #c6fc6a`. Three CTAs with different colors → each rendered with correct color. Border radius `6px` from Figma → overrides template default `25px`. Text color `#000000` applied to `<a>` inside CTA. VML `fillcolor` updated. Missing button properties → template defaults preserved. 12 tests.

---

### 49.8 Design-Sync → EmailTree Bridge (connects to 48.6/48.8) `[Backend]`

**What:** Add a converter output mode that produces an `EmailTree` (Phase 48.6 schema) instead of raw HTML. The design-sync pipeline performs section classification, component matching, and slot fill extraction — then emits a structured tree that Phase 48.8's `TreeCompiler` renders deterministically.
**Why:** The current pipeline has two separate rendering paths: `component_renderer.py` (regex-based slot filling and token override application — fragile) and the future `TreeCompiler` (48.8 — deterministic compilation from typed slot values). Bridging design-sync to `EmailTree` eliminates the regex rendering entirely for the design-sync path, getting deterministic HTML output for free.
**Implementation:**
- `app/design_sync/tree_bridge.py` (new file, ~200 lines):
  - `build_email_tree(layout: DesignLayoutDescription, matches: list[ComponentMatch | RepeatingGroup], tokens: ExtractedTokens, metadata: dict) -> EmailTree`:
    1. Build `TreeMetadata` from `tokens` (primary font, primary colors, preheader text from first PREHEADER section)
    2. For each `ComponentMatch`: create `TreeSection(component_slug=match.component_slug, slot_fills=_convert_slot_fills(match.slot_fills), style_overrides=_convert_token_overrides(match.token_overrides))`
    3. For each `RepeatingGroup`: create `TreeSection(component_slug="repeating-wrapper", children=[TreeSection(...) for each inner match], style_overrides={"background-color": group.container_bgcolor})`
    4. Convert `SlotFill` → typed `SlotValue` union (`TextSlot`, `ImageSlot`, `ButtonSlot`) based on slot name patterns
  - `_convert_slot_fills(fills: list[SlotFill]) -> dict[str, SlotValue]` — map slot names to typed values
  - `_convert_token_overrides(overrides: list[TokenOverride]) -> dict[str, str]` — map to CSS property:value pairs
- `app/design_sync/converter_service.py`:
  - Add `output_format: Literal["html", "tree"] = "html"` parameter to `convert_document()` and `_convert_with_components()`
  - When `output_format == "tree"`: after matching, call `build_email_tree()` instead of rendering. Return `ConversionResult` with `tree: dict` field (serialized `EmailTree`) and `html` compiled via `TreeCompiler` (if available from 48.8) or legacy renderer (fallback)
- Config: `DESIGN_SYNC__TREE_OUTPUT_ENABLED` (default `false` — requires 48.6 + 48.8 to be implemented first)
**Verify:** Design with 5 sections → `EmailTree` with 5 `TreeSection` objects. `RepeatingGroup` → `TreeSection` with `children`. Slot fills correctly typed (`ImageSlot` for images, `TextSlot` for text, `ButtonSlot` for CTAs). Token overrides converted to style_overrides dict. Tree validates against 48.6 JSON Schema. Roundtrip: tree → `TreeCompiler` → HTML produces valid email. Fallback to legacy renderer when `TreeCompiler` unavailable. 10 tests.

---

### ~~49.9 Data-Driven Converter Regression Framework~~ `[Backend]` DONE

**What:** Build a generic, manifest-driven regression test framework for the design-sync converter. Any email design can be added as a test case by dropping a directory with `raw_figma.json` + `expected.html` + `manifest.yaml`. The framework auto-discovers cases, runs the converter, and validates against both universal quality assertions (apply to ALL emails) and case-specific structural assertions (from the manifest). REFRAME 2025 is the first case, but the framework handles any email.
**Why:** The current 49.9 was REFRAME-specific — hardcoded section counts, hardcoded text strings, hardcoded colors. Adding a second email would require writing an entirely new test file. A data-driven framework means adding a new regression case is a 10-minute task (create directory, add Figma JSON, add reference HTML, write manifest YAML) with zero test code changes. The existing snapshot tests in `data/debug/` (MAAP, Starbucks, Mammut) should also be migrated into this framework.
**Implementation:**
- **Test case directory structure** (`data/debug/{case_name}/`):
  ```
  data/debug/reframe/
  ├── raw_figma.json      # Figma API response (already exists)
  ├── expected.html        # Hand-crafted reference HTML (already exists)
  ├── manifest.yaml        # Structural expectations (new)
  ├── structure.json       # Generated: parsed DesignFileStructure
  └── tokens.json          # Generated: extracted ExtractedTokens
  ```
- **Manifest schema** (`app/design_sync/tests/manifest_schema.py`):
  ```python
  class CaseManifest(BaseModel):
      name: str                                    # e.g., "reframe-2025"
      figma_file: str | None = None                # Figma file key
      figma_node: str | None = None                # Target node ID
      description: str = ""                        # What this case exercises

      # Structural expectations
      sections: SectionExpectations
      tokens: TokenExpectations | None = None
      ctas: list[CTAExpectation] = []
      required_content: list[str] = []             # Text that MUST appear in output
      forbidden_content: list[str] = []            # Placeholder text that must NOT appear

      # Pattern flags — which Phase 49 features this case exercises
      patterns: list[str] = []                     # e.g., ["repeating-group", "multiple-ctas", "event-card"]

  class SectionExpectations(BaseModel):
      count: int                                   # Expected section count
      tolerance: int = 1                           # ±N for spacers/dividers
      components: list[ComponentExpectation] = []   # Per-section component mapping

  class ComponentExpectation(BaseModel):
      index: int | None = None                     # Section index (optional, for ordered matching)
      match_by: str = "content"                    # "content" | "index" | "type"
      content_hint: str = ""                       # Text substring to identify section (e.g., "Reason 1")
      expected_component: str                      # Component slug to match
      repeat_count: int | None = None              # For RepeatingGroup sections
      container_bgcolor: str | None = None         # Expected container background

  class TokenExpectations(BaseModel):
      primary_font: str | None = None              # e.g., "Helvetica, Arial, sans-serif"
      banned_fonts: list[str] = []                 # e.g., ["Inter", "-apple-system"] — must NOT appear
      text_color: str | None = None                # Primary text color
      banned_colors: list[str] = []                # Template defaults that should be overridden

  class CTAExpectation(BaseModel):
      text: str                                    # CTA button text
      bg_color: str | None = None                  # Expected background color
      has_vml: bool = False                        # Expects VML roundrect fallback
  ```
- **REFRAME manifest** (`data/debug/reframe/manifest.yaml`):
  ```yaml
  name: reframe-2025
  figma_file: VUlWjZGAEVZr3mK1EawsYR
  figma_node: "2833:1491"
  description: >
    Vimeo REFRAME 2025 event invitation. Exercises repeating-group (5 reasons),
    multiple distinct CTAs, event-card detection, and per-email token scoping.

  sections:
    count: 12
    tolerance: 1
    components:
      - content_hint: ""
        match_by: index
        index: 0
        expected_component: full-width-image
      - content_hint: "REFRAME 2025"
        expected_component: text-block
      - content_hint: "Reason 1"
        expected_component: col-icon
        repeat_count: 5
        container_bgcolor: "#f1f4f9"
      - content_hint: "Grab your spot"
        expected_component: button-filled
      - content_hint: "Join us at"
        expected_component: event-card
      - content_hint: "Can't make it"
        expected_component: text-block
      - content_hint: "Register for livestream"
        expected_component: button-filled

  tokens:
    primary_font: "Helvetica, Arial, sans-serif"
    banned_fonts: ["Inter", "-apple-system", "BlinkMacSystemFont"]
    text_color: "#000000"
    banned_colors: ["#333333", "#555555", "#444444"]

  ctas:
    - text: "Register now"
      bg_color: "#c6fc6a"
      has_vml: true
    - text: "Grab your spot"
      bg_color: "#ffbaf3"
      has_vml: true
    - text: "Register for livestream"
      bg_color: "#06d5ff"
      has_vml: true

  required_content:
    - "REFRAME 2025"
    - "Reason 1"
    - "Reason 2"
    - "Reason 3"
    - "Reason 4"
    - "Reason 5"
    - "Register now"
    - "Grab your spot"
    - "Register for livestream"
    - "Can't make it live?"
    - "October 23, 2025"

  forbidden_content:
    - "Section Heading"
    - "Image caption — describe the content for context."
    - "Editorial heading"
    - "Lorem ipsum"

  patterns:
    - repeating-group
    - multiple-ctas
    - event-card
    - per-email-token-scoping
  ```
- **Test runner** (`app/design_sync/tests/test_converter_regression.py`):
  - `discover_cases() -> list[Path]` — scan `data/debug/*/manifest.yaml`, return all case directories
  - `@pytest.fixture(params=discover_cases(), ids=lambda p: p.name)` — parametrize all tests across all cases
  - **Universal assertions** (run on EVERY case, no manifest needed):
    - `test_no_nested_p_tags[{case}]` — no `<p><p>` or `</p></p>` in output
    - `test_no_empty_sections[{case}]` — no section with zero content
    - `test_valid_html_structure[{case}]` — parseable HTML, proper `<table>` nesting
    - `test_no_bare_layout_divs[{case}]` — no `<div>` used for layout (width/flex/float)
    - `test_mso_conditionals_balanced[{case}]` — every `<!--[if mso]>` has matching `<![endif]-->`
    - `test_images_have_dimensions[{case}]` — all `<img>` have `width` and `height` attributes
    - `test_slot_fill_rate[{case}]` — percentage of `data-slot` attributes with non-default content (warn if <80%)
  - **Manifest-driven assertions** (from case-specific manifest.yaml):
    - `test_section_count[{case}]` — `abs(actual - manifest.sections.count) <= manifest.sections.tolerance`
    - `test_component_selection[{case}]` — for each `ComponentExpectation`, find the section (by index or content_hint substring) and assert `match.component_slug == expected_component`
    - `test_repeating_groups[{case}]` — for expectations with `repeat_count`, assert `RepeatingGroup` detected with correct count
    - `test_required_content[{case}]` — every string in `required_content` appears in output HTML
    - `test_forbidden_content[{case}]` — no string in `forbidden_content` appears in output HTML
    - `test_font_family[{case}]` — if `tokens.primary_font` set, assert it appears in output; if `tokens.banned_fonts` set, assert none appear
    - `test_text_color[{case}]` — if `tokens.text_color` set, verify most text elements use it; if `tokens.banned_colors` set, assert none appear on text elements
    - `test_cta_colors[{case}]` — for each `CTAExpectation`, find the CTA by text, assert background color matches `bg_color`
    - `test_cta_vml[{case}]` — for CTAs with `has_vml: true`, assert `v:roundrect` with correct `fillcolor` in output
    - `test_container_bgcolors[{case}]` — for expectations with `container_bgcolor`, assert the wrapper table has that bgcolor
  - **Structural diff** (optional, per-case):
    - If `expected.html` exists in case directory, compute section-by-section structural diff
    - Report `StructuralDiffResult(sections_matched: int, sections_mismatched: int, missing_sections: list[str], extra_sections: list[str])` as test metadata (not hard fail — reference HTML may be aspirational)
  - **Metrics collection** (written to `{case_dir}/report.json` after each run):
    - `section_count_accuracy: float` — `1 - abs(actual - expected) / expected`
    - `component_match_accuracy: float` — correct matches / total expectations
    - `slot_fill_rate: float` — non-default slots / total slots
    - `content_coverage: float` — found required_content / total required_content
    - `token_compliance: float` — sections with correct font+color / total sections
    - `overall_score: float` — weighted average of above (0.0–1.0)
- **Existing cases migration:** Add `manifest.yaml` to existing `data/debug/5/` (MAAP), `data/debug/10/` (other) cases. Minimal manifests — just `name`, `sections.count`, `required_content` from their `expected.html`. These cases run through the same framework automatically.
- **Make targets:**
  - `make converter-regression` — run all cases, print per-case score table
  - `make converter-regression CASE=reframe` — run single case
  - `make converter-regression-report` — generate summary across all cases, output to `data/debug/regression_report.json`
- Wire into `make test` and `make check`
- Config: `DESIGN_SYNC__REGRESSION_DIR` (default `data/debug`), `DESIGN_SYNC__REGRESSION_STRICT` (default `false` — when `true`, structural diff mismatches are hard failures)
**Adding a new test case (workflow):**
1. Download Figma JSON: `curl -H "X-Figma-Token: ..." "https://api.figma.com/v1/files/{file}/nodes?ids={node}" -o data/debug/{name}/raw_figma.json`
2. Create reference HTML: hand-craft or copy from `email-templates/`
3. Write manifest: copy an existing manifest.yaml, update sections/tokens/ctas/required_content
4. Run: `make converter-regression CASE={name}` — see what passes, iterate on converter
**Verify:** Framework discovers all cases in `data/debug/*/manifest.yaml`. REFRAME case runs all universal + manifest assertions. MAAP case (after manifest migration) runs with its own expectations. Adding a new empty case dir with only `manifest.yaml` + `raw_figma.json` → universal assertions run, manifest assertions run. `report.json` written with metrics. Per-case parametrized test IDs in pytest output. `make converter-regression` runs all cases. Strict mode fails on structural diff mismatch. 18 tests (framework tests) + N×K (N cases × K assertions per case).

---

### Phase 49 — Summary

| Subtask | Scope | Dependencies | Track | Status |
|---------|-------|--------------|-------|--------|
| 49.1 Sibling pattern detector | `app/design_sync/sibling_detector.py` (new) | None | A | DONE |
| 49.2 Repeating-group renderer | `component_renderer.py`, `converter_service.py` | 49.1 | A | |
| 49.3 Classification improvements | `component_matcher.py`, `layout_analyzer.py` | None | B | |
| 49.4 Token override expansion | `component_renderer.py` | None | B | |
| 49.5 Slot content extraction | `layout_analyzer.py`, `component_matcher.py` | None | C | |
| 49.6 Per-email token scoping | `figma/service.py`, `converter_service.py` | None | C | |
| 49.7 CTA fidelity | `layout_analyzer.py`, `component_matcher.py`, `component_renderer.py` | 49.4 | B | |
| 49.8 EmailTree bridge | `tree_bridge.py` (new), `converter_service.py` | 49.1, 49.2, 48.6 | D | |
| 49.9 Data-driven regression framework | `test_converter_regression.py`, `manifest_schema.py`, `data/debug/*/manifest.yaml` | None (can start early) | E | DONE |

> **Execution:** Five tracks, three with internal sequencing.
>
> **Track A (repeated content):** 49.1 → 49.2 (detector before renderer).
> **Track B (matching + tokens):** 49.3 + 49.4 (parallel) → 49.7 (needs 49.4 for CTA overrides).
> **Track C (extraction):** 49.5 + 49.6 (fully parallel, no deps).
> **Track D (tree bridge):** 49.8 (after 49.1 + 49.2 for RepeatingGroup support, after 48.6 for EmailTree schema).
> **Track E (regression framework):** 49.9 (can start early — framework + manifests are independent of converter fixes; assertions will fail until fixes land, which is expected).
>
> Tracks A, B, C can all proceed in parallel. Track D starts after A completes + 48.6 is available. Track E is the final gate.
>
> **Total new code:** ~1200 LOC Python + ~200 LOC test fixtures + 1 new test case directory. Two new files (`sibling_detector.py`, `tree_bridge.py`). No new agents. No database migrations. All behind feature flags — zero behavior change when disabled.
>
> **Impact ladder:**
> - 49.1 + 49.2 alone → **repeated-content patterns work** (5-reasons, product grids, feature lists)
> - 49.3 → **~85% correct component selection** (up from ~40%)
> - 49.4 → **design fonts/colors actually applied** (eliminates template defaults)
> - 49.5 → **no more placeholder text** (actual Figma content in all slots)
> - 49.6 → **correct primary font in shared Figma files** (scoped extraction)
> - 49.7 → **CTA buttons match design** (color, shape, VML)
> - 49.8 → **deterministic rendering via TreeCompiler** (bridges to Phase 48)
> - 49.9 → **regression-proof for any email** (data-driven framework, add cases by dropping manifest.yaml + Figma JSON)
