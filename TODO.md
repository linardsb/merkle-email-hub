# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–16):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing).

---

## Phase 17 — Visual Regression Agent & VLM-Powered QA

**What:** Add a 10th AI agent that uses vision-language models to screenshot rendered emails across simulated clients, detect rendering discrepancies by comparing screenshots, and generate targeted CSS fixes. Integrates Playwright for headless rendering, ODiff for perceptual image diffing, and a VLM (Claude vision / GPT-4o vision) for semantic analysis of visual defects. Includes a component baseline screenshot system for regression detection across builds.
**Why:** Every email platform (Litmus, Email on Acid, Parcel) relies on server-side rendering farms or manual screenshot review. No platform uses AI to _understand_ what went wrong visually and auto-fix it. The hub already has 9 agents, a blueprint engine, and a self-correcting CRAG loop — a Visual QA agent is the natural 10th agent that closes the "render → detect → fix" loop entirely within the platform. The ScreenCoder (2025) multi-agent decomposition pattern (grounding → planning → generation) maps directly to the blueprint engine's node architecture. This single feature makes the hub irreplaceable because it eliminates the $500+/month Litmus dependency and delivers faster, smarter results.
**Dependencies:** Phase 11 (QA engine + agent architecture), Phase 14 (checkpoint for long-running visual pipelines), Phase 16 (CRAG mixin pattern for auto-correction).
**Design principle:** Each sub-task is independently shippable behind feature flags. Visual regression can run as QA check #12 without the VLM fix agent. VLM agent can run standalone without ODiff baselines. Screenshots stored alongside `ComponentVersion` baselines — no new storage infrastructure required.

### 17.1 Playwright Email Rendering Service `[Backend]`
**What:** A rendering service that takes compiled email HTML and produces screenshots across simulated email client viewports. Uses Playwright with pre-configured viewport sizes and CSS injection to simulate client-specific rendering behaviors (Gmail style stripping, Outlook word-engine quirks, Apple Mail full CSS support). Outputs PNG screenshots with metadata (viewport, simulated client, timestamp).
**Why:** The hub currently has no way to see what an email looks like in different clients without external services. Playwright is already a dev dependency (used in e2e tests). Reusing it for email rendering avoids new infrastructure. Client simulation via CSS injection and style stripping is 90% accurate for layout validation without needing actual email client access.
**Implementation:**
- Create `app/rendering/screenshot.py` — `EmailScreenshotService` class:
  - `async render_screenshots(html: str, clients: list[str] | None = None) -> list[ScreenshotResult]` — renders HTML in Playwright, returns list of `ScreenshotResult(client_name: str, viewport: tuple[int, int], image_bytes: bytes, css_modifications: list[str])`
  - Pre-configured client profiles in `RENDERING_PROFILES: dict[str, RenderingProfile]`: `gmail_web` (strip `<style>` blocks, max-width 680px), `outlook_2019` (inject Word engine CSS constraints: no flexbox, no grid, table-only layout enforcement), `apple_mail` (full CSS, 600px), `outlook_dark` (dark mode color inversion), `mobile_ios` (375px viewport)
  - Each profile: `RenderingProfile(name: str, viewport_width: int, viewport_height: int, css_injections: list[str], style_strip_patterns: list[re.Pattern], dark_mode: bool)`
  - Uses `async with async_playwright() as p: browser = await p.chromium.launch(headless=True)` — single browser instance, new context per render
  - Screenshot via `page.screenshot(type="png", full_page=True, clip={"x": 0, "y": 0, "width": viewport_width, "height": min(page_height, 4096)})` — cap at 4096px to prevent memory issues
  - Images stored as bytes in memory (not disk) — caller decides storage
- Create `app/rendering/schemas.py` — `ScreenshotResult`, `RenderingProfile`, `ScreenshotRequest`, `ScreenshotResponse` (base64 encoded images for API transport)
- Modify `app/rendering/routes.py` — add `POST /api/v1/rendering/screenshots` with auth + rate limiting (`5/minute` — rendering is expensive). Accepts `{html: str, clients: list[str]}`, returns `{screenshots: list[{client: str, image_base64: str}]}`
- Config (`app/core/config.py` → `RenderingConfig`): `screenshots_enabled: bool = False`, `screenshot_max_clients: int = 5`, `screenshot_timeout_ms: int = 15000`
**Security:** HTML rendered in Playwright's sandboxed Chromium — no network access (`context.route("**/*", lambda route: route.abort())` blocks all external requests). Screenshot output is a PNG image — no executable content. Rate limited to prevent abuse. HTML input validated via existing `validate_output()` before rendering.
**Verify:** Render a known email HTML with `gmail_web` profile → `<style>` blocks stripped from rendered output, width constrained to 680px. Render same HTML with `apple_mail` → styles preserved. Render with `outlook_2019` → flexbox/grid properties have no visual effect (simulated). Screenshot dimensions match configured viewport. `screenshots_enabled=False` returns 501. `make test` passes. Rendering completes within timeout.
- [x] ~~17.1 Playwright email rendering service~~ DONE

### 17.2 ODiff Visual Regression Baseline System `[Backend]`
**What:** Perceptual image diffing system using ODiff (Zig/SIMD, handles anti-aliasing noise) that compares rendered screenshots against stored baselines. Creates and manages baseline screenshots per `ComponentVersion` and per `GoldenTemplate`. Outputs diff images highlighting pixel regions that changed, with a configurable similarity threshold. Diff images attachable to the approval portal.
**Why:** Manual "does this look right?" screenshot review is the #1 bottleneck in email QA. ODiff (from game QA / visual regression domain) distinguishes real layout changes from anti-aliasing noise — something pixel-exact diff tools can't do. Storing baselines per `ComponentVersion` means every component update automatically gets regression-tested against its last known-good state. This is proven technology repurposed for email.
**Implementation:**
- Install `odiff` as a binary dependency (Zig-compiled, ~2MB, available via npm or direct binary). Python wrapper via subprocess call
- Create `app/rendering/visual_diff.py` — `VisualDiffService` class:
  - `async compare(baseline: bytes, current: bytes, threshold: float = 0.01) -> DiffResult` — returns `DiffResult(identical: bool, diff_percentage: float, diff_image: bytes | None, pixel_count: int, changed_regions: list[Region])`
  - `async update_baseline(entity_type: str, entity_id: int, client: str, image: bytes) -> None` — stores baseline screenshot. Entity types: `component_version`, `golden_template`
  - `async get_baseline(entity_type: str, entity_id: int, client: str) -> bytes | None` — retrieves stored baseline
  - Region detection: parse ODiff output regions into `Region(x: int, y: int, width: int, height: int)` for highlighting in UI
- Create `app/rendering/models.py` — `ScreenshotBaseline` SQLAlchemy model: `id`, `entity_type` (varchar), `entity_id` (int), `client_name` (varchar), `image_data` (LargeBinary), `image_hash` (varchar, SHA-256), `created_at`, `updated_at`. Unique constraint on `(entity_type, entity_id, client_name)`
- Alembic migration for `screenshot_baselines` table
- Create `app/rendering/repository.py` — `ScreenshotBaselineRepository` with CRUD + `get_by_entity(entity_type, entity_id, client_name)` + `list_by_entity(entity_type, entity_id)`
- Modify `app/rendering/routes.py` — add `POST /api/v1/rendering/visual-diff` (accepts two base64 images, returns diff), `GET /api/v1/rendering/baselines/{entity_type}/{entity_id}` (list baselines), `POST /api/v1/rendering/baselines/{entity_type}/{entity_id}/update` (update baseline from current screenshot)
- Config: `visual_diff_enabled: bool = False`, `visual_diff_threshold: float = 0.01` (1% pixel difference triggers alert)
**Security:** Baseline images stored in DB (not filesystem) — BOLA-safe via entity ownership validation. ODiff subprocess called with fixed arguments only — no user input in command. Diff images are PNG output only. All endpoints require auth + developer/admin role.
**Verify:** Upload baseline for a golden template → modify template CSS → re-render → diff detects changes with diff_percentage > threshold. Identical screenshots → `identical=True`, `diff_percentage=0.0`. Anti-aliasing-only changes (sub-pixel rendering differences) → below threshold. Baseline CRUD works. `make test` passes.
- [x] ~~17.2 ODiff visual regression baseline system~~ DONE

### 17.3 VLM Visual Analysis Agent `[Backend]`
**What:** A new AI agent (`VisualQAAgent`) that consumes rendered screenshots and uses a vision-language model to identify rendering defects with semantic understanding — not just pixel diffs but "the CTA button is cut off in Outlook", "the two-column layout collapsed to single column in Gmail", "dark mode inverted the logo but not the background". Produces structured `VisualDefect` reports with suggested CSS fixes.
**Why:** ODiff tells you _where_ pixels changed. A VLM tells you _what went wrong_ and _how to fix it_. This is the ScreenCoder pattern applied to email: grounding (identify the defect region), planning (determine the CSS cause), generation (produce the fix). No email platform does this — it's the single most differentiated capability the hub can offer.
**Implementation:**
- Create `app/ai/agents/visual_qa/` package:
  - `schemas.py` — `VisualDefect(region: Region, description: str, severity: str, affected_clients: list[str], suggested_fix: str, css_property: str | None)`, `VisualQAResult(defects: list[VisualDefect], summary: str, auto_fixable: bool)`
  - `service.py` — `VisualQAAgentService(BaseAgentService)`:
    - Override `process()` to accept multimodal input: rendered screenshots + original HTML
    - Build VLM prompt: "Compare these email screenshots rendered in {clients}. Identify rendering defects — layout breaks, missing elements, color inversions, text overflow, image sizing issues. For each defect, specify the CSS property causing it and suggest a fix."
    - Parse VLM response into structured `VisualDefect` objects via `response_format` (structured output)
    - Cross-reference detected CSS properties against ontology (`load_ontology()`) for known compatibility issues
    - Generate fix suggestions that reference specific ontology fallbacks when available
  - `SKILL.md` — agent skill file following existing pattern (5 evaluation criteria: defect_detection_accuracy, fix_correctness, false_positive_rate, client_coverage, severity_calibration)
