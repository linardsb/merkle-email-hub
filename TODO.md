# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–41):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA). Phase 18 (rendering resilience & property-based testing). Phase 19 (Outlook transition advisor & email CSS compiler). Phase 20 (Gmail AI intelligence & deliverability). Phase 21 (real-time ontology sync & competitive intelligence). Phase 22 (AI evolution infrastructure). Phase 23 (multimodal protocol & MCP agent interface — 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks). Phase 26 (email build pipeline performance & CSS optimization — 5 subtasks). Phase 27 (email client rendering fidelity & pre-send testing — 6 subtasks). Phase 28 (export quality gates & approval workflow — 3 subtasks). Phase 29 (design import enhancements — 2 subtasks). Phase 30 (end-to-end testing & CI quality — 3 subtasks). Phase 31 (HTML import fidelity & preview accuracy — 8 subtasks). Phase 32 (agent email rendering intelligence — 12 subtasks: centralized client matrix, content rendering awareness, import annotator skills, knowledge lookup tool, cross-agent insight propagation, eval-driven skill updates, visual QA feedback loop, MCP agent tools, skill versioning, per-client skill overlays). Phase 33 (design token pipeline overhaul — 12 subtasks). Phase 34 (CRAG accept/reject gate — 3 subtasks). Phase 35 (next-gen design-to-email pipeline — 11 subtasks: MJML compilation, tree normalizer, MJML generation, section templates, AI layout intelligence, visual fidelity scoring, correction learning loop, W3C design tokens, Figma webhooks, section caching). Phase 36 (universal email design document & multi-format import hub — 7 subtasks: EmailDesignDocument JSON Schema, converter refactor, Figma/Penpot adapters, MJML import, HTML reverse engineering, Klaviyo + HubSpot ESP export). Phase 37 (golden reference library for AI judge calibration — 5 subtasks: expand golden component library with VML/MSO/ESP/innovation templates, reference loader & criterion mapping, wire into judge prompts, re-run pipeline & measure improvement, complete human labeling). Phase 38 (pipeline fidelity fix — 8 subtasks). Phase 39 (pipeline hardening — 7 subtasks). Phase 40 (converter snapshot & visual regression testing — 7 subtasks). Phase 41 (converter bgcolor continuity + VLM classification — 7 subtasks: image edge sampler, bgcolor propagation, text color inversion, snapshot regression, VLM component fallback, batch frame export, VLM section classification).

---

~~Phase 37 — Golden Reference Library for AI Judge Calibration~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 38 — Design-to-Email Pipeline Fidelity Fix~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 39 — Pipeline Hardening, Figma Enrichment & Quality Infrastructure~~ DONE — archived to `docs/TODO-completed.md`

---

~~Phase 40 — Converter Snapshot & Visual Regression Testing~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 41 — Converter Background Color Continuity + VLM Classification~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 42 — HTTP Caching, Smart Polling & Data Fetching Hardening~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 43 — Judge Feedback Loop & Self-Improving Calibration~~ DONE — archived to `docs/TODO-completed.md`

~~Phase 44 — Workflow Hardening, CI Gaps & Operational Maturity~~ DONE — archived to `docs/TODO-completed.md`

---

## ~~Phase 45 — Scheduling, Notifications & Build Debounce~~ DONE

> Archived to `docs/TODO-completed.md`. All 6 subtasks complete (45.1–45.6).

---

## Phase 46 — Provider Resilience & Connector Extensibility

> **The platform has a single point of failure per external provider.** Each ESP connector uses one API key. Each LLM call uses one provider credential. When that key is rate-limited, expired, or revoked, the entire feature fails with no fallback. Meanwhile, adding a new ESP connector requires code changes in `app/connectors/` — there's no way to drop in a connector package and have it auto-discovered, despite the plugin system (`app/plugins/`) already supporting manifest-based discovery for other extension types.
>
> **This phase adds credential resilience and connector extensibility.** Key rotation with cooldowns ensures graceful degradation under rate limits. Connector discovery via the existing plugin system makes ESP integrations pluggable. Independent of Phases 37–45. Minimal new infrastructure — extends existing patterns.

- [x] ~~46.1 Credential pool with rotation and cooldowns~~ DONE
- [ ] 46.2 LLM provider key rotation
- [ ] 46.3 ESP connector key rotation
- [ ] 46.4 Credential health API and dashboard
- [ ] 46.5 Dynamic ESP connector discovery via plugin system

