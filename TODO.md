# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–26):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA — Playwright rendering, ODiff baselines, VLM analysis agent #10, auto-fix pipeline, visual QA dashboard). Phase 18 (rendering resilience & property-based testing — chaos engine with 8 profiles, Hypothesis-based property testing with 10 invariants, resilience score integration, knowledge feedback loop). Phase 19 (Outlook transition advisor & email CSS compiler — Word-engine dependency analyzer, audience-aware migration planner, Lightning CSS 7-stage compiler with ontology-driven conversions). Phase 20 (Gmail AI intelligence & deliverability — Gemini summary predictor, schema.org auto-injection, deliverability scoring, BIMI readiness check). Phase 21 (real-time ontology sync & competitive intelligence — caniemail auto-sync, rendering change detector with 25 feature templates, competitive intelligence dashboard). Phase 22 (AI evolution infrastructure — capability registry, prompt template store, token budget manager, fallback chains, cost governor, cross-module integration tests + ADR-009). Phase 23 (multimodal protocol & MCP agent interface — 7 subtasks: content block protocol, adapter serialization, agent integration, MCP tool server with 17 tools, voice brief pipeline, frontend multimodal UI, tests & ADR-010; 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks: WebSocket infra, Yjs CRDT engine, collaborative cursor & presence, visual builder canvas & palette, property panels, bidirectional code↔builder sync, frontend integration, tests & docs, AI-powered HTML import with 10th agent). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks: plugin architecture with manifest/discovery/registry, sandboxed execution & lifecycle, Tolgee multilingual campaigns, per-locale Maizzle builds, Kestra workflow orchestration, Penpot design-to-email pipeline, Typst QA report generator, ecosystem dashboard, template learning pipeline, automatic skill extraction, template-to-eval pipeline, deliverability intelligence, multi-variant campaign assembly). Phase 26 (email build pipeline performance & CSS optimization — 5 subtasks: eliminate redundant CSS inlining, per-build CSS compatibility audit, template-level CSS precompilation, consolidated CSS pipeline in Maizzle sidecar, tests & documentation).

---

## ~~Phase 24 — Real-Time Collaboration & Visual Builder~~ DONE

> All 9 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 24.1 WebSocket infra, 24.2 Yjs CRDT, 24.3 Presence, 24.4 Visual builder canvas, 24.5 Property panels, 24.6 Bidirectional sync, 24.7 Frontend integration, 24.8 Tests & docs, 24.9 AI-powered HTML import.

---

## ~~Phase 25 — Platform Ecosystem & Advanced Integrations~~ DONE

> All 15 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 25.1 Plugin manifest/discovery/registry, 25.2 Sandboxed execution & lifecycle, 25.3 Tolgee multilingual campaigns, 25.4 Per-locale Maizzle builds, 25.5 Kestra workflow orchestration, 25.6 Penpot design-to-email, 25.7 Typst QA report generator, 25.8 Ecosystem dashboard, 25.9 Tests & docs, 25.10 Template learning pipeline, 25.11 Automatic skill extraction, 25.12 Template-to-eval pipeline, 25.13 Deliverability intelligence, 25.14 Multi-variant campaign assembly, 25.15 Tests & docs for 25.10–25.14.

---

## ~~Phase 26 — Email Build Pipeline Performance & CSS Optimization~~ DONE

> All 5 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 26.1 Eliminate redundant CSS inlining, 26.2 Per-build CSS compatibility audit, 26.3 Template-level CSS precompilation, 26.4 Consolidated CSS pipeline in Maizzle sidecar, 26.5 Tests & documentation.

---

## Phase 27 — Email Client Rendering Fidelity & Pre-Send Testing

**What:** Expand the local email client emulation system from 2 emulators to 7, add a calibration feedback loop that compares local previews against external rendering providers (Litmus / Email on Acid) to iteratively improve emulator accuracy, introduce per-client rendering confidence scores, and build a pre-send rendering gate that blocks ESP sync when confidence drops below configurable thresholds. Six subtasks ordered by value — each builds on the previous.
**Why:** The current rendering pipeline has two emulators (Gmail, Outlook.com) and 6 Playwright profiles, but no way to quantify *how faithful* a local preview actually is. Users must either trust the local preview blindly or pay for Litmus/EoA screenshots on every build. The real problem isn't the rendering engine — it's the *sanitizer/preprocessor* each email client runs before its engine sees the HTML. Gmail's Blink can render flexbox perfectly; Gmail's sanitizer strips it first. By modeling these sanitizers as chained transformation rules (which the emulator system already does for Gmail and Outlook.com), and calibrating them against ground truth screenshots, we can give users a confidence score: "Gmail: 94% confidence (emulated)" vs "Outlook 2019: 72% confidence (Word engine — recommend external validation)." This turns rendering testing from binary (local preview looks OK / send and hope) into a quantified risk assessment with actionable thresholds.
**Dependencies:** Phase 17 (visual regression & Playwright rendering), Phase 19 (CSS compiler & ontology), Phase 26 (optimized CSS pipeline & per-build CSS audit). The `RenderingService` multi-provider architecture, `EmailClientEmulator` chain-of-rules pattern, `ScreenshotBaseline` model, ODiff visual comparison, and ontology support matrix are all in place.
**Design principle:** Emulators are approximations, not replacements. Every emulator publishes a confidence score derived from calibration data. The system is honest about what it can and cannot model locally — Word engine rendering is fundamentally impossible to emulate without Word itself, so Outlook desktop emulators focus on the *CSS preprocessing* stage (property stripping, shorthand expansion, VML injection) and report lower confidence for layout-dependent issues. External providers are the ground truth — local emulators are the fast, free alternative that gets better over time via calibration.

