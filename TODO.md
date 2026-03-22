# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–25):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA — Playwright rendering, ODiff baselines, VLM analysis agent #10, auto-fix pipeline, visual QA dashboard). Phase 18 (rendering resilience & property-based testing — chaos engine with 8 profiles, Hypothesis-based property testing with 10 invariants, resilience score integration, knowledge feedback loop). Phase 19 (Outlook transition advisor & email CSS compiler — Word-engine dependency analyzer, audience-aware migration planner, Lightning CSS 7-stage compiler with ontology-driven conversions). Phase 20 (Gmail AI intelligence & deliverability — Gemini summary predictor, schema.org auto-injection, deliverability scoring, BIMI readiness check). Phase 21 (real-time ontology sync & competitive intelligence — caniemail auto-sync, rendering change detector with 25 feature templates, competitive intelligence dashboard). Phase 22 (AI evolution infrastructure — capability registry, prompt template store, token budget manager, fallback chains, cost governor, cross-module integration tests + ADR-009). Phase 23 (multimodal protocol & MCP agent interface — 7 subtasks: content block protocol, adapter serialization, agent integration, MCP tool server with 17 tools, voice brief pipeline, frontend multimodal UI, tests & ADR-010; 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks: WebSocket infra, Yjs CRDT engine, collaborative cursor & presence, visual builder canvas & palette, property panels, bidirectional code↔builder sync, frontend integration, tests & docs, AI-powered HTML import with 10th agent). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks: plugin architecture with manifest/discovery/registry, sandboxed execution & lifecycle, Tolgee multilingual campaigns, per-locale Maizzle builds, Kestra workflow orchestration, Penpot design-to-email pipeline, Typst QA report generator, ecosystem dashboard, template learning pipeline, automatic skill extraction, template-to-eval pipeline, deliverability intelligence, multi-variant campaign assembly).

---

## ~~Phase 24 — Real-Time Collaboration & Visual Builder~~ DONE

> All 9 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 24.1 WebSocket infra, 24.2 Yjs CRDT, 24.3 Presence, 24.4 Visual builder canvas, 24.5 Property panels, 24.6 Bidirectional sync, 24.7 Frontend integration, 24.8 Tests & docs, 24.9 AI-powered HTML import.

---

## ~~Phase 25 — Platform Ecosystem & Advanced Integrations~~ DONE

> All 15 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 25.1 Plugin manifest/discovery/registry, 25.2 Sandboxed execution & lifecycle, 25.3 Tolgee multilingual campaigns, 25.4 Per-locale Maizzle builds, 25.5 Kestra workflow orchestration, 25.6 Penpot design-to-email, 25.7 Typst QA report generator, 25.8 Ecosystem dashboard, 25.9 Tests & docs, 25.10 Template learning pipeline, 25.11 Automatic skill extraction, 25.12 Template-to-eval pipeline, 25.13 Deliverability intelligence, 25.14 Multi-variant campaign assembly, 25.15 Tests & docs for 25.10–25.14.

---

## Phase 26 — Email Build Pipeline Performance & CSS Optimization

**What:** Eliminate redundant CSS processing in the email build pipeline, surface per-client CSS compatibility data in QA output, pre-compile template CSS at registration time, and consolidate CSS compilation into the Maizzle sidecar as a single-pass PostCSS pipeline. Four subtasks ordered by impact — each builds on the previous.
**Why:** The current build pipeline processes CSS twice: Maizzle inlines via Juice, then `EmailCSSCompiler` re-inlines via BeautifulSoup. The BeautifulSoup inliner is O(rules × elements) and adds 1–5s on complex emails — the single largest bottleneck in a pipeline that's otherwise sub-second after the LLM passes. Fixing this unlocks near-instant deterministic builds. The CSS compatibility data already exists in the ontology but isn't surfaced per-build, leaving users to discover rendering failures post-send. Pre-compiling template CSS amortizes optimization cost across all builds using that template. Consolidating into the sidecar is the clean architectural end-state — one HTTP call, one CSS pass, Node.js-native tooling.
**Dependencies:** Phase 19 (CSS compiler, ontology-driven conversions), Phase 25 (Maizzle sidecar, plugin QA checks). The ontology registry, Lightning CSS integration, and 7-stage compiler pipeline are all in place.
**Design principle:** Measure before optimizing — add timing telemetry to each pipeline stage first. Each subtask must preserve the existing `CompilationResult` contract and pass all existing tests. No new feature flags — these are internal optimizations that don't change the external API.

### 26.1 Eliminate Redundant CSS Inlining `[Backend]`
**What:** Reorder the email build pipeline so `EmailCSSCompiler` runs its analyze/transform/eliminate/optimize stages on raw CSS *before* Maizzle inlines it, then skip the compiler's own inline stage (stage 6) entirely. Maizzle's Juice inliner handles the final CSS→inline conversion on already-optimized CSS. This eliminates the BeautifulSoup O(rules × elements) bottleneck — the single most expensive step in the deterministic pipeline.
**Why:** Currently Maizzle inlines raw CSS via Juice, then `EmailCSSCompiler` extracts styles, optimizes, and re-inlines via BeautifulSoup. The BeautifulSoup inliner is quadratic — 100 CSS rules × 50 matching elements = 5,000 element updates. On complex emails (30+ sections, responsive + dark mode CSS), this adds 1–5s. Since Maizzle already does high-quality CSS inlining (specificity-aware, handles pseudo-classes), the Python inliner is redundant. Running ontology optimization *before* Maizzle means Maizzle inlines fewer, cleaner rules — faster on both sides.
**Implementation:**
- Add pipeline stage timing telemetry to `EmailCSSCompiler.compile()` — log `compile.stage_{name}_ms` for each of the 7 stages so we have before/after metrics
- Create `EmailCSSCompiler.optimize_css(html: str, target_clients: list[str]) -> OptimizedCSS` — new public method that runs stages 1-5 only (parse → analyze → transform → eliminate → optimize) and returns `OptimizedCSS(html_with_optimized_styles: str, removed_properties: list, conversions: list, warnings: list)`
  - Extracts `<style>` blocks via `extract_styles()`
  - Runs ontology analysis, conversions, eliminations on each block
  - Runs Lightning CSS minification on each block
  - Re-injects optimized `<style>` blocks into HTML (does NOT inline)
  - Returns HTML ready for Maizzle to inline
- Modify `MaizzleBuildNode.execute()` in `app/ai/blueprints/nodes/maizzle_build_node.py`:
  - Before calling the Maizzle sidecar, call `EmailCSSCompiler.optimize_css()` on `context.html`
  - Pass optimized HTML to Maizzle (Juice inlines the already-optimized CSS)
  - After Maizzle returns, run only `sanitize_html_xss()` — skip the full `compile()` call
  - Store `OptimizedCSS` metadata (removed_properties, conversions, warnings) in build result
- Modify `EmailEngineService.build()` in `app/email_engine/service.py`:
  - Same pattern for direct builds: `optimize_css()` → `_call_builder()` → `sanitize_html_xss()`
  - Preserve `CompilationResult` contract — populate from `OptimizedCSS` + Maizzle build time
- Modify `EmailCSSCompiler.compile()` — keep it working as-is for backward compatibility (CSS compilation API endpoint still uses the full 7-stage pipeline), but add deprecation log encouraging callers to use the optimized flow
- Update `app/email_engine/css_compiler/__init__.py` exports to include `OptimizedCSS`, `optimize_css`
**Security:** No new attack surface. `sanitize_html_xss()` still runs on final output. Ontology-driven property elimination is deterministic and already tested.
**Verify:** Run `make test` — all existing CSS compiler tests pass unchanged. Build the same email with old flow vs new flow → identical HTML output (diff test). Measure build time on a 30-section email → confirm 1–5s reduction. `CompilationResult` fields populated correctly. `make check` all green.
- [ ] 26.1 Eliminate redundant CSS inlining