- Create `app/ai/agents/visual_qa/decisions.py` — `VisualQADecisions` structured output schema (following 11.22.8 pattern): `defects: tuple[VisualDefect, ...]`, `overall_rendering_score: float`, `critical_clients: list[str]`
- Modify `app/ai/blueprints/nodes/` — add `visual_qa_node.py` following existing node pattern (`VisualQANode(BlueprintNode)`). Runs after export node as optional validation step. Integrates with checkpoint system (Phase 14)
- Modify `app/ai/blueprints/handoff.py` — add `VisualQAHandoff(AgentHandoff)` with `screenshots: dict[str, str]` (client → base64), `baseline_diffs: list[DiffSummary]`
- Config: `AI__VISUAL_QA_ENABLED: bool = False`, `AI__VISUAL_QA_MODEL: str = "claude-sonnet-4-5-20250514"` (vision-capable model required), `AI__VISUAL_QA_CLIENTS: list[str] = ["gmail_web", "outlook_2019", "apple_mail"]`
**Security:** Screenshots are generated internally (17.1) — no user-uploaded images in VLM prompts. VLM prompt contains only screenshot images + HTML structure — no PII. Response parsed via structured output (no raw HTML injection). Model selection restricted to vision-capable models via capability check. Output CSS fixes validated via `sanitize_html_xss()` before application.
**Verify:** Generate email with known Outlook incompatibility (flexbox layout) → VLM detects "layout collapsed in Outlook", suggests table-based alternative. Generate fully compatible email → VLM reports zero defects. Cross-reference: VLM-detected CSS issue matches ontology known incompatibility. False positive rate < 10% on golden template test suite. `visual_qa_enabled=False` skips entirely. `make test` passes.
- [x] ~~17.3 VLM visual analysis agent~~ DONE

### 17.4 Auto-Fix Pipeline Integration `[Backend]`
**What:** Connect the VLM Visual QA agent's defect reports back into the CRAG correction loop to automatically fix detected visual issues. When `VisualQAAgent` identifies fixable defects, feed the defect descriptions + suggested fixes back to the Scaffolder/OutlookFixer agent as correction instructions. Creates a render → detect → fix → re-render verification cycle.
**Why:** Detection without correction is just a report. The hub's CRAG mixin (16.5) already handles the "detect CSS issue → retrieve fallback → regenerate" pattern. This extends it to visual defects detected by the VLM, creating a fully autonomous visual QA loop that no human needs to review for common rendering issues.
**Implementation:**
- Create `app/ai/agents/visual_qa/correction.py` — `VisualCorrectionService`:
  - `async correct_visual_defects(html: str, defects: list[VisualDefect], model: str) -> tuple[str, list[str]]` — takes original HTML + detected defects, generates corrected HTML
  - For each defect with `css_property` set: look up ontology fallback via `load_ontology().fallbacks_for()` (reusing CRAG pattern)
  - For defects without known CSS property: include VLM's `suggested_fix` in the correction prompt
  - Correction prompt: "Fix the following rendering issues in this HTML email: {defect_descriptions}. Use these known fallbacks: {ontology_fallbacks}. Preserve all existing functionality."
  - Output validated via `validate_output()` → `extract_html()` → `sanitize_html_xss()`
  - Capped at 1 correction round (same as CRAG) — avoids infinite loops
- Modify `app/ai/blueprints/nodes/visual_qa_node.py` — after VLM analysis, if `auto_fixable=True` and `defects` exist: call `VisualCorrectionService.correct_visual_defects()`, then re-render screenshots for verification. If re-render shows improvement (lower diff percentage), accept the fix. If regression, keep original
- Modify `app/ai/agents/validation_loop.py` — add `VisualCRAGMixin` extending `CRAGMixin` with visual correction capability. `_visual_crag_validate(html, screenshots, model)` chains: screenshot → VLM analysis → correction → re-screenshot → verify
- Config: `AI__VISUAL_QA_AUTO_FIX: bool = False` (separate from detection — detection can run without auto-fix), `AI__VISUAL_QA_MAX_CORRECTION_ROUNDS: int = 1`
**Security:** Correction prompt contains only defect descriptions (generated by VLM, not user input) + ontology fallback code (trusted data). Output sanitised via `sanitize_html_xss()`. Re-render verification prevents regression — if fix makes things worse, original HTML preserved. Cost capped at 1 round.
**Verify:** Email with flexbox layout → VLM detects Outlook break → auto-fix replaces with table layout → re-render confirms fix. Email with no defects → no correction attempted (zero LLM cost). Auto-fix that causes regression → original preserved. `auto_fix=False` runs detection only. `make test` passes.
- [x] ~~17.4 Auto-fix pipeline integration~~ DONE

### 17.5 Frontend Visual QA Dashboard `[Frontend]`
**What:** Frontend UI for visual regression results: side-by-side screenshot comparison across clients, diff overlay toggle, defect annotations with severity badges, baseline management, and "Accept Fix" / "Reject Fix" actions for VLM-suggested corrections. Integrated into the workspace as a new tab alongside the existing QA results panel.
**Why:** The visual QA data is only useful if developers can see and act on it. Side-by-side client comparison replaces the Litmus screenshot review workflow entirely within the hub. Baseline management lets teams track visual regressions across template versions.
**Implementation:**
- Create `cms/apps/web/src/components/visual-qa/` — `VisualQAPanel.tsx` (main container), `ClientComparisonGrid.tsx` (side-by-side screenshots), `DiffOverlay.tsx` (toggle diff image over screenshot), `DefectAnnotation.tsx` (clickable defect regions with description tooltip), `BaselineManager.tsx` (view/update baselines)
- Create `cms/apps/web/src/hooks/use-visual-qa.ts` — SWR hooks: `useScreenshots(templateId)`, `useVisualDiff(templateId)`, `useBaselines(entityType, entityId)`, `useUpdateBaseline()`
- Modify workspace layout — add "Visual QA" tab in the QA results section (alongside existing HTML validation, CSS support, etc.)
- Add i18n keys across 6 locales (en, de, fr, es, it, nl) — ~30 keys for labels, tooltips, status messages
- SDK regeneration for new rendering endpoints
**Security:** Screenshots displayed via `<img src="data:image/png;base64,...">` — no external URLs. Diff overlay uses canvas API — no innerHTML. Baseline update requires developer/admin role.
**Verify:** Render screenshots → display in grid → toggle diff overlay → annotations appear at correct regions. Baseline update flow works end-to-end. Responsive layout at all viewport sizes. `make check-fe` passes. i18n keys present in all 6 locales.
- [x] ~~17.5 Frontend visual QA dashboard~~ DONE

### 17.6 Tests & SDK Integration `[Full-Stack]`
**What:** Comprehensive test suite for visual regression pipeline: screenshot rendering tests, ODiff integration tests, VLM agent unit tests (with mocked vision responses), correction pipeline tests, baseline CRUD tests, route tests with auth/rate limiting. SDK regeneration covering all new rendering endpoints.
**Why:** Visual QA involves multiple async services (Playwright, ODiff, VLM) that must be tested in isolation and integration. The rendering service especially needs reliability testing — browser crashes, timeouts, and memory limits must be handled gracefully.
**Implementation:**
- Create `app/rendering/tests/` — `test_screenshot.py` (rendering profiles, viewport simulation, timeout handling), `test_visual_diff.py` (ODiff integration, threshold logic, baseline CRUD), `test_routes.py` (auth, rate limiting, error handling for all new endpoints)
- Create `app/ai/agents/visual_qa/tests/` — `test_visual_qa_agent.py` (VLM response parsing, defect detection, structured output), `test_correction.py` (auto-fix pipeline, regression prevention, ontology integration)
- SDK regeneration via `@hey-api/openapi-ts`
- Target: 40+ tests covering all paths
**Security:** Tests verify auth requirements on all endpoints. Rate limiting verified. Baseline BOLA protection tested.
**Verify:** `make test` passes with all new tests. `make check` all green. SDK types match API responses. No regression in existing test suite.
- [x] ~~17.6 Tests & SDK integration~~ DONE

---

## Phase 18 — Rendering Resilience & Property-Based Testing