> **All subtasks complete (27.1–27.6):** See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 27.1 Expand email client emulators (8 clients, 14 profiles, chain-of-rules with confidence_impact), 27.2 Rendering confidence scoring (4-signal scorer, GET /confidence/{client_id}, RENDERING__CONFIDENCE_ENABLED), 27.3 Pre-send rendering gate (RenderingSendGate service, GatePanel + GateClientRow + GateSummaryBadge frontend, wired into export + push-to-ESP dialogs, admin override), 27.4 Emulator calibration loop (EmulatorCalibrator with ODiff, EMA α=0.3, CalibrationSampler, RENDERING__CALIBRATION__ENABLED), 27.5 Headless email sandbox (SMTP-based Mailpit capture, DOMDiff, SandboxProfile registry, Playwright Roundcube, RENDERING__SANDBOX__ENABLED), 27.6 Frontend rendering dashboard & tests (RenderingDashboard with preview grid + confidence summary bar + gate status + calibration health panel, ConfidenceBar extracted as shared component, 14 client profiles, 27 frontend tests across 3 test files).

- [x] ~~27.1 Expand email client emulators~~ DONE
- [x] ~~27.2 Rendering confidence scoring~~ DONE
- [x] ~~27.3 Pre-send rendering gate~~ DONE
- [x] ~~27.4 Emulator calibration loop~~ DONE
- [x] ~~27.5 Headless email client sandbox~~ DONE
- [x] ~~27.6 Frontend rendering dashboard & tests~~ DONE

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
- [x] ~~27.3 Pre-send rendering gate~~ DONE

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
- [x] ~~27.6 Frontend rendering dashboard & tests~~ DONE

---

## Phase 28 — Export Quality Gates & Approval Workflow

**What:** Wire QA enforcement and approval workflow into the export/push pipeline so that emails cannot be pushed to ESPs without passing quality checks and (optionally) approval. Currently QA is advisory-only, approval routes exist but aren't connected to export, and there's no approval UI in the frontend.
**Why:** The platform has 14 QA checks, a rendering confidence scorer, and a full approval state machine — but none of these gate the actual export. A developer can push a failing email to Braze without any warning. This defeats the purpose of the entire QA pipeline. Wiring these together turns advisory checks into enforceable workflow steps. The approval workflow is critical for enterprise customers where a manager or legal reviewer must sign off before production sends.
**Dependencies:** Phase 27.3 (rendering gate backend — provides the `RenderingSendGate` integration pattern). Existing: `app/qa_engine/service.py` (14 checks), `app/approval/` (models, service, routes), `app/connectors/service.py` (export flow), frontend export-dialog.tsx and push-to-esp-dialog.tsx.

### 28.1 QA Enforcement in Export Flow `[Backend]`
**What:** Make QA check results a configurable gate on the export/push pipeline. When QA enforcement is enabled, exports are blocked if critical checks fail, unless overridden by an admin.
**Why:** Currently `ConnectorService.export()` calls the ESP provider directly — no QA validation. Users can push emails with broken links, accessibility failures, or spam-score violations to production. The rendering gate (27.3) blocks on rendering confidence, but QA check failures (HTML validation, spam score, link validation, etc.) are completely ignored during export. This subtask adds a parallel QA gate alongside the rendering gate.
**Implementation:**
- Create `app/connectors/qa_gate.py` — `ExportQAGate`:
  - `async evaluate(html: str, project_id: int | None = None) -> QAGateResult`:
    - Runs `QAEngineService.run_checks()` with project-specific config
    - Classifies each check as `blocking` or `warning` based on `ExportQAConfig`
    - Returns `QAGateResult(passed: bool, verdict: QAGateVerdict, blocking_failures: list[QACheckSummary], warnings: list[QACheckSummary])`
  - `QAGateVerdict` enum: `pass`, `warn`, `block`
  - `QACheckSummary`: `check_name: str`, `passed: bool`, `severity: str`, `details: str`, `remediation: str`
- Create `app/connectors/qa_gate_config.py` — `ExportQAConfig`:
  - `enabled: bool = True`
  - `mode: Literal["enforce", "warn", "skip"] = "warn"` — same pattern as rendering gate
  - `blocking_checks: list[str] = ["html_validation", "link_validation", "spam_score", "personalisation_syntax", "liquid_syntax"]` — checks that block export when failing
  - `warning_checks: list[str] = ["accessibility", "dark_mode", "image_optimization", "file_size"]` — checks that produce warnings but don't block
  - `ignored_checks: list[str] = []` — checks to skip entirely during export gate
  - Stored per-project in `Project.export_qa_config` JSON column (nullable, falls back to global defaults)
  - Global defaults in settings: `EXPORT__QA_GATE_MODE`, `EXPORT__QA_BLOCKING_CHECKS`
- Modify `app/connectors/service.py` — `ConnectorService.export()`:
  - After HTML resolution, before ESP provider call:
    ```
    1. Run QA gate: qa_result = await qa_gate.evaluate(html, project_id)
    2. Run rendering gate: render_result = await render_gate.evaluate(html, target_clients, project_id)
    3. If either gate blocks → raise ExportGateError with combined results
    4. If either gate warns → attach warnings to ExportResponse
    5. If both pass → proceed to ESP provider
    ```
  - Add `skip_qa_gate: bool = False` parameter (admin only, logged to audit)
  - Add `qa_result` and `rendering_result` fields to `ExportResponse` for frontend display