### 26.2 Per-Build CSS Compatibility Audit in QA Output `[Backend + Frontend]`
**What:** Surface the ontology-driven CSS compatibility data as a per-build QA check result. When a user runs QA or builds an email, the output includes a matrix showing which CSS properties survive in each target email client, which were converted to fallbacks, and which were removed. This catches rendering surprises *before* send — not after.
**Why:** The ontology data and per-build conversion metadata already exist (from `CompilationResult.removed_properties` and `CompilationResult.conversions`). But this data is only logged — it never reaches the user. Users discover rendering failures by manually testing in Litmus/Email on Acid or worse, from recipient complaints. Surfacing the data per-build is practically free and directly actionable.
**Implementation:**
- Create `app/qa_engine/checks/css_audit.py` — `CSSAuditCheck`:
  - `async run(html: str, config: QACheckConfig) -> QACheckResult`
  - Accepts `target_clients: list[str]` from config (default: Gmail, Outlook, Apple Mail, Yahoo Mail, Samsung Mail)
  - Calls `EmailCSSCompiler.optimize_css()` (from 26.1) to get `OptimizedCSS` with conversion metadata
  - Builds per-client matrix: `dict[client_name, dict[property, SupportStatus]]` where `SupportStatus` is `supported | converted | removed | partial`
  - Severity classification:
    - `error` — property removed with no fallback in a tier-1 client (Gmail, Outlook)
    - `warning` — property converted to fallback (may look different)
    - `info` — property has partial support (works in some contexts)
  - Output: `QACheckResult` with `details.compatibility_matrix`, `details.conversions`, `details.removed_properties`, `details.client_coverage_score` (0–100, percentage of CSS properties fully supported across all target clients)
  - Score formula: `(fully_supported_count / total_property_count) * 100` per client, then average across targets
- Register `css_audit` in `app/qa_engine/checks/__init__.py` — add to default check list (runs after `css_support` check)
- Modify `app/qa_engine/service.py` — `QAEngineService.run_checks()`:
  - Pass `compilation_result` (if available from prior build step) to `CSSAuditCheck` to avoid re-running the compiler
  - If no compilation result available, `CSSAuditCheck` runs `optimize_css()` internally
- Modify existing `CssSupportCheck` in `app/qa_engine/checks/css_support.py`:
  - Add `engine_compatibility_summary` to its output — leverages `OntologyRegistry.engine_support()` for engine-level aggregation
  - Keep existing per-property support check, add per-engine summary view
- Frontend: Add CSS audit visualization to QA results panel:
  - `cms/apps/web/src/components/qa/css-audit-panel.tsx` — new component:
    - Collapsible client matrix table: rows = CSS properties, columns = target clients, cells = colored status (green/yellow/red)
    - Conversion detail expandable: click a "converted" cell → shows original property, fallback property, reason
    - Client coverage score bar: horizontal bar per client with percentage
    - Filter: show all / errors only / warnings only
  - Wire into existing QA results view — new tab "CSS Compatibility" alongside existing check results
- Frontend types: add `CSSAuditResult`, `CompatibilityMatrix`, `ClientCoverageScore` to `cms/apps/web/src/types/qa.ts`
**Security:** Read-only — displays existing ontology data. No new inputs or endpoints beyond the standard QA flow.
**Verify:** Build an email with known unsupported properties (e.g., `border-radius` in Outlook Word engine) → CSS audit check shows `removed` status for Outlook with `error` severity. Build a simple email with only universally-supported properties → 100% coverage score. Frontend matrix renders correctly. `make test` and `make check-fe` pass.
- [ ] 26.2 Per-build CSS compatibility audit in QA output

### 26.3 Template-Level CSS Precompilation `[Backend]`
**What:** Pre-compile ontology-optimized CSS for each `GoldenTemplate` at registration/update time. Store the optimized CSS alongside the raw template HTML. At build time, the `TemplateAssembler` starts from pre-optimized HTML — the only CSS work remaining is token substitution (hex color swap, font swap) which is pure string replacement, not CSS parsing.
**Why:** Golden templates have static CSS that doesn't change between builds. Running ontology analysis, Lightning CSS minification, and property elimination on the *same* CSS for every build is wasted computation. Pre-compiling amortizes this cost to template registration (happens once per template version). Build-time CSS work drops to O(token_count) string replacements — microseconds instead of hundreds of milliseconds. This compounds: 50 builds/day × 200ms savings = 10s/day per template. For platforms with dozens of templates and hundreds of daily builds, this is significant.
**Implementation:**
- Add columns to `GoldenTemplate` model in `app/ai/agents/scaffolder/templates.py`:
  - `optimized_html: str | None` — HTML with pre-compiled CSS (ontology-optimized, Lightning CSS minified, CSS variables resolved)
  - `optimized_at: datetime | None` — timestamp of last precompilation
  - `optimized_for_clients: list[str] | None` — target client list used for optimization (if target clients change, re-optimize)
  - `optimization_metadata: dict | None` — JSON: `{ removed_properties, conversions, compile_time_ms, original_size, optimized_size }`
- Create `app/ai/agents/scaffolder/template_precompiler.py` — `TemplatePrecompiler`:
  - `async precompile(template: GoldenTemplate, target_clients: list[str] | None = None) -> GoldenTemplate`:
    - Uses `EmailCSSCompiler.optimize_css()` (from 26.1) on template HTML
    - Default target clients: `["gmail", "outlook", "apple_mail", "yahoo_mail"]` (configurable via `CSS_OPTIMIZATION__DEFAULT_TARGETS`)
    - Stores result in `optimized_html`, metadata in `optimization_metadata`
    - Preserves slot placeholders, ESP tokens, builder annotations — optimization only touches CSS
  - `async precompile_all(target_clients: list[str] | None = None) -> PrecompilationReport`:
    - Batch precompile all registered templates
    - Returns report: `{ total, succeeded, failed, total_size_reduction_bytes, avg_compile_time_ms }`
  - `is_stale(template: GoldenTemplate, target_clients: list[str]) -> bool`:
    - Returns True if `optimized_at` is None, or `optimized_for_clients` differs from current targets, or template HTML has been modified since `optimized_at`
- Modify `TemplateRegistry` in `app/ai/agents/scaffolder/templates.py`:
  - `register()` / `update()` — after saving template, trigger `TemplatePrecompiler.precompile()` asynchronously (fire-and-forget via `asyncio.create_task`)
  - `get()` — if `optimized_html` is not None and not stale, return `optimized_html` as the build source
  - Fallback: if `optimized_html` is None (first registration, migration), return raw HTML — pipeline still works, just slower
- Modify `TemplateAssembler.assemble()` in `app/ai/agents/scaffolder/assembler.py`:
  - Detect if input HTML is pre-optimized (check `template.optimized_html is not None`)
  - If pre-optimized: skip the `optimize_css()` call in `MaizzleBuildNode` — set a flag `skip_css_optimization=True` on build context
  - Assembler's 11 steps work identically on pre-optimized HTML (they operate on inline styles and HTML attributes, not `<style>` blocks)
- Modify `MaizzleBuildNode.execute()`:
  - Check `context.skip_css_optimization` — if True, skip `optimize_css()` call, pass HTML directly to Maizzle
  - Maizzle still inlines CSS (slot fills may have added new `<style>` rules from components), but the bulk of template CSS is already optimized
- Add management command / API endpoint:
  - `POST /api/v1/templates/precompile` — admin-only, triggers batch precompilation of all templates
  - Returns `PrecompilationReport` with per-template status
- Alembic migration: add `optimized_html`, `optimized_at`, `optimized_for_clients`, `optimization_metadata` columns to `golden_templates` table (nullable, no data migration needed)
**Security:** Pre-compiled HTML goes through the same `sanitize_html_xss()` pipeline as raw HTML. Admin-only precompile endpoint. No new user-facing inputs.
**Verify:** Register a new template → `optimized_html` populated within 1s. Build email from pre-optimized template → identical output to non-optimized path (diff test). Build time measurably faster (skip CSS optimization stage). Modify template HTML → `is_stale()` returns True → next build triggers re-precompilation. `POST /api/v1/templates/precompile` returns report with all templates succeeded. `make test` passes. `make check` all green.
- [ ] 26.3 Template-level CSS precompilation