**What:** Build a chaos testing engine that deliberately degrades email HTML to simulate real-world email client behaviors, and a property-based testing framework that generates hundreds of random email configurations to verify invariants hold. Adds "resilience score" to the QA pipeline alongside the existing 11 checks.
**Why:** Current QA tests emails in ideal conditions — clean HTML, all styles applied, images loaded. Real inboxes are hostile: Gmail strips `<style>` blocks, Outlook ignores modern CSS, corporate firewalls block images, dark mode inverts colors unexpectedly. Chaos engineering (borrowed from distributed systems / Google's 2025 framework) applied to email rendering reveals fragility that golden template tests miss. Property-based testing (borrowed from formal verification / QuickCheck) covers the combinatorial space — the hub currently tests 7 golden templates, but there are thousands of possible section/client/dark-mode/locale combinations.
**Dependencies:** Phase 11 (QA engine checks), Phase 16 (CRAG for auto-correction of discovered issues), Phase 17 (screenshot rendering for visual verification).
**Design principle:** Chaos profiles are composable — test one degradation at a time or stack multiples. Property generators are seeded for reproducibility. Both integrate as optional QA checks — existing pipeline unchanged when disabled. Results feed back into knowledge base as RAG documents.

### 18.1 Email Chaos Engine `[Backend]`
**What:** A testing engine that applies controlled degradations to email HTML, simulating real-world email client behaviors. Each degradation is a composable `ChaosProfile` — strip all `<style>` blocks (Gmail), remove media queries (many mobile clients), block all images (corporate firewalls / image-off settings), inject dark mode color inversion (Outlook/Apple Mail), remove MSO conditional comments, convert all `<div>` to `<span>` (some webmail), limit HTML to 102KB (Gmail clipping), strip `class` attributes. Runs the degraded HTML through the existing QA engine to measure resilience.
**Why:** An email that passes QA with all styles intact but breaks when Gmail strips styles is a false positive. Chaos testing reveals these fragilities before they reach real inboxes. Google's chaos engineering framework (2025) showed systems with ongoing resilience validation recovered 32% faster — the same principle applies to email templates. No email platform offers this; competitors test "does it render correctly?" while this tests "does it survive the real world?"
**Implementation:**
- Create `app/qa_engine/chaos/` package:
  - `profiles.py` — `ChaosProfile(name: str, description: str, transformations: list[Callable[[str], str]])` and pre-built profiles:
    - `GMAIL_STYLE_STRIP`: remove all `<style>` and `<link rel="stylesheet">` elements via BeautifulSoup
    - `IMAGE_BLOCKED`: replace all `<img>` `src` with transparent 1x1 GIF, verify alt text visibility
    - `DARK_MODE_INVERSION`: inject `filter: invert(1) hue-rotate(180deg)` on `<body>`, simulate `[data-ogsc]` and `[data-ogsb]` attribute addition
    - `OUTLOOK_WORD_ENGINE`: strip flexbox/grid properties, convert `<div>` containers to `<table>` wrappers, remove CSS custom properties
    - `GMAIL_CLIPPING`: truncate HTML at 102,400 bytes, verify "View entire message" doesn't cut mid-tag
    - `MOBILE_NARROW`: inject `max-width: 375px` on body, verify no horizontal scroll (content overflow)
    - `CLASS_STRIP`: remove all `class` attributes (some security-focused email clients)
    - `MEDIA_QUERY_STRIP`: remove all `@media` rules from inline and block styles
  - `engine.py` — `ChaosEngine` class:
    - `async run_chaos_test(html: str, profiles: list[str] | None = None) -> ChaosTestResult` — applies each profile, runs QA checks on degraded HTML, returns per-profile results
    - `ChaosTestResult(original_score: float, degraded_scores: dict[str, float], resilience_score: float, critical_failures: list[ChaosFailure])` — `resilience_score` = weighted average of degraded scores / original score
    - `ChaosFailure(profile: str, check_name: str, severity: str, description: str)` — specific QA check failures introduced by degradation
  - `composable.py` — `compose_profiles(*profiles) -> ChaosProfile` — stack multiple degradations for worst-case testing
- Modify `app/qa_engine/service.py` — add `async run_chaos_test(template_id: int, html: str) -> ChaosTestResult` calling `ChaosEngine`. Optional — only runs when `chaos_testing_enabled=True`
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/chaos-test` with auth + rate limiting (`3/minute`)
- Modify `app/qa_engine/schemas.py` — add `ChaosTestResult`, `ChaosFailure`, `ChaosTestRequest` response schemas. Add optional `resilience_score: float | None` to existing `QARunResponse`
- Config: `QA__CHAOS_TESTING_ENABLED: bool = False`, `QA__CHAOS_DEFAULT_PROFILES: list[str] = ["gmail_style_strip", "image_blocked", "dark_mode_inversion", "gmail_clipping"]`
**Security:** Chaos transformations are deterministic pure functions — no LLM calls, no external network. HTML mutations use BeautifulSoup (parser, not eval). Degraded HTML is temporary (never persisted). Rate limited to prevent CPU abuse from expensive transformations.
**Verify:** Apply `GMAIL_STYLE_STRIP` to email with inline styles → QA score unchanged. Apply to email relying on `<style>` block → QA score drops, specific CSS failures reported. Stack `GMAIL_STYLE_STRIP` + `IMAGE_BLOCKED` → compound failures detected. `resilience_score` correctly reflects degradation impact. 102KB Gmail clipping correctly truncates. `chaos_testing_enabled=False` skips entirely. `make test` passes.
- [x] ~~18.1 Email chaos engine~~ DONE

### 18.2 Property-Based Email Testing Framework `[Backend]`
**What:** Define email invariants (properties that must always hold regardless of content) and a generator that produces hundreds of random email configurations to verify these invariants. Borrows from QuickCheck/Hypothesis — generates random section combinations, content lengths, image counts, nesting depths, and client targets, then asserts invariants hold across all generated cases. Failing cases are automatically minimised to find the simplest reproduction.
**Why:** The hub tests 7 golden templates — a tiny fraction of the possible configuration space. Property-based testing covers combinations that no human would think to test: a 12-section email with RTL text, 3 nested tables, and Outlook dark mode. This catches edge cases that manifest in production but never appear in curated test suites. Agentic property-based testing (2025) found genuine bugs in NumPy and other mature libraries.
**Implementation:**
- Create `app/qa_engine/property_testing/` package:
  - `invariants.py` — `EmailInvariant` Protocol with `check(html: str) -> InvariantResult`, pre-built invariants:
    - `ContrastRatio`: all text has WCAG AA contrast ratio >= 4.5:1 against background
    - `ImageWidth`: no `<img>` wider than 600px (email max width standard)
    - `LinkIntegrity`: every `<a>` has non-empty `href`, no `javascript:` URIs
    - `SizeLimit`: total HTML < 102KB (Gmail clipping threshold)
    - `AltTextPresence`: every `<img>` has non-empty `alt` attribute
    - `TableNestingDepth`: table nesting depth <= 8 (Outlook rendering limit)
    - `ViewportFit`: content renders within 600px width without horizontal scroll
    - `EncodingValid`: all characters are valid UTF-8, no null bytes
    - `MSOBalance`: every `<!--[if mso]>` has matching `<![endif]-->`
    - `DarkModeReady`: if `prefers-color-scheme` used, both light and dark values specified
  - `generators.py` — `EmailGenerator` class using `hypothesis` library:
    - `generate_section_config() -> SectionConfig` — random section count (1-15), types from `SectionBlock` categories, content lengths (10-2000 chars)
    - `generate_style_config() -> StyleConfig` — random font stacks, color palettes (including near-threshold contrast), spacing values
    - `generate_client_target() -> str` — weighted random client selection matching real-world market share distribution
    - `generate_email(config: EmailConfig) -> str` — uses `TemplateAssembler` to build valid HTML from random config
  - `runner.py` — `PropertyTestRunner`:
    - `async run(invariants: list[str], num_cases: int = 100, seed: int | None = None) -> PropertyTestReport` — generates N random emails, checks all invariants, returns failures with minimal reproduction
    - `PropertyTestReport(total_cases: int, passed: int, failed: int, failures: list[PropertyFailure], seed: int)` — `PropertyFailure` includes the minimised config that triggers the invariant violation
    - Hypothesis `@given` integration for automatic shrinking of failing cases
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/property-test` with auth + rate limiting (`1/minute` — computationally expensive)
- Config: `QA__PROPERTY_TESTING_ENABLED: bool = False`, `QA__PROPERTY_TEST_CASES: int = 100`, `QA__PROPERTY_TEST_SEED: int | None = None` (fixed seed for CI reproducibility)
- Add `make test-properties` command — runs property tests with fixed seed for CI
**Security:** Generators produce synthetic HTML only — no user data. Hypothesis library is well-established (no security concerns). Rate limited aggressively due to CPU cost. Generated emails never persisted — temporary in-memory only.
**Verify:** Run 100 property tests → at least some invariant violations found (proves the generator covers edge cases). Fix a known invariant violation → re-run with same seed → violation no longer appears. `SizeLimit` invariant catches oversized emails. `ContrastRatio` catches near-threshold color combinations. `make test-properties` completes within 60 seconds. `make test` passes.
- [ ] 18.2 Property-based email testing framework

### 18.3 Resilience Score Integration & Knowledge Feedback `[Backend]`
**What:** Integrate chaos test results and property test findings into the existing QA pipeline as optional check #12 ("rendering resilience"). Auto-generate knowledge base documents from discovered failures — each new chaos failure becomes a RAG-retrievable document describing the failure pattern, affected clients, and recommended fix. This creates a self-improving knowledge base that grows from every test run.
**Why:** Chaos and property testing produce insights that should compound across projects. A Gmail clipping issue found on Project A should inform email generation on Project B. The hub's knowledge base (Phase 8-9) + RAG pipeline (Phase 16) can surface these learnings at generation time — "this section pattern caused Gmail clipping for 3 previous projects."
**Implementation:**
- Create `app/qa_engine/checks/rendering_resilience.py` — `RenderingResilienceCheck(QACheck)`:
  - `async run(html: str, config: QAConfig) -> QACheckResult` — runs chaos engine with default profiles, returns pass/fail based on `resilience_score >= threshold`
  - Threshold: `QA__RESILIENCE_THRESHOLD: float = 0.7` (email must retain 70% of its QA score under degradation)
- Modify `app/qa_engine/service.py` — register `RenderingResilienceCheck` as check #12 (optional, behind feature flag)
- Create `app/qa_engine/chaos/knowledge_writer.py` — `ChaosKnowledgeWriter`:
  - `async write_failure_documents(failures: list[ChaosFailure], project_id: int) -> list[int]` — creates `Document` entries in knowledge base for each unique failure pattern
  - Document format: title = "{profile} failure: {check_name}", content = markdown description with affected clients, failure details, recommended fix, HTML snippet showing the problematic pattern
  - Deduplication: check for existing document with same title + project before creating new one
  - Tags: `domain="chaos_findings"`, `section_type="failure_pattern"`
- Modify `app/knowledge/service.py` — `search()` considers chaos_findings domain when query matches rendering/resilience patterns
- Config: `QA__CHAOS_AUTO_DOCUMENT: bool = False` (auto-generate knowledge docs from failures), `QA__RESILIENCE_CHECK_ENABLED: bool = False`
**Security:** Knowledge documents contain only structural HTML patterns (no PII). Document creation uses existing `KnowledgeService.ingest_document()` with tenant isolation via project_id.
**Verify:** Run chaos test → failures found → knowledge documents auto-created → subsequent RAG search for same pattern returns the chaos finding. Resilience check passes for well-structured email (score > 0.7). Resilience check fails for fragile email (single-column layout breaks under style stripping). `make test` passes.
- [ ] 18.3 Resilience score integration & knowledge feedback

### 18.4 Frontend Chaos & Property Testing UI `[Frontend]`
**What:** Frontend components for chaos test results (per-profile score breakdown, failure details, "Fix This" action dispatching to CRAG) and property test reports (pass/fail summary, failing case inspector with minimised config display). Integrated into the QA dashboard.
**Why:** Chaos and property test data must be actionable — developers need to see which degradations break their email and drill into specific failures. The "Fix This" action connecting to CRAG creates a one-click fix workflow.
**Implementation:**
- Create `cms/apps/web/src/components/qa/ChaosTestPanel.tsx` — profile score radar chart, failure list with severity, "Run Chaos Test" action button
- Create `cms/apps/web/src/components/qa/PropertyTestPanel.tsx` — pass/fail gauge, failing invariant list, expandable case detail with minimised config
- Create `cms/apps/web/src/hooks/use-chaos-test.ts`, `use-property-test.ts` — SWR hooks for new endpoints
- Add i18n keys across 6 locales — ~25 keys
- SDK regeneration for chaos/property endpoints
**Security:** No raw HTML displayed in UI — all results are structured data. "Fix This" action uses existing CRAG endpoint with auth.
**Verify:** Run chaos test → results display in panel → per-profile scores shown → failure details expandable. Property test → pass/fail summary → failing cases inspectable. `make check-fe` passes.
- [ ] 18.4 Frontend chaos & property testing UI

### 18.5 Tests & Documentation `[Full-Stack]`
**What:** Full test suite for chaos engine (profile application correctness, composability, QA integration), property testing (invariant checks, generator coverage, seed reproducibility), resilience check (#12), knowledge feedback writer. ADR documenting the resilience testing architecture.
**Implementation:**
- Create `app/qa_engine/chaos/tests/` — `test_chaos_engine.py` (profile transformations, composability, resilience scoring), `test_knowledge_writer.py` (document creation, deduplication)
- Create `app/qa_engine/property_testing/tests/` — `test_invariants.py` (each invariant against known pass/fail HTML), `test_generators.py` (output validity, seed reproducibility), `test_runner.py` (end-to-end with shrinking)
- Route tests for new endpoints (auth, rate limiting)
- Target: 35+ tests
- ADR-007 in `docs/ARCHITECTURE.md` — Rendering Resilience Testing
**Verify:** `make test` passes. `make check` all green. No regression in existing tests.
- [ ] 18.5 Tests & documentation

---

## Phase 19 — Outlook Transition Advisor & Email CSS Compiler

**What:** Two capabilities that address the most urgent industry event (Microsoft ending Word-based Outlook rendering, October 2026) and the most impactful technical optimization (an email-specific CSS compiler using Lightning CSS). The Outlook Transition Advisor analyzes templates for Word-engine dependencies and generates migration plans. The CSS compiler performs AST-level optimization targeting "email client VMs" — removing unsupported properties, auto-converting modern CSS to table equivalents, and inlining optimally.
**Why:** October 2026 is the biggest rendering engine change in email history. Every enterprise with Outlook-targeted templates needs a migration plan. No platform offers automated analysis of Word-engine dependencies or a clear modernization path. The CSS compiler goes beyond Juice (string-level inlining) to AST-level optimization using the hub's own ontology data — producing smaller, faster, more compatible output than any existing tool.
**Dependencies:** Phase 11 (QA engine + existing Outlook Fixer agent), Phase 16 (ontology data for CSS compatibility), Phase 8-9 (knowledge graph for workaround patterns).
**Design principle:** Advisor is non-destructive — analyzes and reports without modifying templates. Compiler optimizations are opt-in per property class. Both use the hub's ontology as the single source of truth for CSS compatibility.

### 19.1 Outlook Word-Engine Dependency Analyzer `[Backend]`
**What:** Static analyzer that scans email HTML for Word rendering engine dependencies: VML shapes (`v:*` elements), ghost tables (tables used purely for layout in MSO conditionals), MSO conditional comments (`<!--[if mso]>`), Word-specific CSS (`mso-*` properties), DPI-dependent image sizing, and `.ExternalClass` hacks. Produces a dependency report with severity ratings and modernization suggestions.
**Why:** Developers have accumulated years of Outlook workarounds — ghost tables, VML buttons, mso-line-height-rule hacks. After October 2026, these are dead code that bloats HTML and adds maintenance burden. The analyzer tells you exactly which workarounds can be safely removed based on your audience's Outlook version distribution.
**Implementation:**
- Create `app/qa_engine/outlook_analyzer/` package:
  - `detector.py` — `OutlookDependencyDetector`:
    - `analyze(html: str) -> OutlookAnalysis` — parses HTML via BeautifulSoup, returns structured dependency report
    - Detection rules (all regex/AST — no LLM):
      - `VML_SHAPES`: find `<v:roundrect>`, `<v:rect>`, `<v:oval>`, `<v:shape>` elements
      - `GHOST_TABLES`: `<table>` elements inside `<!--[if mso]>` conditionals with no visible content
      - `MSO_CONDITIONALS`: all `<!--[if mso]>` / `<!--[if !mso]>` blocks with content categorization
      - `MSO_CSS_PROPERTIES`: `mso-line-height-rule`, `mso-table-lspace`, `mso-padding-alt`, etc.
      - `DPI_IMAGES`: images with explicit `width`/`height` attributes that differ from CSS dimensions (DPI compensation)
      - `EXTERNAL_CLASS`: `.ExternalClass` CSS rules
      - `WORD_WRAP_HACKS`: `word-wrap`, `word-break` with mso-specific values
    - `OutlookAnalysis(dependencies: list[OutlookDependency], total_count: int, removable_count: int, byte_savings: int, modernization_plan: list[ModernizationStep])`
    - `OutlookDependency(type: str, location: str, line_number: int, code_snippet: str, severity: str, removable: bool, modern_replacement: str | None)`
  - `modernizer.py` — `OutlookModernizer`:
    - `modernize(html: str, analysis: OutlookAnalysis, target: str = "new_outlook") -> str` — applies safe modernizations:
      - Replace VML buttons with CSS `border-radius` + `background-color` (New Outlook = Chromium)
      - Remove ghost tables, unwrap content
      - Remove `mso-*` CSS properties (or keep inside `<!--[if mso]>` for dual-support period)
      - Replace `.ExternalClass` hacks with standard CSS
    - `target` parameter: `"new_outlook"` (aggressive — remove all Word hacks), `"dual_support"` (keep hacks inside conditionals for transition period), `"audit_only"` (report but don't modify)
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/outlook-analysis` (analyze), `POST /api/v1/qa/outlook-modernize` (apply modernizations) with auth + rate limiting
- Config: `QA__OUTLOOK_ANALYZER_ENABLED: bool = False`, `QA__OUTLOOK_DEFAULT_TARGET: str = "dual_support"`
**Security:** Analyzer is read-only — parses HTML via BeautifulSoup (no eval). Modernizer applies deterministic transformations only. No external calls. Output sanitized via `sanitize_html_xss()`.
**Verify:** Analyze email with VML buttons → all VML elements detected, modern CSS replacement suggested. Analyze clean modern email → zero dependencies. Modernize with `new_outlook` → VML replaced with CSS, ghost tables removed, byte size reduced. Modernize with `dual_support` → hacks wrapped in conditionals but functional in both engines. `make test` passes.
- [ ] 19.1 Outlook Word-engine dependency analyzer

### 19.2 Audience-Aware Outlook Migration Planner `[Backend]`
**What:** A migration planning service that combines the dependency analysis (19.1) with audience data (Outlook version distribution from ESP analytics or manual input) to produce a phased migration plan. Shows which workarounds are safe to remove now (< 5% of audience on old Outlook), which need the dual-support period, and projects a timeline for full modernization.
**Why:** "Remove all Outlook hacks" is too aggressive for most enterprises — they need to know which hacks are safe to remove based on their actual audience. A financial services client with 40% Outlook 2016 users has a different migration timeline than a tech company with 90% Gmail. This audience-aware planning is what makes the tool consultancy-grade.
**Implementation:**
- Create `app/qa_engine/outlook_analyzer/planner.py` — `MigrationPlanner`:
  - `plan(analysis: OutlookAnalysis, audience: AudienceProfile) -> MigrationPlan` — produces phased plan
  - `AudienceProfile(client_distribution: dict[str, float])` — e.g., `{"outlook_2016": 0.15, "outlook_2019": 0.20, "new_outlook": 0.10, "gmail_web": 0.35, ...}`
  - `MigrationPlan(phases: list[MigrationPhase], total_savings_bytes: int, estimated_completion: str, risk_assessment: str)`
  - `MigrationPhase(name: str, dependencies_to_remove: list[OutlookDependency], audience_impact: float, safe_when: str)` — `safe_when` = "now" / "when old_outlook < 10%" / "after october 2026"
  - Phase ordering: safest removals first (audience_impact < 1%), riskier removals later
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/outlook-migration-plan` accepting analysis + audience profile
- Modify `app/connectors/service.py` — add `async get_audience_profile(connection_id: int) -> AudienceProfile | None` — pull client distribution from ESP analytics API (Braze/SFMC provide this). Returns `None` if ESP doesn't support analytics
**Security:** Audience data is aggregate statistics (percentages per client) — no PII. ESP analytics API calls use existing encrypted credentials from `ESPConnection`. Migration plan contains only code patterns and percentages.
**Verify:** Plan with 40% old Outlook → conservative phased approach, most hacks kept. Plan with 5% old Outlook → aggressive modernization recommended. Plan with no audience data → generic timeline based on industry averages. ESP audience pull works for Braze (mock server). `make test` passes.
- [ ] 19.2 Audience-aware Outlook migration planner

### 19.3 Lightning CSS Email Compiler `[Backend]`
**What:** An email-specific CSS compiler built on Lightning CSS (Rust, 100x faster than JS parsers) that performs AST-level optimization for email clients. Unlike Juice (which does string-level CSS inlining), this compiler understands the email rendering landscape: removes CSS properties unsupported by target clients (driven by ontology data), auto-converts modern CSS to email-safe equivalents, merges redundant declarations, removes dead selectors, and produces optimal inlined output.
**Why:** Current CSS processing in the Maizzle pipeline uses Juice for inlining — a brute-force approach that doesn't understand email client constraints. The compiler produces smaller HTML (often 15-25% reduction) by eliminating properties that would be ignored anyway, and converts modern CSS to compatible equivalents (e.g., `gap` → `margin` on child elements for Outlook). Lightning CSS's Python bindings make this a drop-in enhancement.
**Implementation:**
- Install `lightningcss` Python bindings (via `pip install lightningcss`) or use Rust binary via subprocess
- Create `app/email_engine/css_compiler/` package:
  - `compiler.py` — `EmailCSSCompiler`:
    - `compile(html: str, target_clients: list[str] | None = None) -> CompilationResult` — full compilation pipeline
    - `CompilationResult(html: str, original_size: int, compiled_size: int, removed_properties: list[str], conversions: list[CSSConversion], warnings: list[str])`
    - Pipeline stages:
      1. **Parse**: extract all CSS (inline styles + `<style>` blocks) via Lightning CSS parser
      2. **Analyze**: cross-reference each property against ontology support matrix for target clients
      3. **Transform**: apply conversions for unsupported properties (ontology `Fallback` objects provide alternatives)
      4. **Eliminate**: remove properties with zero support across all target clients (dead CSS)
      5. **Optimize**: Lightning CSS minification — merge longhands into shorthands, reduce `calc()`, remove redundant declarations
      6. **Inline**: inject optimized styles as inline `style` attributes (replacing Juice)
      7. **Output**: final HTML with optimized CSS
  - `conversions.py` — `CSSConversion` rules driven by ontology fallbacks:
    - `flexbox_to_table`: convert `display:flex` containers to `<table>` equivalents
    - `grid_to_table`: convert `display:grid` layouts to table-based
    - `gap_to_margin`: convert `gap` property to `margin` on child elements
    - `custom_properties_to_values`: resolve `var(--x)` references to computed values
    - `modern_to_outlook`: generate MSO conditional blocks for properties that need dual-path
  - `integration.py` — `MaizzleCompilerPlugin` — hook into Maizzle sidecar build pipeline (replace Juice step)
- Modify `services/maizzle-builder/` — add optional CSS compiler step via POST /compile-css endpoint (alternative to Juice inlining)
- Modify `app/email_engine/routes.py` — add `POST /api/v1/email/compile-css` for standalone CSS compilation
- Config: `EMAIL_ENGINE__CSS_COMPILER_ENABLED: bool = False`, `EMAIL_ENGINE__CSS_COMPILER_TARGET_CLIENTS: list[str] = ["gmail_web", "outlook_2019", "apple_mail", "yahoo_mail"]`
**Security:** CSS parsing via Lightning CSS (Rust, memory-safe). No eval/exec of CSS content. Ontology data is read-only. Output validated via `sanitize_html_xss()`. No external network calls.
**Verify:** Compile email with `display:flex` targeting `[outlook_2019]` → flexbox converted to table layout. Compile targeting `[gmail_web, apple_mail]` only → flexbox preserved (both support it). Size reduction measured: compiled output < original for all golden templates. Juice-replaced output renders identically to Juice output in golden template screenshots. `make test` passes.
- [ ] 19.3 Lightning CSS email compiler

### 19.4 Frontend Outlook Advisor & Compiler Dashboard `[Frontend]`
**What:** Frontend UI for Outlook migration analysis (dependency heatmap, migration timeline, "Modernize" action), audience profile input/ESP import, and CSS compilation results (size before/after, removed properties, conversion list). Integrated into workspace toolbar and QA panel.
**Implementation:**
- Create `cms/apps/web/src/components/outlook/` — `OutlookAdvisorPanel.tsx` (dependency list with severity), `MigrationTimeline.tsx` (phased plan visualization), `AudienceProfileInput.tsx` (manual entry or ESP import)
- Create `cms/apps/web/src/components/email-engine/CSSCompilerPanel.tsx` — before/after size comparison, property removal list, conversion details
- SWR hooks: `useOutlookAnalysis()`, `useMigrationPlan()`, `useCSSCompile()`
- i18n: ~30 keys across 6 locales
- SDK regeneration
**Verify:** Full Outlook analysis → migration plan displayed → "Modernize" applies changes → re-analysis shows reduction. CSS compiler → size reduction shown. `make check-fe` passes.
- [ ] 19.4 Frontend Outlook advisor & compiler dashboard

### 19.5 Tests & Documentation `[Full-Stack]`
**What:** Tests for Outlook analyzer (detection of all 7 dependency types), modernizer (safe transformations, dual-support mode), migration planner (audience-weighted phasing), CSS compiler (all conversion rules, size reduction, ontology integration). 45+ tests. ADR-008.
**Implementation:**
- Create `app/qa_engine/outlook_analyzer/tests/` — `test_detector.py`, `test_modernizer.py`, `test_planner.py` — 25+ tests
- Create `app/email_engine/css_compiler/tests/` — `test_compiler.py`, `test_conversions.py` — 20+ tests
- Route tests for all new endpoints
- ADR-008 in `docs/ARCHITECTURE.md` — Outlook Transition & CSS Compilation
**Verify:** `make test` passes. `make check` all green.
- [ ] 19.5 Tests & documentation

---

## Phase 20 — Gmail AI Intelligence & Deliverability

**What:** Three capabilities targeting the Gmail ecosystem: (1) predict how Gmail's Gemini AI will summarize an email, (2) auto-inject schema.org structured data based on email intent, (3) pre-send deliverability scoring. Plus BIMI readiness verification.
**Why:** Gmail's AI filtering (launched early 2026) creates a new layer between sender and recipient — emails are now summarized, categorized, and filtered by AI before users see them. No email platform addresses this. Schema.org markup directly impacts Gmail Promotions tab visibility (deal annotations, product carousels). BIMI is mandatory for enterprise trust signals in 2026. Deliverability scoring closes the "looks good but never reaches inbox" gap.
**Dependencies:** Phase 11 (QA engine for deliverability checks), Phase 16 (query router intent classification — reusable for email intent classification).
**Design principle:** Gmail AI prediction is best-effort (no one has access to Gemini's actual summarization model) — we use a local LLM to approximate. Schema.org injection is deterministic (rule-based, not LLM). Deliverability scoring is heuristic-based with optional LLM enhancement.

### 20.1 Gmail AI Summary Predictor `[Backend]`
**What:** A service that estimates how Gmail's Gemini-powered summarization will present an email to the recipient. Generates a predicted "summary card" — the 1-2 sentence preview that appears in Gmail's inbox view, the categorization (Primary/Promotions/Updates/Social), and the likely "key action" extraction. Uses an LLM to simulate Gemini's summarization behavior based on the email's subject line, preview text, and body content.
**Why:** Gmail's AI summarization means the email you send is not the email users see. If Gemini summarizes a promotional email as "Company wants you to buy X at Y% off", that summary IS the email for most users. Optimizing the email to produce favorable AI summaries is an entirely new discipline — and no one offers tooling for it. This is greenfield competitive advantage.
**Implementation:**
- Create `app/qa_engine/gmail_intelligence/` package:
  - `predictor.py` — `GmailSummaryPredictor`:
    - `async predict(html: str, subject: str, from_name: str) -> GmailPrediction` — extracts text content from HTML, feeds to LLM with Gmail-specific summarization prompt
    - `GmailPrediction(summary_text: str, predicted_category: str, key_actions: list[str], promotion_signals: list[str], improvement_suggestions: list[str])`
    - Summarization prompt engineered to mimic Gemini's known behaviors: focus on CTAs, pricing, urgency signals, sender reputation heuristics
    - Category prediction based on: sender domain, subject line patterns, CTA density, unsubscribe link presence, schema.org markup presence
    - `improvement_suggestions`: specific changes to subject/preview text/content that would improve the summary
  - `optimizer.py` — `PreviewTextOptimizer`:
    - `async optimize(html: str, subject: str, target_summary: str | None = None) -> OptimizedPreview` — suggests preview text and subject line variations that produce better AI summaries
    - `OptimizedPreview(original_subject: str, suggested_subjects: list[str], original_preview: str, suggested_previews: list[str], reasoning: str)`
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/gmail-predict` (prediction), `POST /api/v1/qa/gmail-optimize` (suggestions)
- Config: `QA__GMAIL_PREDICTOR_ENABLED: bool = False`, `QA__GMAIL_PREDICTOR_MODEL: str = "gpt-4o-mini"` (cost-efficient for summarization)
**Security:** Email content passed to LLM for summarization — same security model as existing agents (no PII expected in template HTML). Prompt sanitized via `sanitize_prompt()`. LLM response is text-only — no code execution. Rate limited.
**Verify:** Promotional email with pricing → predicted category = "Promotions", summary includes price/discount. Transactional email (order confirmation) → predicted category = "Updates", summary includes order details. Subject line optimization → suggestions differ from original and are coherent. `gmail_predictor_enabled=False` skips entirely. `make test` passes.
- [ ] 20.1 Gmail AI summary predictor

### 20.2 Schema.org Auto-Markup Injection `[Backend]`
**What:** Automatically inject appropriate schema.org JSON-LD structured data into email HTML based on classified email intent. Supports Gmail Actions (ConfirmAction, ViewAction, TrackAction), Deal Annotations (promotions tab product cards with price/discount/expiry), Event markup (RSVP actions), and Order tracking (ViewOrderAction with status). Intent classification reuses the hub's QueryRouter pattern (16.1).
**Why:** Schema.org markup directly impacts Gmail inbox experience: Deal Annotations surface product images and prices in the Promotions tab, Action buttons appear in the inbox list view without opening the email, and Event markup enables RSVP from the inbox. Most email platforms ignore this entirely — markup is added manually by developers who happen to know about it. Auto-injection based on detected intent makes it effortless.
**Implementation:**
- Create `app/email_engine/schema_markup/` package:
  - `classifier.py` — `EmailIntentClassifier`:
    - `classify(html: str, subject: str) -> EmailIntent` — regex-first classification (reusing 16.1 pattern):
      - `promotional`: pricing patterns (`$`, `£`, `%`, "sale", "discount", "offer"), CTA patterns ("Shop now", "Buy", "Order")
      - `transactional`: order number patterns, shipping/tracking keywords, receipt indicators
      - `event`: date/time patterns with RSVP/register/attend keywords
      - `newsletter`: "unsubscribe" + regular content without commercial CTAs
      - `notification`: status update patterns, account activity keywords
    - `EmailIntent(type: str, confidence: float, extracted_entities: dict)` — entities include detected prices, dates, order numbers, product names
  - `injector.py` — `SchemaMarkupInjector`:
    - `inject(html: str, intent: EmailIntent) -> str` — injects JSON-LD `<script type="application/ld+json">` in `<head>`
    - Intent → markup mapping:
      - `promotional` → `Product` + `Offer` with `price`, `priceCurrency`, `availabilityEnds` (if detected), `DealAnnotation` for Gmail Promotions tab
      - `transactional` → `Order` + `OrderStatus` with `orderNumber`, `TrackAction` with tracking URL
      - `event` → `Event` with `startDate`, `location`, `RsvpAction` or `ViewAction`
      - `notification` → `ViewAction` linking to relevant dashboard/page
    - Validates generated JSON-LD against schema.org vocabulary before injection
  - `validator.py` — `SchemaValidator` — validates JSON-LD structure, required properties per type, Gmail-specific requirements (sender verification, HTTPS action URLs)
- Modify `app/email_engine/service.py` — add optional schema injection step in email build pipeline (after HTML compilation, before export)
- Modify `app/email_engine/routes.py` — add `POST /api/v1/email/inject-schema` for standalone schema injection
- Config: `EMAIL_ENGINE__SCHEMA_INJECTION_ENABLED: bool = False`, `EMAIL_ENGINE__SCHEMA_TYPES: list[str] = ["promotional", "transactional", "event"]`
**Security:** JSON-LD is structured data — no executable code. Action URLs validated as HTTPS only (Gmail requirement). No user-provided URLs in generated markup — only URLs extracted from the email HTML itself. Injection point is `<head>` only — no body modification.
**Verify:** Email with "$50 off, expires March 30" → `DealAnnotation` injected with price=$50, discount, expiry date. Order confirmation email → `Order` + `TrackAction` injected. Event invitation → `Event` + `RsvpAction` injected. Newsletter → no markup injected (intentional — newsletters don't benefit). JSON-LD validates against schema.org. `make test` passes.
- [ ] 20.2 Schema.org auto-markup injection

### 20.3 Deliverability Prediction Score `[Backend]`
**What:** Pre-send deliverability scoring that analyzes email HTML for spam trigger patterns, image-to-text ratio, link density, authentication readiness (SPF/DKIM/DMARC/BIMI), and content quality signals. Produces a 0-100 deliverability score with specific improvement recommendations. Integrates as QA check #13.
**Why:** An email that renders perfectly but lands in spam is worse than one with rendering issues that reaches the inbox. The global average inbox placement rate is 83.1% — meaning ~17% of emails never reach the recipient. Current QA checks validate rendering and accessibility but ignore deliverability entirely. This closes the gap.
**Implementation:**
- Create `app/qa_engine/checks/deliverability.py` — `DeliverabilityCheck(QACheck)`:
  - `async run(html: str, config: QAConfig) -> QACheckResult` — scoring across dimensions:
    - **Content quality** (0-25): text-to-image ratio (>60% text = good), link density (<1 link per 50 words), no URL shorteners, no excessive capitalization, no spam trigger words ("FREE!!!", "Act now", "Limited time")
    - **HTML hygiene** (0-25): valid `DOCTYPE`, character encoding declared, reasonable HTML size (<102KB), no hidden text (same color as background), no single-image emails
    - **Authentication readiness** (0-25): checks for DKIM alignment hints in headers (if available), DMARC-friendly sender patterns, List-Unsubscribe header presence, unsubscribe link in body
    - **Engagement signals** (0-25): preview text present and distinct from subject, personalization tokens detected, clear primary CTA, reasonable content length
  - Each dimension produces sub-scores + specific `DeliverabilityIssue(dimension: str, severity: str, description: str, fix: str)`
  - Overall score = sum of dimension scores. Pass threshold: `QA__DELIVERABILITY_THRESHOLD: int = 70`
- Modify `app/qa_engine/service.py` — register as optional check #13
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/deliverability-score` for standalone scoring
- Config: `QA__DELIVERABILITY_CHECK_ENABLED: bool = False`, `QA__DELIVERABILITY_THRESHOLD: int = 70`
**Security:** All analysis is local — no external API calls. Spam trigger word list is static (no dynamic loading). No PII in scoring output.
**Verify:** Clean transactional email → score > 85. Spam-like promotional email (ALL CAPS subject, image-heavy, many links) → score < 50. Adding List-Unsubscribe → score increases. Adding preview text → score increases. Single-image email → HTML hygiene score penalized. `make test` passes.
- [ ] 20.3 Deliverability prediction score

### 20.4 BIMI Readiness Check `[Backend]`
**What:** Verify BIMI (Brand Indicators for Message Identification) compliance: check sending domain's DMARC policy (must be quarantine or reject), validate BIMI DNS record format, verify SVG logo meets Gmail's Tiny PS format requirements, and check CMC (Common Mark Certificate) status. Generates the BIMI TXT record as part of deployment checklist.
**Why:** BIMI displays the sender's verified logo in the inbox — directly impacting open rates (up to 10% increase per industry data). Google dropped the trademark requirement in 2025 (CMC now sufficient), making BIMI accessible to all brands. But setup is complex (DMARC + DNS + SVG format + certificate) — automating the readiness check removes the barrier.
**Implementation:**
- Create `app/qa_engine/checks/bimi.py` — `BIMIReadinessCheck`:
  - `async check_domain(domain: str) -> BIMIStatus` — DNS lookups for DMARC record, BIMI record, SVG validation
  - `BIMIStatus(dmarc_ready: bool, dmarc_policy: str, bimi_record_exists: bool, bimi_record: str | None, svg_valid: bool | None, cmc_status: str, generated_record: str, issues: list[str])`
  - DMARC check: DNS TXT lookup for `_dmarc.{domain}`, parse `p=` policy (must be `quarantine` or `reject`)
  - BIMI check: DNS TXT lookup for `default._bimi.{domain}`, parse `v=BIMI1; l={svg_url}; a={pem_url}`
  - SVG validation: if BIMI record exists, fetch SVG URL, validate Tiny PS profile (square, no external references, specific element restrictions)
  - Record generator: produce the TXT record string for the domain based on provided SVG/certificate URLs
- Modify `app/qa_engine/routes.py` — add `POST /api/v1/qa/bimi-check` accepting `{domain: str}` with auth + rate limiting
- Config: `QA__BIMI_CHECK_ENABLED: bool = False`
**Security:** DNS lookups are read-only. SVG fetch uses `httpx` with timeout + size limit (max 32KB). No execution of SVG content. Domain input validated (must be valid domain format). Rate limited to prevent DNS abuse.
**Verify:** Domain with full BIMI setup → all checks pass, record validated. Domain with DMARC `p=none` → `dmarc_ready=False`, specific guidance to change policy. Domain without BIMI record → `bimi_record_exists=False`, generated record template provided. Invalid SVG (non-square, external references) → `svg_valid=False`. `make test` passes.
- [ ] 20.4 BIMI readiness check

### 20.5 Frontend Gmail Intelligence Panel & Tests `[Frontend]`
**What:** Frontend UI for Gmail prediction (predicted summary card preview, category badge, optimization suggestions), deliverability score gauge, BIMI status indicator, and schema.org markup preview. Plus full test suite (30+ tests) and SDK regeneration.
**Implementation:**
- Create `cms/apps/web/src/components/gmail/` — `GmailPredictionPanel.tsx`, `SummaryCardPreview.tsx` (renders predicted summary card), `DeliverabilityGauge.tsx`, `BIMIStatusBadge.tsx`, `SchemaPreview.tsx` (shows injected JSON-LD)
- SWR hooks: `useGmailPrediction()`, `useDeliverabilityScore()`, `useBIMICheck()`, `useSchemaInject()`
- i18n: ~35 keys across 6 locales
- Tests: `test_gmail_predictor.py` (8 tests), `test_schema_markup.py` (10 tests), `test_deliverability.py` (8 tests), `test_bimi.py` (6 tests), route tests
- SDK regeneration
**Verify:** `make test` passes. `make check-fe` passes. `make check` all green.
- [ ] 20.5 Frontend Gmail intelligence panel & tests

---

## Phase 21 — Real-Time Ontology Sync & Competitive Intelligence

**What:** Auto-sync the email compatibility ontology from the caniemail open-source dataset, track email client rendering changes over time, and build a competitive intelligence layer that monitors how email client updates affect existing templates.
**Why:** The ontology (335+ CSS properties × 25+ clients) is the hub's single source of truth for compatibility — but it's manually maintained. The caniemail dataset updates weekly with community-contributed data. Auto-syncing keeps the hub current without manual effort. Client rendering change detection creates a proprietary dataset that goes beyond what caniemail offers — real-time awareness of when a client changes behavior.
**Dependencies:** Phase 8-9 (ontology + knowledge graph), Phase 16 (structured queries use ontology data), Phase 17 (screenshot baselines for change detection).
**Design principle:** Ontology sync is additive-only by default — new data merges, existing data never deleted without manual approval. Change detection is non-blocking — findings are advisory, surfaced in UI, not gates.

### 21.1 caniemail Auto-Sync Pipeline `[Backend]`
**What:** A scheduled pipeline that fetches the latest caniemail dataset from GitHub, diffs against the current ontology, and merges new/updated support data. Runs daily via the existing `DataPoller` infrastructure. Produces a changelog of what changed for developer review.
**Why:** caniemail is the industry standard for CSS email support data — open source, community-maintained, updated weekly. Currently the hub's ontology was seeded once; keeping it current requires manual effort. Auto-sync ensures every CSS support query returns current data. The @jsx-email/doiuse-email npm package proves this data is machine-readable.
**Implementation:**
- Create `app/knowledge/ontology/caniemail_sync.py` — `CanIEmailSyncService`:
  - `async sync(dry_run: bool = False) -> SyncReport` — fetch, diff, merge pipeline
  - Fetch: `httpx.AsyncClient.get("https://raw.githubusercontent.com/hteumeuleu/caniemail/master/data/...")` — individual feature JSON files
  - Parse: convert caniemail format (feature name, stats per client, notes, links) to ontology `CSSProperty` + `SupportLevel` format
  - Diff: compare fetched data against current ontology — identify new properties, updated support levels, new client versions
  - Merge: apply updates to ontology (additive by default). New properties added. Support levels updated only if they improve precision (partial → supported/unsupported)
  - `SyncReport(new_properties: int, updated_levels: int, new_clients: int, changelog: list[ChangelogEntry], errors: list[str])`
  - `ChangelogEntry(property_id: str, client_id: str, old_level: str | None, new_level: str, source: str)`
- Create `app/knowledge/ontology/caniemail_poller.py` — `CanIEmailPoller(DataPoller)`:
  - Runs every 24 hours (configurable)
  - Calls `CanIEmailSyncService.sync(dry_run=False)`
  - Logs sync report via structured logging
  - Stores last sync timestamp + report in Redis for dashboard display
- Modify `app/main.py` — register `CanIEmailPoller` (same pattern as `CheckpointCleanupPoller`)
- Modify `app/knowledge/routes.py` — add `POST /api/v1/knowledge/ontology/sync` (manual trigger, admin only), `GET /api/v1/knowledge/ontology/sync-status` (last sync time + report)
- Config: `KNOWLEDGE__CANIEMAIL_SYNC_ENABLED: bool = False`, `KNOWLEDGE__CANIEMAIL_SYNC_INTERVAL_HOURS: int = 24`, `KNOWLEDGE__CANIEMAIL_DRY_RUN: bool = True` (dry run by default until manually verified)
**Security:** Fetches from a known GitHub URL only — no user-provided URLs. Data is CSS property support information — no executable content. Sync is additive-only by default. Admin-only manual trigger. GitHub rate limiting handled via conditional requests (If-Modified-Since).
**Verify:** Run sync → new properties added that weren't in original ontology seed. Run sync again immediately → no changes (idempotent). Run dry_run → report generated but no data modified. Invalid GitHub response → graceful failure, no data corruption. Ontology queries return updated data after sync. `make test` passes.
- [ ] 21.1 caniemail auto-sync pipeline

### 21.2 Email Client Rendering Change Detector `[Backend]`
**What:** A scheduled service that renders a suite of CSS feature-detection email templates through the Playwright rendering service (17.1), compares screenshots against stored baselines, and flags when a client's rendering behavior changes. Creates a proprietary, real-time email client behavior changelog.
**Why:** caniemail tells you what CSS _should_ work in email clients. This tells you what CSS _actually_ works right now — and when it changes. Email clients update silently (Gmail's CSS support has expanded significantly over the years without announcement). Detecting these changes creates proprietary intelligence that goes beyond any public dataset.
**Implementation:**
- Create `app/knowledge/ontology/change_detector.py` — `RenderingChangeDetector`:
  - `async detect_changes() -> list[RenderingChange]` — renders feature detection templates, compares against baselines
  - Feature detection templates: one per critical CSS property, each tests a single property with visual indicator (e.g., `display:flex` with visible layout difference between flex and fallback)
  - `RenderingChange(property_id: str, client_id: str, previous_behavior: str, current_behavior: str, screenshot_diff: bytes, detected_at: datetime)`
  - Uses 17.1 `EmailScreenshotService` for rendering, 17.2 `VisualDiffService` for comparison
  - Stores detected changes in knowledge base as documents (domain="rendering_changes")
- Create feature detection templates in `app/knowledge/ontology/feature_templates/` — 20-30 HTML files testing critical CSS properties (flexbox, grid, custom properties, `gap`, `aspect-ratio`, `clamp()`, etc.)
- Create `app/knowledge/ontology/change_poller.py` — `RenderingChangePoller(DataPoller)` — runs weekly
- Config: `KNOWLEDGE__CHANGE_DETECTION_ENABLED: bool = False`, `KNOWLEDGE__CHANGE_DETECTION_INTERVAL_HOURS: int = 168` (weekly)
**Security:** Feature detection templates are static HTML (no dynamic content). Rendering uses sandboxed Playwright (17.1 security model). Changes stored as structured data + screenshot diffs — no executable content.
**Verify:** Modify a rendering profile to simulate a client change (e.g., enable flexbox in outlook_2019 profile) → change detector flags the difference. No profile changes → no changes detected. Detected change creates knowledge base document. `make test` passes.
- [ ] 21.2 Email client rendering change detector

### 21.3 Competitive Intelligence Dashboard & Tests `[Frontend]`
**What:** Frontend dashboard showing ontology sync status, rendering change timeline, support matrix diff viewer (what changed since last sync), and email client trend analysis. Plus full test suite and SDK regeneration.
**Implementation:**
- Create `cms/apps/web/src/components/knowledge/OntologySyncPanel.tsx` — last sync status, changelog viewer, manual sync trigger (admin only)
- Create `cms/apps/web/src/components/knowledge/RenderingChangelog.tsx` — timeline of detected rendering changes with screenshot diffs
- SWR hooks: `useOntologySyncStatus()`, `useRenderingChanges()`
- i18n: ~20 keys across 6 locales
- Tests: `test_caniemail_sync.py` (10 tests — fetch, parse, diff, merge, idempotency), `test_change_detector.py` (8 tests), route tests
- SDK regeneration
- Target: 25+ tests
**Verify:** `make test` passes. `make check-fe` passes. `make check` all green.
- [ ] 21.3 Competitive intelligence dashboard & tests

---

## Phase 22 — AI Evolution Infrastructure

**What:** Close the "identified gaps" from the pitch's AI Evolution section: model capability registry with capability-based routing, prompt template store with A/B testing, token budget manager, fallback chains for provider resilience, and cost governor with per-model budget caps and circuit breakers.
**Why:** The hub currently treats models as interchangeable text boxes (hardcoded model names per tier). When a new model launches, model deprecates, or provider has an outage, manual intervention is needed. These five capabilities make every AI improvement a zero-downtime, zero-code operation — the pitch's stated goal for V1 competitive advantage.
**Dependencies:** Phase 15 (adaptive routing foundation), all agent phases (consumers of the new infrastructure).
**Design principle:** Each capability is independently deployable. Existing `LLMProvider` protocol and `get_registry()` patterns preserved — new capabilities wrap the existing interface rather than replacing it.

### 22.1 Model Capability Registry `[Backend]`
**What:** Each model declares capabilities (vision, tool_use, structured_output, extended_thinking), constraints (context_window, max_output_tokens, cost_per_token), and metadata (provider, local_vs_cloud, deprecation_date). The router matches task requirements to model capabilities rather than just tier names.
**Implementation:**
- Create `app/ai/capability_registry.py` — `ModelCapability` enum, `ModelSpec` frozen dataclass, `CapabilityRegistry` singleton with `register(model_id, spec)`, `find_models(requirements: set[ModelCapability], min_context: int) -> list[ModelSpec]`
- Modify `app/ai/routing.py` — `resolve_model()` checks capability requirements when provided, falls back to tier-based routing
- Config: model specs in `AI__MODEL_SPECS` YAML/JSON config
- [ ] 22.1 Model capability registry

### 22.2 Prompt Template Store `[Backend]`
**What:** Move agent system prompts from Python files to a versioned database store with A/B variant support. Agents load prompts at runtime via `PromptStore.get(agent_id, variant)`. Versions tracked with rollback.
**Implementation:**
- Create `app/ai/prompt_store.py` — `PromptTemplate` model (id, agent_id, version, variant, content, active), `PromptStore` with CRUD + `get_active(agent_id, variant)`, migration to seed from existing SKILL.md files
- Modify `app/ai/agents/base.py` — `_build_system_prompt()` checks `PromptStore` first, falls back to SKILL.md
- Config: `AI__PROMPT_STORE_ENABLED: bool = False`
- [ ] 22.2 Prompt template store

### 22.3 Token Budget Manager `[Backend]`
**What:** Count tokens before sending to LLM. Truncate or summarize conversation history to stay within context window. Adaptive strategy: recent messages preserved, older messages summarized.
**Implementation:**
- Create `app/ai/token_budget.py` — `TokenBudgetManager` with `estimate_tokens(messages)` (tiktoken for OpenAI, approximation for others), `trim_to_budget(messages, max_tokens)` with summarization strategy
- Modify `app/ai/adapters/` — all adapters call `trim_to_budget()` before API call
- Config: `AI__TOKEN_BUDGET_ENABLED: bool = False`, `AI__TOKEN_BUDGET_RESERVE: int = 4096` (reserve for response)
- [ ] 22.3 Token budget manager

### 22.4 Fallback Chains & Provider Resilience `[Backend]`
**What:** Ordered model fallbacks per tier. Primary model failure auto-cascades to next. Example: `complex: [claude-opus-4-6 → gpt-4o → local-qwen-72b]`. Every fallback event logged.
**Implementation:**
- Create `app/ai/fallback.py` — `FallbackChain` with `async call_with_fallback(messages, tier) -> Response` — tries each model in order, catches timeout/rate-limit/deprecation errors, logs fallback events
- Modify `app/ai/routing.py` — `resolve_model()` returns `FallbackChain` instead of single model when fallback config present
- Config: `AI__FALLBACK_CHAINS` YAML config per tier
- [ ] 22.4 Fallback chains & provider resilience

### 22.5 Cost Governor `[Backend]`
**What:** Real-time token and cost tracking per model, per agent, per project. Configurable budget caps with circuit breakers — auto-route to cheaper models or local fallbacks when spend approaches threshold.
**Implementation:**
- Create `app/ai/cost_governor.py` — `CostGovernor` with `track(model, tokens_in, tokens_out, agent, project)` (Redis-backed counters), `check_budget(agent, project) -> BudgetStatus`, circuit breaker integration
- Modify `app/ai/adapters/` — all adapters report usage to `CostGovernor` after each call
- Dashboard endpoint: `GET /api/v1/ai/cost-report` (admin only)
- Config: `AI__COST_GOVERNOR_ENABLED: bool = False`, `AI__MONTHLY_BUDGET_GBP: float = 600.0`, `AI__BUDGET_WARNING_THRESHOLD: float = 0.8`
- [ ] 22.5 Cost governor

### 22.6 Tests & Documentation `[Full-Stack]`
**What:** Tests for all 5 capabilities (30+ tests). ADR-009 AI Evolution Infrastructure.
- [ ] 22.6 Tests & documentation

---

## Phase 23 — Multimodal Protocol & MCP Agent Interface

**What:** Extend the message protocol to support mixed content (text, image, audio, structured data) and wrap every Hub service as a Model Context Protocol tool — decoupling the agent layer from the service layer entirely.
**Why:** Vision models can now process design screenshots directly, voice briefs are emerging as input, and structured output guarantees JSON for QA results. MCP compatibility means any MCP-compatible LLM becomes a drop-in agent backbone.
**Dependencies:** Phase 17 (VLM agent already uses vision — formalizes the protocol), Phase 22 (capability registry identifies vision-capable models).

### 23.1 Multimodal Message Protocol `[Backend]`
**What:** Extend `LLMProvider.complete()` to accept `list[ContentBlock]` instead of `str`. `ContentBlock` union: `TextBlock`, `ImageBlock(data: bytes, media_type: str)`, `AudioBlock`, `StructuredOutputBlock(schema: dict)`. Adapters serialize per-provider (Anthropic content blocks, OpenAI multi-part messages).
- [ ] 23.1 Multimodal message protocol

### 23.2 MCP Tool Server `[Backend]`
**What:** Expose Hub services (QA engine, knowledge search, rendering, components, templates) as MCP tools. Any MCP-compatible client (Claude Desktop, Cursor, custom agents) can call Hub services directly.
- [ ] 23.2 MCP tool server

### 23.3 Voice Brief Input `[Full-Stack]`
**What:** Accept audio file uploads as email briefs. Transcribe via Whisper (local) or cloud STT, extract structured brief (topic, sections, tone, CTA) via LLM, feed to Scaffolder agent.
- [ ] 23.3 Voice brief input

### 23.4 Tests & Documentation `[Full-Stack]`
- [ ] 23.4 Tests & documentation

---

## Phase 24 — Real-Time Collaboration & Visual Builder

**What:** Google Docs-style simultaneous editing with OT/CRDT conflict resolution for the Monaco editor, plus a drag-and-drop visual email builder for non-technical users alongside the code editor.
**Why:** The pitch identifies these as key "Future Vision" features. Real-time collaboration enables team workflows (developer + copywriter editing simultaneously). Visual builder opens the hub to non-developers — the largest untapped user base.
**Dependencies:** Phase 11 (component library for builder blocks), Phase 12 (Figma import for design-to-builder), all frontend phases.

### 24.1 CRDT Collaborative Editing Engine `[Full-Stack]`
**What:** Real-time collaborative editing using Yjs CRDT library. WebSocket sync server, cursor awareness, and conflict-free merging for HTML editing.
- [ ] 24.1 CRDT collaborative editing engine

### 24.2 Drag-and-Drop Visual Email Builder `[Frontend]`
**What:** Component-based visual builder using the existing component library. Drag sections from library, configure via property panels, switch between visual and code view. Output is standard template HTML.
- [ ] 24.2 Drag-and-drop visual email builder

### 24.3 Builder ↔ Code Bidirectional Sync `[Full-Stack]`
**What:** Changes in visual builder reflect in code editor and vice versa. AST-level mapping between visual components and HTML source.
- [ ] 24.3 Builder ↔ code bidirectional sync

### 24.4 Tests & Documentation `[Full-Stack]`
- [ ] 24.4 Tests & documentation

---

## Phase 25 — Platform Ecosystem & Advanced Integrations

**What:** Plugin architecture for community-contributed components, Tolgee integration for multilingual campaigns, Kestra workflow orchestration, Penpot design-to-code pipeline, and Typst for programmatic QA report generation.
**Why:** These extend the hub from a tool into a platform. Each integration compounds with existing capabilities — Tolgee + Maizzle enables per-locale builds, Kestra replaces ad-hoc pipeline orchestration, Penpot offers a self-hosted Figma alternative.
**Dependencies:** All previous phases.

### 25.1 Plugin Architecture `[Backend]`
**What:** Extensible plugin system for custom QA checks, agent skills, export connectors, and component packages. Plugin manifest format, discovery, loading, and sandboxed execution.
- [ ] 25.1 Plugin architecture

### 25.2 Tolgee Multilingual Campaign Support `[Full-Stack]`
**What:** Self-hosted TMS integration for multilingual email campaigns. In-context translation, translation memory, per-locale Maizzle builds.
- [ ] 25.2 Tolgee multilingual campaign support

### 25.3 Kestra Workflow Orchestration `[Backend]`
**What:** Declarative YAML email build pipeline with retry logic, parallelism, conditional branching, and full audit trail. Replaces the blueprint engine's ad-hoc orchestration with a production-grade workflow engine.
- [ ] 25.3 Kestra workflow orchestration

### 25.4 Penpot Design-to-Email Pipeline `[Backend]`
**What:** Self-hosted, API-driven design-to-email pipeline using Penpot's CSS-native primitives. Zero-cost Figma alternative with full programmatic access.
- [ ] 25.4 Penpot design-to-email pipeline

### 25.5 Typst QA Report Generator `[Backend]`
**What:** Programmatic PDF generation for QA reports and client approval packages using Typst (Rust, <100ms). Data-driven documents auto-generated from Hub QA results.
- [ ] 25.5 Typst QA report generator

### 25.6 Tests & Documentation `[Full-Stack]`
- [ ] 25.6 Tests & documentation

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

| Metric | Current (Phase 16) | Target (Phase 21) | Target (Phase 25) |
|--------|--------------------|--------------------|---------------------|
| Campaign build time | 1-2 days | Under 4 hours | Under 1 hour |
| Cross-client rendering defects | Caught at QA gate | Auto-fixed by VLM agent | Near-zero (property-tested) |
| Component reuse rate | 30-40% | 60%+ | 80%+ (plugin ecosystem) |
| AI agent count | 9 agents | 10 (Visual QA) | 12+ (plugin agents) |
| QA checks | 11 automated | 14 (resilience, deliverability, BIMI) | 16+ (plugin checks) |
| Ontology freshness | Manual seed | Auto-synced daily | Real-time change detection |
| Outlook migration readiness | Manual analysis | Automated advisor | Audience-aware phased plans |
| Gmail AI optimization | Not addressed | Summary prediction + schema.org | Full AI inbox optimization |
| Cloud AI API spend | Under £600/month | Under £600/month (cost governor) | Under £600/month (budget caps) |
| Email CSS output size | Juice baseline | 15-25% smaller (CSS compiler) | Optimal per-client bundles |
| Knowledge base entries | 500+ | 1000+ (auto-synced) | Self-growing (chaos findings) |