---

### 46.1 Credential Pool with Rotation and Cooldowns `[Backend]`

**What:** Add a `CredentialPool` that manages multiple API keys per service, rotates between them on each request (round-robin), and automatically cools down keys that return rate-limit or auth errors. Keys that recover are re-added to the rotation.
**Why:** Single-key configurations are fragile. Batch eval runs exhaust Anthropic rate limits. SFMC campaign pushes hit per-key send limits. With multiple keys and automatic cooldown, the system degrades gracefully instead of failing hard.
**Implementation:**
- Create `app/core/credentials.py`:
  - `CredentialPool(service: str)` — manages keys for a named service
  - `async get_key() -> CredentialLease` — returns next healthy key (round-robin, skip cooled-down)
  - `lease.report_success()` / `lease.report_failure(status_code)` — updates key health
  - On 429/401/403: key enters cooldown (exponential backoff: 30s → 60s → 120s → 300s, max 5min)
  - On 3 consecutive failures: key marked `unhealthy`, removed from rotation until manual re-enable or TTL expiry (1h)
  - Redis state: `credentials:{service}:{key_hash}` with health, cooldown_until, failure_count
- Config: `CREDENTIALS__POOLS` — YAML/JSON mapping of service → list of keys (loaded from env vars, not stored in code)
  ```yaml
  CREDENTIALS__POOLS:
    anthropic: ["${ANTHROPIC_API_KEY_1}", "${ANTHROPIC_API_KEY_2}"]
    sfmc: ["${SFMC_KEY_1}", "${SFMC_KEY_2}"]
  ```
- `CredentialPool` is a singleton per service, initialized at startup
**Verify:** Round-robin rotation across 3 keys. Key entering cooldown on 429 → skipped for 30s. 3 consecutive failures → key marked unhealthy. Healthy key re-added after cooldown expires. Single key fallback works (pool of 1). 14 tests.

---

### 46.2 LLM Provider Key Rotation `[Backend]`

**What:** Wire `CredentialPool` into the LLM provider layer so that `resolve_model()` calls use rotated credentials. Integrate with the existing `fallback.py` chain — key-level rotation happens before model-level fallback.
**Why:** Batch eval runs (`make eval-full`) make hundreds of LLM calls in rapid succession. A single Anthropic key with a 60 RPM limit throttles the entire run. Rotating across N keys gives N× throughput.
**Implementation:**
- Modify `app/ai/providers/` to accept `api_key` parameter from `CredentialPool.get_key()`
- Modify `app/ai/routing.py` `resolve_model()` to return `(model, credential_lease)` tuple
- In `app/ai/service.py`: use lease for the call, `report_success()`/`report_failure()` on response
- Existing `fallback.py` chain: if all keys for a tier are cooled down, fall through to next model in fallback chain (existing behavior) before rotating keys on the fallback model
**Verify:** 2 Anthropic keys configured → alternating usage. Key 1 rate-limited → key 2 used exclusively until cooldown expires. Both keys exhausted → fallback chain kicks in. 8 tests.

---

### 46.3 ESP Connector Key Rotation `[Backend]`

**What:** Wire `CredentialPool` into ESP connectors so that export/push operations rotate across multiple API keys per ESP provider.
**Why:** SFMC and Braze have per-key rate limits for send and content API operations. During campaign pushes (bulk template upload + list segmentation + send), a single key can exhaust its quota.
**Implementation:**
- Modify `app/connectors/base.py` `BaseConnector` to accept `CredentialPool` instead of a single key
- Update SFMC, Braze, and other connectors to call `pool.get_key()` per request
- Report success/failure per request to enable cooldown tracking
- Backward compatible: single key config → pool of 1 (no behavior change)
**Verify:** SFMC connector with 2 keys → alternating usage. Rate-limited key → cooldown → other key used. Single key config → works as before. 6 tests.

---

### 46.4 Credential Health API and Dashboard `[Backend, Frontend]`

**What:** Expose credential pool health status via API and display it in the CMS ecosystem dashboard. Shows per-service key count, healthy/cooled-down/unhealthy breakdown, and recent failure events.
**Why:** Operators need visibility into credential health — especially during batch operations or campaign pushes — to know whether to add keys or investigate provider issues.
**Implementation:**
- `GET /api/v1/credentials/health` — returns per-service pool status (key count, healthy count, cooled-down count, unhealthy count, recent failures). Key values are never exposed — only hashed identifiers.
- `cms/components/ecosystem/credential-health.tsx` — card in ecosystem dashboard showing traffic-light status per service, expandable to show individual key health and cooldown timers
- Admin-only endpoint (requires `admin` role)
**Verify:** API returns pool status for all configured services. Dashboard renders correctly with mixed healthy/cooled-down keys. Non-admin users get 403. 6 tests.