### 26.4 Consolidated CSS Pipeline in Maizzle Sidecar `[Backend + Sidecar]`
**What:** Move the ontology-driven CSS optimization into the Maizzle sidecar as a custom PostCSS plugin. The sidecar becomes the single CSS processing point: ontology elimination → property conversion → Lightning CSS minification → Juice inlining — all in one Node.js process, one HTTP call. The Python `EmailCSSCompiler` becomes a thin client that calls the sidecar and wraps the result.
**Why:** This is the clean architectural end-state for the CSS pipeline. After 26.1 separated optimization from inlining, the two still run in different processes (Python optimization → HTTP → Node.js inlining). Merging them eliminates: (a) HTTP serialization overhead for the optimize step, (b) HTML re-parsing between stages, (c) process context switching. Node.js has superior CSS tooling — PostCSS, Lightning CSS (native npm package, no FFI), csstools/postcss-plugins. The ontology data is static JSON that can be loaded once at sidecar startup. Expected improvement: 100–300ms per build from eliminated HTTP round-trip + re-parsing.
**Implementation:**
- Create `services/maizzle-builder/postcss-email-optimize.js` — custom PostCSS plugin:
  - `module.exports = (opts = {}) => { return { postcssPlugin: 'email-optimize', ... } }`
  - Loads ontology support matrix from `services/maizzle-builder/data/ontology.json` at startup (copied from `app/email_engine/css_compiler/data/` at build time)
  - `Declaration(decl, { result })` visitor:
    - Looks up `decl.prop` in ontology for each target client in `opts.targetClients`
    - If zero support + no fallback → `decl.remove()` + log to `result.messages`
    - If fallback available → `decl.replaceWith(fallbackDecl)` + log conversion
    - If partial support → keep, add warning to `result.messages`
  - `AtRule(atRule)` visitor:
    - Preserves `@media`, `@keyframes` — no elimination
    - Removes `@charset`, `@layer` (no email client support)
  - `OnceExit(root, { result })`:
    - Collects all messages into `result.messages` with type `email-optimize` for structured reporting
  - Export `removedProperties`, `conversions`, `warnings` arrays attached to result
- Create `services/maizzle-builder/data/ontology.json`:
  - Build script: `services/maizzle-builder/scripts/sync-ontology.js` — reads `app/email_engine/css_compiler/data/` YAML/JSON files → writes merged JSON
  - Run as `npm run sync-ontology` (add to package.json scripts)
  - Also runs as part of `make dev` setup
- Modify `services/maizzle-builder/index.js`:
  - Add `postcss-email-optimize` to the PostCSS plugin chain in Maizzle config
  - New request field: `target_clients: string[]` (optional, default: `["gmail", "outlook", "apple_mail", "yahoo_mail"]`)
  - New response fields: `optimization: { removed_properties, conversions, warnings, original_css_size, optimized_css_size }`
  - Pipeline order: `postcss-email-optimize` → Maizzle transforms → Juice inline → minify (production)
  - Lightning CSS: add `lightningcss` npm package for minification (replaces cssnano if present) — native Node, no Rust FFI
- Modify `services/maizzle-builder/package.json`:
  - Add dependencies: `postcss` (peer), `lightningcss`
  - Add script: `"sync-ontology": "node scripts/sync-ontology.js"`
- Modify `MaizzleBuildNode.execute()` in `app/ai/blueprints/nodes/maizzle_build_node.py`:
  - Pass `target_clients` in sidecar request body
  - Read `optimization` from sidecar response → populate `CompilationResult` metadata
  - Remove call to `EmailCSSCompiler.optimize_css()` — sidecar handles it now
  - Keep `sanitize_html_xss()` on output (Python-side security guarantee)
- Modify `EmailEngineService._call_builder()` in `app/email_engine/service.py`:
  - Same pattern: pass `target_clients`, read `optimization` from response
  - Populate `CompilationResult` from sidecar `optimization` field
- Modify `EmailCSSCompiler` in `app/email_engine/css_compiler/compiler.py`:
  - Keep `compile()` for backward compatibility (CSS compilation API endpoint)
  - Add `compile_via_sidecar(html, target_clients) -> CompilationResult` — thin wrapper that calls sidecar `/build` with CSS optimization enabled and maps response to `CompilationResult`
  - `optimize_css()` (from 26.1) remains available for pre-compilation (26.3) and standalone use
- Update `Makefile`:
  - `make dev` — runs `npm run sync-ontology` in `services/maizzle-builder/` before starting sidecar
  - `make sync-ontology` — standalone target for manual ontology sync
- Update `services/maizzle-builder/Dockerfile` (if present):
  - Add `COPY` for ontology data
  - Add `RUN npm run sync-ontology` in build stage
**Security:** Ontology data is read-only static configuration. No user input reaches the PostCSS plugin — it only processes CSS from trusted template sources. `sanitize_html_xss()` still runs in Python on final output. Sidecar remains internal (not exposed to public network).
**Verify:** Build email via sidecar with `target_clients=["outlook"]` → response includes `optimization.removed_properties` listing Outlook-unsupported CSS. Build same email via old Python path → identical HTML output (diff test). Sidecar `/health` returns ontology version. `npm run sync-ontology` succeeds and produces valid JSON. `make test` passes (backend). `cd services/maizzle-builder && npm test` passes (sidecar). `make check` all green. Measure end-to-end build time → confirm 100–300ms improvement over 26.1 flow.
- [ ] 26.4 Consolidated CSS pipeline in Maizzle sidecar

### 26.5 Tests & Documentation `[Full-Stack]`
**What:** Comprehensive test suite for the entire Phase 26 pipeline, regression tests ensuring output equivalence with the pre-Phase-26 pipeline, and performance benchmarks.
**Implementation:**
- `app/email_engine/css_compiler/tests/test_optimize_css.py` — 15+ tests:
  - `optimize_css()` returns correct `OptimizedCSS` structure
  - Ontology-driven property removal (e.g., `border-radius` removed for Outlook Word engine)
  - Fallback conversions applied (e.g., `flexbox` → `display: block`)
  - Lightning CSS minification reduces size
  - CSS variable resolution with fallbacks
  - MSO conditional comments preserved through optimization
  - Slot placeholders and ESP tokens untouched by CSS optimization
  - Empty `<style>` blocks removed after optimization
  - `@media` and `@keyframes` at-rules preserved
  - Multiple `<style>` blocks handled independently
- `app/qa_engine/checks/tests/test_css_audit.py` — 10+ tests:
  - Audit check returns correct severity per property per client
  - Coverage score calculation (100% for basic emails, <100% for modern CSS)
  - Conversion details populated correctly
  - Handles empty HTML gracefully
  - Respects custom `target_clients` config
  - Integration with `QAEngineService.run_checks()` — css_audit included in results
- `app/ai/agents/scaffolder/tests/test_template_precompiler.py` — 10+ tests:
  - Precompile populates `optimized_html` and metadata
  - `is_stale()` returns True when template modified after optimization
  - `is_stale()` returns True when target clients change
  - Precompile preserves slot placeholders and builder annotations
  - Batch `precompile_all()` returns correct report
  - Build from pre-optimized template produces identical output to non-optimized (regression)
  - Pre-optimized path skips CSS optimization stage (verified via mock/spy)
- `services/maizzle-builder/tests/` — 10+ tests (Jest or Vitest):
  - PostCSS plugin removes unsupported properties per ontology
  - PostCSS plugin applies fallback conversions
  - PostCSS plugin preserves @media rules
  - Ontology sync script produces valid JSON
  - `/build` response includes `optimization` field when `target_clients` provided
  - `/build` without `target_clients` uses defaults
  - End-to-end: HTML in → optimized + inlined HTML out
- `app/email_engine/css_compiler/tests/test_pipeline_equivalence.py` — regression suite:
  - 5 golden email templates (simple, complex, dark-mode-heavy, responsive, MSO-conditional)
  - For each: build via old 7-stage `compile()` path AND new optimized path → `assert html_equal(old, new)`
  - HTML comparison ignores whitespace differences, attribute ordering
  - Guards against any behavioral regression from the pipeline reorder
- `app/email_engine/css_compiler/tests/test_performance_benchmark.py` — performance suite:
  - Benchmark `compile()` vs `optimize_css()` + Maizzle on 5/15/30-section emails
  - Assert new path is at least 2× faster than old path for 30-section emails
  - Log timing breakdowns for CI tracking
  - Marked `@pytest.mark.benchmark` (not run in standard `make test`, run via `make bench`)
