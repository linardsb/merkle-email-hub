# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–30):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA — Playwright rendering, ODiff baselines, VLM analysis agent #10, auto-fix pipeline, visual QA dashboard). Phase 18 (rendering resilience & property-based testing — chaos engine with 8 profiles, Hypothesis-based property testing with 10 invariants, resilience score integration, knowledge feedback loop). Phase 19 (Outlook transition advisor & email CSS compiler — Word-engine dependency analyzer, audience-aware migration planner, Lightning CSS 7-stage compiler with ontology-driven conversions). Phase 20 (Gmail AI intelligence & deliverability — Gemini summary predictor, schema.org auto-injection, deliverability scoring, BIMI readiness check). Phase 21 (real-time ontology sync & competitive intelligence — caniemail auto-sync, rendering change detector with 25 feature templates, competitive intelligence dashboard). Phase 22 (AI evolution infrastructure — capability registry, prompt template store, token budget manager, fallback chains, cost governor, cross-module integration tests + ADR-009). Phase 23 (multimodal protocol & MCP agent interface — 7 subtasks: content block protocol, adapter serialization, agent integration, MCP tool server with 17 tools, voice brief pipeline, frontend multimodal UI, tests & ADR-010; 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks: WebSocket infra, Yjs CRDT engine, collaborative cursor & presence, visual builder canvas & palette, property panels, bidirectional code↔builder sync, frontend integration, tests & docs, AI-powered HTML import with 10th agent). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks: plugin architecture with manifest/discovery/registry, sandboxed execution & lifecycle, Tolgee multilingual campaigns, per-locale Maizzle builds, Kestra workflow orchestration, Penpot design-to-email pipeline, Typst QA report generator, ecosystem dashboard, template learning pipeline, automatic skill extraction, template-to-eval pipeline, deliverability intelligence, multi-variant campaign assembly). Phase 26 (email build pipeline performance & CSS optimization — 5 subtasks: eliminate redundant CSS inlining, per-build CSS compatibility audit, template-level CSS precompilation, consolidated CSS pipeline in Maizzle sidecar, tests & documentation). Phase 27 (email client rendering fidelity & pre-send testing — 6 subtasks: expand emulators to 8 clients/14 profiles, rendering confidence scoring, pre-send rendering gate, emulator calibration loop, headless email sandbox, frontend rendering dashboard). Phase 28 (export quality gates & approval workflow — 3 subtasks: QA enforcement in export flow, approval→export integration, approval frontend UI). Phase 29 (design import enhancements — 2 subtasks: brief-only template creation, Penpot CSS-to-email converter integration). Phase 30 (end-to-end testing & CI quality — 3 subtasks: Playwright e2e suite with 32+ scenarios, visual regression testing, multi-browser coverage).

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

## ~~Phase 27 — Email Client Rendering Fidelity & Pre-Send Testing~~ DONE

> All 6 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 27.1 Expand email client emulators (8 clients, 14 profiles), 27.2 Rendering confidence scoring, 27.3 Pre-send rendering gate, 27.4 Emulator calibration loop, 27.5 Headless email client sandbox, 27.6 Frontend rendering dashboard & tests.

---

## ~~Phase 28 — Export Quality Gates & Approval Workflow~~ DONE

> All 3 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 28.1 QA enforcement in export flow, 28.2 Approval workflow → export integration, 28.3 Approval frontend UI.

---

## ~~Phase 29 — Design Import Enhancements~~ DONE

> All 2 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 29.1 Brief-only template creation, 29.2 Penpot CSS-to-email converter integration.

---

## ~~Phase 30 — End-to-End Testing & CI Quality~~ DONE

> All 3 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 30.1 Playwright e2e user journey suite (32+ scenarios), 30.2 Visual regression testing in CI, 30.3 Multi-browser & CLI e2e coverage (Chromium + Firefox + WebKit).

---

## ~~Phase 31 — HTML Import Fidelity & Preview Accuracy~~ DONE

> All 8 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 31.1 Maizzle passthrough, 31.2 inline CSS ontology pipeline, 31.3 wrapper metadata preservation, 31.4 wrapper reconstruction, 31.5 dark mode text safety & sandbox fix, 31.6 enriched typography & spacing tokens, 31.7 image asset import & dimension preservation, 31.8 tests & integration verification.

---

## Phase 32 — Agent Email Rendering Intelligence

> Upgrade all 11 AI agents from distributed, duplicated email knowledge to a unified rendering intelligence layer: centralized client matrix, runtime knowledge lookup, cross-agent learning, content-aware rendering constraints, deeper import skills, and eval-driven skill evolution.

- [ ] 32.1 Centralized email client rendering matrix
- [ ] 32.2 Content agent email rendering awareness
- [ ] 32.3 Import annotator skill depth
- [ ] 32.4 Agent knowledge lookup tool
- [ ] 32.5 Cross-agent insight propagation
- [ ] 32.6 Eval-driven skill file updates
- [ ] 32.7 Visual QA feedback loop tightening
- [ ] 32.8 Tests & integration verification

### 32.1 Centralized Email Client Rendering Matrix `[Backend + Data]`
**What:** Create a single authoritative `data/email-client-matrix.yaml` file that defines every email client's rendering engine, CSS property support, dark mode behavior, known bugs, size limits, and quirks. Replace the 5+ duplicated client-compatibility references scattered across agent L3 skill files (`client_compatibility.md`, `client_behavior.md`, `email_client_engines.md`, `css_client_support.md`, `dom_rendering_reference.md`) with a loader that reads from this matrix. Integrate with the existing ontology sync pipeline so the matrix stays current with CanIEmail data.
**Why:** Client rendering knowledge is currently duplicated across Scaffolder (`client_compatibility.md`), Dark Mode (`client_behavior.md`, `dom_rendering_reference.md`), Code Reviewer (`css_client_support.md`), and Knowledge (`email_client_engines.md`). These files overlap but aren't identical — they drift as one gets updated and others don't. The Scaffolder says Gmail clips at 102KB; the Code Reviewer says the same; the Dark Mode agent doesn't mention it at all. Outlook VML requirements appear in 3 different files with slightly different syntax examples. When ontology data updates via `make sync-ontology`, none of these skill files update. A centralized matrix eliminates drift, creates a single update point, and enables runtime queries (32.4) instead of static skill file loading.
**Implementation:**
- Create `data/email-client-matrix.yaml`:
  - Structure per client:
    ```yaml
    clients:
      outlook_365_windows:
        display_name: "Outlook 365 (Windows)"
        engine: word
        engine_version: "Word 2019+"
        css_support:
          layout:
            flexbox: { support: none, workaround: "Use nested tables with fixed widths" }
            grid: { support: none, workaround: "Use nested tables" }
            float: { support: none, workaround: "Use align attribute on table/img" }
            position: { support: none }
          box_model:
            max-width: { support: none, workaround: "Use width attribute + MSO table wrapper" }
            border-radius: { support: none, workaround: "Use VML <v:roundrect>" }
            box-shadow: { support: none }
            margin: { support: partial, notes: "Supported on block elements, not table cells" }
          typography:
            font-family: { support: partial, notes: "System fonts only — no web fonts. Use mso-font-alt for fallback" }
            line-height: { support: partial, workaround: "Use mso-line-height-rule:exactly" }
          color:
            background-image: { support: none, workaround: "Use VML <v:fill>" }
            linear-gradient: { support: none, workaround: "Use VML fill patterns" }
          selectors:
            media_queries: false
            attribute_selectors: false
            pseudo_classes: [":hover (partial)"]
        dark_mode:
          type: forced_inversion
          developer_control: none
          selectors: []
          notes: "Outlook desktop (Windows) applies forced color inversion. No CSS override available."
        vml_required: true
        mso_conditionals: true
        known_bugs:
          - id: ghost_table
            symptom: "Multi-column layout collapses to single column"
            fix: "Wrap columns in MSO conditional ghost table"
          - id: dpi_scaling
            symptom: "Images render at wrong size on high-DPI displays"
            fix: "Set explicit width/height attributes on <img> + use CSS width for fluid"
          - id: line_height
            symptom: "Inconsistent line spacing"
            fix: "Add mso-line-height-rule:exactly to elements"
          - id: p_spacing
            symptom: "Extra vertical spacing on <p> tags"
            fix: "Add mso-margin-top-alt:0; mso-margin-bottom-alt:0 or use margin:0 inline"
          - id: font_fallback
            symptom: "Text renders in Times New Roman instead of specified font"
            fix: "Add mso-font-alt: Arial (or appropriate system font) to font-family declaration"
        size_limits: {}
        supported_fonts: [Arial, Georgia, Verdana, "Times New Roman", Tahoma, "Trebuchet MS", "Courier New", "Comic Sans MS", Impact, "Lucida Console"]

      gmail_web:
        display_name: "Gmail (Web)"
        engine: blink_restricted
        css_support:
          layout:
            flexbox: { support: none, workaround: "Use display:inline-block with widths" }
            grid: { support: none, workaround: "Use nested tables" }
          box_model:
            border-radius: { support: full }
            max-width: { support: full }
          typography:
            font-family: { support: full, notes: "Web fonts via <link> in <head>" }
          selectors:
            media_queries: false
            attribute_selectors: true
            pseudo_classes: [":hover"]
        dark_mode:
          type: forced_inversion
          developer_control: none
          selectors: []
          notes: "Gmail forces full color inversion. No developer override. Avoid pure #ffffff/#000000."
        known_bugs: []
        size_limits:
          clip_threshold_kb: 102
          style_block: "Stripped in some contexts (non-AMP, forwarded)"
        supported_fonts: "*"
        requires_link_tag: true

      apple_mail:
        display_name: "Apple Mail"
        engine: webkit
        css_support:
          layout:
            flexbox: { support: full }
            grid: { support: full }
          box_model:
            border-radius: { support: full }
            max-width: { support: full }
          typography:
            font-family: { support: full }
          selectors:
            media_queries: true
            attribute_selectors: true
            pseudo_classes: [":hover", ":active", ":focus"]
        dark_mode:
          type: developer_controlled
          developer_control: full
          selectors: ["@media (prefers-color-scheme: dark)"]
          notes: "Full developer control. Supports <picture> source swap for image dark mode."
        known_bugs: []
        size_limits: {}
        supported_fonts: "*"

      outlook_com:
        display_name: "Outlook.com"
        engine: blink_restricted
        css_support:
          layout:
            flexbox: { support: none }
            grid: { support: none }
          box_model:
            border-radius: { support: full }
          typography:
            font-family: { support: full }
          selectors:
            media_queries: false
        dark_mode:
          type: partial_developer
          developer_control: partial
          selectors: ["[data-ogsc]", "[data-ogsb]"]
          notes: "data-ogsc for text color, data-ogsb for background color. Only these selectors work."

      samsung_mail:
        display_name: "Samsung Mail"
        engine: webview
        dark_mode:
          type: double_inversion_risk
          developer_control: partial
          selectors: ["@media (prefers-color-scheme: dark)"]
          notes: "Applies BOTH custom dark CSS AND its own partial inversion. Risk of double-inversion."
        supported_fonts: "system_plus_google"

      yahoo_mail:
        display_name: "Yahoo Mail"
        engine: blink_restricted
        css_support:
          layout:
            flexbox: { support: none }
          selectors:
            media_queries: true
        dark_mode:
          type: partial_inversion
          developer_control: limited
        known_bugs:
          - id: class_renaming
            symptom: "CSS classes renamed with random prefix"
            fix: "Use inline styles as primary, <style> block as progressive enhancement"

      thunderbird:
        display_name: "Thunderbird"
        engine: gecko
        css_support:
          layout:
            flexbox: { support: full }
          selectors:
            media_queries: true
        dark_mode:
          type: developer_controlled
          developer_control: full
          selectors: ["@media (prefers-color-scheme: dark)"]
    ```
  - Include all 8 client families with 14 profiles as defined in the existing emulator system