---

### 46.5 Dynamic ESP Connector Discovery via Plugin System `[Backend]`

**What:** Extend the existing `PluginDiscovery` system to support ESP connector plugins. A connector plugin is a directory with a manifest (`connector.yaml`) and a Python module implementing the `BaseConnector` protocol. Discovered connectors are auto-registered in the connector registry at startup.
**Why:** Adding a new ESP currently requires code changes in `app/connectors/`. The plugin system (`app/plugins/discovery.py`) already handles manifest-based directory scanning — extending it to connectors makes ESP integrations pluggable without modifying core code.
**Implementation:**
- Extend `app/plugins/manifest.py` to support `type: connector` plugins with connector-specific fields (provider name, supported operations, auth type)
- Add `app/connectors/plugin_loader.py`: scans `plugins/connectors/` directory, validates manifest, dynamically imports module, verifies it implements `BaseConnector` protocol, registers in connector registry
- Startup: `plugin_registry.discover_and_load(connector_dir)` in `app/main.py` lifespan
- Example plugin structure:
  ```
  plugins/connectors/sendgrid/
    connector.yaml       # name, version, provider, auth_type
    __init__.py          # SendGridConnector(BaseConnector)
  ```
- Plugin validation: manifest schema check, protocol conformance check, duplicate provider name check
**Verify:** Drop a connector plugin into `plugins/connectors/` → auto-discovered at startup. Missing manifest → skipped with warning. Protocol violation → skipped with error. Duplicate provider → conflict logged. 10 tests.

---

### Phase 46 — Summary

| Subtask | Scope | Dependencies | Status |
|---------|-------|--------------|--------|
| 46.1 Credential pool | `app/core/credentials.py`, Redis | None | **Done** |
| 46.2 LLM key rotation | `app/ai/providers/`, `routing.py` | 46.1 | Pending |
| 46.3 ESP key rotation | `app/connectors/base.py` | 46.1 | Pending |
| 46.4 Credential health dashboard | API + `cms/components/ecosystem/` | 46.1 | Pending |
| 46.5 Dynamic connector discovery | `app/connectors/plugin_loader.py`, `app/plugins/` | None | Pending |

> **Execution:** Two independent tracks. **Track A:** 46.1 → 46.2 + 46.3 (parallel) → 46.4. **Track B:** 46.5 (fully independent). Total new code: ~500 LOC + config. One Redis dependency (already available). No database migrations.

---

## Phase 47 — VLM Visual Verification Loop & Component Library Expansion

> **The current converter tops out at ~85–93% fidelity.** Even with VLM-assisted classification (41.5–41.7) and background color continuity (41.1–41.4), the converter makes CSS/spacing/color approximations. A hero image may be 5px too tall, a heading may be `#333` instead of `#2D2D2D`, padding may be 16px instead of 20px. These small errors compound across 10+ sections. Additionally, 89 components can't cover the long tail of email design patterns (countdown timers, testimonials, pricing tables, zigzag layouts).
>
> **Solution — two complementary strategies:**
> 1. **Visual verification loop (~97%):** Converter produces HTML → render in headless browser → screenshot → compare against Figma design screenshot → VLM identifies per-section discrepancies → apply CSS corrections automatically → re-render → repeat 2–3 iterations until converged. The VLM acts as the human eye that would normally review the output.
> 2. **Component library expansion + custom generation (~99%):** Expand from 89 to 150+ hand-built components covering common patterns. When no component matches above a confidence threshold, use the Scaffolder agent to generate a one-off email-safe HTML section from Figma section data + design screenshot.
>
> **Infrastructure reuse:** `app/rendering/local/` has headless browser rendering + 14 email client profiles. `app/rendering/visual_diff.py` has ODiff pixel comparison. `app/ai/agents/visual_qa/` already does VLM screenshot analysis. `app/ai/multimodal.py` has `ImageBlock`. Phase 41.6 provides batch Figma frame screenshots. The Scaffolder agent already generates HTML from briefs with `design_context`.
>
> **Why 99.99% is hard:** Email clients aren't browsers — Outlook uses Word, Gmail strips `<style>`, Yahoo ignores `max-width`. Figma designs use features email can't reproduce (drop shadows, gradients, SVG, blend modes). Sub-pixel rounding: Figma says 14.5px, email rounds to 15px. For modern clients (Apple Mail, Gmail web, Outlook.com): 99% is achievable. For Outlook desktop: 95% is realistic — VML covers the big gaps but Word rendering is fundamentally different.