- Add `make bench` target in Makefile — runs benchmark tests only (`pytest -m benchmark`)
- Target: 50+ tests total across all test files
**Verify:** `make test` passes (all new + existing tests). `make check` all green. `make bench` shows measurable improvement. `make eval-golden` passes (no regression in email output quality). Pipeline equivalence tests confirm identical output.
- [ ] 26.5 Tests & documentation

---

## Phase 27 — Email Client Rendering Fidelity & Pre-Send Testing

**What:** Expand the local email client emulation system from 2 emulators to 7, add a calibration feedback loop that compares local previews against external rendering providers (Litmus / Email on Acid) to iteratively improve emulator accuracy, introduce per-client rendering confidence scores, and build a pre-send rendering gate that blocks ESP sync when confidence drops below configurable thresholds. Six subtasks ordered by value — each builds on the previous.
**Why:** The current rendering pipeline has two emulators (Gmail, Outlook.com) and 6 Playwright profiles, but no way to quantify *how faithful* a local preview actually is. Users must either trust the local preview blindly or pay for Litmus/EoA screenshots on every build. The real problem isn't the rendering engine — it's the *sanitizer/preprocessor* each email client runs before its engine sees the HTML. Gmail's Blink can render flexbox perfectly; Gmail's sanitizer strips it first. By modeling these sanitizers as chained transformation rules (which the emulator system already does for Gmail and Outlook.com), and calibrating them against ground truth screenshots, we can give users a confidence score: "Gmail: 94% confidence (emulated)" vs "Outlook 2019: 72% confidence (Word engine — recommend external validation)." This turns rendering testing from binary (local preview looks OK / send and hope) into a quantified risk assessment with actionable thresholds.
**Dependencies:** Phase 17 (visual regression & Playwright rendering), Phase 19 (CSS compiler & ontology), Phase 26 (optimized CSS pipeline & per-build CSS audit). The `RenderingService` multi-provider architecture, `EmailClientEmulator` chain-of-rules pattern, `ScreenshotBaseline` model, ODiff visual comparison, and ontology support matrix are all in place.
**Design principle:** Emulators are approximations, not replacements. Every emulator publishes a confidence score derived from calibration data. The system is honest about what it can and cannot model locally — Word engine rendering is fundamentally impossible to emulate without Word itself, so Outlook desktop emulators focus on the *CSS preprocessing* stage (property stripping, shorthand expansion, VML injection) and report lower confidence for layout-dependent issues. External providers are the ground truth — local emulators are the fast, free alternative that gets better over time via calibration.