- Modify `app/connectors/schemas.py`:
  - Add `QAGateResult` to `ExportResponse` (optional, populated when gate runs)
  - Add `skip_qa_gate: bool = False` to `ExportRequest`
  - Add `ExportGateError` response schema for 422 responses
- Add API endpoint:
  - `POST /api/v1/connectors/export/pre-check` — dry-run both gates without actually exporting (for the frontend to show gate results before user confirms)
  - Request: `{ html: str, project_id: int, target_clients: list[str] | None }`
  - Response: `{ qa: QAGateResult, rendering: GateResult, can_export: bool }`
- Alembic migration: add `export_qa_config` JSON column to `projects` table
- Frontend — modify `export-dialog.tsx` and `push-to-esp-dialog.tsx`:
  - Before showing `GatePanel`, call `/connectors/export/pre-check` to get combined QA + rendering results
  - Show QA failures alongside rendering confidence in the gate panel:
    - Section 1: "QA Checks" — blocking failures (red), warnings (yellow), passes (green)
    - Section 2: "Rendering Confidence" — existing gate panel content
  - "Override" button (admin only) now overrides both QA and rendering gates
  - If `mode=warn`: show warnings banner but allow "Continue" button
- SWR hook:
  - `cms/apps/web/src/hooks/use-export-gate.ts`:
    - `useExportPreCheck()` — `POST /connectors/export/pre-check`
    - Returns combined `{ qa, rendering, can_export }` result