- [ ] 47.1 Section-level screenshot cropping utility
- [x] ~~47.2 Visual comparison service (VLM section-by-section diff)~~ DONE
- [ ] 47.3 Deterministic correction applicator
- [ ] 47.4 Verification loop orchestrator
- [ ] 47.5 Pipeline integration + configuration
- [ ] 47.6 Component gap analysis + new component templates (89 → 150+)
- [ ] 47.7 Extended component matcher scoring
- [ ] 47.8 Custom component generation (AI fallback for unmatched sections)
- [ ] 47.9 Verification loop tests + snapshot regression
- [ ] 47.10 Diagnostic trace enhancement

---

### 47.1 Section-Level Screenshot Cropping Utility `[Backend]`

**What:** Add `crop_section(full_screenshot: bytes, y_offset: int, height: int, viewport_width: int) -> bytes` to `app/rendering/screenshot_crop.py`. Crops a full-page Playwright screenshot into individual section-level images using Pillow.
**Why:** The visual verification loop compares at section granularity, not full-page. Section bounds come from `EmailSection.y_position` and `EmailSection.height` (from layout analysis). Targeted comparison enables precise CSS corrections instead of vague full-page diffs.
**Implementation:**
- Input: full-page PNG bytes from `LocalRenderingProvider.render_screenshots()` (`app/rendering/local/service.py:39`)
- Crop region: `(0, y_offset, viewport_width, y_offset + height)`
- Handle edge cases: section extends beyond image bounds → clamp to image height
- Use Pillow (already a dependency)
- Return cropped PNG bytes
**Verify:** Crop a 680×2000px full-page screenshot at y=500, height=300 → 680×300px PNG. Edge clamp: y=1900, height=300 on a 2000px image → 680×100px PNG. 4 tests.

---

### 47.2 Visual Comparison Service (VLM Section-by-Section Diff) `[Backend]`

**What:** Add `compare_sections(design_screenshots: dict[str, bytes], rendered_screenshots: dict[str, bytes], html: str, sections: list[EmailSection]) -> VerificationResult` to `app/design_sync/visual_verify.py`. Sends paired section screenshots (Figma design vs rendered HTML) to a VLM for semantic comparison.
**Why:** Pixel diff (ODiff) catches differences but can't explain *what's wrong* or *how to fix it*. A VLM can say "the heading is `#333333` but the design shows `#2D2D2D`" or "the padding-top is ~16px but the design shows ~24px" — returning structured corrections that can be applied automatically.
**Implementation:**
- **ODiff pre-filter:** Before calling VLM (expensive), use existing `run_odiff()` (`visual_diff.py:33`) per section. If `diff_percentage < 2%` → skip VLM for that section (good enough). Estimated savings: ~40–60% fewer VLM calls.
- **VLM prompt:** Multimodal message with paired `ImageBlock`s (design left, rendered right) per section. Prompt: "Compare each pair. For each visible difference: section index, property (color/font/spacing/layout/content), expected value (from design), actual value (from rendered), CSS selector to fix. Only report differences you're confident about."
- **Resolution matching:** Both screenshots at 2x scale. Figma: `fidelity_figma_scale` (default 2.0). Playwright: device scale factor = 2. Viewport width matches Figma frame width.
- **Schemas:**
  - `SectionCorrection`: node_id, section_idx, correction_type (`"color"|"font"|"spacing"|"layout"|"content"|"image"`), css_selector, css_property, current_value, correct_value, confidence, reasoning
  - `VerificationResult`: iteration, fidelity_score (0–1), section_scores (dict), corrections[], pixel_diff_pct, converged
- **Token budget:** ~10K per iteration (5 section pairs at ~1.5K each + prompt + response)
**Verify:** Mock VLM returns 3 corrections for a MAAP section pair. ODiff pre-filter skips sections with diff < 2%. Empty corrections → `converged=True`. 8 tests.

---