- Create `app/knowledge/client_matrix.py`:
  - `ClientMatrix` class:
    - `load(path: Path = DATA_DIR / "email-client-matrix.yaml") -> ClientMatrix` — parse YAML, validate with Pydantic model
    - `get_client(client_id: str) -> ClientProfile` — lookup single client
    - `get_css_support(client_id: str, property: str) -> CSSSupport` — lookup CSS property support for a client
    - `get_dark_mode(client_id: str) -> DarkModeProfile` — dark mode behavior
    - `get_known_bugs(client_id: str) -> list[KnownBug]` — known rendering bugs
    - `get_constraints_for_clients(client_ids: list[str]) -> AudienceConstraints` — aggregate constraints for a set of target clients (intersection of support = lowest common denominator)
    - `format_audience_context(client_ids: list[str]) -> str` — generate the formatted `--- TARGET AUDIENCE CONSTRAINTS ---` string currently hardcoded in `audience_context.py`
  - `ClientProfile`, `CSSSupport`, `DarkModeProfile`, `KnownBug`, `AudienceConstraints` — Pydantic models
  - Cache parsed matrix in module-level singleton (YAML doesn't change at runtime)
- Modify `app/ai/blueprints/audience_context.py`:
  - Replace hardcoded constraint strings with `ClientMatrix.format_audience_context(client_ids)`
  - The current `_build_css_constraints()` function has client CSS knowledge embedded in Python code — replace with matrix lookups
  - Preserve the existing `AudienceProfile` interface — `audience_context` output format stays the same for downstream agents
- Modify `app/ai/agents/scaffolder/skills/`, `app/ai/agents/dark_mode/skills/`, `app/ai/agents/code_reviewer/skills/`, `app/ai/agents/knowledge/skills/`:
  - Remove duplicated client compatibility content from L3 skill files
  - Replace with brief reference: "Client rendering constraints are injected via audience context. For specific client capabilities, use the `lookup_client_support` tool (32.4)."
  - Keep agent-specific behavioral guidance (e.g., Dark Mode's "how to apply data-ogsc selectors" stays — but "which clients support data-ogsc" moves to matrix)
- Integration with ontology sync (`make sync-ontology`):
  - Modify `scripts/sync-ontology.js` (or add `scripts/sync-client-matrix.py`):
    - After ontology sync, cross-reference CanIEmail CSS property data with `email-client-matrix.yaml`
    - Flag drift: if ontology says a property is now supported in a client but the matrix says `none` → warning log
    - Auto-update `css_support` entries where ontology data is more recent (with human review flag for breaking changes)
    - Manual review for dark mode, known bugs, and size limits (these aren't in CanIEmail)
**Security:** Read-only YAML file parsed at startup. No user input reaches the parser. Pydantic validation rejects malformed data. No new API endpoints.
**Verify:** `ClientMatrix.get_css_support("outlook_365_windows", "flexbox")` returns `CSSSupport(support="none", workaround="Use nested tables...")`. `ClientMatrix.format_audience_context(["gmail_web", "outlook_365_windows"])` produces constraint string mentioning flexbox unsupported, 102KB clip limit. Agent L3 skill files no longer contain client CSS matrices. `audience_context.py` produces identical output format as before (diff test). `make test` passes. `make sync-ontology` runs without errors and logs any matrix drift warnings.

### 32.2 Content Agent Email Rendering Awareness `[Backend]`
**What:** Add a new L3 skill file `content_rendering_constraints.md` to the Content agent that teaches it how email client rendering constraints affect the text content it generates. Add skill detection triggers so the file loads when the agent is generating subject lines, preheaders, CTAs, or body copy destined for specific email clients.
**Why:** The Content agent generates text in a vacuum — it doesn't know that preheader visible length varies by client (Gmail ~100 chars, Apple Mail ~140, Outlook ~50), that subject lines truncate at different points on mobile vs desktop (35 chars vs 60 chars), that CTA button text renders inside VML `<v:roundrect>` elements with fixed dimensions (long text breaks layout), that body copy inside narrow `<td>` cells wraps differently than web, or that certain characters (smart quotes, em dashes, non-ASCII) break rendering in Outlook's Word engine. The agent's existing `operation_best_practices.md` has generic length guidelines but no client-aware constraints. When building for Outlook-heavy audiences, the Content agent should generate shorter, simpler text. When building for Apple Mail users, it can be more expressive.
**Implementation:**
- Create `app/ai/agents/content/skills/l3/content_rendering_constraints.md`:
  - **Preheader rendering by client:**
    - Gmail web/mobile: ~100-110 visible characters (after subject line), rest hidden
    - Apple Mail: ~140 characters visible in list view
    - Outlook desktop: ~50-60 characters (narrow preview pane)
    - Yahoo: ~100 characters
    - Samsung: ~90 characters
    - Rule: write preheader with critical message in first 50 chars (universal safe zone), supporting detail in chars 51-100 (most clients), optional detail in 101-140 (Apple Mail bonus)
  - **Subject line truncation:**
    - Mobile (all clients): ~35-40 characters visible in notification, ~50-55 in inbox list
    - Desktop Gmail: ~70 characters
    - Desktop Outlook: ~55-60 characters (depends on preview pane width)
    - Desktop Apple Mail: ~70-80 characters
    - Rule: front-load value proposition in first 35 chars, keep total under 60 for safety
  - **CTA button text constraints:**
    - VML buttons (Outlook): fixed width element — text must fit within declared width or overflows/clips
    - Rule: 2-5 words maximum, prefer action verbs, test at 120px-200px button widths
    - Avoid: long CTAs like "Learn More About Our Latest Features" — use "See Features" or "Learn More"
  - **Body copy in table cells:**
    - `<td>` cells have fixed widths (typically 300-560px depending on column layout)
    - Long words without hyphens can overflow cells in Outlook (Word engine doesn't hyphenate)
    - Rule: avoid words longer than 20 characters without soft hyphens (`&shy;`)
    - Outlook ignores `word-break` CSS — only `word-wrap: break-word` partially works
  - **Character encoding gotchas:**
    - Smart quotes (`\u201C` `\u201D` `\u2018` `\u2019`): render as `?` or `â€™` in some older Outlook versions and non-UTF-8 ESP configurations
    - Em dash (`\u2014`): safe in modern clients but breaks in some legacy systems — prefer ` — ` with spaces or ` - `
    - Ellipsis (`\u2026`): safe in modern clients, but `...` is universally safe
    - Non-ASCII characters (accented, CJK): require proper `<meta charset="UTF-8">` in HTML `<head>` — Content agent should flag if generating non-ASCII content
    - Rule: when audience includes Outlook Desktop or unknown clients, prefer ASCII-safe alternatives
  - **Line length and readability:**
    - Optimal reading line length: 45-75 characters per line
    - At 600px email width with 32px padding: ~50-60 chars per line at 16px font
    - At 300px column width (2-col layout): ~25-35 chars per line — requires shorter sentences
    - Rule: adapt sentence length to column width context when provided
- Modify `app/ai/agents/content/prompt.py` — skill detection:
  - Add trigger patterns for `content_rendering_constraints.md`:
    - Always load when `audience_context` is present in node metadata (means we know target clients)
    - Always load for `subject_line` and `preheader` operations (always client-sensitive)
    - Load for `cta` operation (VML button width constraints)
    - Load for `body_copy` when metadata indicates multi-column layout
  - Integrate with audience context: if node metadata includes `audience_client_ids`, inject client-specific preheader/subject limits into the skill context
- Modify Content agent's `SKILL.md` L2 section:
  - Add to L2 capabilities: "Client-aware text generation: adapts preheader length, subject line truncation, CTA word count, and character encoding to target email client constraints"
  - Add to L2 rules: "When audience context is available, respect per-client character limits. When no audience specified, use universal safe defaults (50-char preheader, 35-char subject front-load, 3-word CTA)"
**Security:** Read-only skill file addition. No new code paths, API endpoints, or user input handling. Skill detection uses existing metadata fields.
**Verify:** Content agent generating a preheader with Outlook Desktop in audience → output ≤50 significant characters in first sentence. Content agent generating CTA → ≤5 words. Content agent generating subject line → value proposition in first 35 characters. Content agent without audience context → universal safe defaults applied. Existing Content agent tests still pass. `make test` passes.

### 32.3 Import Annotator Skill Depth `[Backend]`
**What:** Add 4 new L3 skill files to the Import Annotator agent (`app/ai/agents/import_annotator/`) that teach it to recognize HTML patterns from popular email builders, normalize imported CSS, detect wrapper structures, and handle edge-case ESP token patterns. Update skill detection to load these files based on input HTML characteristics.
**Why:** The Import Annotator is the newest agent (Phase 24.9) with the fewest L3 skill files (4: `table_layouts.md`, `div_layouts.md`, `esp_tokens.md`, `column_patterns.md`). Users importing HTML from external tools — Stripo, Bee Free, Mailchimp, MJML-compiled output, Litmus Builder — hit edge cases the annotator doesn't handle: tool-specific ghost table patterns, non-standard comment markers, proprietary CSS class naming (`mc:edit`, `bee-row`, `stripo-*`), MJML's compiled nested table structure, and vendor-specific meta tags. Improving the annotator's recognition directly supports Phase 31's import fidelity goals.
**Implementation:**
- Create `app/ai/agents/import_annotator/skills/l3/common_email_builders.md`:
  - **Stripo patterns:**
    - CSS classes: `esd-structure`, `esd-container`, `esd-block`, `es-content-body`, `es-p-default`
    - Comment markers: `<!--[if !mso]><!-- -->` (standard MSO) + `<!-- stripo-module: -->` (section markers)
    - Structure: deeply nested tables (4-5 levels), `<div class="es-wrapper">` as outer container
    - Ghost tables: Stripo uses MSO conditionals with `mso-table-lspace:0pt; mso-table-rspace:0pt`
    - Annotation rule: preserve `stripo-module` comments as section boundaries, map `esd-*` classes to semantic roles
  - **Bee Free patterns:**
    - CSS classes: `bee-row`, `bee-col`, `bee-block`, `bee-content`
    - Structure: `<div class="bee-page-container">` → `<div class="bee-row">` → `<div class="bee-col">`
    - Note: Bee exports div-heavy layouts that need table conversion for email
    - Annotation rule: map `bee-row` → section boundary, `bee-col` → column, flag div-based layout for table conversion
  - **Mailchimp patterns:**
    - Merge tags: `*|MERGE|*` format, `*|IF:MERGE|*...*|END:IF|*` conditionals
    - Editable regions: `mc:edit="region_name"` attributes
    - CSS classes: `mc-*` prefixed, `templateContainer`, `templateBody`, `templateFooter`
    - Comment markers: `<!-- BEGIN MODULE: -->` section boundaries
    - Annotation rule: preserve `mc:edit` attributes as slot markers, map `BEGIN MODULE` comments to section boundaries, preserve merge tags as ESP tokens
  - **MJML compiled output:**
    - Structure: deeply nested 3-table pattern per section (outer align table → inner width table → content table)
    - CSS classes: `mj-*` removed during compilation, replaced with inline styles
    - Comment markers: `<!-- [mj-column] -->` (sometimes preserved)
    - Width pattern: every structural `<td>` has explicit `width` attribute + `style="width:Npx"`
    - Annotation rule: recognize the 3-table nesting pattern, collapse to single section table in annotation
  - **Litmus Builder patterns:**
    - Similar to hand-coded: clean table structure, minimal classes
    - Comment markers: `<!-- MODULE: -->` section markers
    - Annotation rule: map `MODULE` comments to section boundaries
- Create `app/ai/agents/import_annotator/skills/l3/css_normalization.md`:
  - **Shorthand expansion**: reference 31.2's CSS compiler output — by the time the annotator sees the HTML, shorthands are already expanded (if the upload pipeline ran the compiler). If annotating raw HTML (no compiler step), flag unexpanded shorthands for the compiler.
  - **Vendor prefix cleanup**: `-webkit-`, `-moz-`, `-ms-`, `-o-` prefixes — map to standard property names for annotation, preserve in output (still needed for some clients)
  - **!important handling**: count `!important` declarations — high count (>20) indicates Mailchimp/Stripo export (they use `!important` defensively). Don't strip — but annotate as "tool-generated defensive styles"
  - **Duplicate property detection**: same property declared twice in one `style=""` attribute (common in tool exports as progressive enhancement — e.g., `background: #fff; background: linear-gradient(...)`). Annotate the intent: first value = fallback, second = progressive.
  - **Class-to-inline reconciliation**: when `<style>` block classes AND inline styles both set the same property, annotate which wins (inline wins in email — `<style>` block is progressive enhancement only)
- Create `app/ai/agents/import_annotator/skills/l3/wrapper_detection.md`:
  - **Centering wrapper patterns** (complements 31.3 analyzer work):
    - Pattern 1: `<table width="600" align="center">` (classic email centering)
    - Pattern 2: `<div style="max-width:600px; margin:0 auto;">` (modern, needs table fallback for Outlook)
    - Pattern 3: `<center>` tag (legacy, still used by some builders)
    - Pattern 4: MSO ghost table wrapper `<!--[if mso]><table align="center"><tr><td><![endif]-->` around a `<div>`
    - Pattern 5: Nested wrapper — MSO ghost table outside, div inside, content table innermost
  - **Background wrapper patterns**:
    - Full-width background: `<table width="100%" bgcolor="#f2f2f2">` wrapping centered content table
    - VML background: `<!--[if gte mso 9]><v:rect>...<v:fill>...</v:fill>...<![endif]-->` wrapping content
    - Annotation rule: identify background wrappers separately from centering wrappers — they serve different reconstruction purposes
  - **Preheader wrapper patterns**:
    - Hidden preheader: `<div style="display:none; max-height:0; overflow:hidden;">` or `<span style="display:none;">`
    - Annotation rule: annotate as `preheader_wrapper`, preserve for reconstruction
- Create `app/ai/agents/import_annotator/skills/l3/esp_token_edge_cases.md`:
  - **AMPscript edge cases:**
    - Nested function calls: `%%=Concat(Uppercase(FirstName), " ", LastName)=%%`
    - Inline AMPscript blocks inside attributes: `<a href="%%=RedirectTo(...)=%%">`
    - `TreatAsContent` / `ContentBlockByKey` references (external content inclusion)
    - Multi-line AMPscript blocks: `%%[ ... ]%%` spanning multiple lines with SET/IF/ENDIF
  - **Nested Liquid:**
    - Filters chained: `{{ name | capitalize | truncate: 20 }}`
    - Liquid inside HTML attributes: `<div style="color: {{ brand_color }};">`
    - `{% capture %}` blocks that define variables used later
    - Connected Content: `{% connected_content https://api.example.com :save response %}` (Braze-specific)
  - **Handlebars partials:**
    - `{{> partial_name }}` — external template inclusion
    - `{{#each items}}...{{/each}}` — loop with `{{@index}}`, `{{@first}}`, `{{@last}}`
    - Triple-stache `{{{unescaped}}}` for raw HTML injection
  - **ERB (Ruby-based ESPs):**
    - `<%= expression %>` — output
    - `<% code %>` — logic
    - `<%- include 'partial' %>` — partial inclusion
  - **Annotation rules:** preserve ALL ESP tokens as opaque blocks during structural analysis. Never split an ESP token across section boundaries. When an ESP conditional (`{% if %}...{% endif %}`) wraps multiple sections, annotate the conditional as spanning those sections.
- Modify `app/ai/agents/import_annotator/prompt.py` — skill detection:
  - Load `common_email_builders.md` when HTML contains: `esd-`, `bee-`, `mc:edit`, `mj-`, `stripo`, or `<!-- BEGIN MODULE` / `<!-- MODULE`
  - Load `css_normalization.md` when HTML contains: `!important` (>5 occurrences), vendor prefixes, or duplicate inline properties
  - Load `wrapper_detection.md` always (wrapper detection is core to import fidelity)
  - Load `esp_token_edge_cases.md` when HTML contains: `%%[`, `%%=`, `{%`, `{{`, `<%`, `*|`, or `{{>`
**Security:** Read-only skill file additions. No new code paths. ESP tokens are treated as opaque strings — never evaluated or executed. The annotator is analysis-only (no HTML modification).
**Verify:** Import Stripo-exported HTML → annotator identifies `esd-structure` sections and `stripo-module` comments. Import Mailchimp template → annotator preserves `mc:edit` attributes and merge tags. Import MJML-compiled output → annotator recognizes 3-table nesting pattern. Import HTML with nested AMPscript → ESP tokens preserved intact across section boundaries. Import HTML with `<center>` wrapper → annotator identifies centering pattern. Existing Import Annotator tests pass. `make test` passes.

### 32.4 Agent Knowledge Lookup Tool `[Backend]`
**What:** Create a `lookup_client_support` tool callable by all agents during LLM execution, backed by the centralized client matrix (32.1). Instead of pre-loading full L3 reference files into the prompt, agents can query specific facts at decision time: "Does Outlook 365 support border-radius?" → structured answer with support level, workaround, and confidence. Integrate as an LLM tool/function call in the blueprint engine's agent execution flow.
**Why:** L3 skill files are loaded based on HTML pattern detection — clever but limited. Pattern detection can miss edge cases (HTML has no MSO conditionals, but Outlook IS in the target audience — the Scaffolder should still know Outlook constraints). Loading full reference files burns tokens even when the agent only needs one fact. With a tool, agents ask the right question at the right time, prompt size drops (no pre-loaded reference files for "just in case"), and the system naturally logs what agents need to know (useful for eval improvement and skill file refinement in 32.6). The Knowledge agent already provides RAG-based Q&A, but it's a heavy pipeline (embedding search → reranking → LLM synthesis). The lookup tool is a lightweight, deterministic alternative for structured facts.
**Implementation:**
- Create `app/ai/agents/tools/client_lookup.py`:
  - `ClientLookupTool` class implementing the agent tool interface:
    - Tool name: `lookup_client_support`
    - Tool description: "Look up email client rendering support for a CSS property, dark mode behavior, known bugs, or size limits. Returns structured data from the authoritative client rendering matrix."
    - Parameters schema:
      ```python
      class ClientLookupParams(BaseModel):
          query_type: Literal["css_support", "dark_mode", "known_bugs", "size_limits", "font_support"]
          client_id: str  # e.g., "outlook_365_windows", "gmail_web"
          property: str | None = None  # CSS property name for css_support queries
      ```
    - Returns:
      ```python
      class ClientLookupResult(BaseModel):
          client: str
          query_type: str
          result: dict[str, Any]  # varies by query_type
          workaround: str | None = None
          confidence: float = 1.0  # always 1.0 for matrix data (deterministic)
      ```
    - Implementation: direct lookup from `ClientMatrix` (32.1) — no LLM, no embedding search, no network calls
    - Fallback: if `client_id` not found, return `{"error": "Unknown client", "available_clients": [...]}` so the LLM can self-correct
  - `MultiClientLookupTool` — batch variant:
    - Tool name: `lookup_client_support_batch`
    - Accepts `client_ids: list[str]` + `properties: list[str]`
    - Returns matrix of support levels — useful for "which of my target clients support flexbox?"
    - Reduces round-trips: one tool call instead of N×M individual lookups
- Modify `app/ai/blueprints/engine.py` — tool registration:
  - In `_build_tools_for_node()` (or equivalent tool setup):
    - Register `ClientLookupTool` and `MultiClientLookupTool` for all agentic nodes
    - Tools are available alongside existing tools (memory recall, knowledge search)
  - Tool execution: synchronous (matrix lookup is <1ms) — no async overhead needed
- Modify agent system prompts (Scaffolder, Dark Mode, Outlook Fixer, Accessibility, Code Reviewer, Innovation):
  - Add to L2 section: "You have access to `lookup_client_support` for real-time client rendering queries. Use it instead of guessing CSS support. Available query types: css_support, dark_mode, known_bugs, size_limits, font_support."
  - Remove or reduce L3 skill files that duplicate matrix data (already trimmed in 32.1)
- Add tool usage logging:
  - Log every tool call: `agent_name`, `query_type`, `client_id`, `property`, `timestamp`
  - Aggregate logs feed into 32.6 (eval-driven skill updates): frequently queried facts should be promoted to L2 skill file content (always loaded), rarely queried facts stay in the matrix (on-demand)
**Security:** Tool returns read-only data from a static YAML file. No user input reaches the tool except through LLM function calling (which is already sandboxed). Tool results are structured data, not executable code. No new API endpoints — tool is internal to the blueprint engine.
**Verify:** Scaffolder agent generating email for Outlook audience → calls `lookup_client_support("css_support", "outlook_365_windows", "border-radius")` → receives `{support: "none", workaround: "Use VML <v:roundrect>"}`. Dark Mode agent → calls `lookup_client_support("dark_mode", "samsung_mail")` → receives `{type: "double_inversion_risk", ...}`. Batch lookup for 3 clients × 2 properties → single tool call returns 6 results. Unknown client ID → error response with available clients list. Tool call logging captures all queries. Agent prompt token count reduced vs pre-32.4 baseline (measure before/after). `make test` passes.

### 32.5 Cross-Agent Insight Propagation `[Backend]`
**What:** Create a structured insight bus that extracts learnings from each agent's execution within a blueprint run and propagates them to relevant downstream agents — both within the same run (via handoff metadata) and across runs (via semantic memory with cross-agent routing). When the Dark Mode agent discovers "Samsung Mail double-inverts #1a1a1a backgrounds," the Scaffolder agent should know to avoid that color in future builds for Samsung audiences.
**Why:** Agent learning is currently siloed. Each agent stores its failure patterns in semantic memory tagged with its own name. When the Dark Mode agent discovers a Samsung Mail rendering issue, that insight lives in `source_agent="dark_mode"` memory entries. The Scaffolder never recalls those memories because it queries `agent_type="scaffolder"`. The handoff chain passes structured decisions between agents in a single run, but handoffs describe *what was done* — not *what was learned*. The result: the Scaffolder keeps generating patterns that the Dark Mode agent keeps fixing, run after run.
**Implementation:**
- Create `app/ai/blueprints/insight_bus.py`:
  - `AgentInsight` dataclass:
    ```python
    @dataclass
    class AgentInsight:
        source_agent: str        # "dark_mode"
        target_agents: list[str] # ["scaffolder", "code_reviewer"]
        client_ids: list[str]    # ["samsung_mail"]
        insight: str             # "Avoid #1a1a1a backgrounds — Samsung double-inverts to near-white"
        category: str            # "color", "layout", "typography", "dark_mode", "accessibility", "mso"
        confidence: float        # 0.85 (derived from evidence count / total runs)
        evidence_count: int      # 3 occurrences
        first_seen: str          # ISO timestamp
        last_seen: str           # ISO timestamp
    ```
  - `InsightBus` class:
    - `extract_insights(run_result: BlueprintRunResult) -> list[AgentInsight]`:
      - Parse QA failure details + agent handoffs from the completed run
      - For each QA failure that was fixed by an agent:
        - Identify the *root cause agent* (which upstream agent generated the problematic pattern?)
        - Identify the *fixer agent* (which agent corrected it?)
        - Generate insight: "When building for {clients}, avoid {pattern} — {fixer_agent} had to correct it because {reason}"
        - Route insight to root cause agent + code reviewer
      - For each agent that made a structured decision with confidence < 0.7:
        - Generate insight: "Low confidence on {decision_type} for {clients} — consider {alternative}"
      - Deduplication: hash on (source_agent, category, client_ids, insight_core_text) — merge duplicates by incrementing `evidence_count` and updating `last_seen`
    - `persist_insights(insights: list[AgentInsight])`:
      - Store each insight as a semantic memory entry via `MemoryService.store()`:
        - `memory_type="procedural"` (learned pattern)
        - `agent_type` = comma-joined `target_agents` (so target agents can recall it)
        - `metadata = {"source_agent": ..., "client_ids": ..., "category": ..., "evidence_count": ...}`
        - `content` = formatted insight text
      - Use `is_evergreen=True` for insights with `evidence_count >= 5` (stable patterns shouldn't decay)
    - `recall_insights(agent_name: str, client_ids: list[str] | None, categories: list[str] | None) -> list[AgentInsight]`:
      - Query semantic memory with `agent_type` containing `agent_name`
      - Filter by `client_ids` overlap if provided
      - Filter by `category` if provided
      - Return top 5 most relevant (by recency × evidence_count × similarity)
- Modify `app/ai/blueprints/engine.py` — add insight injection layer:
  - New context layer (after Layer 16 cross-agent failure patterns):
    - `cross_agent_insights = insight_bus.recall_insights(agent_name, audience_client_ids, relevant_categories)`
    - Format as:
      ```
      --- CROSS-AGENT INSIGHTS ---
      From dark_mode agent (3 occurrences, Samsung Mail):
        Avoid #1a1a1a backgrounds — Samsung double-inverts to near-white.
      From outlook_fixer agent (5 occurrences, Outlook 365):
        Always add mso-font-alt when using non-system fonts — Outlook falls back to Times New Roman.
      ```
    - Inject into `NodeContext.metadata["cross_agent_insights"]`
  - Post-run hook: after blueprint completes, call `insight_bus.extract_insights(run_result)` → `persist_insights(insights)`
- Modify `app/ai/blueprints/protocols.py` — `BlueprintRunResult`:
  - Add `insights_extracted: int = 0` — count of insights generated this run (for observability)
- Within-run propagation (immediate, same blueprint execution):
  - Modify handoff metadata in `_build_handoff()`:
    - Add `learnings: list[str]` field to handoff — agent can declare "I learned X about this specific email"
    - Downstream agents see `upstream_handoff.learnings` alongside existing `upstream_handoff.constraints`
    - Example: Dark Mode agent's handoff includes `learnings: ["Samsung dark mode inverted the hero background — added explicit data-ogsb override"]`
    - Scaffolder on next retry sees this learning and adjusts generation
**Security:** Insights are derived from internal agent execution data — no user input in insight generation. Memory storage uses existing `MemoryService` with project scoping. Insight content is descriptive text about rendering patterns — no executable code, no PII, no credentials. Cross-agent recall uses existing memory query paths.
**Verify:** Run blueprint with Samsung Mail audience → Dark Mode agent fixes a color issue → insight extracted: `{source: "dark_mode", target: ["scaffolder"], client: "samsung_mail", insight: "..."}` → stored in semantic memory. Next blueprint run for Samsung Mail → Scaffolder agent receives cross-agent insight in context. Insight deduplication: same pattern extracted twice → `evidence_count` increments, no duplicate memory entry. Insight with `evidence_count >= 5` → `is_evergreen=True`. Handoff learnings: Dark Mode handoff includes `learnings` list visible to downstream agents. `make test` passes.

### 32.6 Eval-Driven Skill File Updates `[Backend + CI]`
**What:** Build a semi-automated pipeline that monitors agent eval pass rates, detects persistent failure patterns, generates proposed skill file patches grounded in failure evidence, and opens PRs for human review. When an agent's pass rate on a criterion drops below threshold for N consecutive eval runs, the pipeline extracts the failure cluster, drafts a skill file addition, and creates a branch with the proposed change.
**Why:** L3 skill files are static — written once by a developer, updated only when someone remembers to. The eval system (`analysis.json`) already tracks per-agent per-criterion pass rates. Failure warnings are injected as ephemeral prompt text, but they don't improve the underlying skill files. The gap: a failure pattern persists for weeks, the warning text keeps compensating, but the root cause (missing knowledge in the skill file) is never fixed. This pipeline closes the loop — eval data drives permanent skill improvements, reviewed by a human before merge.
**Implementation:**
- Create `app/ai/agents/evals/skill_updater.py`:
  - `SkillUpdateDetector` class:
    - `detect_update_candidates(analysis_path: Path = TRACES_DIR / "analysis.json") -> list[SkillUpdateCandidate]`:
      - Load `analysis.json` (per-agent per-criterion pass rates + failure samples)
      - For each agent + criterion pair:
        - If pass rate < `SKILL_UPDATE_THRESHOLD` (default 0.80) AND failure count >= `MIN_FAILURE_COUNT` (default 5):
          - Extract failure cluster: common patterns in failure reasons (group by text similarity)
          - Create `SkillUpdateCandidate(agent, criterion, pass_rate, failure_count, failure_cluster, sample_reasons)`
      - Return candidates sorted by impact (lowest pass rate × highest failure count)
    - `generate_patch(candidate: SkillUpdateCandidate) -> SkillFilePatch`:
      - Identify the relevant L3 skill file for this agent + criterion:
        - Map criterion → skill file (e.g., "dark_mode_coverage" → `client_behavior.md`, "mso_validity" → `mso_bug_fixes.md`)
        - Maintain mapping in `CRITERION_SKILL_MAP: dict[str, dict[str, str]]` (agent → criterion → skill file path)
      - Generate a proposed addition to the skill file:
        - Format:
          ```markdown
          ## Recently Observed Failure: {cluster_summary}

          **Pattern:** {common_pattern_description}
          **Fix:** {recommended_approach}
          **Evidence:** {failure_count} failures in recent eval runs ({pass_rate}% pass rate).
          **Sample failures:**
          - {reason_1}
          - {reason_2}
          - {reason_3}
          ```
        - The patch content is generated by LLM (single call, temperature=0.0) given: failure samples, existing skill file content, agent name, criterion name
        - LLM is instructed: "Generate a concise, actionable addition to this skill file that addresses the observed failure pattern. Use the same formatting style as the existing file. Do NOT repeat existing content."
      - Return `SkillFilePatch(skill_file_path, patch_content, candidate)`
    - `apply_patches(patches: list[SkillFilePatch], branch_name: str) -> str`:
      - Create git branch: `skill-update/{agent}/{criterion}/{date}`
      - For each patch: append content to the relevant skill file
      - Commit with message: `fix(agents): update {agent} skill file for {criterion} (eval-driven)`
      - Return branch name for PR creation
  - `SkillUpdateCandidate`, `SkillFilePatch` — Pydantic models
- Create `scripts/eval-skill-update.py` (CLI entry point):
  - Parse args: `--dry-run` (print candidates, don't create branch), `--threshold` (override), `--agent` (filter to one agent)
  - Call `SkillUpdateDetector.detect_update_candidates()`
  - If candidates found: call `generate_patch()` for each → `apply_patches()` → log branch name
  - If `--dry-run`: print candidates and proposed patches without git operations
  - Exit code: 0 if no updates needed, 1 if patches generated (for CI gating)
- Add to `Makefile`:
  - `eval-skill-update`: run `scripts/eval-skill-update.py --dry-run` (safe default)
  - `eval-skill-update-apply`: run `scripts/eval-skill-update.py` (creates branch)
- Add tool usage analytics integration (from 32.4):
  - `SkillUpdateDetector` also reads tool call logs from 32.4
  - Frequently queried facts (>10 queries across runs for the same agent + property + client) → candidate for promotion to L2 skill file (always-loaded content)
  - Rarely queried L3 content (loaded but never referenced in agent output) → candidate for demotion or removal
- CI integration (optional, future):
  - After `make eval-full` completes, run `eval-skill-update --dry-run`
  - If candidates found: comment on the eval PR with proposed updates
  - Developer can approve → script creates branch → PR opened
**Security:** LLM-generated skill file patches are text-only (Markdown) — no executable code. Patches are always human-reviewed before merge (PR workflow). The script reads `analysis.json` (internal eval data) and skill files (checked into repo) — no external input. Git operations use standard branching (no force-push, no main branch modification). The LLM call for patch generation uses the same API key and rate limits as eval judges.
**Verify:** Run `make eval-full` → `analysis.json` updated. Run `eval-skill-update --dry-run` → candidates printed for agents with pass rate < 80%. Run `eval-skill-update-apply` → git branch created with skill file patches. Patches are well-formatted Markdown matching existing skill file style. No duplicate content (patch doesn't repeat what's already in the skill file). `make test` passes (no production code changes — this is a dev tooling task).

### 32.7 Visual QA Feedback Loop Tightening `[Backend]`
**What:** Integrate the Visual QA agent more tightly into the blueprint recovery loop by adding a pre-Maizzle visual check stage and a post-render screenshot comparison against the original imported design. When Visual QA detects a rendering defect, route it back to the relevant fixer agent with the screenshot attached (via Layer 20 multimodal context). Add per-client defect reports to the QA gate output.
**Why:** The Visual QA agent exists but sits partially outside the main agent loop. It can detect rendering defects from screenshots (Outlook layout collapse, Gmail style stripping, dark mode inversion, responsive breakage), but the feedback path back to fixer agents is indirect — defects appear in QA results as text descriptions without the visual evidence. Fixer agents (Dark Mode, Outlook Fixer, Accessibility) would be significantly more effective if they could *see* the defect they're fixing. The system already has multimodal context support (Layer 20) — we just need to wire it into the recovery loop. Additionally, post-render screenshot comparison against the original design catches drift that text-based QA checks miss (e.g., subtle spacing changes, color shifts, font rendering differences).
**Implementation:**
- Modify `app/ai/blueprints/nodes/qa_gate_node.py`:
  - Add optional `visual_qa_precheck` stage before the 14 standard QA checks:
    - Feature gate: `BLUEPRINT__VISUAL_QA_PRECHECK=true` (default: false — opt-in to avoid latency impact)
    - When enabled: render the current HTML via `RenderingService.render()` for top 3 target clients (from audience profile)
    - Pass screenshots to Visual QA agent (or run the VLM directly — lighter than full agent invocation)
    - Visual QA returns `VisualDefect` list: `{type, severity, client, bounding_box, description, suggested_agent}`
    - Defects with severity >= "high" are added to the QA failure list alongside standard check results
    - Each defect carries its screenshot reference (content block ID) for downstream injection
  - Modify QA failure routing in `RecoveryRouterNode`:
    - When routing a visual defect to a fixer agent, attach the screenshot via Layer 20 multimodal context:
      - `node_context.metadata["multimodal_context"] = [TextBlock(defect_description), ImageBlock(screenshot)]`
    - Fixer agent sees: "Outlook 365 screenshot shows hero image overflowing container. See attached screenshot." + the actual screenshot
    - Agent can use visual context to generate a more targeted fix
- Create `app/ai/blueprints/nodes/visual_comparison_node.py`:
  - `VisualComparisonNode` — runs after Maizzle build, before final output:
    - Compares rendered email screenshots against:
      - (a) Original imported design screenshot (if available from upload phase — stored in `multimodal_context`)
      - (b) Previous iteration's screenshot (if retry — detect regression)
    - Uses ODiff (already in the stack from Phase 17) for pixel-level comparison
    - Threshold: >5% pixel difference → flag as visual drift
    - Output: `VisualComparisonResult` with `drift_score`, `diff_regions`, `diff_image_path`
    - Advisory only — does not block output, but adds drift warnings to build response
    - Feature gate: `BLUEPRINT__VISUAL_COMPARISON=true` (default: false)
- Modify `app/ai/agents/visual_qa/service.py`:
  - Add `detect_defects_lightweight(screenshot: bytes, client_id: str) -> list[VisualDefect]`:
    - Lighter-weight VLM call than full agent invocation (smaller prompt, focused detection)
    - Returns structured defects without fix recommendations (fixes are the fixer agents' job)
    - Used by the QA gate precheck (fast path)
  - Add `compare_screenshots(original: bytes, rendered: bytes, client_id: str) -> VisualComparisonResult`:
    - VLM-assisted comparison: ODiff for pixel diff + VLM for semantic interpretation
    - "The rendered version has 3% pixel difference. Differences: (1) heading font slightly larger, (2) hero section padding reduced by ~4px."
    - Returns structured result with human-readable explanation
- Modify `app/qa_engine/schemas.py`:
  - Add `VisualDefect` model: `type: str`, `severity: Literal["low", "medium", "high", "critical"]`, `client_id: str`, `description: str`, `suggested_agent: str | None`, `screenshot_ref: str | None`, `bounding_box: dict | None`
  - Add `visual_defects: list[VisualDefect] = []` to `QAGateResult`
- Modify `app/email_engine/schemas.py`:
  - Add `visual_drift: VisualComparisonResult | None = None` to `BuildResponse`
**Security:** Screenshots are rendered from the email HTML already in the pipeline — no external content fetched. VLM calls use the same API key and rate limits as other agent calls. ODiff is a deterministic image comparison tool — no code execution. Screenshots are ephemeral (not persisted unless visual regression baselines are enabled). Feature gates default to off — no latency impact unless opted in.
**Verify:** Enable `BLUEPRINT__VISUAL_QA_PRECHECK=true`. Run blueprint for Outlook audience with a flexbox layout → Visual QA precheck detects "layout collapse in Outlook 365" → routes to Outlook Fixer with screenshot → fixer generates ghost table fix. Disable feature gate → no precheck, standard QA flow. Enable `BLUEPRINT__VISUAL_COMPARISON=true` → after Maizzle build, drift score reported in build response. Original design screenshot available (from upload) → comparison shows <5% drift (acceptable). Force a large change → comparison shows >5% drift + VLM description of differences. `make test` passes. `make bench` shows acceptable latency increase (<2s per visual check).

### 32.8 Tests & Integration Verification `[Full-Stack]`
**What:** Comprehensive tests verifying the full agent intelligence pipeline: centralized matrix queries, tool-based lookups, cross-agent insight propagation, content rendering constraints, import annotator recognition, eval-driven updates, and visual QA feedback.
**Implementation:**
- **Client matrix tests** — `app/knowledge/tests/test_client_matrix.py`:
  - `ClientMatrix.load()` parses `email-client-matrix.yaml` without errors
  - `get_css_support("outlook_365_windows", "flexbox")` → `CSSSupport(support="none", workaround=...)`
  - `get_css_support("apple_mail", "flexbox")` → `CSSSupport(support="full")`
  - `get_dark_mode("gmail_web")` → `DarkModeProfile(type="forced_inversion", developer_control="none")`
  - `get_dark_mode("apple_mail")` → `DarkModeProfile(type="developer_controlled", developer_control="full")`
  - `get_known_bugs("outlook_365_windows")` → list with `ghost_table`, `dpi_scaling`, etc.
  - `format_audience_context(["gmail_web", "outlook_365_windows"])` → string contains "flexbox: unsupported", "102KB clip"
  - `format_audience_context(["apple_mail"])` → no layout restrictions mentioned
  - Unknown client ID → raises `ClientNotFoundError`
  - Matrix validation: all client IDs match emulator system's client ID list
- **Client lookup tool tests** — `app/ai/agents/tools/tests/test_client_lookup.py`:
  - `ClientLookupTool.execute(query_type="css_support", client_id="outlook_365_windows", property="border-radius")` → result with `support="none"`, `workaround` containing "VML"
  - `MultiClientLookupTool.execute(client_ids=["gmail_web", "outlook_365_windows"], properties=["flexbox", "border-radius"])` → 4 results (2×2 matrix)
  - Unknown client → error result with available client list
  - Unknown property → result with `support="unknown"`
  - Tool registered for agentic nodes in blueprint engine
- **Content rendering awareness tests** — `app/ai/agents/content/tests/test_content_rendering.py`:
  - Skill detection: `audience_context` present → `content_rendering_constraints.md` loaded
  - Skill detection: `subject_line` operation → constraints loaded regardless of audience
  - Skill detection: `body_copy` without audience → constraints NOT loaded (L3 not needed)
  - Verify skill file parseable and contains: preheader limits, subject truncation, CTA constraints, character encoding section
- **Import annotator skill tests** — `app/ai/agents/import_annotator/tests/test_annotator_skills.py`:
  - Skill detection: HTML with `esd-structure` class → `common_email_builders.md` loaded
  - Skill detection: HTML with `mc:edit` attribute → `common_email_builders.md` loaded
  - Skill detection: HTML with >5 `!important` → `css_normalization.md` loaded
  - Skill detection: HTML with `%%[` (AMPscript) → `esp_token_edge_cases.md` loaded
  - Skill detection: all HTML → `wrapper_detection.md` loaded (always-on)
  - Verify all 4 new skill files parseable and contain expected sections
- **Cross-agent insight tests** — `app/ai/blueprints/tests/test_insight_bus.py`:
  - `InsightBus.extract_insights()` from a mock run result with QA failure fixed by dark_mode agent → returns insight with `target_agents=["scaffolder"]`
  - `persist_insights()` stores insight in semantic memory with correct `agent_type` tag
  - `recall_insights("scaffolder", ["samsung_mail"])` → returns insights tagged for scaffolder + samsung_mail
  - Deduplication: same insight extracted twice → `evidence_count` incremented, single memory entry
  - Insight with `evidence_count >= 5` → `is_evergreen=True`
  - Context injection: insight appears in `NodeContext.metadata["cross_agent_insights"]`
  - Handoff learnings: agent handoff includes `learnings` list
- **Eval skill updater tests** — `app/ai/agents/evals/tests/test_skill_updater.py`:
  - `detect_update_candidates()` with mock `analysis.json` (agent at 70% pass rate, 8 failures) → returns candidate
  - `detect_update_candidates()` with all agents above threshold → returns empty list
  - `generate_patch()` produces valid Markdown with expected structure (## header, **Pattern:**, **Fix:**, **Evidence:**)
  - `--dry-run` mode prints candidates without git operations
  - Criterion-to-skill-file mapping covers all agent + criterion pairs
- **Visual QA integration tests** — `app/ai/blueprints/tests/test_visual_qa_feedback.py`:
  - Feature gate off → no visual precheck, standard QA flow
  - Feature gate on → `detect_defects_lightweight()` called with rendered screenshot
  - Visual defect with severity "high" → added to QA failure list → routes to fixer agent
  - Fixer agent receives `multimodal_context` with screenshot
  - Visual comparison: ODiff <5% → `drift_score` below threshold
  - Visual comparison: ODiff >5% → `drift_score` above threshold + description
- **Audience context integration test** — `app/ai/blueprints/tests/test_audience_context_matrix.py`:
  - `audience_context.py` produces identical output format before and after migration to `ClientMatrix`
  - Regression test: compare output of old hardcoded function vs new matrix-backed function for all 14 client profiles
  - Output diff = zero (format compatibility preserved)
**Security:** Tests only. No production code changes. Mock data contains no real credentials or PII. VLM calls in visual QA tests use test fixtures (pre-captured screenshots), not live rendering.
**Verify:** `make test` passes (all new test files). `make check` all green. `make bench` shows no performance regression in non-visual-QA code paths. Agent prompt token counts with tool access < agent prompt token counts with full L3 skill files (measured via test). Cross-agent insight recall latency < 50ms (semantic memory query). Client matrix lookup latency < 1ms.

---

## Phase 33 — Design Token Pipeline Overhaul (Figma → Email HTML)

> Fix the broken Figma design token extraction, mapping, and HTML conversion pipeline. The current system silently drops opacity, gradients, spacing, line-height, and dark mode tokens; misidentifies colors via fragile heuristics; ignores auto-layout direction; produces broken multi-column layouts; and doesn't support Figma's modern Variables API. This phase rebuilds the pipeline bottom-up: accurate extraction, email-safe token transforms, layout-aware HTML generation, and a validation layer that catches issues before they reach the Scaffolder.

> **Dependency note:** Independent of Phase 32 (Agent Rendering Intelligence). Can be implemented in parallel. However, Phase 33 fixes are *upstream* of Phase 32 — agents receiving better tokens and HTML from this phase will produce better results. Recommended to start Phase 33 first or concurrently.

- [ ] 33.1 Figma Variables API + opacity compositing
- [ ] 33.2 Email-safe token transforms & validation layer
- [ ] 33.3 Typography pipeline: line-height, letter-spacing, font mapping
- [ ] 33.4 Spacing token pipeline & auto-layout → table mapping
- [ ] 33.5 Multi-column layout & proportional width calculation
- [ ] 33.6 Semantic HTML generation (headings, paragraphs, buttons)
- [ ] 33.7 Dark mode token extraction & gradient fallbacks
- [ ] 33.8 Design context enrichment & Scaffolder integration
- [ ] 33.9 Builder annotations for visual builder sync
- [ ] 33.10 Image asset import for design sync pipeline
- [ ] 33.11 Tests & integration verification

### 33.1 Figma Variables API + Opacity Compositing `[Backend]`
**What:** Add support for Figma's Variables API (`/v1/files/:key/variables/local` and `/v1/files/:key/variables/published`) as the primary token extraction source, falling back to the legacy Styles API for older files. Implement opacity compositing that flattens fill opacity × layer opacity into final hex values. Fix gradient and multi-fill handling to extract the topmost visible solid fill with a fallback midpoint color for linear gradients. Stop mixing stroke colors into the fill palette.
**Why:** The current pipeline uses only the legacy Styles endpoint (`/v1/files/{key}/styles`). Figma's Variables API — GA since late 2023 — is now the default way designers define tokens. Files using Variables (which is the majority of modern Figma files) extract **zero tokens** from the styles endpoint. Additionally, `_rgba_to_hex()` discards the alpha channel entirely, node-level `opacity` is never read, gradients silently vanish, and stroke colors pollute the palette. A semi-transparent blue overlay on white currently extracts as solid blue; a gradient hero section extracts nothing.
**Implementation:**
- Extend `FigmaDesignSyncService` in `app/design_sync/figma/service.py`:
  - Add `_fetch_variables()` method:
    - Call `GET /v1/files/{file_key}/variables/local` (returns variable collections, modes, values)
    - Call `GET /v1/files/{file_key}/variables/published` (returns published library variables)
    - Handle 403 (Variables API requires paid plan) — graceful fallback to Styles API
    - Parse variable collections into groups: "Primitives", "Semantic", "Component" (by collection name)
    - Extract modes: light/dark/brand variants from collection modes
    - Resolve aliases: `{color.brand.primary}` → walk reference chain to literal value (detect circular refs, max depth 10)
  - Update `sync_tokens_and_structure()` to try Variables API first, fall back to Styles:
    ```
    try: variables = await _fetch_variables(file_ref, access_token)
    except (SyncFailedError, httpx.HTTPStatusError): variables = None
    if variables: colors, typography = _parse_variables(variables)
    else: colors = _parse_colors(file_data, styles_data)  # existing path
    ```
  - Add `_rgba_to_hex_with_opacity()`:
    - Accept `r, g, b, a` (fill) + `node_opacity` (layer) as parameters
    - Compute effective alpha: `fill_alpha * node_opacity`
    - If effective alpha < 1.0, composite against assumed background (white `#FFFFFF` default, configurable):
      `final_r = round(r * eff_alpha + bg_r * (1 - eff_alpha))`
    - Return hex string of composited color
    - Keep existing `_rgba_to_hex()` as fast path for fully opaque colors
  - Fix `_walk_for_colors()`:
    - Read `node.get("opacity", 1.0)` and pass to `_rgba_to_hex_with_opacity()`
    - For nodes with multiple fills: iterate fills top-to-bottom (last in array = topmost), take the first visible (`visible != false`) solid fill
    - For `GRADIENT_LINEAR` fills: extract the two endpoint colors, compute midpoint hex, add with name suffix " (gradient midpoint)"
    - Separate strokes from fills: add strokes to a separate `stroke_colors` list (not mixed into `colors`). Expose `stroke_colors` on `ExtractedTokens` as optional field but don't feed them into `convert_colors_to_palette()`
  - Fix `_parse_node()` fill extraction (lines 560-576):
    - Read node-level `opacity` and composite with fill opacity
    - Iterate fills top-to-bottom instead of breaking on first match
    - Skip fills with `visible: false`
- Update `ExtractedTokens` in `app/design_sync/protocol.py`:
  - Add optional `variables_source: bool = False` field to indicate extraction source (Variables vs Styles)
  - Add optional `modes: dict[str, str] | None = None` to carry mode names (e.g., `{"light": "mode_id_1", "dark": "mode_id_2"}`)
  - Add optional `stroke_colors: list[ExtractedColor] = field(default_factory=list)` to keep strokes separate
- Add `ExtractedVariable` dataclass:
  ```python
  @dataclass(frozen=True)
  class ExtractedVariable:
      name: str
      collection: str
      type: str  # "COLOR", "FLOAT", "STRING", "BOOLEAN"
      values_by_mode: dict[str, Any]  # mode_name → resolved value
      is_alias: bool = False
      alias_path: str | None = None  # e.g., "color/brand/primary"
  ```
**Security:** Figma API calls use existing encrypted PAT from `DesignConnection.access_token`. No new secrets. Variables API response contains design token values only — no PII. Alias resolution has max-depth guard (10) to prevent infinite loops.
**Verify:** Figma file using Variables API → tokens extracted with correct hex values. Semi-transparent fill (opacity 0.5 blue on white) → extracts as `#8080FF` (composited), not `#0000FF`. Gradient fill → midpoint color extracted with "(gradient midpoint)" suffix. Stroke colors → not present in `convert_colors_to_palette()` output. Node with layer opacity 0.5 + fill opacity 0.5 → effective opacity 0.25 applied. File without Variables (legacy) → falls back to Styles path, existing tests pass. `make test` passes. `make types` passes.

### 33.2 Email-Safe Token Transforms & Validation Layer `[Backend]`
**What:** Add a token validation and transformation layer between extraction (33.1) and consumption (converter, Scaffolder, design system). Validate that all extracted tokens meet email-safe requirements: colors are 6-digit hex (no rgba, no CSS custom properties), sizes are in px (no rem/em/%), font families include fallback stacks, and no unresolved aliases remain. Transform non-conforming values to email-safe equivalents. Reject invalid tokens with descriptive errors.
**Why:** Currently there is zero validation between extraction and conversion. An empty font family becomes `", Arial, Helvetica, sans-serif"` in the output. A color extracted as `rgba(0,0,0,0.5)` (if the pipeline were extended) would pass through verbatim, breaking email clients. There's no way to detect that tokens are incomplete before the Scaffolder generates HTML with missing values. A validation layer catches these issues early and ensures every downstream consumer receives clean, email-safe values.
**Implementation:**
- Create `app/design_sync/token_transforms.py`:
  - `validate_and_transform(tokens: ExtractedTokens) -> tuple[ExtractedTokens, list[TokenWarning]]`:
    - Color validation:
      - Verify hex format matches `#[0-9A-Fa-f]{6}` — reject 3-digit shorthand (expand to 6), reject named colors (map `"red"` → `"#FF0000"` via lookup table of CSS named colors)
      - Reject `rgba()`, `hsl()`, `oklch()` format strings — convert to hex via utility
      - Clamp opacity to 0.0-1.0 range
      - Warn on fully transparent colors (opacity < 0.01)
    - Typography validation:
      - Verify `family` is non-empty string — warn and default to `"Arial"` if empty
      - Verify `size` > 0 and < 200 (sanity bounds) — warn on unreasonable sizes
      - Verify `weight` is valid CSS weight string (100-900 or "normal"/"bold") — map numeric strings to nearest valid weight
      - Verify `line_height` > 0 — if unitless ratio (< 5.0), multiply by font size to get px value
      - Convert any `em` values to px using font size as base
    - Spacing validation:
      - Verify `value` > 0 and < 500 (sanity bounds)
      - Verify no negative spacing values
    - Cross-token validation:
      - At least 1 color extracted — warn (not error) if zero
      - At least 1 typography style extracted — warn if zero
      - No duplicate token names within same type
  - `TokenWarning` dataclass: `(level: "info" | "warning" | "error", field: str, message: str, original_value: str | None, fixed_value: str | None)`
  - CSS named color map: 147 CSS named colors → hex (from CSS Color Level 4 spec)
- Integrate into `DesignSyncService.sync_connection()` and `DesignImportService.run_conversion()`:
  - Call `validate_and_transform()` immediately after token extraction
  - Store warnings in `DesignSyncSnapshot.structure_json["token_warnings"]`
  - Log warnings at appropriate levels
  - Surface warnings in API response via `DesignTokensResponse.warnings` field
- Add `warnings: list[str] | None` to `DesignTokensResponse` in `app/design_sync/schemas.py`
**Security:** Pure data validation. No I/O, no user input in transform logic. Named color map is a static dict.
**Verify:** Empty font family → warning + replaced with "Arial". 3-digit hex `#F00` → expanded to `#FF0000`. Named color "red" → `#FF0000`. Unitless line-height `1.5` with font size `16px` → `24px`. Size of `-5` → error warning. Zero colors extracted → warning in response. Existing extraction tests still pass. `make test` passes.

### 33.3 Typography Pipeline: Line-Height, Letter-Spacing, Font Mapping `[Backend]`
**What:** Fix the typography pipeline to preserve line-height and letter-spacing through the entire extraction → design system → HTML path. Add a configurable web-font → email-safe-font mapping table. Map Figma font weights to email-safe values (400/700). Extract text-transform and text-decoration from Figma nodes. Update the `Typography` model to carry these properties.
**Why:** Currently: (1) `ExtractedTypography.line_height` is extracted from Figma but discarded by `convert_typography()` — the `Typography` model has no `line_height` field. (2) Letter-spacing is extracted at the node level but not in `ExtractedTypography`. (3) The `_font_stack()` function keeps web fonts as the primary font (e.g., `"Inter, Arial, Helvetica, sans-serif"`) — Inter won't render in any email client except Apple Mail with `@font-face`. (4) Font weights like `300` and `500` pass through verbatim — system fonts only support `normal` (400) and `bold` (700). (5) Figma's `textCase` (UPPER/LOWER/TITLE) and `textDecoration` are never read. Uppercase headings in the design render as mixed-case.
**Implementation:**
- Update `ExtractedTypography` in `app/design_sync/protocol.py`:
  - Add `letter_spacing: float | None = None` (px value)
  - Add `text_transform: str | None = None` (uppercase/lowercase/capitalize/none)
  - Add `text_decoration: str | None = None` (underline/line-through/none)
- Update `_parse_typography()` and `_walk_for_typography()` in `app/design_sync/figma/service.py`:
  - Extract `letterSpacing` from Figma style dict → store in `ExtractedTypography.letter_spacing`
  - Extract `textCase` → map: `UPPER` → `"uppercase"`, `LOWER` → `"lowercase"`, `TITLE` → `"capitalize"`, else `None`
  - Extract `textDecoration` → map: `UNDERLINE` → `"underline"`, `STRIKETHROUGH` → `"line-through"`, else `None`
- Update `Typography` in `app/projects/design_system.py`:
  - Add `heading_line_height: str | None = None` (e.g., `"36px"`)
  - Add `body_line_height: str | None = None` (e.g., `"24px"`)
  - Add `heading_letter_spacing: str | None = None` (e.g., `"-0.5px"`)
  - Add `body_letter_spacing: str | None = None` (e.g., `"0px"`)
  - Add `heading_text_transform: str | None = None`
- Update `convert_typography()` in `app/design_sync/converter.py`:
  - Map line-height from heading/body styles to `Typography` fields (convert to px string)
  - Map letter-spacing similarly
  - Map text-transform from heading style
  - Add web-font → email-safe font mapping table:
    ```python
    _WEB_FONT_MAP: dict[str, str] = {
        "Inter": "Arial",
        "Roboto": "Arial",
        "Open Sans": "Arial",
        "Lato": "Arial",
        "Montserrat": "Arial",
        "Poppins": "Arial",
        "Nunito": "Arial",
        "Raleway": "Arial",
        "Source Sans Pro": "Arial",
        "Noto Sans": "Arial",
        "Work Sans": "Arial",
        "DM Sans": "Arial",
        "Playfair Display": "Georgia",
        "Merriweather": "Georgia",
        "Lora": "Georgia",
        "PT Serif": "Georgia",
        "Noto Serif": "Georgia",
        "Source Serif Pro": "Georgia",
        "Libre Baskerville": "Georgia",
        "Roboto Slab": "Georgia",
        "Roboto Mono": "Courier New",
        "Source Code Pro": "Courier New",
        "Fira Code": "Courier New",
        "JetBrains Mono": "Courier New",
        "Space Mono": "Courier New",
    }
    ```
  - Update `_font_stack()` to use the mapping: look up `family_clean` in `_WEB_FONT_MAP`, use mapped font as primary, original as progressive enhancement: `f"{family_clean}, {mapped}, {generic_fallback}"`
  - Map font weight: `int(weight)` → `"bold"` if ≥ 500, `"normal"` if < 500
- Update `node_to_email_html()` in `app/design_sync/converter.py`:
  - When rendering TEXT nodes: include `line-height:{value}px;` if available from node or props
  - Include `letter-spacing:{value}px;` if non-zero
  - Include `text-transform:{value};` if set
  - Include `text-decoration:{value};` if set
  - Use mapped font weight (`normal`/`bold`) instead of raw numeric weight
**Security:** Static mapping table. No user input processing changes.
**Verify:** Figma TEXT node with `Inter` font → HTML has `font-family:Inter, Arial, Arial, Helvetica, sans-serif`. Font weight `300` → `font-weight:normal`. Font weight `600` → `font-weight:bold`. Line-height `28.8` → `line-height:29px` in HTML. Letter-spacing `0.5` → `letter-spacing:1px` in HTML (rounded). Text with `textCase: UPPER` → `text-transform:uppercase` in HTML. `Typography` model populated with `heading_line_height`, `body_line_height`. Existing typography tests still pass. `make test` passes. `make types` passes.

### 33.4 Spacing Token Pipeline & Auto-Layout → Table Mapping `[Backend]`
**What:** Wire spacing tokens through the full pipeline: extraction → design system → HTML conversion. Map Figma auto-layout `itemSpacing` to spacer `<tr>` rows (vertical) or cell padding (horizontal). Apply `padding_top/right/bottom/left` from `DesignNode` directly in `node_to_email_html()` instead of relying on the `_NodeProps` indirection that currently drops padding. Pass spacing tokens to the Scaffolder via the design context.
**Why:** Currently: (1) `ExtractedSpacing` tokens are extracted from Figma but never consumed — there's no `convert_spacing()` function and they're absent from the design context sent to the Scaffolder. (2) `node_to_email_html()` reads padding from `props_map` but `_build_props_map_from_nodes()` only populates `bg_color`, silently discarding padding. (3) `item_spacing` from auto-layout is stored on `DesignNode` but never generates spacer rows or cell padding. The result: every Figma design's carefully crafted spacing is completely lost in the converted HTML.
**Implementation:**
- Create `convert_spacing()` in `app/design_sync/converter.py`:
  - Accept `list[ExtractedSpacing]`, return a spacing scale dict: `dict[str, float]` mapping names to px values
  - Detect common patterns: 4/8/12/16/24/32/48 → standard spacing scale
  - Name normalization: `spacing-8` → `xs`, `spacing-16` → `sm`, `spacing-24` → `md`, `spacing-32` → `lg`, `spacing-48` → `xl` (if values align to multiples of 4 or 8)
- Update `node_to_email_html()` in `app/design_sync/converter.py`:
  - Read padding directly from `DesignNode` fields (not just `props_map`):
    ```python
    pad_top = node.padding_top or (props.padding_top if props else 0)
    pad_right = node.padding_right or (props.padding_right if props else 0)
    pad_bottom = node.padding_bottom or (props.padding_bottom if props else 0)
    pad_left = node.padding_left or (props.padding_left if props else 0)
    ```
  - Apply padding as inline style on the wrapping `<table>` or on inner `<td>` elements
  - Read `node.layout_mode` to determine row grouping strategy:
    - `HORIZONTAL` → children become cells in a single `<tr>` (side by side)
    - `VERTICAL` → children each get their own `<tr>` (stacked)
    - `None` (no auto-layout) → fall back to existing `_group_into_rows()` by y-position
  - Apply `item_spacing`:
    - Vertical layout: insert spacer `<tr><td style="height:{item_spacing}px;font-size:1px;line-height:1px;">&nbsp;</td></tr>` between child rows
    - Horizontal layout: add `padding-left:{item_spacing}px` on all cells except the first
  - Apply `counter_axis_spacing` as padding on the cross-axis direction
- Update `_build_props_map_from_nodes()` in `app/design_sync/converter_service.py`:
  - Populate padding, font_family, font_size, font_weight, and layout_direction from `DesignNode` fields (currently only `bg_color` is set)
- Update `_build_design_context()` in `app/design_sync/import_service.py`:
  - Add `"spacing"` key to `design_tokens`:
    ```python
    "spacing": [
        {"name": s.name, "value": s.value} for s in tokens.spacing
    ]
    ```
  - Include `spacing_map` from layout analysis in the design context
**Security:** No new input paths. Spacing values are numeric, already validated in 33.2.
**Verify:** Figma frame with `paddingTop: 24, paddingLeft: 16` → HTML `<table>` has `style="padding:24px 0px 0px 16px"`. Vertical auto-layout with `itemSpacing: 12` → spacer `<tr>` rows with `height:12px` between children. Horizontal auto-layout with `itemSpacing: 8` → cells have `padding-left:8px` (except first). Spacing tokens appear in Scaffolder design context. `make test` passes.

### 33.5 Multi-Column Layout & Proportional Width Calculation `[Backend]`
**What:** Fix multi-column rendering so that child nodes receive proportional widths based on their Figma dimensions relative to the parent. Replace the current `width="100%"` on all nested tables with calculated widths. Use `layout_mode` from auto-layout to determine horizontal vs. vertical arrangement instead of relying solely on y-position proximity.
**Why:** Currently every nested `<table>` gets `width="100%"`. In a two-column layout (e.g., 200px + 400px in a 600px parent), both columns render at 100% width and stack vertically instead of sitting side by side. The `_group_into_rows()` function uses a 10px y-tolerance to guess which nodes are on the same row, but: (a) auto-layout nodes often lack absolute positions, (b) 11px offset splits columns into separate rows, and (c) it ignores the explicit `layoutMode: "HORIZONTAL"` that Figma provides.
**Implementation:**
- Update `node_to_email_html()` in `app/design_sync/converter.py`:
  - When rendering child nodes in a `<tr>` (horizontal row):
    - Calculate width percentage: `child_width_pct = round((child.width / parent_width) * 100)` if both widths are known
    - Apply as `width="{pct}%"` on the child `<td>` wrapper and `width="100%"` on the inner `<table>` (so the table fills its cell)
    - For unknown widths: distribute equally (`100 / len(row_children)`)%
  - When `node.layout_mode == "HORIZONTAL"`:
    - Override `_group_into_rows()` — treat ALL children as a single row regardless of y-position
    - Skip y-position sorting for this node's children
  - When `node.layout_mode == "VERTICAL"`:
    - Override `_group_into_rows()` — treat EACH child as its own row
  - Only call `_group_into_rows()` when `layout_mode` is `None` (absolute positioning)
  - Add Outlook ghost table wrapping for multi-column rows:
    ```html
    <!--[if mso]><table role="presentation" width="100%"><tr><![endif]-->
    <td width="50%" style="display:inline-block;vertical-align:top;">...</td>
    <!--[if mso]></tr></table><![endif]-->
    ```
- Update `_group_into_rows()`:
  - Increase y-tolerance from 10px to 20px (common offset in manually positioned designs)
  - Handle `y=None` nodes: if ALL children have `y=None`, return them as a single row (assume horizontal auto-layout)
  - If SOME children have y and SOME don't, group y-bearing children normally and append y-less children to the last row
- Update `DesignConverterService.convert()` in `converter_service.py`:
  - Pass `selected_nodes` to `node_to_email_html()` context so width calculation has access to parent frame dimensions
  - Make container width configurable (default 600px) based on design's `overall_width` from layout analysis
**Security:** No new input paths. Width calculations use numeric node dimensions only.
**Verify:** Two children (200px + 400px) in a 600px parent with `layoutMode: "HORIZONTAL"` → `<td width="33%">` and `<td width="67%">`. Three equal columns → `<td width="33%">` each with MSO ghost table. Vertical auto-layout → each child in its own `<tr>`. Mixed y-position nodes with >10px offset but <20px → grouped in same row. All children with `y=None` → single row. Existing single-column layouts unaffected. `make test` passes.

### 33.6 Semantic HTML Generation (Headings, Paragraphs, Buttons) `[Backend]`
**What:** Update `node_to_email_html()` to emit semantic HTML elements inside `<td>` cells: `<h1>`-`<h3>` for headings, `<p>` for body text, and styled `<a>` tags for button components. Use font size relative to the design's body size to determine heading level. Recognize COMPONENT/INSTANCE nodes named as buttons and convert to bulletproof `<a>` buttons with VML fallback.
**Why:** Currently all text becomes a bare `<td>` tag regardless of semantic role. This violates the codebase's own email HTML rules ("Use `<h1>`-`<h6>` with inline styles inside `<td>` cells" and "Use `<p style='margin:0 0 10px 0;'>` inside `<td>` cells"). Screen readers can't distinguish headings from body text. Button components (FRAME/COMPONENT with a single short TEXT child) render as `<table>` wrappers instead of clickable `<a>` elements.
**Implementation:**
- Update TEXT node rendering in `node_to_email_html()`:
  - Determine semantic role from font size + design context:
    - `font_size >= body_size * 2.0` → `<h1>` (or within 80% of largest font in parent)
    - `font_size >= body_size * 1.5` → `<h2>`
    - `font_size >= body_size * 1.2` → `<h3>`
    - Otherwise → `<p>` (not bare text in `<td>`)
  - Body size: determined from `convert_typography()` result or default 16px
  - Wrap semantic element inside the `<td>`:
    ```html
    <td>
      <h1 style="margin:0;font-family:...;font-size:...;font-weight:...;color:...;line-height:...;">
        Heading Text
      </h1>
    </td>
    ```
  - `<p>` tags get `style="margin:0 0 10px 0;"` per codebase convention
  - Multi-line TEXT nodes (containing `\n`): split into multiple `<p>` tags
- Add button detection and rendering:
  - Detect button nodes: COMPONENT/INSTANCE with name containing "button"/"btn"/"cta" AND a single TEXT child ≤30 chars AND height ≤80px (reuse logic from `layout_analyzer._walk_for_buttons`)
  - Render as bulletproof button:
    ```html
    <td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="border-radius:4px;background-color:{fill_color};">
            <a href="#" style="display:inline-block;padding:12px 24px;font-family:...;font-size:...;color:{text_color};text-decoration:none;">
              {button_text}
            </a>
          </td>
        </tr>
      </table>
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" style="width:{width}px;height:{height}px;" arcsize="8%" fillcolor="{fill_color}" stroke="f">
        <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
          <center style="font-family:Arial,sans-serif;font-size:{font_size}px;color:{text_color};">{button_text}</center>
        </v:textbox>
      </v:roundrect>
      <![endif]-->
    </td>
    ```
  - Extract button dimensions from node.width/height, bg color from node.fill_color, text color from child TEXT node
- Pass body font size as parameter to `node_to_email_html()` for heading level calculation
**Security:** HTML content is escaped via `html.escape()` (already in place). Button `href="#"` is a placeholder — no user-controlled URLs in conversion output. VML attributes use escaped values.
**Verify:** TEXT node with font-size 32px (body 16px) → `<h1>` inside `<td>`. TEXT node with font-size 16px → `<p style="margin:0 0 10px 0;">` inside `<td>`. COMPONENT named "CTA Button" with "Shop Now" text → bulletproof `<a>` button with VML fallback. Multi-line text → multiple `<p>` tags. Existing conversion output still has valid email HTML structure. `make test` passes.

### 33.7 Dark Mode Token Extraction & Gradient Fallbacks `[Backend]`
**What:** Extract dark mode color variants from Figma Variables API modes. When a variable collection has a "Dark" mode, extract parallel token sets for light and dark. Generate `prefers-color-scheme: dark` CSS overrides and `[data-ogsc]` / `[data-ogsb]` attribute selectors for Outlook dark mode. Add gradient linear fallback support: emit CSS `background: linear-gradient(...)` with a solid `bgcolor` fallback for Outlook.
**Why:** Currently the pipeline extracts zero dark mode tokens. The Dark Mode agent downstream must guess dark colors algorithmically — often producing poor contrast or off-brand colors. Figma Variables natively support light/dark modes, but the extraction pipeline ignores mode data entirely. Additionally, gradient backgrounds are silently dropped (33.1 extracts a midpoint color, but the actual gradient information is lost). Many modern email designs use subtle gradients in hero sections.
**Implementation:**
- Extend `ExtractedTokens` in `app/design_sync/protocol.py`:
  - Add `dark_colors: list[ExtractedColor] = field(default_factory=list)` — dark mode counterparts
  - Add `gradients: list[ExtractedGradient] = field(default_factory=list)`
- Add `ExtractedGradient` dataclass:
  ```python
  @dataclass(frozen=True)
  class ExtractedGradient:
      name: str
      type: str  # "linear" | "radial"
      angle: float  # degrees (linear only)
      stops: list[tuple[str, float]]  # (hex_color, position 0.0-1.0)
      fallback_hex: str  # midpoint solid fallback for Outlook
  ```
- Update `_fetch_variables()` in `app/design_sync/figma/service.py`:
  - When parsing variable collections: detect modes with names containing "dark", "night", "dim" (case-insensitive)
  - For each color variable: extract both default mode value and dark mode value
  - Create parallel `ExtractedColor` lists: light mode → `colors`, dark mode → `dark_colors`
  - Match by variable name: `dark_colors[i].name` == `colors[i].name` for easy pairing
- Update `_walk_for_colors()`:
  - For `GRADIENT_LINEAR` fills:
    - Extract `gradientHandlePositions` (angle calculation) and `gradientStops` (colors + positions)
    - Compute angle from handle positions: `atan2(handle2.y - handle1.y, handle2.x - handle1.x) * 180 / pi`
    - Build `ExtractedGradient` with stops and fallback midpoint hex
- Update `converter.py`:
  - Add `_gradient_to_css()`: convert `ExtractedGradient` → `background: linear-gradient({angle}deg, {stop1} {pos1}%, {stop2} {pos2}%, ...)`
  - When a node's fill is a gradient: emit both `bgcolor="{fallback_hex}"` for Outlook and `style="background:{gradient_css};"` for modern clients
- Update `converter_service.py`:
  - Add `dark_mode_style_block()`: generate `@media (prefers-color-scheme: dark)` CSS rules mapping light → dark colors
  - Add `[data-ogsc]` and `[data-ogsb]` selectors for Outlook.com dark mode
  - Include dark mode CSS in the `<style>` block of `EMAIL_SKELETON`
- Update `_build_design_context()` in `import_service.py`:
  - Include `dark_colors` in design context when available
  - Include `gradients` list
**Security:** No new input paths. Gradient angle clamped to 0-360. Color hex values validated by 33.2 transform layer.
**Verify:** Figma file with "Light"/"Dark" variable modes → both `colors` and `dark_colors` populated. Dark mode CSS block generated with `prefers-color-scheme: dark` rules. Gradient fill → `background: linear-gradient(...)` in HTML with `bgcolor` fallback. Gradient with 3 stops → all stops present in CSS. No dark mode in Figma → `dark_colors` empty, no dark CSS generated. `make test` passes.

### 33.8 Design Context Enrichment & Scaffolder Integration `[Backend + Frontend]`
**What:** Ensure the full enriched token set (colors, typography with line-height/letter-spacing, spacing, dark mode colors, gradients, token warnings) flows through the design context to the Scaffolder and is visible in the frontend token viewer. Fix the `_layout_to_design_nodes()` reconstruction to preserve typography, padding, and text content. Add token diff display on the design sync page showing what changed between syncs.
**Why:** Currently: (1) `_build_design_context()` drops line_height and spacing from the dict sent to the Scaffolder. (2) `_layout_to_design_nodes()` builds hollow `DesignNode` objects that lose all typography, padding, and text content. (3) The frontend `DesignTokensView` only shows colors, typography families, and spacing values — no line-height, letter-spacing, dark mode variants, or gradient previews. (4) Users can't see what changed between syncs — they must compare manually.
**Implementation:**
- Update `_build_design_context()` in `app/design_sync/import_service.py`:
  - Add `line_height` and `letter_spacing` to typography entries
  - Add `spacing` array from `ExtractedSpacing` tokens
  - Add `dark_colors` array when available
  - Add `gradients` array when available
  - Add `token_warnings` list from validation layer (33.2)
- Fix `_layout_to_design_nodes()` in `app/design_sync/import_service.py`:
  - Preserve `text_content`, `font_family`, `font_size`, `font_weight`, `line_height_px`, `letter_spacing_px` from `TextBlock` data in layout analysis
  - Preserve `padding_top/right/bottom/left` and `item_spacing` from section data
  - Preserve `fill_color` and `text_color` where available
  - Create TEXT-type child nodes from `section.texts` with full typography data
- Update `DesignTokensResponse` schema in `app/design_sync/schemas.py`:
  - Add `dark_colors: list[ColorResponse] | None`
  - Add `gradients: list[GradientResponse] | None`
  - Add `warnings: list[str] | None`
  - Add `typography[].line_height`, `typography[].letter_spacing`, `typography[].text_transform`
- Update frontend `design-tokens-view.tsx`:
  - Show dark mode colors alongside light mode colors (side-by-side swatches)
  - Show gradient previews (CSS gradient rendered in a swatch div)
  - Show line-height and letter-spacing in typography cards
  - Show token warnings as dismissible alerts
- Add token diff logic:
  - Backend: `DesignSyncService.get_token_diff(connection_id)` → compares current snapshot tokens vs previous snapshot
  - Return: `{added: [...], removed: [...], changed: [{name, old_value, new_value}]}`
  - Frontend: show diff summary after sync with color-coded added/removed/changed badges
**Security:** Token warnings are system-generated strings, not user input. No XSS risk in frontend display (React auto-escapes).
**Verify:** Scaffolder receives typography with line_height and letter_spacing in design context. `_layout_to_design_nodes()` produces nodes with font_family, font_size, text_content populated. Frontend shows dark mode swatches when available. Token diff after re-sync shows changed colors. Token warnings visible in UI. `make check-fe` passes. `make test` passes.

### 33.9 Builder Annotations for Visual Builder Sync `[Backend + Frontend]`
**What:** Add `data-section-id`, `data-component-name`, and `data-slot-name` attributes to the HTML output of `node_to_email_html()` and `DesignConverterService.convert()`. These annotations are what the frontend builder sync (`ast-mapper.ts` → `visual-builder-panel.tsx`) uses to populate slot definitions, render actual content instead of placeholders, and enable drag-and-drop editing of imported designs.
**Why:** Phase 31 fixed slot definition inference for the HTML upload/paste path (via `inferSlotDefinitions()` fallback in `visual-builder-panel.tsx`). But the Figma design sync pipeline produces HTML without any builder annotations. The frontend sync engine's Strategy 1 (annotated HTML with `data-section-id`) never matches — it falls through to Strategy 2 (structural content-root analysis), which produces `SectionNode` objects with `componentId=0` and empty `slotValues`. The `sectionNodeToBuilderSection()` function then calls `inferSlotDefinitions()` on the HTML fragment, but since the converter emits bare `<td>` elements (no `data-slot-name` attributes), inference returns `[]` → slot fills are never applied → the visual builder shows "Body content goes here" placeholders instead of the actual Figma content. The fix is to annotate the converter output at generation time, so the builder sync path works end-to-end without relying on fallback inference.
**Implementation:**
- Update `node_to_email_html()` in `app/design_sync/converter.py`:
  - Add `data-section-id="section_{idx}"` on each top-level frame's wrapping `<tr>` element (the `<tr><td>` wrapper in `converter_service.py` line 111)
  - Add `data-component-name="{node.name}"` on the section's outer `<table>` element (using the Figma frame/component name, sanitized via `html.escape()`)
  - Add `data-slot-name="{slot_id}"` on content-bearing elements inside sections:
    - TEXT nodes rendered as `<h1>`/`<h2>`/`<h3>` (from 33.6) → `data-slot-name="heading"` (or `heading_2`, `heading_3` for subsequent headings in the same section)
    - TEXT nodes rendered as `<p>` → `data-slot-name="body"` (or `body_2`, `body_3` for subsequent paragraphs)
    - IMAGE nodes → `data-slot-name="image"` (or `image_2` for subsequent images)
    - Button `<a>` elements (from 33.6) → `data-slot-name="cta"` (or `cta_2` for subsequent buttons)
  - Slot ID generation: maintain a per-section counter dict `{slot_type: count}` to generate unique IDs like `heading`, `body`, `body_2`, `image`, `cta`
  - Pass section index as parameter to `node_to_email_html()` for `data-section-id` generation
- Update `DesignConverterService.convert()` in `converter_service.py`:
  - Pass frame index to `node_to_email_html()` so section IDs are sequential
  - Add `data-section-id` to the `<tr><td>` wrapper:
    ```python
    section_parts.append(
        f'<tr data-section-id="section_{idx}"><td>\n{section_html}\n</td></tr>'
    )
    ```
- Frontend compatibility verification:
  - `ast-mapper.ts` Strategy 1 should now match on `data-section-id` attributes → produces annotated `SectionNode[]`
  - `sectionNodeToBuilderSection()` receives `slotValues` populated from `data-slot-name` elements → slot fills applied → actual content visible in preview
  - `inferSlotDefinitions()` fallback still works for HTML without annotations (backward compatible)
  - `stripAnnotations()` in `section-markers.ts` already handles `data-section-id`, `data-slot-name`, `data-component-name` removal on export (no changes needed)
**Security:** Annotation attributes use `html.escape()` for all values derived from Figma node names. `data-*` attributes are inert HTML — no script execution risk. `stripAnnotations()` removes all builder metadata before export, so annotations never reach the final email output.
**Verify:** Import Figma design via design sync → converter output contains `data-section-id="section_0"`, `data-section-id="section_1"`, etc. on `<tr>` elements. Content elements have `data-slot-name` attributes matching their semantic role. Visual builder preview shows actual Figma content (headings, body text, images) instead of placeholders. `ast-mapper.ts` Strategy 1 matches annotated sections. `stripAnnotations()` removes all `data-*` builder attributes on export. Existing upload/paste path still works (annotations are additive). `make test` passes. `make check-fe` passes.

### 33.10 Image Asset Import for Design Sync Pipeline `[Backend]`
**What:** Wire the existing `ImageImporter` (built in Phase 31.7 for the upload pipeline) into the design sync conversion pipeline. After `DesignConverterService.convert()` produces the HTML skeleton with `<img src="" ...>` placeholders, download the actual images from Figma's image export API, store them locally, and rewrite the `src` attributes to hub-hosted URLs. Preserve image dimensions from both Figma node data and downloaded image metadata.
**Why:** Currently `node_to_email_html()` renders IMAGE nodes as `<img src="" alt="..." width="..." height="..." />` — the `src` is always empty. The Figma API provides image export endpoints (`/v1/images/{file_key}?ids={node_ids}&format=png`) that return temporary CDN URLs for rendered images. Phase 31.7 built a complete `ImageImporter` class with SSRF prevention, magic byte validation, dimension extraction via Pillow, content-hash deduplication, and semaphore-limited concurrent downloads — but it's only wired into the upload pipeline (`TemplateUploadService`). The design sync pipeline needs the same capability to produce complete, renderable HTML from Figma imports.
**Implementation:**
- Update `DesignConverterService` in `converter_service.py`:
  - Add `async convert_with_images()` method that wraps `convert()` + image import:
    - Call `convert()` to produce the HTML skeleton (existing flow)
    - Collect all IMAGE node IDs from the design tree (the `data-node-id` attributes already emitted by `node_to_email_html()` on `<img>` tags)
    - Call `provider.export_images(file_ref, access_token, node_ids, format="png", scale=2.0)` to get temporary Figma CDN URLs
    - Build a mapping: `{node_id: figma_cdn_url}`
    - Rewrite `<img src="" data-node-id="{node_id}"` → `<img src="{figma_cdn_url}" data-node-id="{node_id}"` in the HTML
    - Pass the HTML through `ImageImporter.import_images(html, upload_id=import_id)` to download, validate, store, and rewrite URLs to hub-hosted paths
    - Return `ConversionResult` with the image-complete HTML + `ImportedImage` list
  - Keep `convert()` synchronous and image-free (for tests and cases where image import isn't needed)
- Update `DesignImportService.run_conversion()` in `import_service.py`:
  - Call `convert_with_images()` instead of `convert()` when `generate_html=True`
  - Pass `import_id` for image storage path (same pattern as upload pipeline)
  - Store `ImportedImage` metadata in the import record's `structure_json["images"]`
- Reuse `ImageImporter` from `app/templates/upload/image_importer.py`:
  - No modifications needed — the class is already generic (accepts HTML string, returns modified HTML + image list)
  - Configuration via `settings.templates.import_images`, `max_image_download_size`, etc. (already in place from Phase 31.7)
- Serve imported images via the existing asset endpoint:
  - `GET /api/v1/templates/upload/assets/{upload_id}/{filename}` already serves images with path traversal protection and CSP headers
  - For design sync imports, use `import_id` as the storage directory key (same pattern, different ID namespace)
  - Add a parallel endpoint or alias: `GET /api/v1/design-sync/imports/{import_id}/assets/{filename}` that delegates to the same `DesignAssetService`
- Update `<img>` rendering in `node_to_email_html()`:
  - Preserve `data-node-id` attribute (already present) — used by the image rewriting step to match Figma export URLs to elements
  - Use Figma node dimensions (`width`, `height`) for HTML attributes, but update with actual downloaded dimensions if they differ (Pillow measurement from `ImageImporter`)
  - Set `style="display:block;border:0;width:100%;max-width:{width}px;height:auto;"` for responsive images
**Security:** Figma CDN URLs are temporary (expire after ~30 minutes) — images are downloaded and stored locally immediately. `ImageImporter` already validates: HTTP/HTTPS only (no `file://`), magic byte verification (PNG/JPEG/GIF/WebP/SVG), 5MB size limit per image, 50 images per import. Asset serving endpoint has path traversal prevention via `.resolve()` + `is_relative_to()`. No user-controlled URLs — all URLs come from Figma's API response.
**Verify:** Import Figma design with 3 images → converter fetches Figma export URLs → `ImageImporter` downloads and stores locally → HTML `src` attributes point to hub-hosted URLs. Images render correctly in builder preview. Image dimensions from Figma preserved in HTML attributes. Figma export failure (CDN timeout) → graceful fallback, `src` stays as Figma CDN URL (temporary but functional). Import without images → no errors (empty image list). `ImageImporter` deduplication: same image in two sections → downloaded once. Asset serving endpoint returns correct content-type and CSP headers. `make test` passes.

### 33.11 Tests & Integration Verification `[Full-Stack]`
**What:** Comprehensive tests verifying the full design token pipeline from Figma API response through to email HTML output: Variables API parsing, opacity compositing, token validation, typography transforms, spacing application, multi-column layout, semantic HTML, dark mode extraction, and Scaffolder integration.
**Implementation:**
- **Variables API extraction tests** — `app/design_sync/figma/tests/test_variables_api.py`:
  - Mock Variables API response with color, float, and string variables → `ExtractedTokens` with `variables_source=True`
  - Variable with alias `{color.brand.primary}` → resolved to literal hex value
  - Circular alias `A → B → A` → raises `SyncFailedError("Circular variable alias")`
  - Collection with "Light" and "Dark" modes → separate `colors` and `dark_colors` lists
  - 403 response (no paid plan) → graceful fallback to Styles API path
  - Existing Styles API tests still pass (regression)
- **Opacity compositing tests** — `app/design_sync/figma/tests/test_opacity.py`:
  - `_rgba_to_hex_with_opacity(0, 0, 1.0, a=0.5, node_opacity=1.0)` → `#8080FF` (blue composited on white)
  - `_rgba_to_hex_with_opacity(0, 0, 1.0, a=1.0, node_opacity=0.5)` → `#8080FF` (same via layer opacity)
  - `_rgba_to_hex_with_opacity(0, 0, 1.0, a=0.5, node_opacity=0.5)` → `#C0C0FF` (25% effective opacity)
  - Fully opaque → `_rgba_to_hex()` fast path, identical to current behavior
  - Multiple fills: top solid fill is extracted, lower fills ignored
  - Gradient fill → midpoint color extracted + `ExtractedGradient` created
  - Stroke colors → not in `tokens.colors` list
- **Token validation tests** — `app/design_sync/tests/test_token_transforms.py`:
  - Empty font family → warning + replaced with `"Arial"`
  - 3-digit hex `#F00` → expanded to `#FF0000`
  - Named color `"red"` → `#FF0000`
  - `rgba(255, 0, 0, 0.5)` string → converted to composited hex
  - Unitless line-height `1.5` with font size `16` → `24.0` (px)
  - Negative spacing `-5` → error-level warning
  - Zero colors → info-level warning
  - Valid tokens → zero warnings, pass-through unchanged
- **Typography pipeline tests** — `app/design_sync/tests/test_typography_pipeline.py`:
  - `convert_typography()` with `Inter 400 16px` → `Typography(body_font="Inter, Arial, Arial, Helvetica, sans-serif")`
  - `_font_stack("Inter")` → `"Inter, Arial, Arial, Helvetica, sans-serif"`
  - `_font_stack("Playfair Display")` → `"Playfair Display, Georgia, Georgia, Times New Roman, serif"`
  - `_font_stack("Unknown Custom Font")` → `"Unknown Custom Font, Arial, Helvetica, sans-serif"` (no mapping, default fallback)
  - Font weight `300` → `"normal"`, weight `600` → `"bold"`
  - Line-height `28.8` from Figma → `"29px"` in `Typography.heading_line_height`
  - Letter-spacing preserved through pipeline
  - Text transform `UPPER` → `"uppercase"` in output
- **Spacing and layout tests** — `app/design_sync/tests/test_spacing_layout.py`:
  - Vertical auto-layout with `itemSpacing: 12` → spacer `<tr>` rows in HTML
  - Horizontal auto-layout with `itemSpacing: 8` → `padding-left:8px` on cells (skip first)
  - Node padding `(24, 16, 24, 16)` → `style="padding:24px 16px 24px 16px"` on table
  - Spacing tokens in design context dict for Scaffolder
  - `convert_spacing()` with `[8, 16, 24, 32]` values → named scale
- **Multi-column layout tests** — `app/design_sync/tests/test_multi_column.py`:
  - Two children (200px + 400px) in 600px parent, `layoutMode: "HORIZONTAL"` → `<td width="33%">` and `<td width="67%">`
  - Three equal children → `<td width="33%">` each
  - MSO ghost table wrappers present in multi-column output
  - `layoutMode: "VERTICAL"` → each child in own `<tr>` regardless of position
  - `layoutMode: None` → fallback to `_group_into_rows()` by y-position
  - All children `y=None` → single row (assumes horizontal)
  - `_group_into_rows()` with 15px offset (> old 10px, < new 20px tolerance) → same row
- **Semantic HTML tests** — `app/design_sync/tests/test_semantic_html.py`:
  - TEXT node font-size 32px (body 16px) → `<h1>` inside `<td>`
  - TEXT node font-size 24px → `<h2>` inside `<td>`
  - TEXT node font-size 16px → `<p style="margin:0 0 10px 0;">` inside `<td>`
  - Button component → `<a>` with VML `<v:roundrect>` fallback
  - Multi-line text with `\n` → multiple `<p>` tags
  - All semantic elements have inline styles (font-family, size, weight, color)
- **Dark mode & gradient tests** — `app/design_sync/tests/test_dark_mode_gradients.py`:
  - Variables with "Dark" mode → `dark_colors` populated with matching names
  - Dark mode CSS block has `@media (prefers-color-scheme: dark)` rules
  - Dark mode CSS block has `[data-ogsc]` selectors
  - Linear gradient → `background: linear-gradient(...)` + `bgcolor` fallback
  - Gradient with 3 stops → correct CSS output
  - No dark mode → no dark CSS block (clean output)
- **Builder annotation tests** — `app/design_sync/tests/test_builder_annotations.py`:
  - Single-frame conversion → `<tr data-section-id="section_0">` on outer wrapper
  - Multi-frame conversion → sequential `data-section-id` values (`section_0`, `section_1`, `section_2`)
  - TEXT node rendered as `<h1>` → has `data-slot-name="heading"` attribute
  - Second TEXT node rendered as `<p>` in same section → has `data-slot-name="body"` (not `heading`)
  - Third TEXT node → `data-slot-name="body_2"` (counter increments)
  - IMAGE node → `data-slot-name="image"` attribute
  - Button `<a>` → `data-slot-name="cta"` attribute
  - Multiple buttons in same section → `cta`, `cta_2` (unique IDs)
  - Frame/component name → `data-component-name` attribute on section `<table>` (HTML-escaped)
  - Frame with special characters in name (`"Hero Section / v2"`) → properly escaped in attribute
  - `stripAnnotations()` removes all `data-section-id`, `data-slot-name`, `data-component-name` attributes (existing function, verify coverage)
  - Frontend `ast-mapper.ts` Strategy 1 matches annotated HTML → produces `SectionNode[]` with populated `slotValues`
  - `sectionNodeToBuilderSection()` with annotated sections → `slotDefinitions` populated from `data-slot-name` elements → preview shows actual content (not placeholders)
- **Image import for design sync tests** — `app/design_sync/tests/test_design_sync_images.py`:
  - `convert_with_images()` calls `provider.export_images()` for IMAGE node IDs → receives Figma CDN URLs
  - Figma CDN URLs rewritten into HTML `<img src="">` placeholders before `ImageImporter` processes them
  - `ImageImporter.import_images()` downloads from CDN URLs → stores locally → rewrites `src` to hub-hosted paths
  - 3 images in Figma design → 3 `ImportedImage` entries in result with correct dimensions
  - Duplicate image (same content hash) → downloaded once, reused (deduplication)
  - Figma export failure (mock 500 response) → graceful fallback, `src` retains Figma CDN URL
  - Image exceeding 5MB limit → skipped with warning, original URL preserved
  - SVG image node → validated via magic bytes, stored as `.svg`
  - Asset serving endpoint returns imported image with correct content-type header
  - `import_images=false` in config → images skipped, `src=""` preserved
  - Image dimensions from Figma node match HTML `width`/`height` attributes
  - Image dimensions updated if Pillow measurement differs from Figma node data (actual file dimensions take precedence)
- **End-to-end pipeline test** — `app/design_sync/tests/test_e2e_pipeline.py`:
  - Mock Figma file response with Variables, auto-layout, gradients, dark mode:
    - Variables API returns 6 colors (3 light, 3 dark), 2 typography styles, 4 spacing values
    - Document tree: vertical frame with header (horizontal: logo + nav), hero (gradient bg + heading + CTA button), content (two-column), footer
    - 3 IMAGE nodes (logo, hero image, content image) with mock export URLs
  - Pipeline produces:
    - Valid HTML email with `<!DOCTYPE>`, MSO conditionals, 600px container
    - Header section with proportional columns
    - Hero with gradient CSS + solid fallback + `<h1>` heading + bulletproof button
    - Two-column content with proportional `<td>` widths + MSO ghost tables
    - Dark mode `<style>` block with `prefers-color-scheme` + OGS selectors
    - All spacing from auto-layout applied (padding + spacer rows)
    - Typography with mapped email-safe fonts, line-height, letter-spacing
    - No token validation warnings (all clean)
    - Builder annotations: `data-section-id` on all section `<tr>` elements, `data-slot-name` on content elements, `data-component-name` on section tables
    - Images: all `<img src>` attributes point to hub-hosted URLs (not empty, not Figma CDN)
  - HTML validates (no unclosed tags, proper nesting)
  - Visual builder integration: annotated HTML loaded into builder → sections detected via Strategy 1 → slot fills applied → preview renders actual Figma content
**Security:** Tests only. Mock Figma API responses with synthetic data. No real PATs, no real API calls, no PII. Mock image downloads use `httpx` transport mocking — no real HTTP requests.
**Verify:** `make test` passes (all new test files). `make check` all green. `make types` passes. No regression in existing design sync tests. `make bench` shows no performance regression in conversion pipeline.

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

## Success Criteria (Phases 32–33 — Next)

| Metric | Status |
|--------|--------|
| Campaign build time | Under 1 hour (deterministic CSS pipeline) |
| Cross-client rendering defects | Near-zero + enforced QA + rendering + approval gates |
| QA checks | 17+ (enforced at export) |
| CSS pipeline latency | <500ms (single-pass sidecar) |
| Template CSS precompilation | Amortized at registration (0ms at build time) |
| CSS compatibility visibility | Full gate panel: QA + rendering + approval status |
| Email client emulators | 8 clients, 14 profiles (Gmail, Outlook, Apple Mail, Yahoo, Samsung, Thunderbird, Android Gmail, Outlook.com) |
| Rendering confidence scoring | Per-client 0–100 with breakdown + recommendations + dashboard |
| Pre-send rendering gate | Rendering + QA + approval gates in export pipeline (enforce/warn/skip) |
| Approval workflow | Full UI: request, review, decide, feedback, audit trail |
| E2E test coverage | 32+ Playwright scenarios + visual regression + 3 browsers (Chromium + Firefox + WebKit) |
| Design import paths | Figma + Penpot + brief-only + enhanced Penpot converter |
| HTML import fidelity | Pre-compiled email HTML imports with preserved centering, fonts, colors, images, and dark mode readability |
| Maizzle passthrough | Pre-compiled HTML bypasses render() — no double-inlining or structural scrambling |
| Typography token pipeline | font-weight, line-height, letter-spacing extracted + font-size/spacing applied during assembly + project design system mapping |
| Font compilation | Client-specific font stacks (Outlook mso-font-alt, Gmail web font `<link>`), project design system font mapping with diff preview |
| Image asset import | External images downloaded, re-hosted, dimensions preserved (display + intrinsic) |
| Client rendering matrix | Single authoritative YAML — all 8 client families, CSS support, dark mode, known bugs, synced with ontology |
| Agent knowledge lookup | Runtime `lookup_client_support` tool — <1ms deterministic queries, replaces static L3 duplication |
| Content agent email awareness | Client-aware preheader/subject/CTA lengths, character encoding safety, column-width-adapted copy |
| Import annotator recognition | Stripo, Bee, Mailchimp, MJML patterns recognized + ESP edge cases (AMPscript, nested Liquid, Handlebars partials) |
| Cross-agent learning | Insight bus propagates rendering discoveries between agents — within-run handoff learnings + across-run semantic memory |
| Eval-driven skill updates | Semi-automated pipeline: pass rate drop → failure cluster → skill file patch → PR for review |
| Visual QA feedback loop | Pre-Maizzle visual precheck + screenshot-attached recovery routing + post-render drift comparison |
| Figma Variables API | Modern token extraction via Variables API with Styles API fallback — zero-token files eliminated |
| Opacity compositing | Fill opacity × layer opacity flattened to final hex — semi-transparent colors render correctly |
| Token validation layer | All tokens validated before consumption: hex format, px units, non-empty fonts, no unresolved aliases |
| Web font → email mapping | 25+ web fonts mapped to email-safe system fonts — no raw web fonts in final HTML |
| Auto-layout → table mapping | Figma `layoutMode` drives HTML structure: HORIZONTAL → columns, VERTICAL → rows, with proportional widths |
| Spacing token pipeline | `itemSpacing` → spacer rows/cell padding, `padding_*` → table padding, spacing tokens in Scaffolder context |
| Multi-column proportional widths | Child widths calculated relative to parent — no more `width="100%"` on all nested tables |
| Semantic email HTML | Headings → `<h1>`-`<h3>`, body → `<p>`, buttons → bulletproof `<a>` with VML fallback |
| Dark mode token extraction | Light/dark variable modes extracted in parallel — no more algorithmic guessing |
| Gradient fallbacks | Linear gradients → CSS `linear-gradient()` + solid `bgcolor` fallback for Outlook |
| Design context enrichment | Full token set (typography + spacing + dark + gradients + warnings) flows to Scaffolder |