### 27.1 Expand Email Client Emulators — Yahoo, Samsung, Outlook Desktop, Thunderbird, Android Gmail `[Backend]`
**What:** Add 5 new `EmailClientEmulator` implementations covering the remaining high-market-share clients. Each emulator models the client's HTML/CSS sanitizer as a chain of transformation rules — the same pattern used by the existing Gmail and Outlook.com emulators.
**Why:** Gmail Web and Outlook.com cover ~35% of the email market. Adding Yahoo Mail, Samsung Mail, Outlook desktop (Word engine CSS preprocessing), Thunderbird, and Android Gmail pushes coverage to ~85%. Each emulator doesn't need to be perfect — it needs to replicate the *sanitizer behavior* that determines which CSS/HTML survives to the rendering engine. The ontology already has the data (365 properties × 25 clients); emulators operationalize that data as DOM transforms.
**Implementation:**
- Add emulators to `app/rendering/local/emulators.py`:
  - **Yahoo Mail emulator** (4 rules):
    - `_yahoo_strip_style_blocks()` — Yahoo strips `<style>` blocks in some contexts (mobile) but not others (desktop webmail). Model worst-case: strip `<style>` for mobile Yahoo profile, keep for desktop Yahoo profile (2 profiles per client)
    - `_yahoo_strip_unsupported_css()` — remove `position`, `float`, `overflow`, `clip-path` from inline styles (Yahoo's allowlist is smaller than Gmail's)
    - `_yahoo_rewrite_classes()` — Yahoo prefixes classes with `yiv` + hash (similar to Gmail's `m_` prefix but different pattern): `.hero` → `.yiv1234567890_hero`
    - `_yahoo_enforce_max_width()` — inject `max-width: 800px` on `<body>` (Yahoo's viewport constraint)
  - **Samsung Mail emulator** (3 rules):
    - `_samsung_strip_unsupported_css()` — remove `background-blend-mode`, `mix-blend-mode`, `filter`, `backdrop-filter`, `clip-path` (Samsung's Android WebView has partial CSS3 support)
    - `_samsung_image_proxy()` — rewrite `<img src>` URLs to simulate Samsung's image proxy (adds `?samsung_proxy=1` parameter — does not actually proxy, but tests whether templates break with URL modification)
    - `_samsung_dark_mode_inject()` — Samsung Mail applies `@media (prefers-color-scheme: dark)` system-level override — inject `color-scheme: dark` on `<html>` and force `background-color` / `color` inversion on `<body>` if no explicit dark mode styles exist
  - **Outlook desktop emulator** (5 rules — CSS preprocessing only, not layout):
    - `_outlook_word_strip_unsupported()` — bulk-remove CSS properties unsupported by Word engine: `display: flex|grid|inline-flex|inline-grid`, `position: fixed|sticky`, `float`, `box-shadow`, `text-shadow`, `border-radius`, `background-image` (gradients), `opacity`, `transform`, `transition`, `animation`, `filter`, `overflow`, `clip-path`, `object-fit`. Use ontology `properties_unsupported_by("outlook_2019")` for authoritative list
    - `_outlook_word_shorthand_expand()` — expand all shorthand properties (margin, padding, border, background, font) to longhand — Word doesn't parse shorthand correctly for all properties
    - `_outlook_word_max_width()` — inject `width: 100%; max-width: 600px` on outermost `<table>` (Word ignores `max-width` on `<div>`)
    - `_outlook_word_conditional_process()` — process MSO conditional comments: extract `<!--[if mso]>` blocks, remove `<!--[if !mso]><!-->` blocks — simulate what Word actually sees
    - `_outlook_word_vml_preserve()` — preserve VML blocks (`<v:*>` elements) — these render in Word but not in browsers, so Playwright screenshot won't show them (note in confidence metadata)
  - **Thunderbird emulator** (2 rules):
    - `_thunderbird_strip_unsupported()` — remove `position: sticky`, `backdrop-filter`, `clip-path` (Thunderbird uses Gecko, mostly standards-compliant but missing a few properties)
    - `_thunderbird_preserve_style_blocks()` — no-op (Thunderbird respects `<style>` blocks — this documents the behavior)
  - **Android Gmail emulator** (4 rules):
    - Inherits all 6 Gmail Web rules via `_clone_rules("gmail_web")`
    - `_android_gmail_viewport_override()` — override viewport to mobile width (360px), inject `<meta name="viewport" content="width=device-width">`
    - `_android_gmail_dark_mode()` — Android Gmail applies system dark mode — inject `data-ogsc` and force `color-scheme: dark` on `<html>` if dark mode profile
    - `_android_gmail_amp_strip()` — strip any `<html ⚡4email>` AMP content (Android Gmail handles AMP separately)
- Add rendering profiles to `app/rendering/local/profiles.py`:
  - `yahoo_web` — 800×900, Chromium, `emulator_id="yahoo_web"`
  - `yahoo_mobile` — 375×812, WebKit, `emulator_id="yahoo_mobile"`, device="iPhone 13"
  - `samsung_mail` — 360×780, Chromium, `emulator_id="samsung_mail"`
  - `samsung_mail_dark` — 360×780, Chromium, `emulator_id="samsung_mail"`, `color_scheme="dark"`
  - `outlook_desktop` — 800×900, Chromium, `emulator_id="outlook_desktop"` (Note: Playwright renders the CSS-preprocessed HTML — layout will approximate but not match Word engine)
  - `thunderbird` — 700×900, Firefox (Gecko), `emulator_id="thunderbird"`
  - `android_gmail` — 360×780, Chromium, `emulator_id="android_gmail"`
  - `android_gmail_dark` — 360×780, Chromium, `emulator_id="android_gmail"`, `color_scheme="dark"`
- Modify `get_emulator(client_id: str)` — register all 7 emulators in the emulator registry
- Add `EmulatorRule` typing: `@dataclass class EmulatorRule: name: str, fn: Callable[[str], str], description: str, confidence_impact: float` — each rule declares how much confidence it removes (e.g., Word CSS stripping = high confidence, VML preservation = low confidence since Playwright can't render VML)
- Total profiles after this subtask: 6 (existing) + 8 (new) = 14 rendering profiles
**Security:** Emulators are pure HTML-in → HTML-out string transforms. No network calls, no file system access. `sanitize_html_xss()` still runs after emulation. Samsung image proxy simulation uses URL parameter append only — no actual proxying.
**Verify:** Each new emulator produces expected transforms: Yahoo class rewriting (`yiv` prefix), Samsung dark mode injection, Outlook Word CSS stripping (verify `display:flex` removed), Thunderbird preserves `<style>` blocks. Existing Gmail/Outlook.com emulators unchanged (regression test). All 14 profiles produce Playwright screenshots. `make test` passes.
- [ ] 27.1 Expand email client emulators

### 27.2 Rendering Confidence Scoring `[Backend]`
**What:** Assign a per-client confidence score (0–100) to every local rendering preview, quantifying how faithful the emulated screenshot is expected to be relative to the real email client. Scores are derived from three signals: emulator rule coverage, ontology CSS support gaps, and historical calibration data (initially seed values, later updated by the calibration loop in 27.4).
**Why:** A local preview without a confidence score is a guess the user can't evaluate. "Here's what Gmail will look like" is less useful than "Here's what Gmail will look like — 94% confidence. The remaining 6% uncertainty is from: DOM restructuring we don't model, URL rewriting, and viewport clipping." Confidence scores let users make informed decisions: "92% confident for Gmail? Ship it. 68% confident for Outlook 2019? Send to Litmus first." This converts rendering testing from a binary pass/fail into a quantified risk assessment.
**Implementation:**
- Create `app/rendering/local/confidence.py` — `RenderingConfidenceScorer`:
  - `score(html: str, profile: RenderingProfile) -> RenderingConfidence`:
    - Returns `RenderingConfidence(score: float, breakdown: ConfidenceBreakdown, recommendations: list[str])`
  - `ConfidenceBreakdown`:
    - `emulator_coverage: float` — percentage of the client's known sanitizer behaviors that the emulator models (e.g., Gmail emulator covers 6/8 known behaviors = 75%)
    - `css_compatibility: float` — percentage of CSS properties in the HTML that are fully supported by the target client (from ontology). High CSS compatibility = less emulator work = higher confidence
    - `calibration_accuracy: float` — historical accuracy of this emulator vs ground truth (initial seed: 80% for Gmail, 75% for Outlook.com, 70% for Yahoo, 65% for Samsung, 50% for Outlook desktop, 85% for Thunderbird, 78% for Android Gmail)
    - `layout_complexity: float` — penalty for complex layouts (nested tables >3 deep, flexbox/grid usage, absolute positioning) — more complex = more room for emulator divergence
    - `known_blind_spots: list[str]` — behaviors the emulator cannot model (e.g., "Word table cell width calculation", "Gmail DOM restructuring", "Samsung image proxy URL rewriting")
  - Scoring formula: `score = (emulator_coverage × 0.25 + css_compatibility × 0.25 + calibration_accuracy × 0.35 + (1.0 - layout_complexity) × 0.15) × 100`
    - Calibration accuracy weighted highest because it's empirical ground truth
    - Layout complexity is a penalty — simple emails get higher confidence
  - `layout_complexity_score(html: str) -> float`:
    - Counts: table nesting depth, flexbox/grid usage, absolute/fixed positioning, VML blocks, MSO conditionals, media query count
    - Returns 0.0 (simple) to 1.0 (highly complex)
    - Thresholds: nesting >3 = +0.2, flexbox = +0.15, VML = +0.1, media queries >5 = +0.1
- Create `app/rendering/local/confidence_seeds.yaml` — initial calibration seeds:
  - Per-emulator accuracy estimates based on known emulator rule coverage
  - Updated by the calibration loop (27.4) — seeds are overwritten when real data is available
  - Format: `{client_id: {accuracy: float, sample_count: int, last_calibrated: str, known_blind_spots: [str]}}`
- Modify `LocalRenderingProvider.render()` in `app/rendering/local/runner.py`:
  - After capturing screenshot, compute `RenderingConfidence` for the profile
  - Attach to `RenderingScreenshot` result: add `confidence_score: float`, `confidence_breakdown: dict` fields
- Modify `RenderingScreenshot` model in `app/rendering/models.py`:
  - Add `confidence_score: float | None` — 0–100
  - Add `confidence_breakdown: dict | None` — JSON serialized `ConfidenceBreakdown`
  - Add `confidence_recommendations: list[str] | None` — actionable recommendations
  - Alembic migration for new columns (nullable, no data migration)
- Modify `app/rendering/routes.py` — `POST /api/v1/rendering/screenshots` response:
  - Include `confidence_score` and `confidence_recommendations` per screenshot in response
  - Add `GET /api/v1/rendering/confidence/{client_id}` — returns current confidence data for a client (seed + calibration history)
- Modify `app/rendering/schemas.py` — add `RenderingConfidenceSchema`, `ConfidenceBreakdownSchema` to response models
**Security:** Confidence scoring is read-only analysis — no new inputs or external calls. Seed data is developer-maintained YAML. Calibration data stored in database with standard access controls.
**Verify:** Render a simple email (table layout, inline styles only) for Gmail → confidence >90%. Render a complex email (flexbox, VML, dark mode) for Outlook desktop → confidence <70% with "Word table cell width" in blind spots. Render for Thunderbird → confidence >85% (Gecko is standards-compliant). Confidence data appears in screenshot API response. `make test` passes.
- [ ] 27.2 Rendering confidence scoring

### 27.3 Pre-Send Rendering Gate `[Backend + Frontend]`
**What:** A configurable quality gate that evaluates rendering confidence across all target email clients before allowing ESP sync or export. If confidence drops below threshold for any high-priority client, the gate blocks the action and recommends specific remediation — either fix the HTML or validate with an external rendering provider.
**Why:** Currently, ESP sync (`POST /api/v1/connectors/sync`) and email export have no rendering quality gate — QA checks run independently but don't block sync. A pre-send gate turns rendering confidence into an enforceable workflow step. This is the critical integration point: everything the platform knows about rendering (ontology, emulators, confidence scores, CSS audit) becomes a single go/no-go decision. Without this, all the rendering intelligence is advisory; with this, it's a guardrail.
**Implementation:**
- Create `app/rendering/gate.py` — `RenderingSendGate`:
  - `async evaluate(html: str, target_clients: list[str] | None = None, project_id: str | None = None) -> GateResult`:
    - Runs local rendering across all target client profiles (from 27.1)
    - Computes per-client confidence (from 27.2)
    - Loads project-level thresholds (or global defaults)
    - Returns `GateResult(passed: bool, client_results: list[ClientGateResult], blocking_clients: list[str], recommendations: list[str])`
  - `ClientGateResult`:
    - `client_name: str`, `confidence_score: float`, `threshold: float`, `passed: bool`
    - `blocking_reasons: list[str]` — e.g., "flexbox detected — Outlook Word engine strips it (no fallback)"
    - `remediation: list[str]` — e.g., "Add MSO conditional with table-based fallback", "Validate with Litmus for Outlook 2019"
  - Default thresholds (configurable per project via design system):
    - Tier 1 (Gmail, Outlook, Apple Mail): 85% confidence required
    - Tier 2 (Yahoo, Samsung, Thunderbird): 70% confidence required
    - Tier 3 (Android Gmail, Outlook.com dark): 60% confidence required
  - Gate modes:
    - `enforce` — blocks sync/export if any tier-1 client fails (default for production sends)
    - `warn` — allows sync but returns warnings (default for draft/preview)
    - `skip` — no gate (for testing/development)
- Create `app/rendering/gate_config.py` — `RenderingGateConfig`:
  - `RenderingGateConfig` Pydantic model: `mode: GateMode`, `tier_thresholds: dict[str, float]`, `target_clients: list[str]`, `require_external_validation: list[str]` (clients that always require Litmus/EoA regardless of confidence)
  - Stored per-project in `Project.rendering_gate_config` JSON column (nullable, falls back to global defaults)
  - Global defaults in settings: `RENDERING__GATE_MODE`, `RENDERING__TIER1_THRESHOLD`, `RENDERING__TIER2_THRESHOLD`, `RENDERING__TIER3_THRESHOLD`
- Modify `app/connectors/service.py` — `ConnectorSyncService.sync()`:
  - Before syncing to ESP, run `RenderingSendGate.evaluate()`
  - If gate mode is `enforce` and gate fails → raise `RenderingGateError` (new exception) with blocking details
  - If gate mode is `warn` → proceed but attach warnings to sync result
  - Add `skip_rendering_gate: bool = False` parameter for explicit bypass (admin only)
- Modify `app/email_engine/service.py` — `EmailEngineService.export()`:
  - Same gate integration as connector sync
- Add API endpoints to `app/rendering/routes.py`:
  - `POST /api/v1/rendering/gate/evaluate` — run gate without blocking (preview mode)
  - `GET /api/v1/rendering/gate/config/{project_id}` — get project gate config
  - `PUT /api/v1/rendering/gate/config/{project_id}` — update project gate config (admin only)
- Frontend — gate results panel:
  - `cms/apps/web/src/components/rendering/gate-panel.tsx`:
    - Traffic-light summary: green (all pass) / yellow (warnings) / red (blocked)
    - Per-client row: client name, confidence bar (0–100), threshold line, pass/fail badge
    - Blocking reasons expandable per client
    - Remediation suggestions with actionable links ("Add MSO fallback" → links to builder with relevant section selected)
    - "Override & Send Anyway" button (admin only, logs override decision)
    - "Validate with Litmus" button (triggers external rendering test for failing clients)
  - Wire into connector sync flow — show gate panel before sync confirmation dialog
  - Wire into email export flow — show gate panel in export dialog
- Alembic migration: add `rendering_gate_config` JSON column to `projects` table
**Security:** Gate evaluation is read-only analysis. Override requires admin role. Override decisions logged to audit trail. No new external calls — gate uses existing local rendering pipeline. ESP sync still requires existing auth + rate limiting.
**Verify:** Simple email with high confidence → gate passes for all clients. Email with flexbox (no MSO fallback) → gate blocks Outlook with "flexbox unsupported" reason and "Add MSO conditional" remediation. Override sync → proceeds with audit log entry. Gate mode `warn` → sync proceeds with warnings in response. Per-project threshold override works. Frontend gate panel renders correctly with traffic-light summary. `make test` and `make check-fe` pass.
- [ ] 27.3 Pre-send rendering gate

### 27.4 Emulator Calibration Loop — Local vs External Ground Truth `[Backend]`
**What:** Automated feedback loop that compares local emulator screenshots against external provider (Litmus / Email on Acid) ground truth screenshots, computes per-emulator accuracy deltas, and adjusts confidence seed values. Runs on a sample of builds — not every build — to amortize external provider costs.
**Why:** Emulator rules are hand-coded approximations of real client sanitizer behavior. Without calibration against ground truth, emulators silently drift as email clients update their sanitizers (Gmail changes its class rewriting algorithm, Outlook.com adds new dark mode attributes, Yahoo changes its CSS allowlist). The calibration loop catches this drift: if the Gmail emulator's output diverges from real Gmail screenshots by more than a threshold, it flags the emulator as degraded and lowers its confidence score. Over time, this data also identifies which specific emulator rules need updating — "Gmail class rewriting accuracy dropped 8% since March" is actionable intelligence.
**Implementation:**
- Create `app/rendering/calibration/calibrator.py` — `EmulatorCalibrator`:
  - `async calibrate(html: str, client_id: str, local_screenshot: bytes, external_screenshot: bytes) -> CalibrationResult`:
    - Runs ODiff visual comparison between local and external screenshots
    - Returns `CalibrationResult(client_id: str, diff_percentage: float, diff_regions: list[Region], accuracy: float, regression: bool, regression_details: str | None)`
    - Accuracy = `max(0, 100 - diff_percentage * 2)` — 0% diff = 100% accuracy, 50% diff = 0% accuracy (linear, capped)
  - `async calibrate_batch(html: str, local_results: list[RenderingScreenshot], external_results: list[RenderingScreenshot]) -> list[CalibrationResult]`:
    - Match local and external screenshots by client name
    - Run calibration for each matched pair
    - Handle mismatches (external provider has clients we don't emulate locally → skip, log)
  - `async update_seeds(results: list[CalibrationResult]) -> None`:
    - Read `confidence_seeds.yaml`
    - For each result: exponential moving average update — `new_accuracy = 0.7 * old_accuracy + 0.3 * measured_accuracy`
    - Update `sample_count` and `last_calibrated` timestamp
    - Write back to YAML (or database table — see model below)
    - If accuracy dropped >10% from previous value → log `calibration.regression_detected` warning
- Create `app/rendering/calibration/models.py` — database persistence:
  - `CalibrationRecord` SQLAlchemy model:
    - `id`, `client_id`, `html_hash` (SHA-256 of input HTML), `local_diff_percentage`, `accuracy_score`, `diff_image` (optional — stored ODiff overlay PNG), `created_at`
    - `external_provider: str` — "litmus" | "emailonacid" | "manual"
    - `emulator_version: str` — hash of emulator rules at calibration time (detect if rules changed since calibration)
  - `CalibrationSummary` SQLAlchemy model:
    - `client_id` (unique), `current_accuracy`, `sample_count`, `last_calibrated`, `accuracy_trend` (last 10 values as JSON array), `known_blind_spots` (JSON array)
    - Replaces YAML seeds once calibration data exists — scorer reads from DB first, falls back to YAML
- Create `app/rendering/calibration/sampler.py` — `CalibrationSampler`:
  - Determines which builds should be sent to external providers for calibration
  - `should_calibrate(client_id: str) -> bool`:
    - Rate-limited: max N calibrations per client per day (configurable: `RENDERING__CALIBRATION_RATE_PER_CLIENT_PER_DAY`, default 3)
    - Priority: newly added emulators calibrate more frequently (sample_count < 10 → always calibrate)
    - Staleness: if `last_calibrated` > 7 days ago → increase sampling rate to 2×
    - Budget: total external API cost tracked — if monthly budget exceeded, stop calibrating (configurable: `RENDERING__CALIBRATION_MONTHLY_BUDGET`, default 0 = disabled)
  - `select_builds_for_calibration(builds: list[Build]) -> list[Build]`:
    - Selects diverse HTML samples — avoid calibrating on the same template repeatedly
    - Prefers complex emails (higher layout_complexity_score) for calibration — they reveal more emulator gaps
- Modify `RenderingService.submit_test()` in `app/rendering/service.py`:
  - After external provider returns screenshots, check if this was a calibration-eligible build
  - If so, run `EmulatorCalibrator.calibrate_batch()` with local + external screenshots
  - Store `CalibrationRecord` entries
  - Update `CalibrationSummary` via `update_seeds()`
- Add API endpoints to `app/rendering/routes.py`:
  - `GET /api/v1/rendering/calibration/summary` — current calibration state per client (accuracy, trend, last calibrated)
  - `POST /api/v1/rendering/calibration/trigger` — admin-only, force calibration for specific clients on a given HTML
  - `GET /api/v1/rendering/calibration/history/{client_id}` — calibration history for a client (last N records with diff percentages)
- Add Alembic migration: `calibration_records` and `calibration_summaries` tables
- Config: `RENDERING__CALIBRATION_ENABLED: bool = False`, `RENDERING__CALIBRATION_RATE_PER_CLIENT_PER_DAY: int = 3`, `RENDERING__CALIBRATION_MONTHLY_BUDGET: float = 0.0` (0 = disabled), `RENDERING__CALIBRATION_REGRESSION_THRESHOLD: float = 10.0` (percentage drop that triggers warning)
**Security:** Calibration reads existing local + external screenshots — no new external API calls beyond what `RenderingService` already supports. Budget cap prevents runaway costs. Admin-only trigger endpoint. Calibration records stored with standard database access controls. HTML hashes stored instead of full HTML (privacy — don't persist email content in calibration records).
**Verify:** Submit a rendering test with both local + Litmus screenshots → CalibrationRecord created with correct diff percentage. Accuracy seeds update via EMA formula. Force calibration via admin endpoint → works. Budget cap at $0 → no automatic calibrations run (only manual triggers). Accuracy regression >10% → warning logged. `GET /calibration/summary` returns per-client accuracy data. `make test` passes.
- [ ] 27.4 Emulator calibration loop

### 27.5 Headless Email Client Sandbox — SMTP-Based Real Sanitizer Capture `[Backend + Infrastructure]`
**What:** Optional self-hosted testing environment that sends emails via SMTP to a local mail server, then captures the *actual* sanitized HTML as rendered by webmail interfaces. This provides ground truth without depending on paid external providers, enabling unlimited calibration data at zero marginal cost.
**Why:** External providers (Litmus, EoA) charge per-screenshot. The calibration loop (27.4) works with them but costs add up. A self-hosted sandbox eliminates this cost for the most common clients. The approach: send email to Mailpit (local SMTP), then use Playwright to open a self-hosted webmail client (Roundcube) and capture the rendered DOM. This isn't a perfect replica of Gmail's sanitizer — but it provides a baseline for CSS-level validation. The real value is for Thunderbird (which can be run headless) and for detecting *our own* pipeline regressions (did our MSO conditional generation break?). For Gmail/Outlook.com-specific behavior, the emulators (27.1) plus external provider calibration (27.4) remain the primary approach.
**Implementation:**
- Create `app/rendering/sandbox/` package:
  - `sandbox.py` — `EmailSandbox`:
    - `async send_and_capture(html: str, subject: str, profiles: list[SandboxProfile]) -> list[SandboxResult]`:
      - Sends email via SMTP to Mailpit (configurable SMTP host/port)
      - For each profile: opens webmail URL in Playwright, navigates to the sent email, extracts rendered DOM, captures screenshot
      - Returns `SandboxResult(profile: str, rendered_html: str, screenshot: bytes, dom_diff: DOMDiff | None)`
    - `async extract_rendered_dom(page: Page, profile: SandboxProfile) -> str`:
      - Waits for email content to load (selector-based wait)
      - Extracts innerHTML of the email content container
      - This is the *post-sanitizer* HTML — the ground truth of what the webmail client did to the email
    - `async compute_dom_diff(original_html: str, rendered_html: str) -> DOMDiff`:
      - Structural diff between original and rendered HTML
      - Categories: `removed_elements`, `removed_attributes`, `removed_css_properties`, `added_elements`, `modified_styles`
      - This identifies exactly which sanitizer transforms the webmail applied
  - `profiles.py` — `SandboxProfile`:
    - `mailpit` — Mailpit's built-in HTML viewer (no sanitization — baseline)
    - `roundcube` — Roundcube webmail (PHP-based, applies its own HTML sanitizer — closest to a generic webmail)
    - `thunderbird_headless` — Thunderbird via `thunderbird --headless` with Playwright connection (if available)
    - Each profile: `name`, `webmail_url`, `content_selector` (CSS selector for email content container), `login_required: bool`, `credentials: dict | None`
  - `dom_diff.py` — `DOMDiff` computation:
    - `DOMDiff` dataclass: `removed_elements: list[str]`, `removed_attributes: dict[str, list[str]]`, `removed_css_properties: dict[str, list[str]]`, `added_elements: list[str]`, `modified_styles: dict[str, tuple[str, str]]` (property → (before, after))
    - Uses `lxml` for structural comparison — normalize whitespace, sort attributes, then tree diff
    - CSS diff: parse inline `style=""` attributes on both sides, compare property sets
  - `smtp.py` — `SandboxSMTP`:
    - `async send(html: str, subject: str, from_addr: str, to_addr: str) -> str` (returns message ID)
    - Uses `aiosmtplib` to send to local SMTP server
    - Constructs proper MIME message with HTML content type, UTF-8 encoding
    - Adds standard email headers (Date, Message-ID, MIME-Version)
- Docker Compose additions (optional — only for sandbox testing):
  - `services/mailpit/` — Mailpit container (SMTP + webmail UI) — lightweight, Go-based, ideal for testing
  - `services/roundcube/` — Roundcube container (connects to Mailpit's IMAP) — optional, for webmail sanitizer testing
  - Both behind `profiles: [sandbox]` in docker-compose — only start when explicitly requested
- Add API endpoints to `app/rendering/routes.py`:
  - `POST /api/v1/rendering/sandbox/test` — send email to sandbox, capture results (admin only)
    - Request: `{ html, subject, profiles: ["mailpit", "roundcube"] }`
    - Response: per-profile rendered HTML, screenshot, DOM diff
  - `GET /api/v1/rendering/sandbox/health` — check sandbox infrastructure availability (Mailpit reachable, Roundcube reachable)
- Integrate with calibration loop (27.4):
  - `CalibrationSampler` can select sandbox as a zero-cost calibration source
  - Sandbox results feed into `EmulatorCalibrator.calibrate()` with `external_provider="sandbox"`
  - Lower calibration weight for sandbox (0.5×) vs real external providers (1.0×) — sandbox is less authoritative
- Config: `RENDERING__SANDBOX_ENABLED: bool = False`, `RENDERING__SANDBOX_SMTP_HOST: str = "localhost"`, `RENDERING__SANDBOX_SMTP_PORT: int = 1025`, `RENDERING__SANDBOX_MAILPIT_URL: str = "http://localhost:8025"`, `RENDERING__SANDBOX_ROUNDCUBE_URL: str = "http://localhost:9080"`, `RENDERING__SANDBOX_PLAYWRIGHT_TIMEOUT_MS: int = 15000`
**Security:** Sandbox is entirely local — SMTP to localhost, webmail on localhost. No emails leave the network. Sandbox endpoints admin-only. Email content sent to Mailpit is ephemeral (in-memory by default, configurable persistence). Docker Compose profiles ensure sandbox containers only run when explicitly started. Sandbox credentials (if Roundcube requires login) stored in environment variables, never in code.
**Verify:** Start sandbox infrastructure (`docker compose --profile sandbox up`). Send email via sandbox endpoint → Mailpit receives it, screenshot captured. DOM diff between original and Mailpit-rendered HTML shows minimal changes (Mailpit is near-passthrough). Roundcube DOM diff shows sanitizer transforms (stripped some CSS, modified some attributes). Sandbox health endpoint reports both services healthy. Calibration loop uses sandbox results with 0.5× weight. `make test` passes (sandbox tests use mocked SMTP — no Docker dependency). `RENDERING__SANDBOX_ENABLED=false` → sandbox endpoints return 503.
- [ ] 27.5 Headless email client sandbox

### 27.6 Frontend Rendering Dashboard & Tests `[Frontend + Full-Stack]`
**What:** Unified rendering intelligence dashboard that surfaces emulator previews, confidence scores, calibration status, gate results, and sandbox DOM diffs in a single view. Plus comprehensive test suite for the entire Phase 27 pipeline.
**Why:** All the rendering intelligence built in 27.1–27.5 needs a user-facing surface. Users need to see at a glance: "How will my email look across 14 client profiles? Which clients am I confident about? Which need external validation? What did the pre-send gate flag?" Without this dashboard, the backend capabilities remain API-only — powerful but invisible.
**Implementation:**
- Frontend — Rendering Dashboard:
  - `cms/apps/web/src/components/rendering/rendering-dashboard.tsx` — main dashboard:
    - **Preview Grid**: 14 client profile thumbnails in a responsive grid (4 columns desktop, 2 mobile)
      - Each thumbnail: client icon, name, confidence badge (green >85, yellow 60–85, red <60)
      - Click thumbnail → full-size preview with confidence breakdown overlay
      - Toggle: light mode / dark mode for clients with dark profiles
    - **Confidence Summary Bar**: horizontal segmented bar showing overall rendering health
      - Segments: per-client, colored by confidence tier, width proportional to client market share
      - Hover segment → tooltip with client name, confidence %, known blind spots
      - Overall score: weighted average by market share (e.g., "Overall rendering confidence: 87%")
    - **Gate Status Panel**: traffic-light indicator from pre-send gate (27.3)
      - Green: all clients pass → "Ready to send"
      - Yellow: warnings present → expandable list of warnings
      - Red: blocked → expandable list of blocking reasons + remediation steps
    - **Calibration Health** (collapsible, admin view):
      - Per-emulator accuracy trend (sparkline last 10 calibrations)
      - Last calibrated date per client
      - Regression alerts (accuracy dropped >10%)
      - "Recalibrate" button per client (triggers 27.4 manual calibration)
  - `cms/apps/web/src/components/rendering/client-preview-card.tsx`:
    - Individual client card: screenshot, confidence score, breakdown tooltip, "View Full" button
    - Comparison toggle: local preview vs last external provider screenshot (if available from calibration)
    - DOM diff viewer (for sandbox results): side-by-side original vs rendered HTML with diff highlighting
  - `cms/apps/web/src/components/rendering/confidence-bar.tsx`:
    - Reusable confidence bar component with threshold line and color zones
    - Props: `score`, `threshold`, `label`, `breakdown`
  - SWR hooks:
    - `cms/apps/web/src/hooks/use-rendering.ts`:
      - `useRenderingPreviews(html: string, clients: string[])` — triggers `POST /rendering/screenshots`, returns screenshots + confidence
      - `useRenderingGate(html: string, projectId: string)` — triggers `POST /rendering/gate/evaluate`, returns gate result
      - `useCalibrationSummary()` — `GET /rendering/calibration/summary`
      - `useCalibrationHistory(clientId: string)` — `GET /rendering/calibration/history/{clientId}`
  - Types:
    - `cms/apps/web/src/types/rendering.ts` — `RenderingConfidence`, `GateResult`, `ClientGateResult`, `CalibrationSummary`, `ConfidenceBreakdown`
  - Route: integrate into existing rendering section or add `/rendering` route with RBAC (developer+ for previews, admin for calibration)
- Tests — Backend:
  - `app/rendering/local/tests/test_emulators_expanded.py` — 25+ tests:
    - Each new emulator's rules produce expected transforms (Yahoo class rewriting, Samsung dark mode, Outlook Word CSS stripping, etc.)
    - Existing Gmail/Outlook.com emulators unchanged (regression)
    - Emulator rule chaining order matters (test rule ordering)
    - Edge cases: empty HTML, HTML without `<style>`, HTML with only inline styles
  - `app/rendering/local/tests/test_confidence.py` — 15+ tests:
    - Simple HTML → high confidence for all clients
    - Complex HTML (flexbox + VML) → low confidence for Outlook desktop
    - Layout complexity scoring: nested tables, flexbox, positioning
    - Calibration seeds correctly loaded and applied
    - Formula produces expected scores for known inputs
  - `app/rendering/tests/test_gate.py` — 15+ tests:
    - Gate passes for simple email with high confidence
    - Gate blocks when tier-1 client below threshold
    - Gate warns in `warn` mode
    - Gate skips in `skip` mode
    - Per-project threshold override
    - Admin bypass with audit log
    - Integration with connector sync (mock sync → gate blocks → sync fails with `RenderingGateError`)
  - `app/rendering/calibration/tests/test_calibrator.py` — 15+ tests:
    - ODiff comparison produces correct diff percentage
    - EMA update formula: accuracy converges toward measured value
    - Regression detection when accuracy drops >10%
    - Budget cap prevents automatic calibration when exceeded
    - Sampler selects diverse HTML samples
    - Sandbox results weighted at 0.5×
  - `app/rendering/sandbox/tests/test_sandbox.py` — 10+ tests:
    - SMTP send constructs valid MIME message (mock SMTP)
    - DOM diff correctly identifies removed elements, attributes, CSS properties
    - Sandbox profiles configured correctly
    - Health check returns correct status (mock HTTP)
- Tests — Frontend:
  - `cms/apps/web/src/components/rendering/__tests__/rendering-dashboard.test.tsx`
  - `cms/apps/web/src/components/rendering/__tests__/gate-panel.test.tsx`
  - `cms/apps/web/src/components/rendering/__tests__/confidence-bar.test.tsx`
  - `cms/apps/web/src/hooks/__tests__/use-rendering.test.ts`
- Target: 90+ tests total across all test files
**Verify:** `make test` passes (80+ backend tests). `make check-fe` passes (10+ frontend tests). All 14 rendering profiles produce screenshots with confidence scores. Gate panel renders correctly in all states (pass/warn/block). Calibration dashboard shows per-client accuracy trends. DOM diff viewer highlights removed CSS properties. Dashboard responsive on mobile. `make check` all green.
- [ ] 27.6 Frontend rendering dashboard & tests

---

## Security Checklist (Run Before Each Sprint Demo)

- [ ] All new endpoints have auth dependency injection
- [ ] All new endpoints have rate limiting configured
- [ ] All request schemas validate input (no raw strings to DB)
- [ ] All response schemas exclude sensitive fields
- [ ] No credentials in logs (grep for password, secret, key, token in log output)
- [ ] New database tables have appropriate RLS policies
- [ ] Frontend forms sanitise input before API calls
- [ ] Preview iframes use sandbox attribute
- [ ] Error responses don't leak internal details
- [ ] Audit entries created for all state-changing operations
- [ ] CORS configuration checked (no wildcards)
- [ ] Docker containers run as non-root
- [ ] New environment variables documented in `.env.example`

---

## Success Criteria (Updated)

| Metric | Phase 25 (Current) | Target (Phase 26) | Target (Phase 27) |
|--------|--------------------|--------------------|---------------------|
| Campaign build time | Under 1 hour (Kestra parallel pipelines) | Under 1 hour (faster deterministic CSS pipeline) | Under 1 hour (unchanged — rendering gate adds <2s) |
| Cross-client rendering defects | Near-zero (property-tested + plugin checks) | Near-zero + pre-send CSS audit per client | Near-zero + pre-send rendering gate with per-client confidence |
| QA checks | 16+ (plugin checks) | 17+ (CSS compatibility audit) | 17+ (unchanged — gate is workflow, not a check) |
| CSS pipeline latency | 1–5s (dual inlining via BeautifulSoup + Juice) | <500ms (single-pass sidecar, no dual inlining) | <500ms (unchanged) |
| Template CSS precompilation | N/A (re-optimized every build) | Amortized at registration (0ms CSS optimization at build time) | Amortized (unchanged) |
| CSS compatibility visibility | Log-only (not user-facing) | Per-build audit matrix in QA UI with per-client coverage scores | Per-build audit + rendering confidence scores + gate traffic light |
| Email CSS output size | Optimal per-client bundles | Optimal + pre-compiled template CSS | Optimal (unchanged) |
| Ontology freshness | Real-time change detection + plugin extensions | Real-time + sidecar ontology sync | Real-time + emulator calibration drift detection |
| Cloud AI API spend | Under £600/month (budget caps + plugin cost tracking) | Under £600/month (no change — Phase 26 is deterministic, zero LLM) | Under £600/month (no change — Phase 27 is deterministic, zero LLM) |
| Email client emulators | 2 (Gmail Web, Outlook.com) | 2 (unchanged) | 7 (+ Yahoo, Samsung, Outlook desktop, Thunderbird, Android Gmail) |
| Rendering profiles | 6 | 6 (unchanged) | 14 (+ 8 new client profiles incl. dark mode variants) |
| Rendering confidence scoring | N/A (binary pass/fail) | N/A | Per-client 0–100 confidence with breakdown + recommendations |
| Pre-send rendering gate | N/A | N/A | Configurable enforce/warn/skip with per-project thresholds |
| Emulator calibration | N/A (hand-coded, no feedback) | N/A | Automated calibration loop vs Litmus/EoA + self-hosted sandbox |