### 47.3 Deterministic Correction Applicator `[Backend]`

**What:** Add `apply_corrections(html: str, corrections: list[SectionCorrection]) -> str` to `app/design_sync/correction_applicator.py`. Applies VLM-identified corrections to converter HTML by modifying inline styles within section marker boundaries.
**Why:** Most corrections are simple CSS value changes (wrong color, wrong padding, wrong font-size). These can be applied deterministically without an LLM — just string replacement in inline styles. Only complex layout changes need LLM-based correction.
**Implementation:**
- **HTML targeting:** Section markers (`<!-- section:NODE_ID -->`) are already injected by the converter. Parse HTML, find section boundary, locate element by CSS selector within that section.
- **By correction type:**

| Type | Strategy |
|------|----------|
| `color` | Find element by selector, replace `color:`/`background-color:` value in inline style |
| `font` | Replace `font-size:`/`font-family:`/`font-weight:` in inline style |
| `spacing` | Replace `padding:`/`margin:` values in inline style |
| `layout` | Replace `width:`/`text-align:` — if complex, delegate to LLM |
| `content` | Replace text content (rare — usually means wrong slot fill) |
| `image` | Replace `width`/`height` attributes on `<img>` tags |

- **Fallback:** For corrections that can't be applied deterministically (complex layout restructuring), reuse `correct_visual_defects()` from `app/ai/agents/visual_qa/correction.py`
- Corrections applied in order; later corrections see earlier modifications
**Verify:** Apply `{color, "#333", "#2D2D2D"}` correction → inline style updated. Apply `{spacing, "padding:16px", "padding:24px"}` → padding changed. Section marker targeting isolates changes to correct section. 10 tests.

---

### 47.4 Verification Loop Orchestrator `[Backend]`

**What:** Add `run_verification_loop(html: str, design_screenshots: dict[str, bytes], sections: list[EmailSection], max_iterations: int = 3) -> VerificationLoopResult` to `app/design_sync/visual_verify.py`. Self-correcting render-compare-fix cycle that converges toward design fidelity.
**Why:** A single comparison pass catches obvious errors but may introduce new ones. Iterating 2–3 times allows cascading corrections (fix color → fix dependent text contrast → fix spacing that was masked by wrong color). The loop also detects regressions and stops before making things worse.
**Implementation:**
- **Per iteration:**
  1. Render HTML via `LocalRenderingProvider.render_screenshots()` with `gmail_web` profile (680×900)
  2. Crop rendered screenshot into per-section images via `crop_section()` (47.1)
  3. ODiff pre-filter: skip sections with diff < `vlm_verify_odiff_threshold` (default 2%)
  4. VLM compare remaining sections via `compare_sections()` (47.2)
  5. If `fidelity_score > vlm_verify_target_fidelity` (default 0.97) or no corrections → converge, break
  6. Apply corrections via `apply_corrections()` (47.3) → updated HTML
  7. If score regressed vs previous iteration → revert, use previous HTML, break
  8. Record `VerificationResult`
- **Output:** `VerificationLoopResult`: iterations[], final_html, initial_fidelity, final_fidelity, total_corrections_applied, total_vlm_cost_tokens
- **Safety:** Max iterations cap. Score regression detection (stop early). Per-correction confidence threshold (skip low-confidence fixes).
**Verify:** 3-iteration loop with mock VLM: iteration 1 applies 5 corrections (score 0.82→0.91), iteration 2 applies 2 corrections (0.91→0.96), iteration 3 applies 1 correction (0.96→0.98, converge). Regression detection: score drops → revert to previous iteration's HTML. Max iterations → returns best result. 8 tests.

---

### 47.5 Pipeline Integration + Configuration `[Backend]`

**What:** Wire the verification loop into `converter_service.py` after `_convert_with_components()` returns. Add feature flags and configuration to `app/core/config.py`.
**Why:** The loop must be opt-in (adds latency + VLM cost) and configurable per-connection for gradual rollout.
**Implementation:**
- **Modify `converter_service.py` `convert_document()`** (after component rendering, before QA contracts):
  1. Check `settings.design_sync.vlm_verify_enabled`
  2. If enabled and design screenshots available: call `run_verification_loop(html, design_screenshots, layout.sections)`
  3. Replace `ConversionResult.html` with verified HTML
  4. Add metadata to `ConversionResult`: `verification_iterations: int = 0`, `verification_initial_fidelity: float | None = None`, `verification_final_fidelity: float | None = None`