- Tests:
  - `app/connectors/tests/test_qa_gate.py` — 15+ tests:
    - Export with all QA passing → gate passes
    - Export with blocking check failing → gate blocks in enforce mode
    - Export with warning check failing → gate warns (doesn't block)
    - Admin skip_qa_gate → bypasses with audit log
    - Per-project config overrides (different blocking checks per project)
    - Pre-check endpoint returns combined results without exporting
    - Integration: QA blocks + rendering passes → still blocked
  - `cms/apps/web/src/hooks/__tests__/use-export-gate.test.ts` — 5+ tests
**Security:** QA gate is read-only analysis. Override requires admin role. Override decisions logged with user_id, timestamp, and gate results. No new external calls. `skip_qa_gate` parameter validated against user role server-side.
**Verify:** Email with broken links → export blocked with "link_validation failed" and remediation. Email passing all checks → export proceeds. `mode=warn` → export proceeds with warnings in response. Admin override → proceeds with audit trail. Per-project config: disable spam_score blocking for testing project → spam-flagged email exports. Pre-check endpoint returns correct combined results. `make test` passes. `make check-fe` passes.
- [x] ~~28.1 QA enforcement in export flow~~ DONE

### 28.2 Approval Workflow → Export Integration `[Backend]`
**What:** Wire the existing approval state machine (`app/approval/`) into the export pipeline so that emails optionally require approval before ESP push. When approval is required, exports are blocked until an authorized reviewer approves the build.
**Why:** Enterprise email workflows require sign-off before production sends. The approval system exists (models, service, routes, state machine with `pending → approved/rejected/revision_requested` transitions, audit trail) but is completely disconnected from the export flow. A developer can push to Braze without any approval. This subtask makes approval an optional gate in the export pipeline — when enabled per-project, the export flow checks approval status before proceeding.
**Implementation:**
- Create `app/connectors/approval_gate.py` — `ExportApprovalGate`:
  - `async evaluate(build_id: int, user: User) -> ApprovalGateResult`:
    - Checks if project has `require_approval_for_export: bool` enabled
    - If not required → return `ApprovalGateResult(required=False, passed=True)`
    - If required → look up `ApprovalRequest` for this build_id:
      - No approval request → return `passed=False, reason="No approval request submitted"`
      - Status `pending` → return `passed=False, reason="Approval pending review"`
      - Status `revision_requested` → return `passed=False, reason="Revisions requested"`
      - Status `rejected` → return `passed=False, reason="Approval rejected"`
      - Status `approved` → return `passed=True, approved_by=reviewer, approved_at=timestamp`
    - `ApprovalGateResult`: `required: bool`, `passed: bool`, `reason: str | None`, `approval_id: int | None`, `approved_by: str | None`, `approved_at: datetime | None`
- Modify `app/connectors/service.py` — `ConnectorService.export()`:
  - Add approval gate as third gate in the pipeline:
    ```
    1. QA gate (28.1)
    2. Rendering gate (27.3)
    3. Approval gate (28.2) — only if build_id provided (template_version exports skip approval)
    4. ESP provider call
    ```
  - If approval gate blocks → raise `ApprovalRequiredError` with status and instructions
  - Add `approval_result` to `ExportResponse`
- Modify `app/approval/service.py`:
  - Add `get_approval_for_build(build_id: int) -> ApprovalResponse | None` — lookup by build_id
  - Add `is_approved(build_id: int) -> bool` — quick check for export gate
- Add project-level config:
  - Add `require_approval_for_export: bool = False` field to project settings
  - Admin-only toggle via `PATCH /api/v1/projects/{id}` (existing endpoint)
- Modify `app/connectors/schemas.py`:
  - Add `ApprovalGateResult` to `ExportResponse`
  - Add `skip_approval: bool = False` to `ExportRequest` (admin only)
- Update pre-check endpoint (from 28.1):
  - `/connectors/export/pre-check` response now includes `approval: ApprovalGateResult`
  - Frontend shows approval status alongside QA and rendering gates
- Tests:
  - `app/connectors/tests/test_approval_gate.py` — 12+ tests:
    - Project without approval required → gate passes (not required)
    - Project with approval required, no request → gate blocks
    - Approval pending → gate blocks
    - Approval approved → gate passes
    - Approval rejected → gate blocks
    - Admin skip_approval → bypasses with audit
    - Template version export (no build_id) → approval gate skipped
    - Integration: QA passes + rendering passes + approval pending → still blocked
**Security:** Approval gate checks are read-only lookups. Override requires admin role. The approval state machine already has BOLA checks (`_verify_approval_access`). No new models or migrations needed — uses existing `ApprovalRequest.build_id` FK.
**Verify:** Project with `require_approval=true`, no approval → export blocked with "No approval request submitted". Submit approval → export still blocked ("Approval pending"). Reviewer approves → export proceeds. Project without `require_approval` → export proceeds without approval. Admin `skip_approval=true` → proceeds with audit. Pre-check shows all three gate results. `make test` passes.
- [ ] 28.2 Approval workflow → export integration

### 28.3 Approval Frontend UI `[Frontend]`
**What:** React components for the approval workflow — request approval, review/decide, feedback, and audit trail. Integrated into the workspace and export flow.
**Why:** The approval backend has 7 endpoints and a full state machine, but zero frontend UI. Users cannot request, review, or approve builds from the interface. This is the final piece to make approval usable.
**Implementation:**
- Create `cms/apps/web/src/components/approval/` package:
  - `approval-request-dialog.tsx` — submit build for approval:
    - Props: `buildId: number`, `projectId: number`, `onSubmitted: () => void`
    - Dialog with "Submit for Approval" button
    - Shows current build QA status summary (from pre-check)
    - Optional note field for reviewer context
    - Calls `POST /api/v1/approvals/` with `{ build_id, project_id }`
    - Success → toast + close
  - `approval-review-panel.tsx` — reviewer decision panel:
    - Props: `approvalId: number`
    - Shows build preview (iframe sandbox), QA results, rendering confidence
    - Three action buttons: "Approve" (green), "Request Revisions" (yellow), "Reject" (red)
    - Each action opens confirmation dialog with required `review_note` field
    - Calls `POST /api/v1/approvals/{id}/decide` with `{ status, review_note }`
    - State badge: pending (blue), approved (green), rejected (red), revision_requested (yellow)
  - `approval-feedback-thread.tsx` — feedback conversation:
    - Props: `approvalId: number`
    - Shows chronological feedback thread (like comments)
    - Input field with "Add Feedback" button
    - Calls `POST /api/v1/approvals/{id}/feedback` and `GET /api/v1/approvals/{id}/feedback`
    - Feedback types: `comment`, `suggestion`, `blocker` (color-coded)
  - `approval-audit-trail.tsx` — audit log:
    - Props: `approvalId: number`
    - Shows timeline of all actions (created, decided, feedback added, overridden)
    - Calls `GET /api/v1/approvals/{id}/audit`
    - Each entry: actor name, action, timestamp, details
  - `approval-status-badge.tsx` — reusable status indicator:
    - Props: `status: ApprovalStatus`
    - Color-coded badge: pending=blue, approved=green, rejected=red, revision_requested=amber
  - `approval-list.tsx` — list of approvals for a project:
    - Props: `projectId: number`
    - Table with columns: Build, Status, Requested By, Reviewer, Date
    - Filter by status
    - Click row → opens review panel
    - Calls `GET /api/v1/approvals/?project_id={id}`
- SWR hooks — `cms/apps/web/src/hooks/use-approvals.ts`:
  - `useApprovals(projectId)` — list approvals for project
  - `useApproval(approvalId)` — single approval detail
  - `useApprovalFeedback(approvalId)` — feedback thread
  - `useApprovalAudit(approvalId)` — audit trail
  - `useCreateApproval()` — submit for approval (SWRMutation)
  - `useDecideApproval(approvalId)` — approve/reject/revise (SWRMutation)
  - `useAddFeedback(approvalId)` — add feedback (SWRMutation)
- Types — `cms/apps/web/src/types/approval.ts`:
  - `ApprovalStatus`, `ApprovalRequest`, `ApprovalDecision`, `Feedback`, `AuditEntry`
  - `ApprovalResponse`, `FeedbackResponse`, `AuditResponse`
- Integration points:
  - Workspace page (`projects/[id]/workspace/page.tsx`): add "Submit for Approval" button next to export button (shown when `require_approval` is enabled for project)
  - Export dialog: show `ApprovalStatusBadge` in gate panel — if approval required and not approved, show "Approval Required" with link to submit
  - Project settings: add "Require Approval for Export" toggle (admin only)
  - Navigation: add "Approvals" tab in project workspace (badge with pending count)
- Tests:
  - `cms/apps/web/src/components/approval/__tests__/approval-review-panel.test.tsx` — 8+ tests:
    - Renders pending approval with action buttons
    - Approve action sends correct API call
    - Reject action requires review_note
    - Approved state shows green badge, no action buttons
  - `cms/apps/web/src/hooks/__tests__/use-approvals.test.ts` — 5+ tests
**Security:** Approval actions respect server-side RBAC (developer can submit, admin/designated reviewer can decide). Frontend hides action buttons based on user role. No client-side approval bypasses — all enforcement is backend.
**Verify:** Developer submits build for approval → approval appears in list with "pending" status. Reviewer sees build preview + QA results. Reviewer approves → status changes to "approved", export unblocked. Reviewer requests revisions → developer sees feedback. Audit trail shows all actions with timestamps. Export dialog shows "Approval Required" when not yet approved. `make check-fe` passes.
- [ ] 28.3 Approval frontend UI

---

## Phase 29 — Design Import Enhancements

**What:** Enable template creation from a text brief without requiring a live Figma/Penpot design file, and complete the Penpot CSS-to-email converter so Penpot imports produce the same quality as Figma imports.
**Why:** The current design sync flow requires a live design file connection (`connection_id` is mandatory in `StartImportRequest`). Users who have a written brief but no Figma file must either create a dummy connection or use the blueprint API directly (`POST /blueprints/run`). The brief-only path should be a first-class citizen in the UI. Additionally, Penpot imports are incomplete — the converter has color/typography extraction but the CSS-to-email HTML conversion is not wired into the import flow, so Penpot users get a degraded experience compared to Figma users.
**Dependencies:** Existing: `app/design_sync/` (import pipeline, brief generator, import service), `app/ai/agents/scaffolder/` (can accept brief directly), `app/design_sync/penpot/converter.py` (partial implementation).

### 29.2 Penpot CSS-to-Email Converter Integration `[Backend]`
**What:** Wire the Penpot converter's CSS-to-email HTML generation into the design import flow so Penpot imports produce email-ready HTML with table-based layouts, inline styles, and MSO conditionals — matching the quality of Figma imports.
**Why:** `app/design_sync/penpot/converter.py` has `convert_colors_to_palette()`, `convert_typography()`, `node_to_email_html()`, and `_group_into_rows()` — but the import pipeline (`DesignImportService.run_conversion()`) doesn't call the Penpot-specific converter. It uses the generic brief→Scaffolder path for all providers. The Penpot converter can produce initial HTML directly from the design tree, which can then be enhanced by the Scaffolder (richer than starting from a brief alone). This subtask integrates the converter as an optional pre-processing step for Penpot imports.
**Implementation:**
- Modify `app/design_sync/import_service.py` — `DesignImportService.run_conversion()`:
  - After layout analysis, before Scaffolder call:
    - If provider is `penpot` and `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED`:
      - Call `PenpotConverter.convert(structure_json, tokens)` → initial HTML
      - Pass initial HTML to Scaffolder as `initial_html` parameter (existing blueprint input)
      - Scaffolder enhances rather than generates from scratch
    - If provider is `figma` or converter disabled: keep existing brief-only path
  - This means Penpot imports get a head start with structural HTML from the design tree
- Create `app/design_sync/penpot/converter_service.py` — `PenpotConverterService`:
  - `async convert(structure: DesignFileStructure, tokens: ExtractedTokens, *, selected_nodes: list[str] | None = None) -> PenpotConversionResult`:
    - Walks design tree for selected nodes (or all top-level frames)
    - For each frame: `node_to_email_html()` → table-based HTML section
    - Assembles sections into email skeleton (DOCTYPE, head with meta/style, body with wrapper table)
    - Applies extracted tokens: colors → inline styles, typography → font stacks
    - Adds MSO conditionals for Outlook compatibility
    - Returns `PenpotConversionResult(html: str, sections: list[str], warnings: list[str])`
  - `PenpotConversionResult`: `html: str`, `sections_count: int`, `warnings: list[str]` (e.g., "Unsupported SVG filter in node X — replaced with placeholder")
- Enhance `app/design_sync/penpot/converter.py`:
  - `node_to_email_html()` — improve existing implementation:
    - Add `COMPONENT` and `INSTANCE` node type handling (currently only FRAME, TEXT, IMAGE, GROUP, VECTOR)
    - Add `auto-layout` detection from Penpot node properties → flexbox-to-table conversion
    - Add background color/image extraction from node fills
    - Add border/border-radius extraction (with email-safe fallbacks)
    - Add padding/margin from Penpot spacing properties
  - `_group_into_rows()` — improve spatial grouping:
    - Handle overlapping elements (z-index ordering)
    - Detect hero images (full-width images above fold)
    - Detect CTA buttons (small frames with centered text)
- Config: `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED: bool = False` (opt-in while stabilizing)
- Tests:
  - `app/design_sync/penpot/tests/test_converter_integration.py` — 15+ tests:
    - Simple Penpot frame → valid email HTML with table layout
    - Text nodes → `<td>` with inline font styles
    - Image nodes → `<img>` with width/height attributes
    - Grouped elements → multi-column table row
    - Auto-layout frame → table with correct column widths
    - Extracted tokens applied → correct colors and fonts in inline styles
    - MSO conditionals present in output
    - Converter disabled → falls back to brief-only path
    - Integration: Penpot import with converter → Scaffolder receives initial_html → enhanced output
  - Update `app/design_sync/penpot/tests/test_penpot_converter.py` — extend existing 14 tests
**Security:** Converter output runs through `sanitize_html_xss()` before storage. No external calls — all conversion is local string manipulation. SVG content stripped (email-unsafe).
**Verify:** Penpot design file with header + hero + 2-column content + footer → converter produces table-based HTML with correct structure. Scaffolder enhances with content and design tokens. QA checks pass on output. Converter disabled → brief-only path works as before. `make test` passes.
- [ ] 29.2 Penpot CSS-to-email converter integration

---

## Phase 30 — End-to-End Testing & CI Quality

**What:** Comprehensive Playwright e2e test suite covering all major user journeys, visual regression testing for rendering emulators, and multi-browser coverage. Transforms the current stub (single `example.spec.ts`) into a production-grade test suite.
**Why:** The backend has 258+ unit tests and the frontend has 23 unit tests, but the e2e suite has exactly 1 test (a smoke test that clicks a link). No user journey is tested end-to-end through the browser. The rendering emulator system produces screenshots but there's no CI validation that they match expected output. The Playwright config only includes Chromium — the visual email builder relies on DOM APIs that may behave differently in Firefox/Safari. The existing CLI-based e2e testing (`.claude/commands/e2e-test.md`) provides exploratory coverage via `agent-browser` but is not automated in CI.
**Dependencies:** Phase 28 (export gates, approval UI — tests will exercise these flows). Existing: `cms/apps/web/e2e/playwright.config.ts` (Chromium-only), `cms/apps/web/e2e/example.spec.ts`, `services/mock-esp/` (port 3002).

### 30.1 Playwright E2E User Journey Suite `[Frontend + Full-Stack]`
**What:** 20+ Playwright test scenarios covering the core user journeys: login, workspace, template building, QA review, export flow, approval workflow, design sync, collaboration, and ecosystem dashboard.
**Why:** The CLI-based e2e testing guide (`.claude/commands/e2e-test.md`) covers 13 major journeys but requires manual execution via `agent-browser`. These same journeys need automated Playwright tests that run in CI on every PR. The current `example.spec.ts` only verifies that a page loads — it doesn't test any real user workflow.
**Implementation:**
- Create `cms/apps/web/e2e/fixtures/` — shared test fixtures:
  - `auth.ts` — login fixture: authenticates via API (`POST /api/v1/auth/login`), stores session cookie, provides `authenticatedPage` fixture
  - `project.ts` — creates test project via API, returns `projectId` for test isolation
  - `template.ts` — creates test template via brief API (29.1) or seed data, returns `templateId`
  - `mock-esp.ts` — ensures mock-esp service is running on port 3002
- Create test files in `cms/apps/web/e2e/`:
  - `auth.spec.ts` — 3 tests:
    - Login with valid credentials → redirects to dashboard
    - Login with invalid credentials → shows error message
    - Logout → redirects to login page
  - `dashboard.spec.ts` — 3 tests:
    - Dashboard loads with project list
    - Create new project → appears in list
    - Search/filter projects
  - `workspace.spec.ts` — 5 tests:
    - Open project workspace → template list visible
    - Select template → code editor loads with HTML
    - Switch to visual builder tab → canvas renders preview
    - Switch to preview tab → sandboxed iframe shows email
    - QA panel shows check results
  - `builder.spec.ts` — 5 tests:
    - Component palette loads with available components
    - Drag component from palette to canvas → component added
    - Select component on canvas → property panel opens with correct tabs
    - Edit property value → preview updates
    - Undo/redo → canvas state reverts/reapplies
  - `export.spec.ts` — 5 tests:
    - Open export dialog → shows ESP tabs
    - Select Braze → enter content block name → click export
    - Gate panel appears with QA + rendering results
    - Gate passes → export succeeds (mock ESP returns 200)
    - Gate blocks (inject failing HTML) → export blocked with remediation
  - `approval.spec.ts` — 4 tests:
    - Submit build for approval → approval appears with "pending" status
    - Reviewer opens approval → sees build preview + QA results
    - Reviewer approves → status changes to "approved"
    - Developer exports after approval → export proceeds
  - `design-sync.spec.ts` — 3 tests:
    - Open connect design dialog → select mock provider → connection created
    - Browse file structure → select frames → generate brief
    - Convert import → template created and appears in workspace
  - `collaboration.spec.ts` — 2 tests:
    - Two browser contexts open same template → presence indicators visible
    - One user edits → other user sees change (CRDT sync)
  - `ecosystem.spec.ts` — 2 tests:
    - Navigate to ecosystem dashboard → tabs visible (plugins, workflows, reports)
    - Open plugin manager → plugin list loads
- Update `cms/apps/web/e2e/playwright.config.ts`:
  - Add `globalSetup` for API-based test data seeding
  - Add `globalTeardown` for cleanup
  - Configure screenshot-on-failure: `use: { screenshot: 'only-on-failure' }`
  - Add `timeout: 30000` per test (email builds can be slow)
  - Keep single Chromium project for now (30.3 adds more browsers)
- Update `Makefile`:
  - `make e2e` — run full Playwright suite (headless)
  - `make e2e-ui` — run with Playwright UI (interactive debug)
  - `make e2e-report` — open last HTML report
- Tests: 32+ test cases total across 9 spec files
**Security:** Test fixtures use dedicated test user accounts. Mock ESP captures but doesn't forward. Test data isolated per run (unique project names). No real ESP credentials in tests.
**Verify:** `make e2e` runs all 32+ tests in CI (headless Chromium). All pass on clean environment. Failures produce screenshots + traces. HTML report generated. `make e2e-ui` opens interactive runner. Tests complete in <5 minutes total.
- [ ] 30.1 Playwright e2e user journey suite

### 30.2 Visual Regression Testing in CI `[Full-Stack + CI]`
**What:** Automated screenshot comparison for rendering emulator outputs. On each PR, the CI pipeline renders a set of reference emails through all 14 client profiles and compares against baseline screenshots using ODiff. Regressions flag the PR with a diff image.
**Why:** The emulator system (27.1) produces screenshots via Playwright, and the calibration loop (27.4) compares against external providers — but there's no CI check that emulator outputs are *stable across code changes*. A refactor to the Gmail emulator rules could silently change all Gmail screenshots. Visual regression testing catches this: baseline screenshots are committed, and any deviation is flagged.
**Implementation:**
- Create `app/rendering/tests/visual_regression/` package:
  - `baseline_generator.py` — `BaselineGenerator`:
    - `async generate_baselines(templates: list[str], profiles: list[str], output_dir: Path) -> list[BaselineResult]`:
      - For each template × profile: run emulator → capture screenshot → save as PNG
      - Generates `baselines/{template_slug}/{profile_id}.png`
      - Also generates `baselines/manifest.json` with template names, profile IDs, timestamps, emulator versions
    - Reference templates: 5 golden templates selected for visual diversity:
      - Simple text-only (minimal CSS)
      - Hero image + CTA (common marketing pattern)
      - Multi-column product grid (complex table layout)
      - Dark mode enabled (tests dark mode emulation)
      - Progressive enhancement (flexbox with MSO fallback)
  - `regression_runner.py` — `VisualRegressionRunner`:
    - `async run(baseline_dir: Path, profiles: list[str] | None = None) -> RegressionReport`:
      - For each baseline: re-render template → compare with ODiff → compute diff percentage
      - Threshold: 0.5% pixel difference (configurable via `RENDERING__VISUAL_REGRESSION_THRESHOLD`)
      - Returns `RegressionReport(passed: bool, results: list[ComparisonResult])`
    - `ComparisonResult`: `template: str`, `profile: str`, `diff_percentage: float`, `passed: bool`, `diff_image_path: Path | None` (generated only on failure)
  - `conftest.py` — pytest fixtures:
    - `@pytest.fixture` `visual_baselines` — loads baselines from committed directory
    - `@pytest.fixture` `regression_runner` — initialized runner with default config
- Baseline storage:
  - `app/rendering/tests/visual_regression/baselines/` — committed to git (binary PNGs)
  - `.gitattributes` entry: `*.png filter=lfs diff=lfs merge=lfs` (if Git LFS available) or direct commit for small baselines
  - Baselines regenerated via `make rendering-baselines` (manual, reviewed before commit)
- Makefile targets:
  - `make rendering-baselines` — regenerate all baselines (manual, destructive)
  - `make rendering-regression` — run visual regression tests (CI-safe)
- CI integration (GitHub Actions or equivalent):
  - Add `rendering-regression` step after `make test`
  - On failure: upload diff images as artifacts
  - PR comment with diff summary (optional, via `gh` CLI)
- Tests:
  - `app/rendering/tests/visual_regression/test_regression.py` — 5+ tests:
    - All baselines match current output → passes
    - Modified emulator rule → detects regression for affected clients
    - New emulator rule with no baseline → skipped (not failed)
    - Threshold override via config
    - Diff images generated on failure
  - Mark with `@pytest.mark.visual_regression` for selective execution
**Security:** Baselines are static PNGs — no secrets. ODiff runs locally. No external calls.
**Verify:** `make rendering-regression` passes on clean main branch. Intentionally modify Gmail emulator rule → regression detected for Gmail profiles with diff image. Restore rule → passes again. `make rendering-baselines` regenerates all baselines. `make test` still passes (visual regression tests excluded by default, only in `make rendering-regression`).
- [ ] 30.2 Visual regression testing in CI

### 30.3 Multi-Browser & CLI E2E Coverage `[Frontend + CI]`
**What:** Extend Playwright configuration to run critical user journeys across Firefox and WebKit (Safari), and integrate the existing CLI-based e2e testing (`agent-browser`) as a complementary exploratory layer that can be triggered manually or on release branches.
**Why:** The visual email builder uses DOM APIs (drag-and-drop, selection, contentEditable, clipboard) that behave differently across browser engines. The current Playwright config only tests Chromium. Firefox and WebKit have known differences in: CSS `user-select` behavior, drag-and-drop DataTransfer API, `contentEditable` cursor positioning, and flexbox rendering. Additionally, the CLI-based e2e test suite (`.claude/commands/e2e-test.md`) provides 13 exploratory journeys via `agent-browser` that complement automated Playwright tests — these should be documented as the exploratory testing strategy and made easy to run.
**Implementation:**
- Modify `cms/apps/web/e2e/playwright.config.ts`:
  - Add Firefox project: `{ name: "firefox", use: { ...devices["Desktop Firefox"] } }`
  - Add WebKit project: `{ name: "webkit", use: { ...devices["Desktop Safari"] } }`
  - Keep Chromium as default for `make e2e`
  - Add `make e2e-all-browsers` for full matrix (CI nightly or release gate)
  - Configure per-browser test selection:
    - `auth.spec.ts`, `dashboard.spec.ts`, `workspace.spec.ts` — run on all 3 browsers
    - `builder.spec.ts` — run on all 3 browsers (most likely to have cross-browser issues)
    - `export.spec.ts`, `approval.spec.ts` — Chromium only (API-heavy, less browser-dependent)
    - `collaboration.spec.ts` — Chromium + Firefox (WebSocket behavior)
  - Tag tests with `@chromium-only`, `@all-browsers` annotations via `test.describe`
- Cross-browser test hardening:
  - `builder.spec.ts` — add browser-specific workarounds:
    - Firefox: use `page.dispatchEvent()` for drag-and-drop (Firefox's native DnD differs)
    - WebKit: add explicit waits for `contentEditable` focus (Safari is slower)
  - `collaboration.spec.ts` — add longer WebSocket connection timeout for Firefox
- CLI e2e integration:
  - Create `cms/apps/web/e2e/CLI_E2E_TESTING.md` — documents the existing CLI-based e2e approach:
    - What it covers (13 user journeys)
    - When to use (exploratory testing, pre-release validation, visual inspection)
    - How to run (`/e2e-test` in Claude Code)
    - How it complements Playwright (Playwright = regression, CLI = exploration)
  - No code changes to the CLI e2e system — it already works
- Makefile targets:
  - `make e2e` — Chromium only (fast, default)
  - `make e2e-firefox` — Firefox only
  - `make e2e-webkit` — WebKit only
  - `make e2e-all-browsers` — full matrix (Chromium + Firefox + WebKit)
- CI integration:
  - PR checks: `make e2e` (Chromium only — fast feedback)
  - Nightly: `make e2e-all-browsers` (full matrix)
  - Release gate: `make e2e-all-browsers` + manual CLI e2e review
- Tests: existing 30.1 tests × 3 browsers where applicable = ~60 total test executions
**Security:** Same as 30.1 — no new security surface. Browser binaries downloaded via `npx playwright install` (official Playwright registry).
**Verify:** `make e2e-all-browsers` runs tests across Chromium, Firefox, and WebKit. Builder drag-and-drop works in all three. Collaboration presence works in Chromium + Firefox. Failures produce per-browser screenshots. CI nightly runs full matrix. `make e2e` (Chromium-only) still completes in <5 minutes.
- [ ] 30.3 Multi-browser & CLI e2e coverage

---

## Execution Order

| Order | Subtask | Depends On | Scope |
|-------|---------|-----------|-------|
| 1 | **27.3** Pre-send rendering gate backend | 27.1, 27.2 (done) | Backend |
| 2 | **27.6** Frontend rendering dashboard & tests | 27.3 | Frontend + Tests |
| 3 | **28.1** QA enforcement in export flow | 27.3 | Backend |
| 4 | **28.2** Approval → export integration | 28.1 | Backend |
| 5 | **28.3** Approval frontend UI | 28.2 | Frontend |
| 6 | **29.1** Brief-only template creation | — | Backend + Frontend |
| 7 | **29.2** Penpot converter integration | — | Backend |
| 8 | **30.1** Playwright e2e suite | 28.3, 29.1 | Frontend + Full-Stack |
| 9 | **30.2** Visual regression in CI | — | Full-Stack + CI |
| 10 | **30.3** Multi-browser & CLI e2e | 30.1 | Frontend + CI |

**Parallelizable:** 29.1 + 29.2 + 30.2 can run in parallel with 28.x. 30.1 should wait for 28.3 (approval UI) so it can test the full flow.

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

| Metric | Phase 26 (Current) | Target (Phase 27) | Target (Phase 28–30) |
|--------|--------------------|--------------------|----------------------|
| Campaign build time | Under 1 hour (faster deterministic CSS pipeline) | Under 1 hour (unchanged — rendering gate adds <2s) | Under 1 hour (unchanged) |
| Cross-client rendering defects | Near-zero + pre-send CSS audit per client | Near-zero + pre-send rendering gate with per-client confidence | Near-zero + enforced QA + approval gates |
| QA checks | 17+ (CSS compatibility audit) | 17+ (unchanged — gate is workflow, not a check) | 17+ (QA now enforced at export) |
| CSS pipeline latency | <500ms (single-pass sidecar, no dual inlining) | <500ms (unchanged) | <500ms (unchanged) |
| Template CSS precompilation | Amortized at registration (0ms CSS optimization at build time) | Amortized (unchanged) | Amortized (unchanged) |
| CSS compatibility visibility | Per-build audit matrix in QA UI with per-client coverage scores | Per-build audit + rendering confidence scores + gate traffic light | Full gate panel: QA + rendering + approval status |
| Email client emulators | 2 (unchanged) | 7 (+ Yahoo, Samsung, Outlook desktop, Thunderbird, Android Gmail) | 7 (unchanged) |
| Rendering profiles | 6 (unchanged) | 14 (+ 8 new client profiles incl. dark mode variants) | 14 (unchanged) |
| Rendering confidence scoring | N/A | Per-client 0–100 confidence with breakdown + recommendations | Per-client (unchanged, surfaced in dashboard) |
| Pre-send rendering gate | N/A | Configurable enforce/warn/skip with per-project thresholds | Rendering + QA + approval gates in export pipeline |
| Export quality enforcement | None (advisory QA only) | Rendering gate (optional) | QA gate + rendering gate + approval gate (configurable per-project) |
| Approval workflow | Backend-only (no UI) | Backend-only (unchanged) | Full UI: request, review, decide, feedback, audit trail |
| E2E test coverage | 1 smoke test (example.spec.ts) | 1 (unchanged) | 32+ Playwright scenarios + visual regression + 3 browsers |
| Design import paths | Figma + Penpot (design file required) | Unchanged | + Brief-only path + enhanced Penpot converter |
