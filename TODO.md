# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–10):** See [docs/TODO-completed.md](docs/TODO-completed.md)

## Phase 11 — QA Engine Hardening & Agent Quality Improvements ✅

> **Tasks 11.1-11.24 COMPLETE.** Detailed descriptions: [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: 11 QA checks upgraded to DOM-parsed validation (11.1-11.12), 8 agent skills hardened (11.13-11.21), template-first hybrid architecture (11.22, all 9 subtasks — golden templates + structured output + cascading repair + SKILL.md rewrites + eval-driven iteration), inline eval judges on retries (11.23), production trace sampling (11.24).

### 11.25 Client Design System & Template Customisation

**What:** Bridge the gap between the global golden template library (`app/ai/templates/`) and the user-managed component library (`app/components/`) by adding per-project design systems, component-to-section adapters, project-scoped template registries, and constraint injection into the agent pipeline. Currently these two HTML stores are completely disconnected — golden templates are global with no client scoping, `DesignTokens` are invented by the LLM from scratch every request, and user-created components never enter the agent composition pipeline.

**Why:** Without client-level customisation, every project gets identical template choices and the LLM guesses brand colors/fonts each time, producing inconsistent output that fails brand compliance. A Pampers email could end up with Nike's typography. A client's custom branded footer sits unused in the component library while the agent generates a generic one. The brand compliance check catches violations AFTER generation (reactive), triggering retry loops — instead of preventing them at generation time (proactive). This task makes design systems the single source of truth used for generation (Pass 3 constraints), repair (brand repair stage), and validation (brand compliance check).

**Dependencies:** 11.22.1 (golden templates), 11.22.3 (multi-pass pipeline), 11.22.4 (repair pipeline), 11.22.7 (composer/sections). Phase 2 (component library). 11.22.8 (agent role redefinition — Phase A is a prerequisite for meaningful agent constraint injection).

**Architecture pattern:** One source of truth (design system) → three uses: generative constraints (Pass 3 locked tokens), deterministic repair (brand repair stage), validation (brand compliance check). Component → Section bridge uses existing repair pipeline to harden user HTML before it enters the composition system.

**Use cases:**
1. **Single-brand onboarding (Nike):** Admin configures design system (palette, fonts, logo, footer text) + pins branded header/footer components as section overrides. Every agent-generated email inherits Nike's exact identity. Pass 3 locks colors to the palette. Assembly swaps footer section with Nike's component. Brand compliance validates the same data used for generation — zero drift.
2. **Multi-brand portfolio (P&G — Tide + Pampers):** Same ClientOrg, two Projects with distinct design systems. Tide gets bold orange palette + Impact headings + sharp CTAs + `promotional_grid` preference. Pampers gets soft teal/pink + Georgia serif + rounded CTAs + `newsletter_1col` preference. Same agent pipeline, radically different outputs driven by project config. Zero cross-contamination.
3. **Campaign-specific template iteration (Sephora Holiday):** Developer creates `holiday-gift-grid` component, annotates slots, QA bridge validates (0.87 → repair hardens to 0.94), promotes to project section block. Composer uses it for December campaigns. January: unpinned, component stays in library but exits the composition pipeline. Temporary customisation without permanent architecture changes.

#### 11.25.1 Client Design System Model — Per-Project Brand Identity Store
**What:** Create a `DesignSystem` Pydantic model storing brand palette, typography, logo, footer config, button style, and social links. Persist as a JSON column on the `Project` model. Expose via API endpoints. Link to brand compliance so validation and generation use identical data.
**Why:** Highest-impact change — eliminates LLM color/font guessing entirely. Currently `DesignTokens` are generated from scratch every request. With a design system, Pass 3 receives the client's exact palette as constraints, not suggestions.
**Implementation:**
- Create `app/projects/design_system.py`:
  - `BrandPalette` frozen dataclass: `primary`, `secondary`, `accent`, `background`, `text`, `link` (hex strings), optional `dark_background`, `dark_text` for dark mode variants
  - `Typography` frozen dataclass: `heading_font`, `body_font` (CSS font stacks), `base_size` (default `"16px"`)
  - `LogoConfig` frozen dataclass: `url`, `alt_text`, `width: int`, `height: int`
  - `FooterConfig` frozen dataclass: `company_name`, `legal_text`, `address`, `unsubscribe_text`
  - `SocialLink` frozen dataclass: `platform` (Literal), `url`, `icon_url`
  - `DesignSystem` frozen dataclass: `palette`, `typography`, `logo: LogoConfig | None`, `footer: FooterConfig | None`, `social_links: tuple[SocialLink, ...]`, `button_border_radius`, `button_style: Literal["filled", "outlined", "text"]`
  - `load_design_system(raw: dict) -> DesignSystem` — parse JSON from DB column
  - `design_system_to_brand_rules(ds: DesignSystem) -> dict` — convert to `brand_compliance` params format (`allowed_colors`, `required_fonts`, `required_elements`)
- Add `design_system: Mapped[dict[str, Any] | None]` JSON column to `Project` model
- Alembic migration: `add_design_system_to_project`
- Add API endpoints to `app/projects/routes.py`:
  - `GET /api/v1/projects/{id}/design-system` — returns `DesignSystem` or empty default
  - `PUT /api/v1/projects/{id}/design-system` — validates via Pydantic, stores JSON
  - Auth: `developer`+`admin` for PUT, `viewer`+ for GET
- When `design_system` is set and `qa_profile.brand_compliance.params` is empty, auto-populate brand compliance params from design system via `design_system_to_brand_rules()` — one source of truth, no manual duplication
**Security:** Design system is project-scoped, validated by Pydantic. Hex color values validated by regex (`^#[0-9a-fA-F]{6}$`). Font stacks are strings (no code execution). Logo URL validated as HTTPS. No raw user input reaches SQL.
**Verify:** Create project with design system via API. Verify JSON stored correctly. Verify `design_system_to_brand_rules()` produces valid brand compliance params. Run brand compliance check — uses design system colors. `make test` passes. `make types` clean.
- [x] ~~11.25.1 Client design system model~~ DONE

#### 11.25.2 Component → Section Bridge — Adapter for Agent Pipeline
**What:** Create a `SectionAdapter` that converts a QA-validated `ComponentVersion` into a `SectionBlock` compatible with the `TemplateComposer`. Users annotate content slots when uploading components. The adapter hardens HTML via the repair pipeline before it enters the composition system.
**Why:** User-created components (branded headers, footers, CTAs, product cards) currently sit in the component library with no path into the agent pipeline. This bridge lets users' best components become building blocks that the composer and agents can use, while the repair pipeline ensures they meet golden template quality standards.
**Implementation:**
- Create `app/components/section_adapter.py`:
  - `SlotHint` dataclass: `slot_id`, `slot_type: SlotType`, `selector: str`, `required: bool`, `max_chars: int | None`
  - `SectionAdapter` class:
    - `adapt(version: ComponentVersion, slot_hints: list[SlotHint]) -> SectionBlock` — takes component HTML, runs through `RepairPipeline.run()` to harden (MSO, dark mode, a11y), injects `data-slot` markers from slot_hints, validates QA score ≥ 0.8, returns `SectionBlock`
    - `validate_for_composition(block: SectionBlock) -> list[QACheckResult]` — runs QA checks, returns results
  - `AdaptationError` exception — raised if QA score < 0.8 after repair
- Extend `ComponentVersion` model: add `slot_definitions: Mapped[list[dict[str, Any]] | None]` JSON column
- Extend `VersionCreate` schema: add optional `slot_definitions: list[SlotHint] | None`
- Alembic migration: `add_slot_definitions_to_component_versions`
- Cache adapted sections per component version ID (immutable once version is created)
**Security:** Component HTML sanitised by existing `sanitize_component_html()` before adaptation. Repair pipeline is deterministic (no LLM). Slot hints validated by Pydantic. `data-slot` injection uses `lxml` DOM manipulation (no string interpolation).
**Verify:** Create component with slot_definitions. Adapt via `SectionAdapter`. Verify: repair pipeline hardens HTML (adds MSO/dark mode/a11y). Slot markers injected correctly. QA score ≥ 0.8. Adapted `SectionBlock` works with `TemplateComposer.compose()`. Component with un-repairable HTML raises `AdaptationError`. `make test` passes.
- [x] ~~11.25.2 Component → section bridge~~ DONE

#### 11.25.3 Project-Scoped Template Registry — Client-Specific Template Sets
**What:** Extend `TemplateRegistry` with project awareness. Each project sees global golden templates (minus disabled ones) + project-specific custom templates (adapted from components) + section overrides (client components replacing default sections). Add `ProjectTemplateConfig` model stored as JSON on `Project`.
**Why:** Without project scoping, all projects see identical templates. A client that only sends transactional emails still sees promotional templates in the LLM's selection list (noise). A client with custom branded sections can't inject them into the composition pipeline.
**Implementation:**
- Create `app/projects/template_config.py`:
  - `SectionOverride` dataclass: `section_block_id: str`, `component_version_id: int`
  - `CustomSection` dataclass: `component_version_id: int`, `block_id: str`
  - `ProjectTemplateConfig` dataclass:
    - `section_overrides: tuple[SectionOverride, ...]` — e.g., `("footer_standard", 42)` → "always use component v42 as footer"
    - `custom_sections: tuple[CustomSection, ...]` — component versions promoted to section blocks
    - `disabled_templates: tuple[str, ...]` — golden template names to exclude
    - `preferred_templates: tuple[str, ...]` — golden template names to prioritise in selection
- Add `template_config: Mapped[dict[str, Any] | None]` JSON column to `Project` model
- Alembic migration: `add_template_config_to_project`
- Extend `TemplateRegistry`:
  - `get_for_project(project_id: int, template_config: ProjectTemplateConfig, db: AsyncSession) -> list[GoldenTemplate]` — returns merged template list:
    1. Load global golden templates
    2. Remove `disabled_templates`
    3. Adapt `custom_sections` via `SectionAdapter` (Phase B) and add to composer's available sections
    4. Apply `section_overrides` — when composing, swap default sections with client's components
    5. Tag `preferred_templates` for LLM selection prompt (listed first with "recommended" marker)
  - `list_for_selection_scoped(project_id, template_config) -> list[TemplateMetadata]` — project-aware version of `list_for_selection()`
- Add API endpoints to `app/projects/routes.py`:
  - `GET /api/v1/projects/{id}/template-config` — returns `ProjectTemplateConfig` or empty default
  - `PUT /api/v1/projects/{id}/template-config` — validates, stores JSON
  - Auth: `developer`+`admin` for PUT, `viewer`+ for GET
**Security:** Template config is project-scoped, validated by Pydantic. Component version IDs validated against DB (must exist and be accessible to project). Disabled/preferred template names validated against registry (must exist). No arbitrary code paths.
**Verify:** Configure project with `disabled_templates=["minimal_text"]`, `preferred_templates=["promotional_hero"]`, one section override, one custom section. Call `get_for_project()`. Verify: `minimal_text` excluded, `promotional_hero` first in list, section override swaps correctly, custom section available to composer. Unconfigured project returns full global list (backward compatible). `make test` passes.
- [x] ~~11.25.3 Project-scoped template registry~~ DONE

#### 11.25.4 Agent Pipeline Constraint Injection — Design System as Generation Constraints
**What:** Update the multi-pass pipeline to inject design system constraints into each pass. Pass 1 receives project-scoped template list. Pass 2 receives design system footer text as locked slot content. Pass 3 receives the design system palette as constraints — the LLM decides which palette color goes where but CANNOT invent new colors. Assembly enforces locked fields, overriding any LLM deviation.
**Why:** Without constraint injection, the design system is validation-only (brand compliance catches violations after generation). Constraint injection makes it generative — the LLM works within the client's brand identity from the start, eliminating retry loops caused by brand violations.
**Implementation:**
- Extend `DesignTokens` in `app/ai/agents/schemas/build_plan.py`:
  - Add `source: Literal["design_system", "llm_generated", "brief_extracted"] = "llm_generated"`
  - Add `locked_fields: tuple[str, ...] = ()` — field names from design system that assembly should enforce
- Update `app/ai/agents/scaffolder/pipeline.py` (multi-pass pipeline):
  - Accept `design_system: DesignSystem | None` and `template_config: ProjectTemplateConfig | None` parameters
  - **Pass 1 (Layout):** inject project-scoped template list via `list_for_selection_scoped()`. If `preferred_templates` set, include "RECOMMENDED" marker in prompt
  - **Pass 2 (Content):** if `design_system.footer` exists, pre-fill footer slot content as locked (LLM cannot override). If `design_system.logo` exists, pre-fill logo image slot
  - **Pass 3 (Design):** inject `design_system.palette` as "You MUST use ONLY these colors: {palette}. Assign each color to a role (primary_color, background_color, etc.)." Set `locked_fields` on output `DesignTokens`
- Update `app/ai/agents/scaffolder/assembler.py`:
  - After assembly, enforce locked fields: if `design_tokens.source == "design_system"`, replace any LLM-deviated values with design system originals
  - Apply section overrides: swap sections per `template_config.section_overrides`
- Update `app/ai/blueprints/nodes/scaffolder_node.py`:
  - Load project's `design_system` and `template_config` from `NodeContext.metadata` (injected by blueprint engine from project config)
  - Pass to pipeline
**Security:** Design system values are project-owned, loaded from DB. Palette colors validated as hex. Font stacks are CSS strings (no injection). Locked field enforcement is deterministic string replacement. No new LLM prompt injection surface (design system is system-prompt-level context, not user input).
**Verify:** Create project with design system (palette + footer + logo). Run scaffolder pipeline. Verify: Pass 1 uses project-scoped template list. Pass 2 pre-fills footer/logo slots. Pass 3 output uses only palette colors. Assembly enforces locked fields. Brand compliance check passes on first attempt (no retry needed). Compare: same brief without design system → LLM invents colors → may fail brand compliance. `make test` passes.
- [x] ~~11.25.4 Agent pipeline constraint injection~~ DONE

#### 11.25.5 Consistency Enforcement — Brand Repair Stage & End-to-End Validation
**What:** Add a `brand` repair stage to the repair pipeline that auto-corrects off-palette colors and missing design system elements. Link brand compliance check to read from design system directly. Create end-to-end integration test covering the full flow: design system config → agent generation → repair → QA gate.
**Why:** Defense in depth. Even with constraint injection (11.25.4), edge cases can produce off-brand output (LLM hallucinating a color despite constraints, slot content from user input containing off-brand styles). The brand repair stage is the last deterministic safety net before QA validation.
**Implementation:**
- Create `app/qa_engine/repair/brand.py` — `BrandRepair(RepairStage)`:
  - If project has design system, scan assembled HTML for inline CSS colors
  - Replace off-palette colors with nearest palette match (Euclidean distance in RGB space)
  - If footer text doesn't match `design_system.footer.legal_text`, inject correct footer
  - If logo `src` doesn't match `design_system.logo.url`, correct it
  - Log all corrections as `repair_warnings`
- Register `BrandRepair` as Stage 8 in `RepairPipeline` (after existing Stage 7 links.py)
- Update `app/qa_engine/checks/brand_compliance.py`:
  - If `QACheckConfig.params` is empty but project has `design_system`, auto-populate params from `design_system_to_brand_rules()` at check time
  - This ensures brand compliance uses the same data regardless of whether params were manually configured or derived from design system
- Create `app/ai/templates/tests/test_design_system_e2e.py` — end-to-end integration test:
  - Set up project with design system (Nike use case)
  - Set up section overrides (custom footer component)
  - Run scaffolder pipeline with design system constraints
  - Verify: output HTML uses only palette colors, correct fonts, Nike footer, Nike logo
  - Run repair pipeline — verify no-op (constraints already correct)
  - Run QA gate — verify brand compliance passes
  - Compare: remove design system, run same brief — verify inconsistent output
**Security:** Brand repair is deterministic color replacement via lxml/regex. No LLM calls. Nearest-color calculation is pure math. Footer/logo injection uses design system values (trusted, admin-configured). No user input in repair logic.
**Verify:** Run repair pipeline on HTML with 3 off-palette colors → all corrected to nearest palette match. Run on HTML with wrong footer → footer replaced. Run on already-correct HTML → no-op (idempotent). End-to-end test passes for all 3 use cases (Nike, P&G multi-brand, Sephora holiday). `make test` passes. `make types` clean. `make check` green.
- [x] ~~11.25.5 Consistency enforcement~~ DONE

### ~~11.23 Inline Eval Judges — Selective LLM Judge on Recovery Retries~~ DONE
**What:** Wire eval judges (`JUDGE_REGISTRY`) into the blueprint engine as an inline quality signal, but ONLY on self-correction retries (`iteration > 0`). First-attempt agents rely on the fast QA gate (0 tokens, <200ms). When an agent has already failed QA and is retrying, invoke the LLM judge for that agent to get a nuanced verdict before deciding whether to retry again or escalate to human review.
**Why:** The 10-point QA gate catches structural issues but misses semantic quality (brief fidelity, tone accuracy, colour coherence). Eval judges check 5 nuanced criteria per agent but cost ~3,200 tokens per call. Running judges on every handoff is cost-prohibitive (+67% per run). Running them only on retries bounds the cost (max 2 retries × 1 judge = 6,400 extra tokens) and targets the moment where the signal is most valuable — the agent already failed once and extra context prevents wasted retry loops. After 11.22 (template-first), retries are rare (~5% of runs), making the cost negligible.
**Implementation:**
- Create `app/ai/blueprints/inline_judge.py` — adapter between `JUDGE_REGISTRY` judges and `NodeContext`. Builds `JudgeInput` from live context (brief, HTML output, QA failures, handoff history). Calls judge via provider registry with `temperature=0.0` and `AI__MODEL_LIGHTWEIGHT` tier.
- Update `app/ai/blueprints/engine.py` — after agentic node execution when `iteration > 0` and `self._judge_enabled`, call `run_inline_judge()`. If `verdict.overall_pass` is False, set `run.status = "needs_review"` and break (don't retry again). If True, proceed to QA gate normally.
- Add `judge_verdict: JudgeVerdict | None` field to `BlueprintRun` dataclass in `protocols.py`
- Expose `judge_verdict` in `BlueprintRunResponse` schema (criterion results + reasoning visible in API)
- Engine config: `judge_on_retry: bool` (default `False`, opt-in per blueprint definition)
- Use lightweight model to keep cost low (~1,500 tokens with Haiku-tier vs ~3,200 with Sonnet)
**Security:** Judge prompts contain only generated HTML + brief (already in agent context). No new user input paths. Judge response parsed as structured JSON, validated against `JudgeVerdict` schema.
**Verify:** Blueprint test with intentionally flawed HTML: first attempt → QA fail → recovery → fixer retry triggers judge → judge verdict surfaces in API response. Compare: run with judge enabled escalates bad retries faster (fewer wasted loops) vs run without judge retries blindly. Cost delta measurable via `run.model_usage`.

### ~~11.24 Production Trace Sampling for Offline Judge Feedback Loop~~ DONE
**What:** Sample a configurable percentage of successful production blueprint runs and judge them asynchronously in a background worker. Results feed back into `traces/analysis.json`, which `failure_warnings.py` reads to inject updated failure patterns into agent system prompts. This closes the eval feedback loop — agents continuously learn from production data, not just synthetic test cases.
**Why:** Current eval data is synthetic (12-14 cases per agent). Real production briefs have different distributions of complexity, client requirements, and edge cases. Without production sampling, `failure_warnings.py` only reflects synthetic test failures. With sampling, agents get warnings based on actual production quality — the feedback loop becomes self-improving.
**Implementation:**
- ~~Create `app/ai/agents/evals/production_sampler.py`:~~
  - ~~`enqueue_for_judging(trace: BlueprintTrace, sample_rate: float)` — probabilistic Redis enqueue~~
  - ~~`ProductionJudgeWorker` — pulls from Redis queue, runs agent-specific judge, appends verdict to `traces/production_verdicts.jsonl`~~
  - ~~`refresh_analysis()` — merges production verdicts with synthetic verdicts, regenerates `traces/analysis.json`~~
- ~~Update `app/ai/blueprints/service.py` — on successful blueprint completion (`status == "completed"` and `qa_passed`), call `enqueue_for_judging()` with configured sample rate~~
- ~~Add config: `EVAL__PRODUCTION_SAMPLE_RATE` (default `0.0` — disabled until opted in), `EVAL__PRODUCTION_QUEUE_KEY` (Redis key)~~
- ~~`failure_warnings.py` already reads from `traces/analysis.json` — no changes needed (production verdicts merged via `refresh_analysis()`)~~
- ~~Add `make eval-refresh` command to manually trigger analysis refresh from production verdicts~~
- ~~Worker runs via `DataPoller` pattern (same as `OutcomeGraphPoller`, `CanIEmailSyncPoller`), registered in `app/main.py` lifecycle~~
**Security:** Production traces contain generated HTML + briefs (no raw user credentials). Sampling rate configurable to control LLM cost. Redis queue uses same auth as existing Redis config. Verdicts stored locally in `traces/` (not exposed via API).
**Verify:** ~~Set sample rate to 1.0 (100%) in test. Run 5 blueprints → verify 5 traces enqueued → worker processes all 5 → `production_verdicts.jsonl` has 5 entries → `refresh_analysis()` produces updated `analysis.json` with production data merged. Agent prompt includes warnings derived from production failures.~~ 15/15 tests pass, mypy + pyright clean.

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

## Success Criteria (Plan Section 14.2)

| Metric | Target (3 months) | Target (6 months) |
|--------|-------------------|-------------------|
| Campaign build time | 1-2 days (from 3-5) | Under 1 day |
| Cross-client rendering defects | Caught before export | Near-zero reaching client |
| Component reuse rate | 30-40% | 60%+ |
| AI agent adoption | Team actively using 3 agents | Agents embedded in daily workflow |
| Knowledge base entries | 200+ indexed | 500+, team contributing |
| Cloud AI API spend | Under £600/month | Under £600/month |

---

## Phase 12 — Design-to-Email Import Pipeline

**What:** Pull actual design files from Figma, convert them to editable Maizzle email templates via AI-assisted conversion, extract components, and import images — all through the Hub UI. Extends the existing `design_sync` module beyond token extraction.
**Approach:** AI-assisted conversion — extract layout structure + images from Figma, generate a structured brief, feed to the Scaffolder agent to produce Maizzle HTML. User can review/edit the brief before conversion.
**Scope:** Figma only (real API). Sketch/Canva stubs remain unchanged.
**Dependencies:** Phase 2 (Scaffolder agent), Phase 4.3 (design_sync module), Phase 0.3 (SDK).

### 12.1 Extend Protocol & Figma API Integration
**What:** Add 3 new methods to `DesignSyncProvider` protocol + implement in Figma provider. New dataclasses: `DesignNode`, `DesignFileStructure`, `DesignComponent`, `ExportedImage`.
**Files:** `app/design_sync/protocol.py`, `app/design_sync/figma/service.py`, `app/design_sync/sketch/service.py`, `app/design_sync/canva/service.py`
**Implementation:**
- `get_file_structure(file_ref, access_token)` → parse Figma `GET /v1/files/{key}` into `DesignNode` tree
- `list_components(file_ref, access_token)` → `GET /v1/files/{key}/components` → `list[DesignComponent]`
- `export_images(file_ref, access_token, node_ids, format, scale)` → `GET /v1/images/{key}` → `list[ExportedImage]` (batch max 100 IDs)
- Sketch/Canva: stub implementations returning empty results
**Security:** Uses existing Fernet-encrypted PAT storage. No new credential handling.
**Verify:** Unit test Figma JSON parsing. Stub providers return empty defaults.
- [x] ~~12.1 Protocol extension + Figma API integration~~ DONE

### 12.2 Asset Storage Pipeline
**What:** Download images from Figma's temporary URLs (expire ~14 days), store locally, serve via authenticated endpoint.
**Files:** New `app/design_sync/assets.py`. Modify `app/core/config.py`, `app/design_sync/routes.py`.
**Implementation:**
- `DesignAssetService`: download via httpx, store at `data/design-assets/{connection_id}/{node_id}.{format}`
- Resize if >1200px wide (2x retina for 600px email containers), optional Pillow compression
- `GET /api/v1/design-sync/assets/{connection_id}/{filename}` — serve with BOLA check
- Path traversal prevention in `get_stored_path()`
- `asset_storage_path` config in `DesignSyncConfig`
**Security:** BOLA check on connection access. Path traversal guard. No directory listing.
**Verify:** Download mock URL → file stored → serve via endpoint returns correct bytes.
- [x] ~~12.2 Asset storage pipeline~~ DONE

### 12.3 Design Import Models & Migration
**What:** Track import jobs (`DesignImport`) and their exported assets (`DesignImportAsset`).
**Files:** `app/design_sync/models.py`, `alembic/versions/`, `app/design_sync/repository.py`, `app/design_sync/schemas.py`
**Implementation:**
- `DesignImport`: id, connection_id, project_id, status (pending|extracting|converting|completed|failed), selected_node_ids (JSON), structure_json, generated_brief, template_id (FK), error_message, created_by_id
- `DesignImportAsset`: id, import_id (CASCADE), node_id, node_name, file_path, width, height, format, usage (hero|logo|icon|background|content)
- Alembic migration for both tables with indexes
- Repository CRUD: create_import, get_import, update_import_status, create_import_asset, list_import_assets
- Request/response Pydantic schemas for all new models
**Security:** FKs enforce referential integrity. BOLA via project_id.
**Verify:** Migration up/down clean. Repository CRUD unit tests pass.
- [x] ~~12.3 Design import models & migration~~ DONE

### 12.4 Layout Analyzer & Brief Generator
**What:** Convert Figma document structure into a Scaffolder-compatible campaign brief.
**Files:** New `app/design_sync/figma/layout_analyzer.py`, `app/design_sync/brief_generator.py`
**Implementation:**
- `LayoutAnalyzer`: pure function, no I/O. Input: `DesignFileStructure` (selected nodes). Detect email sections (header, hero, content, CTA, footer) by name conventions + position. Detect column layouts from sibling frames. Extract text from TEXT nodes. Identify image placeholders. Output: `DesignLayoutDescription` with typed `EmailSection` list.
- `BriefGenerator`: transform layout + images into structured markdown brief. Image refs point to local asset URLs. Includes design token summary. User can edit before conversion.
**Security:** Pure computation. No I/O, no user input in SQL or templates.
**Verify:** Mock Figma JSON → expected section detection. Layout with 2 columns → correct brief format.
- [x] ~~12.4 Layout analyzer & brief generator~~ DONE

### 12.5 AI-Assisted Conversion Pipeline
**What:** Wire Figma import → Scaffolder agent → Template creation. Full orchestration service.
**Files:** New `app/design_sync/import_service.py`. Modify `app/design_sync/routes.py`, `app/design_sync/schemas.py`, `app/ai/agents/scaffolder/schemas.py`, `app/ai/agents/scaffolder/prompt.py`, `app/ai/agents/scaffolder/service.py`
**Implementation:**
- `DesignImportService` orchestrator: fetch structure → export images → analyze layout → generate brief → call Scaffolder → create Template + TemplateVersion → update import status
- Status polling: frontend polls `GET /imports/{id}` until completed/failed
- `DesignContext` schema for Scaffolder: image_urls, design_tokens, source
- Scaffolder prompt enhancement: when design_context present, use image URLs as `<img src>`, apply design tokens as inline styles
- 6 new API endpoints: GET structure, GET components, POST export-images, POST imports, GET import status, PATCH import brief
**Security:** BOLA on all endpoints. Rate limit imports. Scaffolder sanitises output via nh3.
**Verify:** Mock Figma API + mock Scaffolder → import completes with template. Brief edit → re-conversion works.
- [ ] 12.5 AI-assisted conversion pipeline

### 12.6 Component Extraction
**What:** Extract Figma components → Hub `Component` + `ComponentVersion` with auto-generated HTML.
**Files:** New `app/design_sync/component_extractor.py`. Modify `app/design_sync/routes.py`, `app/design_sync/schemas.py`
**Implementation:**
- `ComponentExtractor`: list components from Figma, export PNG previews, detect category (button→cta, header→header, footer→footer, hero→hero, card→content, default→general), generate mini-brief per component → Scaffolder → create Component + ComponentVersion
- Store Figma origin reference in ComponentVersion metadata JSON
- `POST /api/v1/design-sync/connections/{id}/extract-components` endpoint
**Security:** BOLA check. Component HTML sanitised via nh3.
**Verify:** Mock Figma components → Hub components created with correct categories and HTML.
- [x] ~~12.6 Component extraction~~ DONE

### 12.7 Frontend: File Browser & Import Dialog
**What:** Tree view of Figma file structure + multi-step import wizard in the UI.
**Files:** New `design-file-browser.tsx`, `design-import-dialog.tsx`, `design-components-panel.tsx`. Modify `design-connection-card.tsx`, design-sync page, hooks, types, i18n.
**Implementation:**
- File browser: pages → frames → components tree, thumbnails, checkbox selection, node type icons
- Import dialog wizard: Select Frames → Review Brief (editable textarea) → Converting (progress) → Result (preview + "Open in Workspace")
- Component extraction panel: thumbnail previews, batch checkbox selection, progress, results link to Hub components
- Connection card: "Import Design" and "Extract Components" buttons
- Hooks: useDesignFileStructure, useDesignComponents, useExportImages, useCreateDesignImport, useDesignImport (polling), useUpdateImportBrief, useExtractComponents
- Types: DesignNode, DesignFileStructure, DesignComponent, ExportedImage, DesignImport, DesignImportAsset
- i18n keys for all new UI text
**Security:** authFetch for all API calls. No dangerouslySetInnerHTML.
**Verify:** File browser renders mock tree. Import wizard completes all steps. Component extraction shows progress.
- [ ] 12.7 Frontend file browser & import dialog

### 12.8 Design Reference in Workspace
**What:** "Design Reference" tab in workspace bottom panel showing the original Figma design alongside the editor.
**Files:** New `design-reference-panel.tsx`. Modify workspace bottom panel registration.
**Implementation:**
- Show exported Figma frame image alongside editor
- Display design tokens (colors, typography, spacing) for quick reference
- Click-to-copy hex values and font specs
- Link back to Figma file
**Security:** Images served via authenticated asset endpoint.
**Verify:** Panel shows design image + tokens. Copy-to-clipboard works.
- [ ] 12.8 Design reference in workspace

### 12.9 SDK Regeneration & Tests
**What:** Regenerate SDK for all new endpoints. Backend tests for all new modules.
**Files:** `app/design_sync/tests/` (extend + new files)
**Implementation:**
- Layout analyzer unit tests (mock Figma JSON → expected sections)
- Brief generator unit tests (structured layout → expected brief text)
- Asset service tests (download, store, serve)
- Import orchestrator tests (mock Figma API + mock scaffolder)
- Component extractor tests
- New endpoint route tests
- `make sdk` to cover all new endpoints
- Update frontend type imports
**Verify:** `make test` — all design_sync tests pass. `make types` — clean. `make lint` — clean. `make check-fe` — clean.
- [ ] 12.9 SDK regeneration & tests

---

## Phase 13 — ESP Bidirectional Sync & Mock Servers

**What:** Transform the Hub's 4 ESP connectors (Braze, SFMC, Adobe Campaign, Taxi) from export-only mock stubs into fully bidirectional sync with real API surface. Adds local mock ESP servers with pre-loaded realistic email templates, encrypted credential management, and pull/push template workflows.
**Why:** Currently connectors only export via fake IDs — no template browsing, no round-trip editing, no credential validation. This phase makes the connector pipeline usable end-to-end for demos and development.
**Dependencies:** Phase 0-3 foundation (auth, projects, templates, connectors export). Reuses Fernet encryption from `app/design_sync/crypto.py`, connection model pattern from `app/design_sync/models.py`, BOLA pattern from `app/projects/service.py`.

### 13.1 Mock ESP Server — Core Infrastructure
**What:** Create `services/mock-esp/` — a standalone FastAPI app (port 3002) with SQLite persistence, auto-seeding on startup, and per-ESP auth patterns (Bearer for Braze/Taxi, OAuth token exchange for SFMC/Adobe).
**Why:** Real ESP APIs require paid accounts and complex setup. A local mock server lets developers test the full sync workflow offline with realistic data.
**Implementation:**
- `services/mock-esp/main.py` — FastAPI app with lifespan (init DB + seed)
- `services/mock-esp/database.py` — aiosqlite manager, DDL for 4 ESP tables
- `services/mock-esp/auth.py` — per-ESP auth dependencies (Bearer validation, OAuth token issuance)
- `services/mock-esp/seed.py` — loads JSON seed data into SQLite on startup
- `services/mock-esp/Dockerfile` — python:3.12-slim, port 3002
- `services/mock-esp/requirements.txt` — fastapi, uvicorn, pydantic, aiosqlite
- `GET /health` endpoint for Docker healthcheck
**Security:** Mock server is dev-only. Auth accepts any non-empty token (Braze/Taxi) or issues mock OAuth tokens (SFMC/Adobe). No real credentials stored.
**Verify:** `uvicorn main:app --port 3002` starts clean. `GET /health` returns `{"status": "healthy"}`.

### 13.2 Mock ESP — Braze Content Blocks API
**What:** Braze API routes at `/braze/content_blocks/` — create, list, info, update, delete. Auth via Bearer token.
**Implementation:**
- `services/mock-esp/braze/routes.py` — 5 endpoints matching Braze REST API surface
- `services/mock-esp/braze/schemas.py` — ContentBlockCreate, ContentBlockResponse, etc.
**Verify:** `curl -H "Authorization: Bearer test" http://localhost:3002/braze/content_blocks/list` returns seeded templates.

### 13.3 Mock ESP — SFMC Content Builder API
**What:** SFMC API routes — OAuth token exchange at `/sfmc/v2/token`, CRUD at `/sfmc/asset/v1/content/assets`. Auth via client_credentials flow.
**Implementation:**
- `services/mock-esp/sfmc/routes.py` — token endpoint + 5 CRUD endpoints
- `services/mock-esp/sfmc/schemas.py` — TokenRequest, AssetResponse, etc.
**Verify:** Token exchange returns access_token. CRUD with Bearer works.

### 13.4 Mock ESP — Adobe Campaign Delivery API
**What:** Adobe API routes — IMS token at `/adobe/ims/token/v3`, CRUD at `/adobe/profileAndServicesExt/delivery`. Auth via IMS OAuth.
**Implementation:**
- `services/mock-esp/adobe/routes.py` — IMS token + 5 CRUD endpoints
- `services/mock-esp/adobe/schemas.py` — IMSTokenRequest, DeliveryResponse, etc.
**Verify:** IMS token exchange works. Delivery CRUD with Bearer works.

### 13.5 Mock ESP — Taxi for Email API
**What:** Taxi API routes at `/taxi/api/v1/templates` — standard REST CRUD. Auth via `X-API-Key` header.
**Implementation:**
- `services/mock-esp/taxi/routes.py` — 5 REST endpoints
- `services/mock-esp/taxi/schemas.py` — TemplateCreate, TemplateResponse, etc.
**Verify:** `curl -H "X-API-Key: test" http://localhost:3002/taxi/api/v1/templates` returns seeded templates.

### 13.6 Mock ESP — Seed Data (44 Templates)
**What:** Pre-loaded realistic email templates with ESP-specific personalization tags — 12 Braze (Liquid), 12 SFMC (AMPscript), 10 Adobe (expressions), 10 Taxi (Taxi Syntax). Full HTML with DOCTYPE, dark mode, MSO conditionals, fluid hybrid 600px layout.
**Implementation:**
- `services/mock-esp/seed/braze.json` — 12 templates with `{{first_name}}`, `{% if %}`, `{{content_blocks.${}}}` etc.
- `services/mock-esp/seed/sfmc.json` — 12 templates with `%%=v(@firstName)=%%`, `%%[SET ...]%%` etc.
- `services/mock-esp/seed/adobe.json` — 10 templates with `<%= recipient.firstName %>` etc.
- `services/mock-esp/seed/taxi.json` — 10 templates with `<!-- taxi:editable -->` regions
**Verify:** After startup, each ESP table has its full seed data. Templates render correctly in a browser.

### 13.7 Backend — ESP Sync Protocol, Model & Migration
**What:** New `ESPSyncProvider` Protocol, `ESPConnection` model, Pydantic schemas, repository, and Alembic migration for the `esp_connections` table. Reuses Fernet encryption from design_sync and BOLA pattern from projects.
**Implementation:**
- `app/connectors/sync_protocol.py` — `ESPSyncProvider` Protocol (runtime_checkable) with 6 methods: validate_credentials, list/get/create/update/delete templates
- `app/connectors/sync_schemas.py` — `ESPTemplate`, `ESPTemplateList`, `ESPConnectionCreate`, `ESPConnectionResponse`, `ESPImportRequest`, `ESPPushRequest`
- `app/connectors/sync_models.py` — `ESPConnection(Base, TimestampMixin)` with encrypted_credentials, project FK, status tracking
- `app/connectors/sync_repository.py` — `ESPSyncRepository` with BOLA-safe list (user-owned + accessible projects)
- `app/connectors/sync_config.py` — `ESPSyncConfig` with per-ESP base URLs (default to mock-esp:3002)
- `app/connectors/exceptions.py` — add `ESPConnectionNotFoundError`, `ESPSyncFailedError`, `InvalidESPCredentialsError`
- `app/core/config.py` — add `esp_sync: ESPSyncConfig` to Settings
- `alembic/versions/d8e9f0a1b2c3_add_esp_connections.py` — migration
- `alembic/env.py` — import sync_models
**Security:** Credentials encrypted at rest via Fernet (same PBKDF2 key as design_sync). Only `credentials_hint` (last 4 chars) exposed in responses. BOLA via `verify_project_access()`.
**Verify:** `make db-migrate` applies cleanly. `ESPConnection` CRUD works in tests. Protocol type-checks with mypy.

### 13.8 Backend — Per-ESP Sync Providers
**What:** Four sync provider implementations — one per ESP — each using `httpx.AsyncClient` to call the mock (or real) ESP API. Implements `ESPSyncProvider` Protocol.
**Implementation:**
- `app/connectors/braze/sync_provider.py` — `BrazeSyncProvider` (Bearer auth, Content Blocks API)
- `app/connectors/sfmc/sync_provider.py` — `SFMCSyncProvider` (OAuth token exchange + Asset API)
- `app/connectors/adobe/sync_provider.py` — `AdobeSyncProvider` (IMS OAuth + Delivery API)
- `app/connectors/taxi/sync_provider.py` — `TaxiSyncProvider` (X-API-Key + Templates API)
- Provider registry dict in sync service (Step 13.9)
**Security:** Credentials decrypted in-memory only for API calls, never logged. httpx timeout enforced (10-30s).
**Verify:** Each provider conforms to `ESPSyncProvider` Protocol (isinstance check). Integration test with mock-esp server.

### 13.9 Backend — Sync Service & Routes
**What:** `ConnectorSyncService` orchestrating connections and template operations, plus REST API routes at `/api/v1/connectors/sync/`.
**Implementation:**
- `app/connectors/sync_service.py` — `ConnectorSyncService(db)` with:
  - `create_connection()` — validate via provider, encrypt creds, save
  - `list_connections()` — BOLA-scoped via accessible project IDs
  - `delete_connection()` — BOLA check
  - `list_remote_templates()` / `get_remote_template()` — decrypt creds, call provider
  - `import_template()` — pull from ESP, create local template via `TemplateService`
  - `push_template()` — read local template, push to ESP via provider
- `app/connectors/sync_routes.py` — Router at `/api/v1/connectors/sync` with 8 endpoints:
  - `POST /connections` (developer, 10/min) — create connection
  - `GET /connections` (viewer, 30/min) — list connections
  - `GET /connections/{id}` (viewer, 30/min) — get connection
  - `DELETE /connections/{id}` (developer, 10/min) — delete connection
  - `GET /connections/{id}/templates` (developer, 20/min) — list remote templates
  - `GET /connections/{id}/templates/{template_id}` (developer, 20/min) — get remote template
  - `POST /connections/{id}/import` (developer, 10/min) — import remote → local
  - `POST /connections/{id}/push` (developer, 10/min) — push local → remote
- `app/main.py` — register sync_routes router
**Security:** All endpoints authenticated + role-checked. BOLA on every operation. Rate limited. Credentials never in responses.
**Verify:** Full connection lifecycle: create → list → browse remote → import → push. BOLA denies cross-project access.

### 13.10 Frontend — ESP Sync UI
**What:** Frontend components for managing ESP connections, browsing remote templates, and import/push workflows. Adds tabs to the existing connectors page.
**Implementation:**
- `cms/apps/web/src/hooks/use-esp-connections.ts` — SWR hooks for connection CRUD
- `cms/apps/web/src/hooks/use-esp-templates.ts` — SWR hooks for remote template list/get
- `cms/apps/web/src/components/connectors/esp-connection-card.tsx` — status, provider icon, last synced
- `cms/apps/web/src/components/connectors/create-esp-connection-dialog.tsx` — provider-specific credential fields
- `cms/apps/web/src/components/connectors/esp-template-browser.tsx` — template list with search, import button
- `cms/apps/web/src/components/connectors/esp-template-preview-dialog.tsx` — HTML preview + import/push
- Modify `connectors/page.tsx` — add 3 tabs: Export History | ESP Connections | Remote Templates
- `cms/apps/web/messages/en.json` — i18n keys for espSync namespace
**Security:** All API calls via `authFetch`. No credentials displayed beyond hint. Token stored server-side only.
**Verify:** Create connection → browse remote templates → import one → verify in local templates. Push local template back → verify in mock ESP.

### 13.11 Tests, SDK & Docker Integration
**What:** Backend tests, SDK regeneration, Docker compose integration, and Makefile target.
**Implementation:**
- `app/connectors/tests/test_sync_service.py` — connection CRUD, encryption, template ops, BOLA, errors
- `app/connectors/tests/test_sync_protocol.py` — Protocol conformance for all 4 providers
- `app/connectors/tests/test_sync_routes.py` — route-level tests with auth/rate-limit
- `docker-compose.yml` — add `mock-esp` service (port 3002, healthcheck, resource limits)
- `Makefile` — add `dev-mock-esp` target
- SDK regeneration (`make sdk`) to include new sync endpoints
**Verify:** `make check` passes (lint + types + tests + security). `docker compose up` starts mock-esp healthy. SDK includes sync types.

---

## Phase 14 — Blueprint Checkpoint & Recovery

**What:** Add per-node checkpoint persistence to the blueprint engine so that failed or interrupted runs can resume from the last successful node instead of restarting from scratch. Inspired by LangGraph's checkpoint-based execution model (Deep Agents SDK).
**Why:** Currently `BlueprintEngine.run()` holds all state in an in-memory `BlueprintRun` dataclass. If the Maizzle sidecar times out, a container restarts mid-pipeline, or the 11.22.3 multi-pass pipeline fails at Pass 2, the entire run restarts from the entry node — wasting tokens, time, and API budget. With checkpointing, a 5-node blueprint that fails at node 4 resumes from node 4 (saving ~80% of the rerun cost). This also enables long-running blueprints to survive process restarts and provides a full audit trail of per-node state for debugging.
**Dependencies:** Phase 11.22 (blueprint engine, multi-pass pipeline, repair pipeline). Phase 0.3 (PostgreSQL, Redis).
**Design principle:** Checkpoints are opt-in (disabled by default for backward compatibility). The engine serialises `BlueprintRun` state after each successful node completion. Resume loads the latest checkpoint and continues from the next node in the graph. Checkpoint storage uses PostgreSQL (durable) with Redis as optional write-ahead cache for latency.

### 14.1 Checkpoint Storage Layer
**What:** Create `app/ai/blueprints/checkpoint.py` — `CheckpointStore` protocol + PostgreSQL implementation. Each checkpoint captures the full `BlueprintRun` state (HTML, progress, iteration counts, handoff history, QA results, model usage) after a node completes successfully.
**Why:** The storage layer must be durable (survive process restarts), fast (< 50ms write), and queryable (list runs, find latest checkpoint for a run). PostgreSQL provides durability; optional Redis write-ahead provides speed.
**Implementation:**
- Create `app/ai/blueprints/checkpoint.py`:
  - `CheckpointData` frozen dataclass: `run_id: str`, `blueprint_name: str`, `node_name: str`, `node_index: int`, `status: str`, `html: str`, `progress: list[dict]`, `iteration_counts: dict[str, int]`, `qa_failures: list[str]`, `qa_failure_details: list[dict]`, `qa_passed: bool | None`, `model_usage: dict[str, int]`, `skipped_nodes: list[str]`, `routing_decisions: list[dict]`, `handoff_history: list[dict]`, `created_at: datetime`
  - `CheckpointStore` Protocol (runtime_checkable): `save(data: CheckpointData) -> None`, `load_latest(run_id: str) -> CheckpointData | None`, `list_checkpoints(run_id: str) -> list[CheckpointData]`, `delete_run(run_id: str) -> int`
  - `PostgresCheckpointStore(db: AsyncSession)` — implements protocol using `blueprint_checkpoints` table
  - `serialize_run(run: BlueprintRun, node_name: str, node_index: int, blueprint_name: str) -> CheckpointData` — snapshot current run state
  - `restore_run(data: CheckpointData) -> BlueprintRun` — reconstruct run state from checkpoint
- Create `app/ai/blueprints/checkpoint_models.py`:
  - `BlueprintCheckpoint(Base, TimestampMixin)` SQLAlchemy model: `id` (PK), `run_id` (indexed), `blueprint_name`, `node_name`, `node_index`, `state_json` (JSONB — serialised `CheckpointData`), `html_hash` (SHA-256 of HTML for deduplication), `created_at`
  - Composite index on `(run_id, node_index)` for fast latest-checkpoint lookup
  - `run_id` index for listing checkpoints per run
- Alembic migration for `blueprint_checkpoints` table
**Security:** `state_json` contains generated HTML and brief text (already in memory during execution). No credentials stored. JSONB column validated by Pydantic before write. RLS scoped by project (via join through future `project_id` column if needed).
**Verify:** Unit tests: `serialize_run` → `restore_run` round-trips correctly. `save` + `load_latest` returns most recent checkpoint. `list_checkpoints` returns ordered history. `delete_run` removes all checkpoints for a run. `make test` passes. `make types` clean.
- [ ] 14.1 Checkpoint storage layer

### 14.2 Engine Integration — Save Checkpoints After Each Node
**What:** Update `BlueprintEngine.run()` to optionally save a checkpoint after each successful node completion. The checkpoint captures the full `BlueprintRun` state at that point, enabling resume from any node boundary.
**Why:** This is the core integration — the engine must checkpoint without impacting the hot path performance. Checkpoint writes are fire-and-forget (logged warning on failure, never crash the run).
**Implementation:**
- Update `BlueprintEngine.__init__()` — add `checkpoint_store: CheckpointStore | None = None` parameter
- In `BlueprintEngine.run()`, after updating run state and before resolving the next node:
  ```python
  # Checkpoint after successful node completion (fire-and-forget)
  if self._checkpoint_store is not None and result.status in ("success", "skipped"):
      try:
          data = serialize_run(run, current_node_name, steps, self._definition.name)
          await self._checkpoint_store.save(data)
      except Exception:
          logger.warning(
              "blueprint.checkpoint_save_failed",
              node=current_node_name,
              run_id=run.run_id,
              exc_info=True,
          )
  ```
- Do NOT checkpoint on failed nodes (the retry loop handles those)
- Do NOT checkpoint on `qa_gate` failures (they trigger recovery routing, not resume)
- Checkpoint on `qa_gate` success (marks a clean resumption point)
- Update `BlueprintService.run()` — instantiate `PostgresCheckpointStore(db)` if `settings.blueprint.checkpoints_enabled` is True, pass to engine
- Add `checkpoints_enabled: bool = False` to `BlueprintConfig` in `app/core/config.py`
**Security:** No new endpoints. Checkpoint writes use existing DB session. No user input in checkpoint data.
**Verify:** Enable checkpoints, run a blueprint end-to-end. Verify: checkpoint row created for each successful node. Disable checkpoints — no rows created (backward compatible). Checkpoint write failure doesn't crash the run. `make test` passes.
- [ ] 14.2 Engine integration — save checkpoints

### 14.3 Engine Integration — Resume From Checkpoint
**What:** Add `BlueprintEngine.resume(run_id: str)` method that loads the latest checkpoint and continues execution from the next node in the graph.
**Why:** This is the payoff — a failed run can be retried without re-running completed nodes, saving tokens, API cost, and latency.
**Implementation:**
- Add `BlueprintEngine.resume(run_id: str, brief: str) -> BlueprintRun`:
  - Load latest checkpoint via `self._checkpoint_store.load_latest(run_id)`
  - If no checkpoint found, raise `BlueprintError("No checkpoint found for run {run_id}")`
  - Call `restore_run(data)` to reconstruct `BlueprintRun` state
  - Determine next node: use `_resolve_next_node()` with a synthetic success `NodeResult` from the checkpointed node, OR store `next_node_name` in `CheckpointData` (simpler)
  - Update `CheckpointData` to include `next_node_name: str | None` — the node that should execute next
  - Continue the `while` loop from `next_node_name` with restored state
  - Log `blueprint.run_resumed` with run_id, checkpoint node, next node
- Handle edge cases:
  - If `next_node_name` is None (checkpoint was at terminal node), return the restored run as-is (status = completed)
  - If the blueprint definition has changed since the checkpoint (node removed/renamed), raise `BlueprintError` with details
  - Validate blueprint name matches between checkpoint and current definition
- Add resume endpoint to routes:
  - `POST /api/v1/blueprints/resume` — `BlueprintResumeRequest(run_id: str, brief: str)` → `BlueprintRunResponse`
  - Auth: `admin`, `developer` roles. Rate limit: `3/minute` (same as run)
- Add `BlueprintResumeRequest` schema to `schemas.py`
- Update `BlueprintService` with `resume()` method
**Security:** Resume loads only checkpoints from `blueprint_checkpoints` table (no user-controlled paths). `run_id` is a server-generated UUID hex — not guessable. Future: add `user_id` to checkpoint for BOLA (ensure user can only resume their own runs).
**Verify:** Run a blueprint with checkpoints enabled. Kill the process mid-run (or mock a node failure). Call resume with the `run_id`. Verify: run continues from the last successful node, not from the start. Final output matches a full run. Progress log shows resumed nodes. `make test` passes.
- [ ] 14.3 Engine integration — resume from checkpoint

### 14.4 Multi-Pass Pipeline Checkpoints
**What:** Extend checkpoint support into the 11.22.3 scaffolder `MultiPassPipeline` (3-pass: layout → content → design). Each pass is a natural checkpoint boundary — if Pass 2 (content generation) fails, resume from Pass 2 with the Pass 1 result (template selection) intact.
**Why:** The multi-pass pipeline is the most token-expensive component (~5,000 tokens total). Without per-pass checkpointing, a failure in Pass 3 (design tokens, ~500 tokens) wastes the Pass 1 + Pass 2 results (~3,500 tokens). With checkpointing, only the failed pass is re-run.
**Implementation:**
- Create `PipelineCheckpoint` dataclass in `app/ai/agents/scaffolder/pipeline.py`:
  - `run_id: str`, `pass_number: int`, `pass_name: str`, `result: dict` (serialised pass output), `accumulated_plan: dict` (partial `EmailBuildPlan` so far)
- Add `checkpoint_store: CheckpointStore | None` parameter to pipeline's execution method
- After each successful pass, save a `PipelineCheckpoint`
- On resume: load latest pipeline checkpoint for the run, skip completed passes, continue from the next pass with accumulated context
- The blueprint-level checkpoint (14.2) stores which node was executing; the pipeline-level checkpoint stores which pass within that node was executing — two levels of granularity
**Security:** Pipeline checkpoints contain pass-specific JSON (template selection, slot fills, design tokens). No credentials. Same JSONB storage as blueprint checkpoints.
**Verify:** Run scaffolder with 3-pass pipeline. Mock Pass 2 failure. Resume → Pass 1 skipped (cached), Pass 2 re-runs, Pass 3 runs. Token usage shows savings (~60% reduction vs full rerun). `make test` passes.
- [ ] 14.4 Multi-pass pipeline checkpoints

### 14.5 Checkpoint Cleanup & Observability
**What:** Automatic cleanup of old checkpoints + observability integration for checkpoint-related events.
**Why:** Without cleanup, the `blueprint_checkpoints` table grows unbounded. Without observability, operators can't monitor checkpoint health or debug resume failures.
**Implementation:**
- Create `app/ai/blueprints/checkpoint_cleanup.py`:
  - `cleanup_old_checkpoints(db, max_age_days: int = 7) -> int` — delete checkpoints older than `max_age_days`, return count deleted
  - `cleanup_completed_runs(db) -> int` — delete all checkpoints for runs with status `completed` (no resume needed)
  - Wire into existing `DataPoller` pattern (same as `MemoryCompactionPoller`) — run daily
- Add `BLUEPRINT__CHECKPOINT_RETENTION_DAYS` config (default 7)
- Add structured logging events:
  - `blueprint.checkpoint_saved` — node, run_id, size_bytes, duration_ms
  - `blueprint.checkpoint_loaded` — run_id, node, age_seconds
  - `blueprint.checkpoint_cleanup` — deleted_count, retained_count
- Add `GET /api/v1/blueprints/runs/{run_id}/checkpoints` endpoint:
  - Returns list of checkpoints with node names, timestamps, sizes
  - Auth: `admin`, `developer` roles
  - Useful for debugging failed runs
- Update `BlueprintRunResponse` — add `checkpoint_count: int = 0` field (how many checkpoints exist for this run)
- Update `BlueprintRunResponse` — add `resumed_from: str | None = None` field (node name if this was a resumed run)
**Security:** Cleanup runs on the server, not user-triggered (except via explicit API call). Checkpoint listing is read-only. No new write paths.
**Verify:** Create 10 blueprint runs with checkpoints. Run cleanup with `max_age_days=0`. Verify all deleted. Run cleanup with `max_age_days=30`. Verify none deleted. Completed run cleanup removes only completed runs. `make test` passes. `make types` clean.
- [ ] 14.5 Checkpoint cleanup & observability

### 14.6 Frontend — Run History & Resume UI
**What:** Frontend components for viewing blueprint run history, inspecting checkpoints, and resuming failed runs.
**Why:** Without UI, resume is API-only. Developers need to see which runs failed, where they failed, and trigger a resume with one click.
**Implementation:**
- Update `cms/apps/web/src/components/workspace/blueprint/runs-list.tsx`:
  - Add "Resume" button on failed/interrupted runs (visible only when checkpoints exist)
  - Show `resumed_from` badge on resumed runs
- Create `cms/apps/web/src/components/workspace/blueprint/run-checkpoints.tsx`:
  - Expandable checkpoint timeline within run detail view
  - Shows node name, timestamp, status for each checkpoint
  - Highlights the resume point
- Add `useResumeBlueprint` hook in `cms/apps/web/src/hooks/`:
  - Calls `POST /api/v1/blueprints/resume` with run_id
  - Handles loading state, error display
- Update `cms/apps/web/src/types/blueprint-runs.ts` — add `checkpoint_count`, `resumed_from` fields
- i18n keys for resume UI text
**Security:** Resume action requires `developer` role (same as run). UI shows no checkpoint content (only metadata).
**Verify:** Run a blueprint that fails. See "Resume" button in UI. Click resume → run continues from checkpoint. Checkpoint timeline shows progression. Completed runs don't show resume button.
- [ ] 14.6 Frontend — run history & resume UI

### 14.7 Tests & Documentation
**What:** Comprehensive tests for the checkpoint system + architecture documentation.
**Implementation:**
- `app/ai/blueprints/tests/test_checkpoint.py`:
  - `TestCheckpointStore` — CRUD operations, round-trip serialisation, edge cases (empty run, max checkpoints)
  - `TestEngineCheckpoints` — engine saves checkpoints at correct points, skips on failure, fire-and-forget on error
  - `TestEngineResume` — resume from checkpoint, validate state restoration, handle missing checkpoint, handle stale blueprint
  - `TestPipelineCheckpoints` — multi-pass pipeline per-pass checkpointing and resume
  - `TestCheckpointCleanup` — age-based cleanup, completed-run cleanup, retention config
- `app/ai/blueprints/tests/test_resume_route.py`:
  - Route-level tests: auth, rate limiting, valid resume, invalid run_id, no checkpoints
- Update `docs/ARCHITECTURE.md` — add Checkpoint & Recovery section explaining the two-level checkpoint model (blueprint node + pipeline pass)
- SDK regeneration (`make sdk`) for new endpoints
**Verify:** `make test -k test_checkpoint` — all tests pass. `make test -k test_resume` — route tests pass. `make check` — full suite green. `make types` clean.
- [ ] 14.7 Tests & documentation

---

## Phase 15 — Agent Communication & Efficiency Refinements

**What:** Five incremental improvements to existing agent orchestration, memory, routing, evaluation, and knowledge graph systems. No architectural changes — these refine what's already built to improve token efficiency, context quality, cost, agent quality, and reduce redundant work.
**Dependencies:** Phase 11 (QA engine + agent deterministic architecture), Phase 14 (blueprint checkpoints), Phase 8-9 (knowledge graph).
**Design principle:** Each task is independently shippable. No task blocks another. All changes are backward-compatible with existing APIs and schemas.

### 15.1 Typed Handoff Schemas Between Blueprint Agents
**What:** Replace raw HTML/text handoffs between DAG nodes with structured, typed contracts. When agent A passes output to agent B, the handoff includes metadata: components used, client constraints, confidence scores, and uncertainty flags.
**Why:** Currently downstream agents re-infer context from raw output. The Scaffolder generates HTML but the Dark Mode agent doesn't know which components were used, what the Scaffolder was uncertain about, or what client constraints apply. This causes redundant LLM inference and occasional hallucinated assumptions.
**Implementation:**
- Create `app/ai/blueprints/handoff.py` — `AgentHandoff` Pydantic model with fields: `output: str`, `components_used: list[str]`, `constraints: dict[str, Any]`, `confidence: float`, `uncertainties: list[str]`, `metadata: dict[str, Any]`
- Update `app/ai/blueprints/nodes/agent_node.py` — agent nodes produce `AgentHandoff` instead of raw string output
- Update `app/ai/blueprints/engine.py` — engine passes `AgentHandoff` to downstream nodes, each agent's system prompt includes relevant handoff context
- Each agent's SKILL.md updated to instruct structured JSON output that maps to `AgentHandoff` fields
- Backward-compatible: if an agent returns raw string, engine wraps it in `AgentHandoff(output=raw, confidence=1.0)` with empty metadata
**Security:** Handoff schemas are internal data structures. No user input reaches handoff construction directly.
**Verify:** Run a multi-agent blueprint (Scaffolder → Dark Mode → QA). Verify Dark Mode agent receives component list and constraints from Scaffolder. Compare token usage before/after. `make test` passes. `make eval-run` shows no regression.
- [ ] 15.1 Typed handoff schemas between blueprint agents

### 15.2 Phase-Aware Memory Decay Rates
**What:** Replace the fixed 30-day half-life with project-phase-aware decay. Active projects retain memories longer; shipped/dormant projects decay faster. Add intent-aware compaction that merges functionally redundant memories even when textually different.
**Why:** A fixed decay rate is a compromise. During active client development, 30 days is too aggressive — useful context fades before the project ships. After a project goes to maintenance, 30 days is too slow — stale assumptions linger. Additionally, compaction by text similarity misses semantic duplicates (e.g., "client X prefers blue CTAs" and "brand guide says primary action color is #0066CC" are functionally identical).
**Implementation:**
- Add `phase: Literal["active", "maintenance", "archived"]` field to `Project` model (default: `"active"`)
- Update `app/memory/service.py` — `MemoryService.get_decay_rate()` returns half-life based on project phase: active=60 days, maintenance=14 days, archived=3 days
- Update `app/memory/compaction.py` — add intent-aware merging step: before similarity check, run lightweight embedding comparison (cosine > 0.85) + LLM judge call (lightweight tier) to confirm functional equivalence before merging
- Add `MEMORY__DECAY_ACTIVE_DAYS`, `MEMORY__DECAY_MAINTENANCE_DAYS`, `MEMORY__DECAY_ARCHIVED_DAYS` config options
- Migration: add `phase` column to `projects` table, default `"active"`
**Security:** Phase field is enum-validated. LLM judge call for compaction uses sanitized memory content (no PII). No user-facing API changes.
**Verify:** Create project in each phase. Store memories. Run decay cycle. Verify active memories persist longer, archived memories decay faster. Run compaction on two semantically equivalent but textually different memories — verify they merge. `make test` passes.
- [ ] 15.2 Phase-aware memory decay rates

### 15.3 Adaptive Model Tier Routing
**What:** Track per-agent, per-client success rates and auto-downgrade model tier when confidence is high. If the Content agent consistently produces accepted output on lightweight models for client X, don't use standard tier just because the blueprint default says "standard."
**Why:** The current tier mapping is static: task complexity → model. But complexity varies by client and agent. Simple brand voices need lightweight models; complex personalisation needs standard+. Static routing wastes budget on easy tasks and under-serves hard ones. This directly reduces the £60-150/month API spend.
**Implementation:**
- Create `app/ai/routing_history.py` — `RoutingHistory` model: `agent_id`, `client_org_id`, `tier_used`, `accepted: bool`, `created_at`
- Update `app/ai/routing.py` — before selecting tier, query last 20 runs for this agent+client. If acceptance rate > 90% on a lower tier, downgrade. If acceptance rate < 70% on current tier, upgrade. Minimum 10 runs before adaptive routing kicks in.
- Add `AI__ADAPTIVE_ROUTING_ENABLED=true` config flag (default off, opt-in)
- Dashboard metric: show current effective tier per agent per client in admin panel
- Fallback: if adaptive routing produces a rejection, auto-retry on one tier higher (single retry, not loop)
**Security:** Routing history is internal analytics data. No PII. Rate decisions are server-side only; clients cannot influence tier selection.
**Verify:** Seed 20 successful lightweight runs for Content agent + client X. Next run should auto-select lightweight instead of default standard. Seed 15 runs with 50% failure rate — should auto-upgrade. `AI__ADAPTIVE_ROUTING_ENABLED=false` bypasses all adaptive logic. `make test` passes.
- [ ] 15.3 Adaptive model tier routing

### 15.4 Auto-Surfacing Prompt Amendments from Eval Failures
**What:** Close the eval feedback loop. When `make eval-judge` identifies recurring failure patterns, automatically generate suggested SKILL.md amendments and surface them for developer review — not auto-applied, but ready to merge.
**Why:** The eval pipeline currently produces reports, but translating failure taxonomy into prompt improvements is a manual process. Recurring patterns (e.g., "Outlook Fixer misses VML backgrounds in 2-column layouts") sit in reports until someone reads them and manually edits SKILL.md. This delays quality improvements.
**Implementation:**
- Create `app/ai/evals/amendment_suggester.py` — after `make eval-judge`, group failures by agent + failure category. For clusters with 3+ occurrences, generate a suggested SKILL.md patch using the complex-tier LLM with the failure examples as context
- Output: `evals/suggestions/{agent_name}_{date}.md` — each file contains: failure pattern description, example traces, suggested SKILL.md diff, confidence score
- Add `make eval-suggest` command that runs the suggester after `make eval-judge`
- Update `make eval-full` pipeline to include suggestion step
- Suggestions are review-only: developer approves/rejects via PR or manual edit. No auto-application.
**Security:** Suggestions are generated from eval traces (already sanitized). Output is local markdown files, not applied to production prompts.
**Verify:** Run `make eval-full` on a dataset with known recurring failures. Verify suggestion files are generated with actionable SKILL.md diffs. Apply a suggestion manually, re-run eval — verify the failure cluster shrinks. `make test` passes.
- [ ] 15.4 Auto-surfacing prompt amendments from eval failures

### 15.5 Bidirectional Knowledge Graph — Agent Pre-Query
**What:** Before generating from scratch, agents query the Cognee knowledge graph for similar past outcomes. If a similar template was built for this client before, the agent starts from that baseline instead of zero.
**Why:** The outcome poller already feeds agent results into the knowledge graph, but it's write-only. Agents never read from it before starting work. This means the Scaffolder rebuilds similar templates from scratch every time, even when a proven baseline exists. Bidirectional flow turns the knowledge graph from an archive into an active asset.
**Implementation:**
- Create `app/ai/agents/knowledge_prefetch.py` — `KnowledgePrefetch` service: takes agent type + task description + client_org_id, queries Cognee for top-3 similar past outcomes (by embedding similarity + client match)
- Update `app/ai/agents/base.py` — `BaseAgent.execute()` calls `KnowledgePrefetch` before LLM invocation. If relevant prior work found, inject into system prompt as "Reference: a similar task was completed previously with this approach: {summary}"
- Add `COGNEE__PREFETCH_ENABLED=true` config flag (default off when Cognee disabled)
- Prefetch is advisory only: agents can ignore prior work if the task differs meaningfully
- Cache prefetch results in Redis (5-min TTL) to avoid repeated graph queries within a blueprint run
**Security:** Prefetch results are filtered by `client_org_id` — agents only see outcomes from the same organization. No cross-tenant data leakage. Redis cache key includes org_id.
**Verify:** Run Scaffolder for client X with a brief similar to a past completed task. Verify prefetch returns the prior outcome. Verify the generated template shows influence from the baseline (not identical, but structurally similar). Run for client Y — verify no cross-tenant results. `COGNEE__PREFETCH_ENABLED=false` skips prefetch entirely. `make test` passes.
- [ ] 15.5 Bidirectional knowledge graph — agent pre-query

---

## Phase 16 — Domain-Specific RAG Architecture

**What:** Transform the knowledge RAG pipeline from generic document retrieval into a multi-path, domain-aware retrieval system with post-generation validation. Add a query router that classifies intent and routes to the optimal retrieval path (structured ontology lookup, component search, or existing hybrid search), code-aware HTML chunking, multi-representation indexing, and a CRAG validation loop that catches incompatible CSS before it ships.
**Why:** The current RAG embeds everything as text chunks and runs cosine similarity — losing the relational precision of the ontology (335+ CSS properties × 25+ clients × support levels) and the structural integrity of HTML code. Email development is a constraint satisfaction problem (does property X work in client Y?), not a document retrieval problem. Developers asking "Does Gmail support flexbox?" get text chunks instead of a definitive structured answer. Code chunks split mid-tag, MSO conditionals get fragmented, and agents generate CSS that looks correct but breaks in major clients.
**Dependencies:** Phase 8-9 (ontology + graph operational), Phase 11 (QA engine + agent deterministic architecture), Phase 4 (components table exists).
**Design principle:** Each sub-phase is independently shippable behind feature flags. New `/search/routed` endpoint sits alongside existing `/search` — no breaking changes. All schema additions are nullable. Specialized retrieval paths fall back to existing `search()` when they return empty results.

### 16.1 Query Router — Intent Classification & Entity Extraction
**What:** Classify incoming knowledge queries by intent (compatibility, how_to, template, debug, general) and route to the optimal retrieval path. Two-tier classification: fast regex patterns (pre-compiled from ontology client/property IDs) with optional LLM fallback for ambiguous queries. Entity extraction resolves fuzzy names to ontology IDs ("Gmail" → `gmail_web`, "flexbox" → `display_flex`).
**Why:** Currently all queries go through the same hybrid search pipeline. A factual question like "Does Gmail support flexbox?" gets the same treatment as "Email best practices?" — cosine similarity over text chunks. The router enables each query type to use its strongest retrieval path without changing the existing pipeline for queries that work well today.
**Implementation:**
- Create `app/knowledge/router.py` — `QueryIntent` enum (compatibility, how_to, template, debug, general), `ClassifiedQuery` dataclass (intent, original_query, extracted_entities, confidence), `QueryRouter` class with regex-first + optional LLM fallback classification
- Entity extraction: build regex patterns from `OntologyRegistry.client_ids()` and `OntologyRegistry.property_ids()`. Reuse `_property_id_from_css()` from `app/knowledge/ontology/query.py` for CSS name → property_id resolution. Resolve fuzzy client names by matching against `EmailClient.name` and `EmailClient.family` fields
- Modify `app/knowledge/service.py` (`KnowledgeService`) — add `async search_routed(request: SearchRequest) -> SearchResponse` that classifies via `QueryRouter`, then routes to `_search_compatibility()`, `_search_components()`, `_search_debug()`, or falls back to existing `search()`. Constructor unchanged (`__init__(self, db, graph_provider)`)
- Modify `app/knowledge/schemas.py` — add `intent: str | None = None` to `SearchResponse` (alongside existing `results`, `query`, `total_candidates`, `reranked` fields)
- Modify `app/knowledge/routes.py` — add `POST /api/v1/knowledge/search/routed` with `@limiter.limit("30/minute")` and auth dependency (matching existing `search_knowledge` endpoint pattern). Existing `/search` endpoint unchanged
- Modify `app/ai/agents/knowledge/service.py` (`KnowledgeAgentService`) — update `process(request, rag_service)` to call `rag_service.search_routed(search_request)` instead of `rag_service.search(search_request)`. Note: `KnowledgeAgentService` is standalone (not a `BaseAgentService` subclass), receives `rag_service: RAGService` as a parameter
- Config (`app/core/config.py` → `KnowledgeConfig`): `router_enabled: bool = False`, `router_llm_fallback: bool = False`, `router_llm_model: str = "gpt-4o-mini"`. When `router_enabled=False`, `search_routed()` delegates directly to `search()` (zero-cost bypass)
**Security:** Router input is the `query` field from `SearchRequest` (Pydantic-validated, max 1000 chars). LLM fallback (when enabled) passes query through `sanitize_prompt()` from `app/ai/sanitize.py`. New endpoint uses same auth + rate limit pattern as existing `/search`. No new credential handling — LLM fallback uses provider registry (`get_registry().get_llm()`).
**Verify:** Test 10+ cases per intent — compatibility queries ("Does Gmail support flexbox?", "flexbox support") classified correctly, how-to queries fall through to existing search, template queries route to component search, debug queries include ontology context. Entity extraction resolves common aliases ("Gmail" → `gmail_web`, "Outlook desktop" → `outlook_2019_win`). Confidence gating works (low-confidence → fallback to general). `search_routed()` with `router_enabled=False` produces identical results to `search()`. `make test` passes.
- [ ] 16.1 Query router — intent classification & entity extraction

### 16.2 Structured Compatibility Queries via Ontology
**What:** For `compatibility` intent, bypass vector search and query `OntologyRegistry` directly for exact, structured answers. Returns property support levels per client, known workarounds, and safe alternatives — formatted as backward-compatible `SearchResult` objects.
**Why:** The ontology already has 335+ CSS properties × 25+ clients with support levels, fallbacks, and workarounds. Embedding this data as text chunks and doing cosine similarity loses relational precision. "Does Gmail support flexbox?" should return a definitive yes/no with fallback, not a text snippet that might mention it. The existing `lookup_support()` in `query.py` already does name+value → support level lookup but isn't wired into the RAG pipeline.
**Dependencies:** 16.1 (router classifies query as `compatibility`)
**Implementation:**
- Create `app/knowledge/ontology/structured_query.py` — `CompatibilityAnswer` frozen dataclass (property: `CSSProperty`, client_results: `tuple[ClientSupportResult, ...]`, fallbacks: `tuple[Fallback, ...]`, summary: `str`), `ClientSupportResult` frozen dataclass (client: `EmailClient`, level: `SupportLevel`, notes: `str`, workaround: `str`), `OntologyQueryEngine` class (stateless, receives `OntologyRegistry` via `load_ontology()`):
  - `query_property_support(property_id, client_ids: list[str] | None) -> CompatibilityAnswer` — uses `registry.get_support_entry()` for each client, collects into structured answer
  - `query_client_limitations(client_id) -> list[CSSProperty]` — delegates to `registry.properties_unsupported_by(client_id)`
  - `find_safe_alternatives(property_id, target_clients) -> list[Fallback]` — delegates to `registry.fallbacks_for(property_id)`, filters by `target_clients ∩ fallback.client_ids`
  - `format_as_search_results(answer) -> list[SearchResult]` — renders structured answer as `SearchResult` objects (backward-compatible with `SearchResponse.results`)
- Modify `app/knowledge/ontology/registry.py` — add two fuzzy lookup methods to `OntologyRegistry`:
  - `find_property_by_name(css_name: str, value: str | None = None) -> CSSProperty | None` — tries exact `_property_id_from_css(css_name, value)` lookup first, falls back to case-insensitive scan of `property_name` field, then prefix match. Reuses ID construction logic from `app/knowledge/ontology/query.py._property_id_from_css()`
  - `find_client_by_name(name: str) -> EmailClient | None` — case-insensitive match against `EmailClient.name`, then `EmailClient.family`, then substring match. Returns highest-market-share match on ambiguity
- Modify `app/knowledge/service.py` — implement `async _search_compatibility(classified: ClassifiedQuery) -> SearchResponse` using `OntologyQueryEngine`. When structured answer found → format as `SearchResult` list with `intent="compatibility"`. When no ontology match (extracted entities don't resolve) → fall back to `search()` with note in first result
**Security:** Ontology queries are read-only lookups against the in-memory `OntologyRegistry` (frozen dataclasses, `__slots__`, `lru_cache`). No SQL, no external API calls, no user input reaches any mutable state. Input entities already validated by router's regex + Pydantic.
**Verify:** "Does Gmail support flexbox?" → structured answer: `display_flex` + `gmail_web` → `SupportLevel.FULL` (Gmail supports flexbox). "Does Outlook support flexbox?" → `SupportLevel.NONE` + table fallback from `fallbacks.yaml`. "What CSS properties don't work in Outlook?" → `properties_unsupported_by("outlook_2019_win")` list. Unknown property ("does Gmail support container queries?") → graceful fallback to vector search. `make test` passes.
- [ ] 16.2 Structured compatibility queries via ontology

### 16.3 Code-Aware HTML Chunking
**What:** Replace generic text splitter with HTML/CSS-aware chunker that respects structural boundaries. `<style>` blocks become standalone chunks, MSO conditional blocks (`<!--[if mso]>`) are preserved whole, and `<body>` is split by major structural elements (first-level `<table>` or `<div>`). Sections exceeding chunk_size are split at nested level (rows → cells). Parse failures fall back to existing `chunk_text()`.
**Why:** The current `chunk_text()` in `app/knowledge/chunking.py` splits on character count (default 512 chars, 50-char overlap) using separator hierarchy (`\n\n`, `\n`, `. `, ` `). This fragments code mid-tag, splits MSO conditionals, and separates CSS properties from their selectors. Retrieval returns broken code that agents must guess how to reassemble.
**Independent:** Can run in parallel with 16.1-16.2.
**Implementation:**
- Create `app/knowledge/chunking_html.py`:
  - `HTMLChunkStrategy` enum (section, component, style_block, mso_conditional, table, text_fallback)
  - `HTMLChunkResult` dataclass — extends pattern of existing `ChunkResult` from `chunking.py` (content, chunk_index, metadata dict) but adds `section_type: str | None` and `summary: str | None`. Must remain convertible to `DocumentChunk` model in `ingest_document()`
  - `chunk_html(html: str, chunk_size: int = 1024, overlap: int = 100) -> list[HTMLChunkResult]` — main entry point:
    1. Detect if content is HTML (check for `<!DOCTYPE`, `<html`, `<table` — reuse pattern from `app/qa_engine/checks/html_validation.py`)
    2. Parse with `lxml.html.document_fromstring()` (already a dependency, used by rule engine in `app/qa_engine/rule_engine.py`)
    3. Extract `<style>` blocks as standalone chunks (metadata: `section_type="style"`)
    4. Extract MSO conditional blocks using regex patterns from `app/qa_engine/mso_parser.py` (`MSOConditionalPattern` constants) as standalone chunks (metadata: `section_type="mso_conditional"`)
    5. Split `<body>` content by first-level structural elements (`<table>`, `<div>`, `<section>`)
    6. If any section exceeds `chunk_size`, recurse into nested elements (table rows → cells)
    7. Wrap in try/except → fall back to `chunk_text()` from `app/knowledge/chunking.py` on any parse error
- Modify `app/knowledge/service.py` → `ingest_document()` — after text extraction via `processing.extract_text()`, detect HTML content type. If HTML and `html_chunking_enabled`: call `chunk_html()` instead of `chunk_text()`. Convert `HTMLChunkResult` objects to `DocumentChunk` model instances (same pattern as existing `ChunkResult` → `DocumentChunk` conversion, but populate new `section_type` and `summary` columns)
- Modify `app/knowledge/models.py` → `DocumentChunk` — add two nullable columns:
  - `section_type: Mapped[str | None] = mapped_column(String(50), nullable=True)` — chunk content type
  - `summary: Mapped[str | None] = mapped_column(Text, nullable=True)` — human-readable summary (used by 16.6)
- Config (`app/core/config.py` → `KnowledgeConfig`): `html_chunk_size: int = 1024`, `html_chunk_overlap: int = 100`, `html_chunking_enabled: bool = True`
- Migration: `add_chunk_section_type_and_summary` — two nullable columns with no defaults (instant `ALTER TABLE` in PostgreSQL, no table rewrite)
**Security:** Parser input is document content already extracted by `processing.extract_text()` and stored in the knowledge base. `lxml.html.document_fromstring()` is lenient by design (handles malformed HTML without raising). No external fetches. Feature flag `html_chunking_enabled` allows instant rollback.
**Verify:** Valid HTML email → chunks respect `<style>` boundaries (never split mid-rule), MSO conditionals preserved whole (opener through closer), structural elements intact. `chunk_html()` on malformed HTML → falls back to `chunk_text()` (no exception). Plain-text markdown document → `chunk_text()` used (unchanged behavior). Re-ingest existing seed HTML doc → verify new chunk boundaries vs old. Migration up/down clean (`alembic upgrade head && alembic downgrade -1`). `make test` passes.
- [ ] 16.3 Code-aware HTML chunking

### 16.4 Template/Component Retrieval
**What:** For `template` intent, search the `Component` table for reusable code artifacts. Extends the existing `ComponentRepository.list(search=..., category=...)` pattern with compatibility-aware filtering via `ComponentQAResult.compatibility` JSON column. Results formatted as backward-compatible `SearchResult` objects alongside top-3 knowledge base results.
**Why:** When an agent asks "Show me a CTA button component," the current pipeline searches text chunks of knowledge documents. But tested, QA'd components already exist in the `components` table with `ComponentVersion.html_source`, `ComponentVersion.css_source`, and per-client compatibility data via `ComponentQAResult`. This connects the retrieval pipeline to the existing component library.
**Dependencies:** 16.1 (router classifies query as `template`)
**Implementation:**
- Create `app/knowledge/component_search.py` — `ComponentSearchService` class (receives `AsyncSession`):
  - `async search_components(query: str, *, category: str | None = None, compatible_with: list[str] | None = None, limit: int = 5) -> list[SearchResult]` — orchestrates text search + optional compatibility filter + result formatting
  - `format_as_search_results(components: list[Component], versions: dict[int, ComponentVersion]) -> list[SearchResult]` — converts component + latest version HTML to `SearchResult` objects (backward-compatible with `SearchResponse.results`)
  - Optional embedding search: if `Component.search_embedding` is populated, combine text ILIKE score with pgvector cosine distance (same operator pattern as `KnowledgeRepository.search_vector()`)
- Modify `app/knowledge/service.py` — implement `async _search_components(classified: ClassifiedQuery) -> SearchResponse`: instantiate `ComponentSearchService(self.db)`, call `search_components()`, merge with top-3 results from existing `search()` for supplementary knowledge context
- Modify `app/components/repository.py` — add two methods:
  - `async search_with_compatibility(search: str | None, category: str | None, compatible_with: list[str] | None, limit: int) -> list[tuple[Component, ComponentVersion]]` — extends existing `list()` pattern: ILIKE on `Component.name` using `escape_like()` from `app/shared/utils`, join to latest `ComponentVersion`, optional join to `ComponentQAResult` filtering where `compatibility->>client_id != 'none'` for each client in `compatible_with`. Uses parameterised queries throughout
  - `async search_by_embedding(embedding: list[float], limit: int) -> list[tuple[Component, float]]` — pgvector cosine distance on `Component.search_embedding`, same pattern as `KnowledgeRepository.search_vector()` (`.cosine_distance().label("distance")`)
- Modify `app/components/models.py` — add to `Component`:
  - `search_embedding = mapped_column(Vector(1024), nullable=True)` — matches `DocumentChunk.embedding` dimension. Import `Vector` from `pgvector.sqlalchemy` (already imported in `app/knowledge/models.py`)
- Migration: `add_component_search_embedding` — one nullable `vector(1024)` column on `components` table (no default, instant in PostgreSQL)
**Security:** Text search uses `escape_like()` utility (prevents LIKE injection, same pattern as existing `ComponentRepository.list()`). All queries use SQLAlchemy ORM parameterisation. Components are not project-scoped (all authenticated users can search), matching existing `ComponentRepository` access pattern. No new credential handling. Soft-deleted components excluded via `deleted_at.is_(None)` filter (existing pattern).
**Verify:** "CTA button" → returns matching components with `html_source` from latest `ComponentVersion`. Category filter ("cta") narrows results. Compatibility filter (`compatible_with=["outlook_2019_win"]`) excludes components with `"none"` support for that client. Empty component results → falls back to knowledge search only. Soft-deleted components excluded. Migration up/down clean. `make test` passes.
- [ ] 16.4 Template/component retrieval

### 16.5 CRAG Validation Loop
**What:** After HTML generation, validate against the compatibility matrix. If incompatible CSS is detected, retrieve fallbacks from ontology and re-generate. Implemented as a `CRAGMixin` class providing `_crag_validate_and_correct()`. Capped at 1 correction round to avoid loops.
**Why:** Agents generate CSS that passes QA string checks but breaks in major clients. The ontology knows `display:flex` doesn't work in Outlook, but that knowledge isn't in the generation loop — only in post-hoc QA reports the user reads after the fact. The existing `CssSupportCheck` in QA engine calls `unsupported_css_in_html()` but only reports issues — it never corrects them. CRAG closes the loop: detect → retrieve fallback → correct → ship.
**Independent:** Benefits from 16.2's `OntologyQueryEngine` but can use ontology directly via `load_ontology()`.
**Implementation:**
- Create `app/ai/agents/validation_loop.py` — `CRAGMixin` class (no `__init__`, stateless):
  - `async _crag_validate_and_correct(html: str, system_prompt: str, model: str) -> tuple[str, list[str]]` — returns `(corrected_html, corrections_applied)`. Flow:
    1. Call `unsupported_css_in_html(html)` from `app/knowledge/ontology/query.py` (same function used by `CssSupportCheck`)
    2. Filter to issues with severity ≥ `crag_min_severity` (default: `"error"` = >20% market share affected)
    3. If no qualifying issues → return `(html, [])` (no LLM call, zero cost)
    4. For each issue: call `load_ontology().fallbacks_for(issue["property_id"])` to get `Fallback` objects with `code_example` and `technique`
    5. Build correction prompt: list each issue + its fallback code example. Pass through `sanitize_prompt()` from `app/ai/sanitize.py`
    6. Call LLM via `get_registry().get_llm(provider_name).complete()` (same pattern as `BaseAgentService.process()`)
    7. Validate output: `validate_output()` → `extract_html()` → `sanitize_html_xss()` (same pipeline as `BaseAgentService._post_process()`)
    8. Return `(corrected_html, [issue["property_id"] for issue in qualifying_issues])`
  - Settings access via `get_settings()` singleton (same as all agents)
- Modify `app/ai/agents/base.py` → `process()` — insert CRAG step between `_post_process()` (step 14) and QA gate (step 15): `if hasattr(self, '_crag_validate_and_correct') and settings.knowledge.crag_enabled: html, corrections = await self._crag_validate_and_correct(html, system_prompt, model)`. This hooks CRAG into all `BaseAgentService` subclasses that mix in `CRAGMixin`
- Modify `app/ai/agents/scaffolder/service.py` — add `CRAGMixin` to class inheritance: `class ScaffolderService(CRAGMixin, BaseAgentService)`. For structured mode (`_process_structured()`), add explicit CRAG call after `TemplateAssembler.assemble()` and `sanitize_html_xss()` but before QA gate
- Modify `app/ai/agents/outlook_fixer/service.py` — add `CRAGMixin` to class inheritance: `class OutlookFixerService(CRAGMixin, BaseAgentService)`. Integration note: OutlookFixerService overrides `process()` with its own MSO repair loop (programmatic `repair_mso_issues()` + LLM retry via `_retry_with_mso_errors()`). CRAG should run BEFORE the MSO repair loop — CSS compatibility first (semantic), then MSO syntax (structural). Insert `_crag_validate_and_correct()` call after `super().process()` returns but before `validate_mso_conditionals()` check
- Config (`app/core/config.py` → `KnowledgeConfig`): `crag_enabled: bool = False`, `crag_max_rounds: int = 1`, `crag_min_severity: str = "error"` (matches severity levels from `_compute_severity()` in `query.py`: `"error"` >20% market share, `"warning"` >5%, `"info"` rest)
**Security:** CRAG correction prompt contains only ontology data (CSS property names, fallback code examples from `fallbacks.yaml`) — no user PII. Prompt sanitised via `sanitize_prompt()`. Output sanitised via `sanitize_html_xss()` (nh3 allowlist). LLM call uses same `get_registry().get_llm()` with circuit breaker protection (`_ResilientLLMProvider`). Cost capped: `max_rounds=1` (single retry), `crag_min_severity="error"` (only fires on high-impact issues), global `crag_enabled=False` default. Output validated via `validate_output()` (null byte stripping, 100K char truncation).
**Verify:** Generate HTML with `display:flex` via Scaffolder → CRAG detects (`unsupported_css_in_html` returns severity="error" for Outlook's ~8% market share × multiple Outlook clients), retrieves `flex_to_table` fallback with MSO conditional code example, re-generates with table layout. Generate compatible HTML (only properties with FULL support) → CRAG passes through unchanged (no LLM call, verified by checking no `complete()` call in logs). `crag_enabled=False` skips entirely (verified). OutlookFixerService: CRAG runs before MSO repair loop (verified by log ordering). ScaffolderService structured mode: CRAG runs after `TemplateAssembler.assemble()`. `make test` passes. `make eval-run` shows no regression (CRAG corrections counted in eval metrics).
- [ ] 16.5 CRAG validation loop

### 16.6 Multi-Representation Indexing
**What:** Store summaries for retrieval (better embedding match) but return full code for generation. Summaries are embedded instead of raw content; `search_vector()` returns the original full chunk. CSS blocks get deterministic summaries (list properties/values). HTML sections get deterministic summaries (tag structure, classes, styles). Optional LLM-generated summaries for complex content.
**Why:** Raw HTML/CSS code embeds poorly — angle brackets, property names, and hex values don't capture semantic meaning. A summary like "responsive 2-column layout using media queries with mobile-first stacking" embeds much better for the query "how to make a responsive email layout" than the raw `<table>` markup it describes.
**Dependencies:** 16.3 (uses `summary` column on `DocumentChunk`)
**Implementation:**
- Create `app/knowledge/summarizer.py` — `ChunkSummarizer` class (stateless):
  - `summarize_css_block(css: str) -> str` — deterministic: parse CSS text, list selectors + property names + values (no LLM, pure string processing)
  - `summarize_html_section(html: str) -> str` — deterministic: parse with `lxml.html`, list tag structure, class names, inline style properties (no LLM, uses `lxml.html.document_fromstring()`)
  - `async summarize_batch(chunks: list[DocumentChunk]) -> list[str]` — for chunks where deterministic summary is insufficient (e.g., prose mixed with code): call LLM via `httpx.AsyncClient` (same pattern as `KnowledgeService._auto_tag_document()` — uses `settings.knowledge.multi_rep_model` and `settings.knowledge.multi_rep_api_base_url`). Best-effort: on failure, fall back to first 200 chars of content
  - Route by `section_type`: `"style"` → `summarize_css_block()`, `"mso_conditional"` → deterministic MSO description, HTML sections → `summarize_html_section()`, `None`/text → `summarize_batch()` LLM call
- Modify `app/knowledge/service.py` → `ingest_document()` — after chunking, if `settings.knowledge.multi_rep_enabled`:
  1. Generate summaries via `ChunkSummarizer` (deterministic where possible, LLM for remainder)
  2. Store summaries in `DocumentChunk.summary` column
  3. Embed summaries (not raw content) via module-level `_get_embedding()` provider
  4. Store embeddings in `DocumentChunk.embedding` column as usual
  5. `DocumentChunk.content` retains full original code (unchanged)
- `app/knowledge/repository.py` → `search_vector()` — NO CHANGE needed. Already returns `chunk.content` (full code) alongside the distance score. The embedding was built from summary, but the returned content is always the full chunk
- Config (`app/core/config.py` → `KnowledgeConfig`): `multi_rep_enabled: bool = False`, `multi_rep_model: str = "gpt-4o-mini"`, `multi_rep_api_base_url: str = "https://api.openai.com/v1"`, `multi_rep_api_key: str = ""` (follows same pattern as existing `auto_tag_*` config fields)
- Migration: None (uses 16.3's `summary` column)
**Security:** Summaries are generated from document content already in the knowledge base. LLM summarization uses `httpx.AsyncClient` with the same pattern as `_auto_tag_document()` (API key from config, timeout, best-effort error handling). No user PII in summaries (document content is knowledge base articles, not user data). `multi_rep_api_key` stored in config alongside existing `auto_tag_api_key` — same security posture.
**Verify:** Ingest HTML document with `multi_rep_enabled=True` → chunks have deterministic summaries (CSS blocks list properties, HTML sections list structure). Search "responsive layout" → returns full `<table>` markup (not summary), but ranking improved because summary embedding matches better. Ingest plain-text document → LLM-generated summaries for prose chunks. `multi_rep_enabled=False` → existing behavior unchanged (content embedded directly, no summaries). Chunks without summaries still searchable (embedding from content as before). `make test` passes.
- [ ] 16.6 Multi-representation indexing