- **Config** (`app/core/config.py` `DesignSyncConfig`):

| Setting | Env var | Default |
|---------|---------|---------|
| `vlm_verify_enabled` | `DESIGN_SYNC__VLM_VERIFY_ENABLED` | `false` |
| `vlm_verify_model` | `DESIGN_SYNC__VLM_VERIFY_MODEL` | `""` (default routing) |
| `vlm_verify_max_iterations` | `DESIGN_SYNC__VLM_VERIFY_MAX_ITERATIONS` | `3` |
| `vlm_verify_target_fidelity` | `DESIGN_SYNC__VLM_VERIFY_TARGET_FIDELITY` | `0.97` |
| `vlm_verify_odiff_threshold` | `DESIGN_SYNC__VLM_VERIFY_ODIFF_THRESHOLD` | `2.0` |
| `vlm_verify_correction_confidence` | `DESIGN_SYNC__VLM_VERIFY_CORRECTION_CONFIDENCE` | `0.6` |
| `vlm_verify_client` | `DESIGN_SYNC__VLM_VERIFY_CLIENT` | `"gmail_web"` |

- **Relationship to existing Visual QA:** Phase 47 runs BEFORE the blueprint (ensuring converter output matches the design). Visual QA (`app/ai/agents/visual_qa/`) runs AFTER (ensuring cross-client consistency). Complementary, not overlapping.
**Verify:** Flag off → pipeline unchanged, zero VLM calls. Flag on → `ConversionResult` has verification metadata. Design screenshots unavailable → graceful skip. 6 tests.

---

### 47.6 Component Gap Analysis + New Component Templates `[Backend, Templates]`

**What:** Expand the component library from 89 to 150+ hand-built components. Add new HTML files to `email-templates/components/` and entries to `app/components/data/component_manifest.yaml`.
**Why:** The remaining 3% gap at 97% comes from designs that don't map to any existing component. Every new component covers another email design pattern. With 150+ components, most real-world email layouts are covered.
**Implementation:**
- **New components by category:**

| Category | New Components | Count |
|----------|---------------|-------|
| Content | Countdown timer (4 variants), testimonial (3), pricing table (3), team/author bio (2), event card (3), video placeholder (3), FAQ/Q&A (2), social proof/reviews (4) | 24 |
| Structure | Multi-level nav (3), announcement bar (3), app download badges (2), loyalty/points (2) | 10 |
| Interactive | Survey/poll CTA (2), progressive disclosure (2) | 4 |
| Layout | Zigzag/alternating (3), asymmetric hero (2), mosaic grid (2), card grid (3), sidebar (2) | 12 |
| Misc | Structural variants of existing (text-block-centered, hero-video, footer-minimal, etc.) | 11+ |

- All new components: table/tr/td layout, `data-slot` attributes, dark mode classes, MSO conditionals, pass quality contracts
- One `.html` file per slug + manifest entry with slot definitions
**Verify:** `component_manifest.yaml` has 150+ entries. All new HTML files validate (no div/p layout, contrast passes). `make golden-conformance` passes. Slot fill tests for 5 representative new components. 20+ tests.

---

### 47.7 Extended Component Matcher Scoring `[Backend]`

**What:** Add `_score_extended_candidates()` to `component_matcher.py` (called after existing `_score_candidates()` line 192) with scoring rules for the new component types from 47.6.
**Why:** New components need new detection signals. The existing scorer checks img_count, text_count, col_groups — but can't distinguish a countdown timer from a text block, or a testimonial from an article card.
**Implementation:**
- **New scoring signals:**

| Component Type | Detection Signal |
|---------------|-----------------|
| Countdown timer | Numeric text blocks with time-like patterns (HH:MM:SS, colon separators) |
| Testimonial | Quotation marks + short text + small circular image (avatar pattern) |
| Pricing table | Currency symbols, aligned numeric columns, feature/check lists |
| Video placeholder | Play button icon detected, 16:9 aspect ratio image |
| Event card | Date patterns, location text, calendar icon patterns |
| FAQ/Q&A | Question marks in headings, alternating bold/regular text pairs |
| Zigzag layout | Alternating image-left/image-right column groups |

- Append extended candidates to scoring list; existing scoring logic picks highest
- No changes to existing component scoring — purely additive
**Verify:** Synthetic section with time-pattern text → scored as countdown-timer. Section with quote + avatar image → scored as testimonial. Existing component scoring unchanged (regression tests pass). 12 tests.

---

### 47.8 Custom Component Generation (AI Fallback) `[Backend]`

**What:** Add `CustomComponentGenerator` to `app/design_sync/custom_component_generator.py`. When `ComponentMatch.confidence < custom_component_confidence_threshold` (default 0.6), generate a one-off email-safe HTML section from Figma data + design screenshot instead of using a poorly-matched template.
**Why:** Even with 150+ components, some designs have unique layouts (5-column icon grid, brand-specific hero with custom structure). The Scaffolder agent already generates HTML from briefs with `design_context` — generating from Figma section data is a natural extension.
**Implementation:**
- `async generate(section: EmailSection, design_screenshot: bytes | None, tokens: ExtractedTokens) -> RenderedSection`
- Build focused brief from section data: type, texts[], images[], buttons[], column layout, design tokens (colors, typography, spacing)
- Include design screenshot as `ImageBlock` in `design_context` (VLM-capable model sees what to build)
- Call existing `ScaffolderService` with brief: "Generate a single email section (not full email) for [section_type] with [N] text blocks, [M] images, [K] buttons. Table-based layout, inline styles only."
- If verification loop enabled (47.4): run single verification iteration against design screenshot to validate output
- **Integration:** In `converter_service.py` `_convert_with_components()`, after `match_all()`: if `match.confidence < threshold` AND custom gen enabled → call generator, replace the low-confidence `RenderedSection`
- **Cost control:** `DESIGN_SYNC__CUSTOM_COMPONENT_MAX_PER_EMAIL` (default 3) caps how many sections per email use custom generation (~3K tokens each)
- **Config:** `DESIGN_SYNC__CUSTOM_COMPONENT_ENABLED` (default `false`), `DESIGN_SYNC__CUSTOM_COMPONENT_CONFIDENCE_THRESHOLD` (0.6), `DESIGN_SYNC__CUSTOM_COMPONENT_MODEL` (empty = default), `DESIGN_SYNC__CUSTOM_COMPONENT_MAX_PER_EMAIL` (3)
**Verify:** Low-confidence section (0.4) → custom generation triggered. High-confidence section (0.8) → uses template. Cap at 3 → 4th low-confidence section uses template fallback. Generated HTML passes quality contracts. Flag off → no generation. 10 tests.

---

### 47.9 Verification Loop Tests + Snapshot Regression `[Backend, Tests]`

**What:** Comprehensive test suite for the verification loop pipeline (47.1–47.5) and snapshot regression extensions.
**Why:** The loop is multi-stage with many failure modes (VLM errors, score regression, correction conflicts). Thorough testing prevents silent fidelity regressions.

> **GROUND-TRUTH REFERENCE:** `email-templates/training_HTML/for_converter_engine/` contains the primary validation assets for all 3 active cases:
> - **Hand-built reference HTMLs:** `mammut-duvet-day.html` (18 sections), `starbucks-pumpkin-spice.html` (9 sections), `maap-kask.html` (13 sections) — visually verified correct output
> - **Design screenshots:** `mammut-duvet-day.png`, `starbucks-pumpkin-spice.png`, `maap-kask.png` — full-page Figma design captures for visual comparison baseline
> - **Section-level annotations:** `CONVERTER-REFERENCE.md` — per-section component mappings, slot fills, style overrides, bgcolor values, and design reasoning for all 3 emails. Use as assertion ground truth for correction accuracy and fidelity scoring.
> - **Figma links + node IDs:** `training_figma_links_and_screenhsots.md` — Figma URLs, node IDs (2833-1135, 2833-1424, 2833-1623), case-to-asset directory mapping, and re-export instructions
>
> **ASSET LAYOUT:** Test image assets are **case-scoped** in `data/debug/{case_id}/assets/` (not the legacy `data/design-assets/` bulk dumps):
> - Case 5 (MAAP): `data/debug/5/assets/` — 98 images (node 2833-1623 descendants)
> - Case 6 (Starbucks): `data/debug/6/assets/` — 21 images (node 2833-1424 descendants)
> - Case 10 (Mammut): `data/debug/10/assets/` — 38 images (node 2833-1135 descendants)
>
> `data/design-assets/{connection_id}/` is the **runtime cache** for live Figma downloads (ephemeral, gitignored). Test fixtures must never depend on it.

**Implementation:**
- **New:** `app/design_sync/tests/test_visual_verify.py` — loop convergence, regression detection, max iterations, ODiff pre-filter
- **New:** `app/design_sync/tests/test_correction_applicator.py` — each correction type, section marker targeting, inline style edge cases
- **Extend:** `test_snapshot_regression.py` — store `design_section_screenshots/` per debug case. Run verification loop with mock VLM on 3 active cases (MAAP, Starbucks, Mammut). Assert final fidelity improves vs unverified baseline. Use `CONVERTER-REFERENCE.md` per-section bgcolor/style annotations as expected values for correction assertions.
- **New snapshot data:** Per debug case, add `design_section_screenshots/{node_id}.png` for section-level Figma exports. Full-page design PNGs from `email-templates/training_HTML/for_converter_engine/` serve as the cropping source for section-level screenshots (47.1).
**Verify:** `make test` — all pass. `make snapshot-test` — 3 cases pass with verification metadata. Correction applicator handles all 6 correction types. Loop handles VLM timeout/error gracefully.

---

### 47.10 Diagnostic Trace Enhancement `[Backend]`

**What:** Extend `SectionTrace` in `app/design_sync/diagnose/models.py` with verification and generation fields. Wire into `DiagnosticRunner`.
**Why:** Developers need visibility into which sections used VLM classification, verification corrections, or custom generation — for debugging and tuning thresholds.
**Implementation:**
- Add to `SectionTrace`: `vlm_classification: str | None`, `vlm_confidence: float | None`, `verification_fidelity: float | None`, `corrections_applied: int = 0`, `generation_method: str = "template"` (`"template"` | `"custom"`)
- Add to `DiagnosticReport`: `verification_loop_iterations: int = 0`, `final_fidelity: float | None = None`
- Wire into `DiagnosticRunner.run_from_structure()` — capture verification results
- **Observability events** (structured logging via `get_logger()`):

| Event | Key Fields |
|-------|------------|
| `design_sync.verify_loop.iteration` | iteration, fidelity_score, corrections_count, converged |
| `design_sync.verify_loop.completed` | iterations, initial_fidelity, final_fidelity, total_token_cost |
| `design_sync.custom_component.generated` | section_type, confidence, generation_time_ms |

**Verify:** Diagnostic report includes verification fields. Events logged on verification run. 4 tests.

---

### Phase 47 — Summary

| Subtask | Scope | Dependencies | Status |
|---------|-------|--------------|--------|
| 47.1 Screenshot cropping | `app/rendering/screenshot_crop.py`, Pillow | None | Pending |
| 47.2 VLM section comparison | `app/design_sync/visual_verify.py` | 47.1, 41.6 | **Done** |
| 47.3 Correction applicator | `app/design_sync/correction_applicator.py` | None | Pending |
| 47.4 Verification loop | `app/design_sync/visual_verify.py` | 47.1 + 47.2 + 47.3 | Pending |
| 47.5 Pipeline integration | `converter_service.py`, `config.py` | 47.4 | Pending |
| 47.6 New component templates | `email-templates/components/`, manifest | None | Pending |
| 47.7 Extended matcher scoring | `component_matcher.py` | 47.6 | Pending |
| 47.8 Custom component generation | `custom_component_generator.py` | 47.6, Scaffolder agent | Pending |
| 47.9 Verification tests | `tests/test_visual_verify.py` | 47.4 + 47.5 | Pending |
| 47.10 Diagnostic enhancement | `diagnose/models.py`, `diagnose/runner.py` | 47.4 + 47.8 | Pending |

> **Execution:** Three independent tracks. **Track A (visual verify loop):** 47.1 + 47.3 (parallel, no deps) → 47.2 (needs 47.1 + 41.6) → 47.4 → 47.5 → 47.9. **Track B (component expansion):** 47.6 → 47.7 + 47.8 (parallel). **Track C (diagnostics):** 47.10 (after tracks A + B). Tracks A and B can proceed in parallel. Token cost worst case: ~44K per email (verify loop ~30K + custom gen ~9K + classification ~5K). All behind feature flags — zero behavior change when disabled.

> **Fidelity ladder:** Phase 40 completion (~85%) → Phase 41 VLM classification (~93%) → Phase 47.1–47.5 visual verify loop (~97%) → Phase 47.6–47.8 component expansion + custom gen (~99%). Each layer is independently valuable and incrementally deployable.
