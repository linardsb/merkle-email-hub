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

> Upgrade all 11 AI agents from distributed, duplicated email knowledge to a unified rendering intelligence layer: centralized client matrix, runtime knowledge lookup, cross-agent learning, content-aware rendering constraints, deeper import skills, eval-driven skill evolution, MCP integration for IDE-native agent access, skill versioning for safe automated updates, and per-client skill overlays for multi-tenant customization.

- [ ] 32.1 Centralized email client rendering matrix
- [x] ~~32.2 Content agent email rendering awareness~~ DONE
- [x] ~~32.3 Import annotator skill depth~~ DONE
- [ ] 32.4 Agent knowledge lookup tool
- [ ] 32.5 Cross-agent insight propagation
- [ ] 32.6 Eval-driven skill file updates
- [ ] 32.7 Visual QA feedback loop tightening
- [ ] 32.8 Tests & integration verification
- [ ] 32.9 MCP server exposure for agent tools
- [ ] 32.10 Skill versioning with rollback
- [ ] 32.11 Per-client skill overlays

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

### ~~32.2 Content Agent Email Rendering Awareness~~ `[Backend]` DONE
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

### ~~32.3 Import Annotator Skill Depth~~ `[Backend]` DONE
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

### 32.9 MCP Server Exposure for Agent Tools `[Backend + Integration]`
**What:** Expose all 9 production agents as MCP (Model Context Protocol) tools via a stdio-based MCP server, so coding agents (Claude Code, Cursor, Windsurf) can invoke email generation, dark mode processing, accessibility fixes, and code review directly from the IDE without going through the REST API. Package as `email-hub-mcp` binary alongside the existing FastAPI server.
**Why:** The current integration surface is REST-only — developers must use the web UI or make API calls. Coding agents like Claude Code already support MCP tool calling natively. When a developer is editing an email template in their IDE, they should be able to ask their coding agent "fix Outlook rendering" and have it call the Outlook Fixer agent directly, receiving structured results in-context. This eliminates the tab-switch to the web UI, enables agent-to-agent composition (Claude Code orchestrating email-hub agents as tools), and opens the door for community integrations. The pattern is proven: Context Hub (open-source doc platform) uses exactly this architecture — CLI + MCP server exposing search/get/annotate tools via `@modelcontextprotocol/sdk`, with Zod schema validation and structured error responses. Email-hub can follow the same pattern but expose domain-specific agent tools instead of doc retrieval.
**Implementation:**
- Create `app/mcp/server.py`:
  - Use `mcp` Python SDK (`pip install mcp`) with stdio transport
  - Redirect stdout to stderr (MCP uses stdout for JSON-RPC — all logging must go to stderr)
  - Register one tool per agent:
    ```python
    @server.tool("email_scaffold", "Generate Maizzle email HTML from a campaign brief")
    async def handle_scaffold(brief: str, brand: str | None = None,
                               output_mode: str = "html") -> ToolResult:
        service = get_scaffolder_service()
        request = ScaffolderRequest(brief=brief, brand_voice=brand, output_mode=output_mode)
        result = await service.run(request)
        return text_result({"html": result.html, "confidence": result.confidence,
                           "qa_passed": result.qa_passed, "warnings": result.warnings})

    @server.tool("email_dark_mode", "Generate dark mode styles for email HTML")
    async def handle_dark_mode(html: str, target_clients: list[str] | None = None) -> ToolResult:
        ...

    @server.tool("email_content", "Generate email copy: subject lines, CTAs, body text")
    async def handle_content(operation: str, text: str, tone: str | None = None,
                              num_alternatives: int = 3) -> ToolResult:
        ...

    @server.tool("email_outlook_fix", "Fix Outlook rendering issues in email HTML")
    async def handle_outlook_fix(html: str) -> ToolResult:
        ...

    @server.tool("email_accessibility", "Add alt text and WCAG improvements to email HTML")
    async def handle_accessibility(html: str) -> ToolResult:
        ...

    @server.tool("email_code_review", "Review email HTML for quality and compatibility issues")
    async def handle_code_review(html: str) -> ToolResult:
        ...

    @server.tool("email_personalise", "Add dynamic content blocks to email HTML")
    async def handle_personalise(html: str, esp: str | None = None) -> ToolResult:
        ...

    @server.tool("email_innovate", "Suggest structural improvements for email HTML")
    async def handle_innovate(html: str) -> ToolResult:
        ...

    @server.tool("email_knowledge", "Look up brand/product knowledge for email content")
    async def handle_knowledge(query: str, brand: str | None = None) -> ToolResult:
        ...
    ```
  - Each handler follows the pattern: validate input → build domain request → call service singleton → format structured result → return `text_result()` or `error_result()`
  - Tool parameter schemas use Pydantic models converted to JSON Schema (reuse existing `schemas.py` per agent)
- Create `app/mcp/helpers.py`:
  - `text_result(data: dict) -> ToolResult` — wraps response as MCP content block
  - `error_result(message: str) -> ToolResult` — wraps error with `isError=True`
  - `html_result(html: str, metadata: dict) -> ToolResult` — returns HTML as a separate content block for easy extraction by the calling agent
- Create `bin/email-hub-mcp` entry point:
  - Loads config, initializes services (same startup as FastAPI but without HTTP server)
  - Starts MCP server on stdio transport
  - Graceful shutdown on SIGTERM/SIGINT
- Add MCP resource: `email-hub://agents` — returns list of available agents with capabilities, model tiers, and supported operations (analogous to Context Hub's `chub://registry` resource)
- Add to `pyproject.toml`:
  - `[project.scripts]` entry: `email-hub-mcp = "app.mcp.server:main"`
  - Add `mcp` dependency
- Create `mcp-config.example.json` for Claude Code integration:
  ```json
  {
    "mcpServers": {
      "email-hub": {
        "command": "email-hub-mcp",
        "env": {
          "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
          "EMAIL_HUB_DB_URL": "${EMAIL_HUB_DB_URL}"
        }
      }
    }
  }
  ```
- Rate limiting: reuse existing `RateLimiter` from the FastAPI layer — same per-agent limits apply via MCP as via REST
- Authentication: MCP runs locally (stdio) so no API key auth needed — the user's own environment credentials are used for LLM calls
**Security:** MCP stdio transport is local-only — no network exposure. Tool inputs are validated through the same Pydantic schemas as REST endpoints (XSS sanitization, length limits, input validation all apply). No new attack surface beyond what the REST API already exposes. LLM API keys come from the user's environment, not from the MCP protocol. Tool results contain HTML output — same sanitization profile as REST responses.
**Verify:** `email-hub-mcp` starts without errors. Claude Code can discover all 9 tools via MCP handshake. Calling `email_scaffold` with a brief → returns valid HTML with confidence score. Calling `email_code_review` with HTML → returns structured review. Calling `email_content` with `operation="subject_line"` → returns alternatives list. Error cases: invalid operation → `error_result` with message. Missing required params → MCP validation error. `email-hub://agents` resource → returns agent list with capabilities. `make test` passes.

### 32.10 Skill Versioning with Rollback `[Backend]`
**What:** Add version metadata to all L3 skill file frontmatter, implement version tracking in the skill loader, and provide a rollback mechanism that can pin a project to a previous skill file version when a 32.6 eval-driven update causes a regression. Store version history in a `skill-versions.yaml` manifest per agent directory.
**Why:** Phase 32.6 introduces automated skill file patching — the eval pipeline detects failure patterns, generates patches, and opens PRs. But once merged, there's no clean rollback path beyond `git revert`. If a skill patch improves pass rate on one criterion but regresses another (common with prompt changes), the team needs to: (a) know which version of the skill file was active during a given eval run, (b) quickly revert to the prior version without touching git history, and (c) A/B test the old vs new version using the existing `skill_override.py` infrastructure. Without versioning, the 32.6 pipeline creates churn — patches get merged, regress, get reverted, get re-applied. Versioning adds the control surface that makes 32.6's automation safe to trust.
**Implementation:**
- Add version metadata to L3 skill file frontmatter:
  ```yaml
  ---
  token_cost: 1500
  priority: 2
  version: "1.2.0"
  updated: "2026-03-20"
  changelog:
    - "1.2.0: Added Samsung double-inversion workaround (eval-driven, 32.6)"
    - "1.1.0: Expanded Outlook.com data-ogsc selector examples"
    - "1.0.0: Initial release"
  ---
  ```
- Create `skill-versions.yaml` manifest per agent:
  ```yaml
  # app/ai/agents/dark_mode/skill-versions.yaml
  skills:
    client_behavior:
      current: "1.2.0"
      pinned: null  # null = use current, or "1.1.0" to pin
      versions:
        "1.2.0":
          hash: "a3f8c2d"  # git short hash of the commit that introduced this version
          date: "2026-03-20"
          source: "eval-driven"  # or "manual"
          eval_pass_rate: 0.87  # pass rate at time of introduction
        "1.1.0":
          hash: "b7e1f4a"
          date: "2026-03-01"
          source: "manual"
          eval_pass_rate: 0.82
        "1.0.0":
          hash: "c9d2e5b"
          date: "2026-01-15"
          source: "manual"
          eval_pass_rate: null
    dark_mode_queries:
      current: "1.0.0"
      pinned: null
      versions:
        "1.0.0":
          hash: "c9d2e5b"
          date: "2026-01-15"
          source: "manual"
          eval_pass_rate: null
  ```
- Modify `app/ai/agents/skill_loader.py`:
  - `load_skill_file(agent_name, skill_name)`:
    - Read `skill-versions.yaml` for the agent
    - If `pinned` is set for this skill → load the pinned version from git (`git show {hash}:{skill_file_path}`)
    - If `pinned` is null → load current file from disk (existing behavior)
    - Add `loaded_version` to the skill metadata returned to the agent (appears in `skills_loaded` response field)
  - `pin_skill(agent_name, skill_name, version: str)` → sets `pinned` in `skill-versions.yaml`
  - `unpin_skill(agent_name, skill_name)` → clears `pinned` (resume using current)
  - `list_skill_versions(agent_name, skill_name) -> list[SkillVersion]` → returns version history with eval pass rates
- Modify `app/ai/agents/evals/skill_updater.py` (32.6 integration):
  - After `generate_patch()`: bump version in skill file frontmatter (semver minor bump)
  - After `apply_patches()`: update `skill-versions.yaml` with new version entry including git hash and current eval pass rate
  - Add `--rollback` flag to `scripts/eval-skill-update.py`:
    - `--rollback {agent} {skill} {version}` → pins skill to specified version, logs reason
    - Validates version exists in manifest before pinning
- Modify `app/ai/agents/skill_override.py` — version-aware override:
  - `set_override_from_version(agent_name, skill_name, version: str)`:
    - Loads skill content from git at the specified version hash
    - Sets it as the active override (same mechanism as A/B testing)
    - Enables comparing two versions head-to-head in eval runs without changing the on-disk file
- Add to `Makefile`:
  - `skill-versions`: list all agents' skill versions and pin status
  - `skill-pin`: pin a skill to a version (`make skill-pin AGENT=dark_mode SKILL=client_behavior VERSION=1.1.0`)
  - `skill-unpin`: unpin a skill (`make skill-unpin AGENT=dark_mode SKILL=client_behavior`)
- Backfill: create initial `skill-versions.yaml` for all 9 agents with current files as `1.0.0`, `hash` = current HEAD, `pinned = null`
**Security:** Version pinning reads skill file content via `git show` — no shell injection risk (hash and path are validated against the manifest). `skill-versions.yaml` is checked into the repo — changes are reviewed via PR. Pinning does not modify skill files on disk — it loads an older version at runtime only. No new API endpoints.
**Verify:** `load_skill_file("dark_mode", "client_behavior")` with no pin → loads current file, returns `loaded_version: "1.2.0"`. Pin to `1.1.0` → loads content from git hash `b7e1f4a`, returns `loaded_version: "1.1.0"`. Unpin → resumes loading current. `eval-skill-update-apply` → bumps version in frontmatter and updates manifest. `--rollback dark_mode client_behavior 1.1.0` → pins and logs. `set_override_from_version` → loads old version as override for A/B eval. `make skill-versions` → prints table of all agents' skill versions. `make test` passes.

### 32.11 Per-Client Skill Overlays `[Backend]`
**What:** Allow project-level skill file overlays that extend or override core agent L3 skills with client-specific behavioral guidance. A project linked to brand "Acme Corp" can have custom skill files at `data/clients/acme/agents/scaffolder/skills/brand_patterns.md` that are loaded alongside (or instead of) core skills when processing that project's emails. Integrate with the existing skill loader's budget-aware progressive disclosure system.
**Why:** The centralized client matrix (32.1) solves data duplication for email client rendering facts, but different brands need different agent *behaviors* — not just different data. Acme Corp's brand guidelines require 2-column layouts with a hero image pattern that the Scaffolder should follow; BrandX prefers single-column with heavy typography. The Content agent's tone for a luxury brand differs from a SaaS product. Currently, per-brand customization only happens through L4 knowledge (brand guidelines fetched at runtime) — but L4 is unstructured RAG retrieval, not curated skill instructions. Brand-specific L3 overlays provide structured, version-controlled, budget-aware behavioral customization that slots into the existing skill loading pipeline. This also supports agency use cases where email-hub serves multiple clients from a single deployment.
**Implementation:**
- Define overlay directory structure:
  ```
  data/clients/
  └── acme/
      └── agents/
          ├── scaffolder/
          │   └── skills/
          │       └── brand_patterns.md      # Acme-specific layout patterns
          ├── content/
          │   └── skills/
          │       └── brand_voice.md         # Acme tone & style override
          └── dark_mode/
              └── skills/
                  └── brand_colors.md        # Acme dark mode color mappings
  ```
- Skill file frontmatter for overlays:
  ```yaml
  ---
  token_cost: 800
  priority: 1
  overlay_mode: "extend"  # "extend" (append to core) or "replace" (substitute core skill)
  replaces: null           # skill name to replace when overlay_mode="replace", e.g., "brand_voice"
  client_id: "acme"
  ---
  ```
  - `extend` (default): overlay content is appended after the core skill file content. Both are loaded within the same budget allocation. Use for additive brand guidance.
  - `replace`: overlay completely substitutes the named core skill file. The core skill's `token_cost` budget is freed and reallocated to the overlay. Use when brand guidelines fundamentally contradict core defaults (e.g., brand insists on patterns the core skill file advises against).
- Modify `app/ai/agents/skill_loader.py`:
  - `discover_overlays(agent_name: str, client_id: str | None) -> dict[str, OverlaySkill]`:
    - If `client_id` is None → return empty (no overlays)
    - Scan `data/clients/{client_id}/agents/{agent_name}/skills/` for `.md` files
    - Parse frontmatter → return mapping of skill name → `OverlaySkill(content, mode, replaces, token_cost, priority)`
    - Cache per `(agent_name, client_id)` pair — overlays don't change at runtime
  - Modify `load_skills_for_agent(agent_name, request, client_id=None)`:
    - After loading core L3 skills via `detect_relevant_skills()`:
      - Call `discover_overlays(agent_name, client_id)`
      - For each overlay with `mode="replace"`: remove the named core skill from the loaded set, add overlay in its place
      - For each overlay with `mode="extend"`: append overlay content to the end of the loaded skill set
      - Budget accounting: overlay `token_cost` counts against the agent's `skill_docs_max` budget (same as core skills)
      - Priority ordering: overlays respect the same priority system (1=critical, 2=standard, 3=supplementary) — under budget pressure, low-priority overlays are dropped before high-priority core skills
    - Add `overlays_loaded: list[str]` to skill loading metadata (returned in agent response's `skills_loaded` field as `"overlay:acme/brand_patterns"`)
- Modify `app/ai/agents/base.py` — `BaseAgentService.run()`:
  - Extract `client_id` from request metadata (project → client mapping from database)
  - Pass `client_id` to skill loading pipeline
  - No changes to agent prompt building — overlays are transparent to the agent (they appear as additional or replacement skill content)
- Modify `app/ai/blueprints/engine.py`:
  - Extract `client_id` from project context at blueprint start
  - Pass through `NodeContext.metadata["client_id"]` to all agent nodes
  - Agent nodes pass `client_id` to their service's `run()` method
- Create `scripts/validate-overlays.py`:
  - Validates all overlay files in `data/clients/`:
    - Frontmatter is valid (required fields present, `overlay_mode` is valid enum)
    - `replaces` skill name exists in the core agent's `SKILL_FILES` mapping (catch typos)
    - `token_cost` is within budget (overlay + remaining core skills ≤ `skill_docs_max`)
    - No conflicting overlays (two overlays both replacing the same core skill)
  - Run as part of `make check` and as a pre-commit hook
- Add to `Makefile`:
  - `validate-overlays`: run `scripts/validate-overlays.py`
  - `list-overlays`: list all client overlays grouped by client and agent
- Create starter overlay for documentation/testing:
  - `data/clients/_example/agents/content/skills/brand_voice.md`:
    ```yaml
    ---
    token_cost: 500
    priority: 2
    overlay_mode: "extend"
    client_id: "_example"
    ---
    ## Example Brand Voice Overlay

    This is a template for creating client-specific content agent overlays.
    Replace this content with the client's brand voice guidelines.

    **Tone:** [Professional / Casual / Playful / Authoritative]
    **Vocabulary:** [Industry-specific terms to use or avoid]
    **CTA style:** [Direct / Soft / Question-based]
    ```
**Security:** Overlay files are checked into the repo under `data/clients/` — changes go through PR review. No user input reaches the overlay loader (client_id comes from the database project record, not from the request body). Overlay content is treated identically to core skill content — same sanitization, same budget limits, same token counting. `validate-overlays.py` catches malformed files before they reach production. The `replace` mode cannot inject content outside the skill loading pipeline — it only substitutes one skill file for another within the existing budget. No new API endpoints.
**Verify:** Project linked to client "acme" → Scaffolder loads core skills + `brand_patterns.md` overlay (extend mode). Response `skills_loaded` includes `"overlay:acme/brand_patterns"`. Project with no client → no overlays loaded. Overlay with `mode="replace"` and `replaces="brand_voice"` → core `brand_voice.md` not loaded, overlay loaded instead. Budget pressure: overlay has `priority=3`, budget < 70% → overlay dropped. `validate-overlays.py` catches: missing frontmatter fields, `replaces` pointing to nonexistent skill, two overlays replacing the same skill. `_example` overlay loads without errors. `make test` passes. `make validate-overlays` passes.

### 32.12 Tests for 32.9–32.11 `[Full-Stack]`
**What:** Tests covering MCP server exposure, skill versioning, and per-client skill overlays.
**Implementation:**
- **MCP server tests** — `app/mcp/tests/test_mcp_server.py`:
  - MCP server starts and completes handshake (tool listing)
  - All 9 agent tools registered with correct parameter schemas
  - `email_scaffold` tool call with valid brief → returns HTML + confidence + qa_passed
  - `email_content` tool call with `operation="subject_line"` → returns alternatives list
  - `email_code_review` tool call with HTML → returns structured review results
  - Invalid operation → `error_result` with descriptive message
  - Missing required parameter → MCP validation error (not a crash)
  - `email-hub://agents` resource → returns JSON with 9 agents, each with name, capabilities, model_tier
  - Rate limiting applies: rapid successive calls → rate limit error after threshold
- **Skill versioning tests** — `app/ai/agents/tests/test_skill_versioning.py`:
  - `load_skill_file()` with no pin → loads current version from disk, returns correct `loaded_version`
  - `pin_skill("dark_mode", "client_behavior", "1.1.0")` → updates `skill-versions.yaml`
  - `load_skill_file()` after pin → loads content from git hash, returns pinned version
  - `unpin_skill()` → clears pin, resumes loading current
  - `list_skill_versions()` → returns version history with eval pass rates
  - Pin to nonexistent version → raises `VersionNotFoundError`
  - `set_override_from_version()` → loads old version content as override
  - `eval-skill-update-apply` → bumps version in frontmatter, updates manifest with new entry
  - `--rollback` flag → pins skill and logs reason
  - Backfill: all 9 agents have `skill-versions.yaml` with `1.0.0` entries
- **Per-client overlay tests** — `app/ai/agents/tests/test_skill_overlays.py`:
  - `discover_overlays("scaffolder", "acme")` → finds overlay files in `data/clients/acme/agents/scaffolder/skills/`
  - `discover_overlays("scaffolder", None)` → returns empty dict
  - `discover_overlays("scaffolder", "nonexistent")` → returns empty dict
  - Extend mode: core skill + overlay both loaded, overlay appended after core content
  - Replace mode: core skill removed, overlay loaded in its place
  - Budget accounting: overlay `token_cost` deducted from `skill_docs_max`
  - Priority drop: overlay with `priority=3` dropped when budget < 70%
  - `skills_loaded` response includes `"overlay:acme/brand_patterns"` for extend, replaces core entry for replace
  - `validate-overlays.py` rejects: missing `overlay_mode`, invalid `replaces` target, duplicate replacements
  - `validate-overlays.py` passes for `_example` overlay
  - Caching: `discover_overlays` called twice with same args → second call uses cache
**Security:** Tests only. No production code changes. Test fixtures use `_example` client and mock skill files — no real client data. Git operations in versioning tests use test repo fixtures.
**Verify:** `make test` passes (all new test files). `make check` all green. `make validate-overlays` passes.

---

## Phase 33 — Design Token Pipeline Overhaul (Figma → Email HTML)

> **Continues Phase 31.5–31.6 design sync work.** Phase 31.6 enriched `layout_analyzer.py` with typography data (`TextBlock.font_family/weight/line_height/letter_spacing`, `EmailSection.buttons/column_layout/item_spacing`) and added `spacing_bridge.py` for token extraction — but the converter (`converter.py`, `converter_service.py`) never consumes this data. Phase 33 refactors the existing converter to use the rich layout analysis already available, improves HTML output quality (semantic elements, MSO fallbacks, dark mode, proportional widths), and adds a validation layer. No new pipeline — same files, same entry points, same data flow. The converter just gets smarter.
>
> The current system silently drops opacity, gradients, spacing, line-height, and dark mode tokens; misidentifies colors via fragile heuristics; ignores auto-layout direction; produces broken multi-column layouts; and doesn't support Figma's modern Variables API. Knowledge from agent skill files (`table_layouts.md`, `mso_bug_fixes.md`, `dark-mode-css.md`, `color_remapping.md`, `cta-buttons.md`, `vml_reference.md`), ontology data (`css_properties.yaml`, `support_matrix.yaml`), and data files (`email_client_fonts.yaml`) is encoded directly into the converter code — not connected at runtime.

> **Dependency note:** Direct continuation of Phase 31.5–31.6. Independent of Phase 32 (Agent Rendering Intelligence). Can be implemented in parallel with Phase 32. However, Phase 33 fixes are *upstream* of Phase 32 — agents receiving better tokens and HTML from this phase will produce better results. Recommended to start Phase 33 first or concurrently.

- [x] ~~33.0 Wire layout analyzer into converter (prerequisite for 33.4–33.9)~~ DONE
- [x] ~~33.1 Figma Variables API + opacity compositing~~ DONE
- [x] ~~33.2 Email-safe token transforms & validation layer~~ DONE
- [x] ~~33.3 Typography pipeline: line-height, letter-spacing, font mapping~~ DONE
- [x] ~~33.4 Spacing token pipeline & auto-layout → table mapping~~ DONE
- [x] ~~33.5 Multi-column layout & proportional width calculation~~ DONE
- [x] ~~33.5b Client-aware conversion — ontology wire-up (prerequisite for 33.7)~~ DONE
- [x] ~~33.6 Semantic HTML generation (headings, paragraphs, buttons)~~ DONE
- [x] ~~33.7 Dark mode token extraction & gradient fallbacks~~ DONE
- [x] ~~33.8 Design context enrichment & Scaffolder integration~~ DONE
- [x] ~~33.9 Builder annotations for visual builder sync~~ DONE
- [x] ~~33.10 Image asset import for design sync pipeline~~ DONE
- [x] ~~33.11 Tests & integration verification~~ DONE

### 33.0 Wire Layout Analyzer into Converter `[Backend]`
**What:** Connect the existing `analyze_layout()` function in `app/design_sync/figma/layout_analyzer.py` to `DesignConverterService.convert()` in `app/design_sync/converter_service.py`. Currently the converter calls `node_to_email_html()` directly on raw `DesignNode` trees, bypassing the layout analyzer entirely. The analyzer already detects column layouts, buttons, heading hierarchy, item spacing, element gaps, and section types — but none of this data reaches the HTML generation step. This subtask bridges the gap so that subsequent subtasks (33.4–33.9) can consume rich `EmailSection` data instead of reimplementing detection logic. Additionally, fix `_build_props_map_from_nodes()` to extract all `DesignNode` fields (currently only `bg_color`), add MSO reset styles to the email skeleton and inline table/image output, and extend `_NodeProps` and `ConversionResult` dataclasses for downstream use.
**Why:** `converter_service.py` line 110 calls `node_to_email_html(frame, ...)` on raw frames. The layout analyzer's `EmailSection` dataclass already carries: `column_layout` (single/two/three/multi), `column_count`, `texts` (with `is_heading`), `images`, `buttons` (with dimensions + text), `spacing_after`, `bg_color`, `padding_*`, `item_spacing`, and `element_gaps`. Without this connection, every Phase 33 subtask must reimplement detection that already exists — e.g., 33.6 describes button detection rules that are identical to `layout_analyzer._walk_for_buttons()`. Additionally, `_build_props_map_from_nodes()` only extracts `bg_color` from `DesignNode` fields, silently discarding `font_family`, `font_size`, `font_weight`, `padding_*`, and `layout_mode` — data that the Penpot path (`_build_props_map`) already handles. The `EMAIL_SKELETON` style block lacks mandatory MSO table resets (`mso-table-lspace:0pt;mso-table-rspace:0pt`), image resets (`-ms-interpolation-mode:bicubic`), and the inline table/image styles don't include them either — Gmail clips emails at 102KB and strips `<style>` blocks, so inline styles must be self-sufficient.
**Knowledge sources (encode as code, do not connect at runtime):**
- `app/ai/agents/scaffolder/skills/email_structure.md` — document skeleton requirements: VML/Office XML namespace (`xmlns:v`, `xmlns:o`), DPI fix (`o:PixelsPerInch=96`), required meta tags (`format-detection`, `x-apple-disable-message-reformatting`, `color-scheme`, `supported-color-schemes`, `-webkit-text-size-adjust:100%`, `word-spacing:normal`). Verify `EMAIL_SKELETON` in `converter_service.py` includes all elements — currently missing `<meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">` and `<meta name="x-apple-disable-message-reformatting">`
- `app/ai/agents/outlook_fixer/skills/mso_bug_fixes.md` — 15 Outlook bug patterns. MSO reset styles that must be present: (1) every `<table>`: `border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;` — prevents 1px white lines between cells, (2) every `<img>`: `-ms-interpolation-mode:bicubic;display:block;border:0;outline:none;text-decoration:none;` — prevents image spacing and DPI scaling artifacts, (3) `<body>`: `margin:0;padding:0;` reset. These must be both in the `<style>` block AND inline on each element (belt-and-suspenders for Gmail which strips `<style>` in clipped emails >102KB)
- `app/knowledge/data/seeds/best_practices/table-based-layout.md` — structural wrapper pattern: 100% outer table for body background + fixed-width (600px) content table with `align="center"` + `role="presentation"` on ALL layout tables. `cellpadding="0" cellspacing="0" border="0"` on every table (already present in `node_to_email_html()`). Avoid nesting tables deeper than 6 levels (Outlook rendering degrades). Current skeleton has a single-level wrapper — verify the converter doesn't produce nesting >6 on deeply nested Figma trees
- `app/knowledge/data/seeds/css_support/box-model.md` — padding works ONLY on `<td>` cells (Outlook ignores on `<p>`/`<div>`/`<a>`). Never use `margin: 0 auto` for centering — use `align="center"` HTML attribute. Width must be set as both HTML attribute (`width="600"`) AND CSS (`style="width:600px"`) for Outlook compatibility. `box-sizing` is ignored by Outlook — always use content-box math. Percentage widths are reliable on `<td>` elements
**Implementation:**
- Update `DesignConverterService.convert()` in `app/design_sync/converter_service.py`:
  - Add import: `from app.design_sync.figma.layout_analyzer import analyze_layout, DesignLayoutDescription, EmailSection`
  - After `frames = self._collect_frames(structure, selected_nodes)`, call layout analysis:
    ```python
    layout = analyze_layout(structure)
    sections_by_node_id: dict[str, EmailSection] = {
        section.node_id: section for section in layout.sections
    }
    ```
  - Build button ID lookup for O(1) hit testing during recursion:
    ```python
    button_node_ids: set[str] = set()
    for section in layout.sections:
        for btn in section.buttons:
            button_node_ids.add(btn.node_id)
    ```
  - Build text ID lookup for heading detection during recursion:
    ```python
    text_meta: dict[str, TextBlock] = {}
    for section in layout.sections:
        for tb in section.texts:
            text_meta[tb.node_id] = tb
    ```
  - Pass all lookups to `node_to_email_html()`:
    ```python
    section_html = node_to_email_html(
        frame,
        indent=1,
        props_map=props_map or None,
        section_map=sections_by_node_id,
        button_ids=button_node_ids,
        text_meta=text_meta,
    )
    ```
  - Use `layout.overall_width` as container width when available:
    ```python
    container_width = int(layout.overall_width) if layout.overall_width else 600
    ```
    Replace hardcoded `width="600"` and `max-width:600px` in `EMAIL_SKELETON.format()` with `container_width`. Update MSO wrapper table width to match.
  - Add inter-section spacer rows using `section.spacing_after`:
    ```python
    for idx, frame in enumerate(frames):
        section = sections_by_node_id.get(frame.id)
        section_html = node_to_email_html(frame, ...)
        section_parts.append(f'<tr><td>\n{section_html}\n</td></tr>')
        if section and section.spacing_after and section.spacing_after > 0:
            spacer_h = int(section.spacing_after)
            section_parts.append(
                f'<tr><td style="height:{spacer_h}px;font-size:1px;'
                f'line-height:1px;mso-line-height-rule:exactly;" '
                f'aria-hidden="true">&nbsp;</td></tr>'
            )
    ```
  - Store layout on result:
    ```python
    return ConversionResult(
        html=result_html,
        sections_count=len(frames),
        warnings=warnings,
        layout=layout,
    )
    ```
- Update `node_to_email_html()` signature in `app/design_sync/converter.py`:
  - Add new optional parameters:
    ```python
    def node_to_email_html(
        node: DesignNode,
        *,
        indent: int = 0,
        props_map: dict[str, _NodeProps] | None = None,
        parent_bg: str | None = None,
        parent_font: str | None = None,
        section_map: dict[str, EmailSection] | None = None,
        button_ids: set[str] | None = None,
        text_meta: dict[str, TextBlock] | None = None,
        current_section: EmailSection | None = None,
        body_font_size: float = 16.0,
    ) -> str:
    ```
  - At the top of FRAME/GROUP/COMPONENT/INSTANCE handling, look up section data:
    ```python
    section = current_section
    if section_map and node.id in section_map:
        section = section_map[node.id]
    ```
  - Thread `current_section=section`, `button_ids`, `text_meta`, `section_map`, and `body_font_size` through all recursive calls to `node_to_email_html()` for child nodes
  - When `section` is available:
    - Use `section.column_layout` and `section.column_count` to decide row grouping strategy (consumed by 33.5 — for now, store on context, 33.5 will use it)
    - Use `section.item_spacing` to insert spacer `<tr>` rows or cell padding between children (consumed by 33.4)
    - Check `button_ids` for button detection (consumed by 33.6 — for now, pass through)
    - Check `text_meta` for heading classification (consumed by 33.6 — for now, pass through)
- Fix `_build_props_map_from_nodes()` in `app/design_sync/converter_service.py` (lines 169-181):
  - Replace the current `_walk()` that only extracts `bg_color`:
    ```python
    def _build_props_map_from_nodes(self, frames: list[DesignNode]) -> dict[str, _NodeProps]:
        """Build props_map from DesignNode fields (provider-agnostic)."""
        props: dict[str, _NodeProps] = {}

        def _walk(node: DesignNode) -> None:
            has_data = (
                node.fill_color or node.font_family or node.font_size
                or node.font_weight or node.padding_top or node.padding_right
                or node.padding_bottom or node.padding_left or node.layout_mode
                or node.line_height_px or node.letter_spacing_px
            )
            if has_data:
                props[node.id] = _NodeProps(
                    bg_color=node.fill_color,
                    font_family=node.font_family,
                    font_size=node.font_size,
                    font_weight=str(node.font_weight) if node.font_weight else None,
                    padding_top=node.padding_top or 0,
                    padding_right=node.padding_right or 0,
                    padding_bottom=node.padding_bottom or 0,
                    padding_left=node.padding_left or 0,
                    layout_direction=(
                        "row" if node.layout_mode == "HORIZONTAL"
                        else "column" if node.layout_mode == "VERTICAL"
                        else None
                    ),
                    line_height_px=node.line_height_px,
                    letter_spacing_px=node.letter_spacing_px,
                )
            for child in node.children:
                _walk(child)

        for frame in frames:
            _walk(frame)
        return props
    ```
  - This aligns the Figma path with the Penpot path (`_build_props_map`, lines 183-213) which already extracts font, padding, and layout data from raw file objects
- Extend `_NodeProps` dataclass in `app/design_sync/converter.py` (lines 30-44):
  - Add typography fields consumed by 33.3 and 33.6:
    ```python
    @dataclass(frozen=True)
    class _NodeProps:
        """Supplementary visual properties not carried by DesignNode."""
        bg_color: str | None = None
        font_family: str | None = None
        font_size: float | None = None
        font_weight: str | None = None
        padding_top: float = 0
        padding_right: float = 0
        padding_bottom: float = 0
        padding_left: float = 0
        border_color: str | None = None
        border_width: float = 0
        layout_direction: str | None = None  # "row" | "column" | None
        line_height_px: float | None = None  # NEW: explicit line-height in px
        letter_spacing_px: float | None = None  # NEW: letter-spacing in px
    ```
- Extend `ConversionResult` dataclass in `app/design_sync/converter_service.py` (lines 56-61):
  - Add layout field for downstream consumers (33.8 Scaffolder integration, 33.9 builder annotations):
    ```python
    @dataclass(frozen=True)
    class ConversionResult:
        """Result of converting a design tree to email HTML."""
        html: str
        sections_count: int
        warnings: list[str] = field(default_factory=list)
        layout: DesignLayoutDescription | None = None  # NEW: rich layout data
    ```
- Update `EMAIL_SKELETON` in `app/design_sync/converter_service.py` (lines 26-52):
  - Add missing meta tags to `<head>` (before `{style_block}`):
    ```html
    <meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
    <meta name="x-apple-disable-message-reformatting">
    ```
  - Expand `{style_block}` generation to include MSO reset styles:
    ```python
    style_block = (
        "<style>\n"
        f"  body {{ font-family: {safe_body_font}; margin: 0; padding: 0; }}\n"
        "  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }\n"
        "  img { -ms-interpolation-mode: bicubic; border: 0; display: block; outline: none; text-decoration: none; }\n"
        "</style>"
    )
    ```
  - Make container width dynamic (replace hardcoded `600`):
    ```python
    result_html = EMAIL_SKELETON.format(
        style_block=style_block,
        bg_color=bg_color,
        text_color=text_color,
        body_font=safe_body_font or "Arial, Helvetica, sans-serif",
        sections=sections_html,
        container_width=container_width,
    )
    ```
    Update `EMAIL_SKELETON` template to use `{container_width}` in place of `600` (3 occurrences: MSO table `width`, CSS `max-width`, and outer table `width` attribute)
- Update `node_to_email_html()` table output in `app/design_sync/converter.py` (lines 301-303):
  - Add MSO reset styles inline on every `<table>` element (belt-and-suspenders for Gmail clipping):
    ```python
    table_style_parts = [
        "border-collapse:collapse",
        "mso-table-lspace:0pt",
        "mso-table-rspace:0pt",
    ]
    if any(v > 0 for v in pad_vals):
        table_style_parts.append(
            f"padding:{int(props.padding_top)}px {int(props.padding_right)}px "
            f"{int(props.padding_bottom)}px {int(props.padding_left)}px"
        )
    style_attr = f' style="{";".join(table_style_parts)}"'
    ```
  - This replaces the current `style_parts` list that only includes padding
- Update `node_to_email_html()` image output in `app/design_sync/converter.py` (lines 246-254):
  - Expand inline image styles (partially present, add missing properties):
    ```python
    return (
        f'{pad}<img src="" alt="{alt}"{node_id_attr}{w}{h}'
        f' style="display:block;border:0;outline:none;text-decoration:none;'
        f'-ms-interpolation-mode:bicubic;width:100%;height:auto;" />'
    )
    ```
  - Currently missing: `outline:none`, `text-decoration:none`, `-ms-interpolation-mode:bicubic`
- Guard against excessive table nesting depth:
  - Add `max_depth: int = 6` parameter to `node_to_email_html()`
  - Track `current_depth` through recursion, increment when entering FRAME/GROUP/COMPONENT/INSTANCE
  - If `current_depth > max_depth`: flatten remaining children as `<tr><td>` without nesting a new `<table>`, log warning `"design_sync.nesting_depth_exceeded"` with node ID
  - This prevents Outlook rendering degradation on deeply nested Figma trees (per `best_practices/table-based-layout.md`)
**Security:** No new input paths. Layout analysis is pure computation on existing `DesignNode` data — no I/O, no external calls. MSO reset styles are static CSS strings. Container width comes from `layout.overall_width` (a `float | None` derived from node dimensions) — clamped to `400 <= width <= 800` before use in `EMAIL_SKELETON.format()` to prevent injection via absurd values. Table nesting depth guard is a safety limit, not a security boundary. No user input reaches the new code paths.
**Verify:** `analyze_layout(structure)` is called during `convert()` and returns valid `DesignLayoutDescription` with correct section count matching frame count. `sections_by_node_id` lookup maps at least one node ID to an `EmailSection` object. `button_node_ids` set contains IDs of all detected buttons. `text_meta` dict maps TEXT node IDs to `TextBlock` objects with `is_heading` set. `node_to_email_html()` accepts new parameters without error — existing callers using keyword args still work (all new params have defaults). `_build_props_map_from_nodes()` populates all `_NodeProps` fields from `DesignNode` — frame with `padding_top=24, font_family="Inter", layout_mode="HORIZONTAL"` → `_NodeProps(padding_top=24, font_family="Inter", layout_direction="row")`. `_NodeProps` has `line_height_px` and `letter_spacing_px` fields. `ConversionResult.layout` is populated with `DesignLayoutDescription`. `EMAIL_SKELETON` contains `<meta name="format-detection">` and `<meta name="x-apple-disable-message-reformatting">`. Style block contains `border-collapse: collapse`, `mso-table-lspace: 0pt`, `-ms-interpolation-mode: bicubic`. All `<table>` elements have `border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt` inline. All `<img>` elements have `display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic` inline. Container width from `layout.overall_width=700` → `width="700"` and `max-width:700px` in output. Container width `None` → falls back to 600. Container width `1200` → clamped to `800`. Inter-section spacer rows present when `spacing_after > 0`, with `mso-line-height-rule:exactly` and `aria-hidden="true"`. Nesting depth >6 → children flattened, warning logged. Existing conversion tests still pass (all changes are additive — new params default to `None`). `make test` passes. `make types` passes.

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
**Knowledge sources (encode as code, do not connect at runtime):**
- `ontology/data/css_properties.yaml` (365 properties) — use as the authoritative source for which CSS properties exist and their valid value types. Load at module level. When validating a generated CSS property, check it against the ontology instead of hardcoding safe/unsafe lists
- `ontology/data/support_matrix.yaml` — per-client support flags (25+ email clients). Use to determine which CSS properties are safe to emit for target clients. E.g., `border-radius` is ⚠️ (partial) — emit but add VML fallback; `position` is ❌ — never emit
- `code_reviewer/skills/css_syntax_validation.md` — error patterns and severity levels to implement: empty value (error), missing semicolon (error), unclosed braces (error), invalid property (warning), unitless numeric (warning for non-zero, info for zero). Use these severity classifications in the `TokenWarning` dataclass
- `code_reviewer/skills/css_client_support.md` — vendor prefix rules (all invalid except `-webkit-text-size-adjust`); external resources (`@font-face`/`@import` stripped by Gmail); `!important` guidelines (expected in dark mode, flag if >10 non-dark uses)
- `css_support/colors-backgrounds.md` — Outlook rejects `rgba()`/`hsl()` — always convert to 6-digit hex. Gmail strips `background-image` from inline styles. Use these rules in color validation
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
  - **Load font fallback map from `data/email_client_fonts.yaml`** at module level instead of hardcoding. The YAML file already contains:
    - `fallback_map`: web-font → email-safe fallback chain (e.g., `Inter: [Arial, Helvetica, sans-serif]`, `Playfair Display: [Georgia, "Times New Roman", serif]`)
    - `clients`: per-client font support data including `requires_mso_font_alt: true` for Outlook desktop
    ```python
    import yaml
    from pathlib import Path

    _FONT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "email_client_fonts.yaml"
    _FONT_DATA = yaml.safe_load(_FONT_DATA_PATH.read_text())
    _FALLBACK_MAP: dict[str, list[str]] = _FONT_DATA.get("fallback_map", {})
    _MSO_FONT_ALT_CLIENTS = {
        k for k, v in _FONT_DATA.get("clients", {}).items()
        if isinstance(v, dict) and v.get("requires_mso_font_alt")
    }
    ```
  - Update `_font_stack()` to use the YAML mapping: look up `family_clean` in `_FALLBACK_MAP`, build stack from YAML fallback chain, use original font as progressive enhancement: `f"{family_clean}, {', '.join(fallback_chain)}"`
  - When `requires_mso_font_alt` is true for target clients: add `mso-font-alt` CSS property to the inline style (e.g., `mso-font-alt:Arial;`) so Outlook uses the mapped system font
  - Map font weight: `int(weight)` → `"bold"` if ≥ 500, `"normal"` if < 500
- Update `node_to_email_html()` in `app/design_sync/converter.py`:
  - When rendering TEXT nodes: include `line-height:{value}px;` if available from node or props
  - Include `letter-spacing:{value}px;` if non-zero
  - Include `text-transform:{value};` if set
  - Include `text-decoration:{value};` if set
  - Use mapped font weight (`normal`/`bold`) instead of raw numeric weight
**Knowledge sources (encode as code, do not connect at runtime):**
- `data/email_client_fonts.yaml` — **primary data source** for font fallback mapping and per-client font support. Load at module level (replaces hardcoded `_WEB_FONT_MAP`). Contains `fallback_map` (10 web fonts → email-safe chains) and `clients` (11 email clients with `type`, `fonts`, `requires_mso_font_alt` fields)
- `css_support/typography.md` — px units only for `font-size`/`line-height` (unitless line-height breaks Outlook); `-webkit-text-size-adjust: 100%` required for iOS; intermediate font weights (300, 500) may fail in Outlook — only `normal` (400) and `bold` (700) are safe; reset heading margins explicitly (`margin:0`)
- `outlook_fixer/skills/mso_bug_fixes.md` — `mso-font-alt` property for Outlook font fallback; `mso-line-height-rule: exactly` required when setting explicit line-height in Outlook (without this, Outlook may override line-height)
- `scaffolder/skills/client_compatibility.md` — font-family, font-size, font-weight, line-height, text-align, text-decoration are universally safe CSS properties; letter-spacing is partially supported (safe to include but may be ignored by some clients)
**Security:** Static mapping table loaded from YAML. No user input processing changes.
**Verify:** Figma TEXT node with `Inter` font → HTML has `font-family:Inter, Arial, Helvetica, sans-serif` (from YAML `fallback_map`). `mso-font-alt:Arial` included in inline style. Font weight `300` → `font-weight:normal`. Font weight `600` → `font-weight:bold`. Line-height `28.8` → `line-height:29px` in HTML with `mso-line-height-rule:exactly`. Letter-spacing `0.5` → `letter-spacing:1px` in HTML (rounded). Text with `textCase: UPPER` → `text-transform:uppercase` in HTML. `Typography` model populated with `heading_line_height`, `body_line_height`. Unknown font not in `fallback_map` → falls back to `Arial, Helvetica, sans-serif` (generic sans-serif). Existing typography tests still pass. `make test` passes. `make types` passes.

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
**Knowledge sources (encode as code, do not connect at runtime):**
- `css_support/box-model.md` — **critical rules**: padding works ONLY on `<td>` cells (Outlook ignores padding on `<p>`/`<div>`/`<a>`). Never use `margin: 0 auto` for centering — use `align="center"` HTML attribute. Width must be set as both HTML attribute (`width="600"`) and CSS (`style="width:600px"`) for Outlook compatibility. `box-sizing` is ignored by Outlook. Percentage widths are reliable on `<td>` elements
- `outlook_fixer/skills/mso_bug_fixes.md` — spacer row pattern must include `font-size:1px;line-height:1px;mso-line-height-rule:exactly` to prevent Outlook from expanding spacer rows to default line height (~18px). Without `mso-line-height-rule:exactly`, a `height:12px` spacer row renders as 18px in Outlook
- `css_support/layout-properties.md` — `display:inline-block` fails in Outlook (use ghost tables instead); `float` is ignored by Gmail and Outlook; flexbox/grid are Apple Mail only. Table layout is the only reliable approach for multi-client emails
- `best_practices/table-based-layout.md` — always include `cellpadding="0" cellspacing="0" border="0"` on layout tables; `role="presentation"` on all non-data tables; avoid nesting tables deeper than 6 levels (Outlook rendering degrades)
**Security:** No new input paths. Spacing values are numeric, already validated in 33.2.
**Verify:** Figma frame with `paddingTop: 24, paddingLeft: 16` → HTML `<td>` has `style="padding:24px 0px 0px 16px"` (padding on `<td>`, NOT on `<table>`). Vertical auto-layout with `itemSpacing: 12` → spacer `<tr>` rows with `height:12px;font-size:1px;line-height:1px;mso-line-height-rule:exactly` between children. Horizontal auto-layout with `itemSpacing: 8` → cells have `padding-left:8px` (except first). Centering uses `align="center"` attribute, not `margin:0 auto`. Spacing tokens appear in Scaffolder design context. `make test` passes.

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
**Knowledge sources (encode as code, do not connect at runtime):**
- `scaffolder/skills/table_layouts.md` — **complete HTML patterns** for 2-column (50/50 with MSO ghost table), 3-column (33/33/33), hero + content grid, 70/30 sidebar, fluid-hybrid spongy layout. Use these as parameterized templates in `node_to_email_html()` rather than generating from scratch. Each pattern includes MSO conditional ghost table wrapper, `display:inline-block;vertical-align:top;` for modern clients, and `width` on both `<td>` cells and MSO table cells
- `outlook_fixer/skills/mso_conditionals.md` — ghost table nesting rules: NEVER nest MSO conditionals (causes Word engine stack corruption). Always close `<![endif]-->` before opening another `<!--[if mso]>`. Version targeting operators: `gte mso 12` (Outlook 2007+), `lte mso 16` (Outlook 2021 and earlier). Count conditional pairs to verify balanced open/close
- `outlook_fixer/skills/mso_bug_fixes.md` — MSO table reset styles: `mso-table-lspace:0pt;mso-table-rspace:0pt` on every `<table>` (prevents 1px white lines between cells). Ghost table pattern must include `cellpadding="0" cellspacing="0"`. DPI scaling fix (`PixelsPerInch=96`) already in `EMAIL_SKELETON` — verify it's not duplicated
- `css_support/layout-properties.md` — `display:inline-block` requires `vertical-align:top` and `width` set via both attribute and CSS. Gmail clips emails at 102KB — monitor generated HTML size for multi-column layouts
- `import_annotator/skills/column_patterns.md` — column detection patterns for reverse mapping: table-based columns (each `<td>` = column), inline-block columns (parent = section), and the key rule that individual columns are NOT sections (parent gets the section annotation)
**Security:** No new input paths. Width calculations use numeric node dimensions only.
**Verify:** Two children (200px + 400px) in a 600px parent with `layoutMode: "HORIZONTAL"` → `<td width="33%">` and `<td width="67%">` with ghost table wrapper. Three equal columns → `<td width="33%">` each with MSO ghost table. Ghost table includes `cellpadding="0" cellspacing="0"` and `mso-table-lspace:0pt;mso-table-rspace:0pt`. No nested MSO conditionals (balanced open/close count). Vertical auto-layout → each child in its own `<tr>`. Mixed y-position nodes with >10px offset but <20px → grouped in same row. All children with `y=None` → single row. Existing single-column layouts unaffected. `make test` passes.

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
  - **Reuse `layout_analyzer` output**: 33.0 wires `analyze_layout()` into the converter, producing `EmailSection.buttons` (list of `ButtonElement` with `node_id`, `text`, `width`, `height`). Check if the current node's `id` matches a button in the section's buttons list rather than re-detecting. Fallback detection for nodes outside analyzed sections: COMPONENT/INSTANCE with name containing "button"/"btn"/"cta" AND a single TEXT child ≤30 chars AND height ≤80px (same rules as `layout_analyzer._walk_for_buttons`)
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
- **Reuse `layout_analyzer` heading detection**: 33.0 wires `analyze_layout()` into the converter, producing `EmailSection.texts` with `is_heading=True/False` already set by `_detect_content_hierarchy()`. Use `TextBlock.is_heading` from the section's text list to determine whether a TEXT node is a heading, rather than re-computing font size ratios. The heading level (h1/h2/h3) still uses the font size thresholds described above — `is_heading` determines *whether* it's a heading, the size ratio determines *which level*
**Knowledge sources (encode as code, do not connect at runtime):**
- `best_practices/cta-buttons.md` — **complete bulletproof button patterns**: padding-based table button (widest support), VML roundrect for Outlook (with `arcsize` percentage), and border-based approach (fallback). Design rules: 44px minimum touch target height, 4.5:1 contrast ratio between button text and background, action verb copy (2-4 words), multiple CTAs should have visual hierarchy (primary = filled, secondary = outlined). The VML `<v:roundrect>` pattern includes `stroke="f"` (no border), `<v:textbox inset="0,0,0,0">`, and `<center>` for text alignment
- `outlook_fixer/skills/vml_reference.md` — VML shape syntax: `<v:roundrect>` for buttons (with `arcsize` as percentage of shortest side), `<v:fill type="solid" color="{hex}">`, `<v:textbox>` with `mso-fit-shape-to-text:true` to auto-size. VML namespace must be declared on `<html>` (already in `EMAIL_SKELETON`). Always include `xmlns:v="urn:schemas-microsoft-com:vml"` and `xmlns:o="urn:schemas-microsoft-com:office:office"`
- `accessibility/skills/screen_reader_behavior.md` — `role="presentation"` on ALL layout tables (already present but verify button wrapper tables get it too). Headings create navigation landmarks — ensure heading hierarchy doesn't skip levels (h1 → h3 without h2). `aria-hidden="true"` on decorative spacer rows. Reading order follows DOM order, not visual order — verify the converter outputs elements in the same order as the design's top-to-bottom reading flow
- `accessibility/skills/color_contrast.md` — WCAG AA contrast: 4.5:1 for normal text (<18px or <14px bold), 3:1 for large text (≥18px or ≥14px bold). Apply to button text vs button background color. The converter already has `_relative_luminance()` and `_contrast_ratio()` — extend to validate button contrast and warn if below threshold
- `outlook_fixer/skills/mso_bug_fixes.md` — `mso-line-height-rule:exactly` required on ALL elements with explicit `line-height` (headings, paragraphs). Without it, Outlook overrides line-height with its own default. Paragraph margins: use `mso-margin-top-alt` and `mso-margin-bottom-alt` for Outlook-specific margin control
**Security:** HTML content is escaped via `html.escape()` (already in place). Button `href="#"` is a placeholder — no user-controlled URLs in conversion output. VML attributes use escaped values.
**Verify:** TEXT node with font-size 32px (body 16px) → `<h1>` inside `<td>` with `mso-line-height-rule:exactly`. TEXT node with font-size 16px → `<p style="margin:0 0 10px 0;">` inside `<td>`. COMPONENT named "CTA Button" with "Shop Now" text → bulletproof `<a>` button with VML `<v:roundrect>` fallback, `role="presentation"` on button wrapper table, contrast ratio ≥ 4.5:1 validated. Button height ≥ 44px (touch target). Multi-line text → multiple `<p>` tags. Heading hierarchy is sequential (no skipped levels). Layout tables have `role="presentation"`. Existing conversion output still has valid email HTML structure. `make test` passes.

### ~~33.7 Dark Mode Token Extraction & Gradient Fallbacks~~ DONE `[Backend]`
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
**Knowledge sources (encode as code, do not connect at runtime):**
- `css_support/dark-mode-css.md` — **complete dark mode email template** with all techniques combined. Three-tier approach: (1) `<meta name="color-scheme" content="light dark">` + `<meta name="supported-color-schemes" content="light dark">` in `<head>`, (2) `@media (prefers-color-scheme: dark)` with `!important` on all overrides (for Apple Mail, iOS, Samsung), (3) `[data-ogsc]` (text) and `[data-ogsb]` (background) attribute selectors for Outlook.com. CSS `color-scheme: light dark;` property on `<body>`. All three must be present for full coverage
- `dark_mode/skills/color_remapping.md` — **magic color values**: use `#010101` instead of `#000000` and `#fefefe` instead of `#ffffff` to prevent Outlook auto-inversion (Outlook categorizes pure black and pure white for automatic dark mode swapping). Luminance-based color categorization zones: light (lum > 0.5) → may be darkened, dark (lum < 0.2) → may be lightened, mid-range (0.2-0.5) → usually preserved. Pre-verified dark mode color pairs with WCAG AA contrast ratios
- `dark_mode/skills/outlook_dark_mode.md` — Outlook.com-specific patterns: `[data-ogsc]` targets text color, `[data-ogsb]` targets background color. The 1x1 pixel background trick prevents Outlook from inverting CTA button backgrounds: set a 1x1 transparent PNG as `background-image` on the button `<td>` (`background-image:url(data:image/png;base64,...)`) — Outlook won't invert elements with background images. Class-based selectors required (not element selectors) because Outlook.com rewrites class names
- `dark_mode/skills/client_behavior.md` — client behavior matrix: Apple Mail = full control (color-scheme + @media), Outlook.com = partial (`[data-ogsc]`/`[data-ogsb]` only), Outlook Desktop = no dark mode control, Gmail = no dark mode control, **Samsung = double-inversion risk** (Samsung inverts colors, then re-inverts `prefers-color-scheme` overrides — test carefully). Implementation priority: Apple/iOS first (largest dark mode market share), then Outlook.com, then Samsung
- `dark_mode/skills/meta_tag_injection.md` — required meta tags (must be in `<head>`, before any `<style>` block): `<meta name="color-scheme" content="light dark">` and `<meta name="supported-color-schemes" content="light dark">`. Without these, Apple Mail ignores `@media (prefers-color-scheme: dark)` entirely
- `dark_mode/skills/image_handling.md` — image swap techniques for dark mode: `<picture><source media="(prefers-color-scheme: dark)" srcset="dark-logo.png">` for Apple Mail; CSS show/hide with `display:none` / `display:block !important` for broader support; transparent PNG logos work natively in dark mode. Product images: add 1-2px white border to prevent blend-in on dark backgrounds
- `css_support/colors-backgrounds.md` — gradient CSS support: only Apple Mail/iOS/Samsung support `background: linear-gradient(...)`. All other clients need solid `bgcolor` fallback. For Outlook: use VML `<v:fill type="gradient" color="{start_hex}" color2="{end_hex}" angle="{angle}">` (from `outlook_fixer/skills/vml_reference.md`). Always emit both CSS gradient AND `bgcolor` attribute on the same element
- `accessibility/skills/color_contrast.md` — dark mode colors must ALSO meet WCAG AA contrast: validate all dark color pairs (dark text on dark background) at 4.5:1 for normal text, 3:1 for large text. Use `_relative_luminance()` and `_contrast_ratio()` already in `converter.py`
**Security:** No new input paths. Gradient angle clamped to 0-360. Color hex values validated by 33.2 transform layer. Magic color values (#010101, #fefefe) are static constants.
**Verify:** Figma file with "Light"/"Dark" variable modes → both `colors` and `dark_colors` populated. Dark mode CSS block contains all three tiers: meta tags, `@media (prefers-color-scheme: dark)` rules with `!important`, and `[data-ogsc]`/`[data-ogsb]` selectors. Magic colors used: generated dark CSS uses `#010101` instead of `#000000` and `#fefefe` instead of `#ffffff`. Dark color pairs validated for WCAG AA contrast. Gradient fill → `background: linear-gradient(...)` in CSS + `bgcolor="{fallback_hex}"` attribute + VML `<v:fill type="gradient">` for Outlook. Gradient with 3 stops → all stops present in CSS. CTA buttons have 1x1 pixel background trick to prevent Outlook inversion. No dark mode in Figma → `dark_colors` empty, no dark CSS generated, no meta tags added. `make test` passes.

### ~~33.8 Design Context Enrichment & Scaffolder Integration~~ DONE `[Backend + Frontend]`
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

### ~~33.9 Builder Annotations for Visual Builder Sync~~ DONE `[Backend]`
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
| CRAG accept/reject gate | Corrections verified via before/after issue count — regressions rejected, originals preserved |

---

## Phase 34 — CRAG Accept/Reject Gate

> The CRAG validation loop (Phase 16.5) detects unsupported CSS in agent-generated HTML, retrieves ontology fallbacks, and asks the LLM to apply them. But its acceptance gate is blind: if the corrected output is longer than 50 characters, it ships. The LLM can break MSO conditionals, drop sections, introduce new unsupported CSS, or bloat past Gmail's 102KB clip threshold — and CRAG will accept it. QA catches these regressions *after* CRAG, but by then the original pre-CRAG HTML is gone. The response ships with the damaged version plus QA warnings.
>
> This phase adds a before/after compatibility check: re-run `unsupported_css_in_html()` on the corrected output and reject corrections that didn't reduce qualifying issues. Zero LLM cost — the function is a pure regex scan already imported in the same file. Also adds structured logging for observability and targeted tests for the new gate.
>
> **Dependency note:** Independent of Phases 32–33. Can be implemented at any time. The fix is contained to `validation_loop.py` + its test file.

- [ ] 34.1 Accept/reject gate on CRAG corrections
- [ ] 34.2 Structured CRAG observability logging
- [ ] 34.3 Tests for accept/reject gate

### 34.1 Accept/Reject Gate on CRAG Corrections `[Backend]`
**What:** After CRAG calls the LLM and extracts corrected HTML, re-scan the corrected output with `unsupported_css_in_html()` using the same severity threshold. Compare qualifying issue counts before vs. after. Only accept the correction if the post-correction count is strictly lower. Otherwise reject and return the original HTML unchanged.
**Why:** The current acceptance gate (`validation_loop.py:129-131`) only checks `len(corrected) < 50`. This means any non-trivial LLM output is accepted regardless of whether it actually fixed the compatibility issues or introduced new ones. The LLM is instructed to "preserve all other HTML exactly as-is" but frequently: (1) breaks MSO conditional balancing while swapping CSS properties, (2) drops sections or structural elements during the rewrite, (3) introduces new unsupported CSS alongside the fallback code, (4) inflates HTML size with verbose table fallbacks. All of these produce output >50 chars, so they pass the current gate. `unsupported_css_in_html()` is already imported and called 10 lines earlier in the same method — reusing it adds zero new dependencies and near-zero latency (pure regex scan over CSS contexts).
**Implementation:**
- In `app/ai/agents/validation_loop.py`, after the existing length gate (line 129–131) and before the success log (line 133), add post-correction scanning:
  ```python
  # Accept/reject gate: verify correction actually improved compatibility
  post_issues = unsupported_css_in_html(corrected)
  post_qualifying = [
      issue for issue in post_issues
      if severity_order.get(str(issue["severity"]), 2) <= threshold
  ]

  if len(post_qualifying) >= len(qualifying):
      logger.warning(
          "agents.crag.correction_rejected",
          pre_issues=len(qualifying),
          post_issues=len(post_qualifying),
          reason="correction did not reduce qualifying issues",
      )
      return html, []
  ```
- The `severity_order` and `threshold` variables are already in scope from step 2 of the method — no new locals needed
- The `qualifying` list (pre-correction issues) is already computed at line 48–50 — reuse it for the comparison
- Keep the existing `len(corrected) < 50` gate above this new gate — it's a fast short-circuit for degenerate outputs that avoids the regex scan entirely
- Move the `corrections` list construction and success log below the new gate so they only execute on accepted corrections
**Security:** No new input paths. `unsupported_css_in_html()` operates on sanitized HTML (already passed through `extract_html()` + `sanitize_html_xss()` at line 126–127). No new LLM calls, no new config, no new dependencies.
**Verify:** Unit test: CRAG correction that introduces new unsupported CSS → rejected, original returned. Unit test: CRAG correction that fixes 2 of 3 issues but adds 1 new → net reduction, accepted. Unit test: CRAG correction that fixes all issues → accepted. Existing tests still pass (the new gate is transparent when corrections improve things). `make check` passes.

### 34.2 Structured CRAG Observability Logging `[Backend]`
**What:** Enhance CRAG logging to emit structured fields that enable monitoring correction acceptance rates, rejection reasons, and per-property fix effectiveness.
**Why:** Currently CRAG logs `agents.crag.correction_applied` on success and `agents.crag.output_too_short` on length failure — but there's no visibility into *what* was fixed vs. *what* regressed. When the accept/reject gate starts rejecting corrections, operators need to understand: which CSS properties are the LLM failing to fix? Which fallback techniques produce regressions? Is the rejection rate climbing (suggesting prompt degradation or ontology drift)? Structured logging fields enable dashboards and alerting without log parsing.
**Implementation:**
- Update the success log (`agents.crag.correction_applied`) to include before/after counts and per-property outcomes:
  ```python
  logger.info(
      "agents.crag.correction_accepted",
      pre_issues=len(qualifying),
      post_issues=len(post_qualifying),
      issues_fixed=len(qualifying) - len(post_qualifying),
      corrections=corrections,
      original_length=len(html),
      corrected_length=len(corrected),
  )
  ```
- The rejection log (`agents.crag.correction_rejected`) added in 34.1 already includes `pre_issues`, `post_issues`, and `reason` — no changes needed
- Update `agents.crag.issues_detected` to include property IDs for correlation:
  ```python
  logger.info(
      "agents.crag.issues_detected",
      total_issues=len(issues),
      qualifying_issues=len(qualifying),
      qualifying_property_ids=[str(i["property_id"]) for i in qualifying],
      min_severity=min_severity,
  )
  ```
- Rename `agents.crag.correction_applied` → `agents.crag.correction_accepted` for symmetry with `agents.crag.correction_rejected`
- Update the `base.py` caller log at line 313 to use the same event name:
  ```python
  logger.info(
      f"agents.{self.agent_name}.crag_accepted",
      corrections=crag_corrections,
  )
  ```
**Security:** Logging only — no new endpoints, no PII in log fields (property IDs and counts only). Verify no CSS values (which could contain user content) appear in log output.
**Verify:** Enable CRAG, trigger a correction → `agents.crag.correction_accepted` log includes `pre_issues`, `post_issues`, `issues_fixed`. Trigger a rejection → `agents.crag.correction_rejected` log includes `pre_issues`, `post_issues`, `reason`. Grep production log output for PII — none found in CRAG events. `make check` passes.

### 34.3 Tests for Accept/Reject Gate `[Backend]`
**What:** Add targeted tests in `app/ai/agents/tests/test_validation_loop.py` covering the new accept/reject gate behavior: regressions rejected, partial improvements accepted, full fixes accepted, and edge cases (same count, new property types).
**Why:** The existing test suite (`TestCRAGMixin`) covers: no issues, severity filtering, successful correction, LLM failure, empty output, no-fallback instructions, and severity threshold. None of these tests verify that a "successful" LLM call with bad output gets rejected. The accept/reject gate is the critical safety mechanism — it must be tested explicitly.
**Implementation:**
- Add new test class `TestCRAGAcceptRejectGate` in `test_validation_loop.py`:
  ```python
  class TestCRAGAcceptRejectGate:
      """Test the before/after compatibility gate."""

      @pytest.mark.asyncio
      async def test_correction_introducing_new_issues_rejected(self) -> None:
          """LLM 'fixes' flex but introduces gap → same issue count → rejected."""
          # Pre: 1 qualifying issue (display:flex)
          # Post: 1 qualifying issue (gap) — different property, same count
          # Expected: rejection, original returned

      @pytest.mark.asyncio
      async def test_correction_increasing_issues_rejected(self) -> None:
          """LLM output has MORE issues than input → rejected."""
          # Pre: 1 qualifying issue
          # Post: 2 qualifying issues
          # Expected: rejection, original returned

      @pytest.mark.asyncio
      async def test_partial_fix_accepted(self) -> None:
          """LLM fixes 2 of 3 issues → net reduction → accepted."""
          # Pre: 3 qualifying issues
          # Post: 1 qualifying issue
          # Expected: accepted, corrected HTML returned

      @pytest.mark.asyncio
      async def test_full_fix_accepted(self) -> None:
          """LLM fixes all issues → 0 post issues → accepted."""
          # Pre: 2 qualifying issues
          # Post: 0 qualifying issues
          # Expected: accepted, corrected HTML returned

      @pytest.mark.asyncio
      async def test_length_gate_runs_before_compatibility_gate(self) -> None:
          """Empty output rejected by length gate — compatibility scan never runs."""
          # LLM returns "" → length gate rejects → unsupported_css_in_html not called on ""
  ```
- Mock strategy: patch `unsupported_css_in_html` with `side_effect` that returns different results for the original HTML vs. the corrected HTML. Use the call order (first call = pre-scan on original, inside the method at line 43; the pre-scan result is already captured in `qualifying`) — but since `unsupported_css_in_html` is called TWICE now (once on original at line 43, once on corrected after the new gate), the mock's `side_effect` can return `[issue_list_1, issue_list_2]` to simulate before/after.
- Verify that rejected corrections return `(original_html, [])` — empty corrections list signals no changes applied
- Verify that accepted corrections return `(corrected_html, [property_ids])` — non-empty corrections list
**Security:** Tests only — no production code paths, no PII, no real LLM calls.
**Verify:** `python -m pytest app/ai/agents/tests/test_validation_loop.py -v` — all existing + new tests pass. `make check` passes. No test relies on real ontology data (all mocked).

---

## Phase 35 — Next-Gen Design-to-Email Pipeline (MJML + AI Intelligence + Standards)

> **The design-to-email pipeline (Phases 31–33) works end-to-end but has structural limitations.** The converter (`converter.py`) hand-rolls every email HTML pattern — ghost tables, MSO conditionals, responsive column stacking, VML buttons — duplicating battle-tested logic that MJML already handles. The layout analyzer classifies sections by naming convention heuristics that fail on arbitrarily-named Figma frames. There's no visual fidelity validation (no comparison between Figma design and converted output). Token input is Figma-only (no W3C Design Tokens standard). Sync is manual (no Figma webhooks). And AI agents fix converter mistakes repeatedly without feeding corrections back into the converter itself.
>
> This phase addresses all of these with 5 pillars: **(1)** MJML as an intermediate representation — offload responsive email compilation to a mature library, **(2)** Figma node tree normalization — clean input produces better output, **(3)** AI-powered layout intelligence — LLM fallback for unclassifiable sections + vision-based fidelity scoring + self-improving converter, **(4)** W3C Design Tokens + caniemail.com data — standards compliance and live client support data, **(5)** Figma webhooks + incremental conversion — real-time sync with section-level caching.
>
> **Dependency note:** Builds on Phase 33 (token pipeline) and Phase 27 (rendering infrastructure). Independent of Phase 32 (agent intelligence) and Phase 34 (CRAG gate). The MJML sidecar endpoint (35.1) is prerequisite for all MJML subtasks. AI subtasks (35.5–35.7) can run in parallel with MJML work.

- [ ] 35.1 MJML compilation service in Maizzle sidecar
- [ ] 35.2 Figma node tree normalizer
- [ ] 35.3 MJML generation backend in converter
- [ ] 35.4 MJML email section templates
- [ ] 35.5 AI layout intelligence & semantic detection
- [ ] 35.6 AI visual fidelity scoring pipeline
- [ ] 35.7 AI conversion learning loop
- [ ] 35.8 W3C Design Tokens & caniemail.com integration
- [ ] 35.9 Figma webhooks & live preview sync
- [ ] 35.10 Incremental conversion & section caching
- [ ] 35.11 Tests & integration verification

### 35.1 MJML Compilation Service in Maizzle Sidecar `[Sidecar]`
**What:** Add MJML as an npm dependency to the Maizzle sidecar and expose a `POST /compile-mjml` endpoint that accepts MJML markup and returns compiled, production-ready email HTML with inline CSS, MSO conditionals, and responsive media queries.
**Why:** MJML (`mjmlio/mjml`, MIT, ~17k GitHub stars) is the industry standard for email HTML compilation. It handles the hardest parts of email rendering — responsive column stacking, ghost tables for Outlook, MSO conditional comments, CSS inlining, image sizing, `@media` queries — with output battle-tested across 50+ email clients. Our converter currently hand-rolls all of these patterns in `converter.py:_render_multi_column_row()`, `node_to_email_html()`, and the `EMAIL_SKELETON` template. MJML compilation eliminates ~60% of the low-level HTML generation code and produces more reliable output. The Maizzle sidecar already runs Node.js and accepts HTML via HTTP — adding MJML is a natural extension.
**Implementation:**
- Add `mjml` npm dependency to `services/maizzle-builder/package.json` (MIT license, ~2MB)
- Add `POST /compile-mjml` endpoint to `services/maizzle-builder/index.js`:
  ```
  Request:  { mjml: string, options?: { minify?: bool, beautify?: bool, validationLevel?: "strict"|"soft"|"skip" } }
  Response: { html: string, errors: MjmlError[], build_time_ms: number }
  ```
- MJML compilation options: `keepComments: false`, `fonts: {}` (we inject font links ourselves), `minify: production`, `validationLevel: "soft"` (warn but don't fail on custom attributes like `data-slot-name`)
- After MJML compilation, run existing `postcss-email-optimize.js` if `target_clients` provided — MJML output still benefits from ontology-driven CSS elimination
- Add health check extension: `GET /health` response includes `mjml_version` field
- Wire `MaizzleClient` in `app/design_sync/converter_service.py` to call the new endpoint via the existing HTTP client pattern used for `/build`
- Add `compile_mjml()` method to `MaizzleClient`:
  ```python
  async def compile_mjml(self, mjml: str, *, minify: bool = True, target_clients: list[str] | None = None) -> MjmlCompileResult
  ```
- `MjmlCompileResult` dataclass: `html: str`, `errors: list[MjmlError]`, `build_time_ms: float`
**Security:** MJML is a template compiler — no network calls, no eval, no file system access. Input is our own generated MJML (not user-provided). Output is HTML that still passes through `sanitize_html_xss()` before reaching users. No new attack surface.
**Verify:** `POST /compile-mjml` with `<mjml><mj-body><mj-section><mj-column><mj-text>Hello</mj-text></mj-column></mj-section></mj-body></mjml>` returns valid HTML with `<table>` layout, MSO conditionals, and inline CSS. Invalid MJML returns errors array. `/health` includes `mjml_version`. Existing `/build` and `/preview` endpoints unchanged. `npm test` passes in sidecar.

### 35.2 Figma Node Tree Normalizer `[Backend]`
**What:** Add a `normalize_tree()` pre-processing pass in `app/design_sync/figma/tree_normalizer.py` that cleans and simplifies the Figma node tree before it reaches the layout analyzer or converter. Handles: instance resolution, group flattening, hidden node removal, auto-layout inference, and contiguous text merging.
**Why:** The Figma REST API returns the raw document tree including invisible nodes, deeply nested GROUP wrappers, unresolved COMPONENT_INSTANCE overrides, and frames without auto-layout that use absolute positioning. The converter and layout analyzer each work around these issues independently (`_has_visible_content()` in `converter_service.py:263`, y-position grouping with 20px tolerance in `layout_analyzer.py`, 6-level depth guard in `converter.py`). A single normalization pass produces a cleaner tree that all downstream stages benefit from, similar to Locofy's "Design Optimizer" pre-processing step.
**Implementation:**
- Create `app/design_sync/figma/tree_normalizer.py`:
  ```python
  def normalize_tree(root: DesignNode, *, raw_file_data: dict[str, Any] | None = None) -> DesignNode:
  ```
- **Transform 1 — Remove invisible nodes:** Drop nodes where `visible=False` or `opacity=0.0`. Recurse depth-first, prune leaf-up. Preserves nodes inside `<!--[if mso]>` blocks (MSO-only content is intentionally hidden from visual tree).
- **Transform 2 — Flatten redundant groups:** If a GROUP node has exactly one child and no meaningful properties (no fill, no stroke, no effects, no auto-layout), replace the GROUP with its child, inheriting position. Reduces nesting depth by 1–3 levels in typical Figma files.
- **Transform 3 — Resolve component instances:** If `raw_file_data` provided, resolve INSTANCE nodes by overlaying override properties onto the source component's node tree. Uses Figma's `overrides` array format: `{"id": "node_id", "overriddenFields": ["characters", "fills"]}`. Result: INSTANCE nodes become FRAME nodes with resolved values.
- **Transform 4 — Infer auto-layout from positioning:** For FRAME nodes without `layout_mode`, analyze children's x/y coordinates:
  - If all children share the same x (within 5px tolerance) and are stacked vertically → infer `layout_mode=VERTICAL`, compute `item_spacing` from y-deltas
  - If all children share the same y (within 5px tolerance) and are side-by-side → infer `layout_mode=HORIZONTAL`, compute `item_spacing` from x-deltas
  - Otherwise → leave as-is (true absolute positioning)
  - Set `inferred_layout=True` flag so downstream code can distinguish real vs. inferred auto-layout
- **Transform 5 — Merge contiguous text nodes:** Adjacent TEXT children within the same parent that share identical styling (family, size, weight, color) and are vertically contiguous (y-delta equals line-height) → merge into single TEXT node with combined content. Reduces text fragmentation common in Figma exports.
- Wire into `converter_service.py:convert()` — call `normalize_tree()` on each page's root before `analyze_layout()`:
  ```python
  normalized = normalize_tree(page_root, raw_file_data=raw_file_data)
  layout = analyze_layout(normalized, ...)
  ```
- Add `NormalizationStats` dataclass returned alongside: `nodes_removed: int`, `groups_flattened: int`, `instances_resolved: int`, `layouts_inferred: int`, `texts_merged: int` — logged as structured event `design_sync.tree_normalized`
**Security:** Pure tree transformation — no network calls, no file system access. Input is already-parsed Figma API response. `raw_file_data` is the same dict used in `converter_service.py` today. No new user input vectors.
**Verify:** Tree with 3 hidden nodes → `normalize_tree()` returns tree without them, `nodes_removed=3`. GROUP with single FRAME child → flattened. FRAME with 3 vertically-stacked children at x=0 → `layout_mode=VERTICAL` inferred. Two adjacent TEXT nodes with same style → merged. Existing converter output unchanged for auto-layout frames (normalization is additive). `make test` passes.

### 35.3 MJML Generation Backend in Converter `[Backend]`
**What:** Add a third conversion path `_convert_mjml()` in `converter_service.py` that generates MJML markup from the layout analysis, then compiles via the sidecar's `/compile-mjml` endpoint. This replaces the hand-rolled table generation for the common case while keeping the recursive converter as fallback.
**Why:** The existing `_convert_recursive()` path manually generates every email HTML pattern — multi-column ghost tables (`_render_multi_column_row()`), VML buttons (`_render_button()`), MSO resets, responsive stacking, spacer rows. This is ~800 lines of intricate HTML generation in `converter.py` that duplicates what MJML handles automatically. By generating `<mj-section>/<mj-column>/<mj-text>/<mj-button>/<mj-image>` markup and letting MJML compile it, we get: (a) responsive stacking on mobile for free, (b) Outlook ghost tables generated by MJML's battle-tested compiler, (c) CSS inlining handled by MJML, (d) fewer edge-case bugs in our code. The recursive converter remains for designs that use advanced features MJML can't express (deep nesting, arbitrary VML, custom MSO blocks).
**Implementation:**
- Add `_convert_mjml()` method to `DesignConverterService`:
  ```python
  async def _convert_mjml(
      self, layout: DesignLayoutDescription, palette: BrandPalette,
      typography: dict, tokens: ExtractedTokens, *, container_width: int = 600,
      target_clients: list[str] | None = None,
  ) -> ConversionResult:
  ```
- **Section-to-MJML mapping** (one function per section type):

  | EmailSectionType | MJML output |
  |------------------|-------------|
  | HEADER | `<mj-section>` with `<mj-column>` + `<mj-image>` (logo) + `<mj-text>` (nav) |
  | HERO | `<mj-hero>` or `<mj-section>` with `background-url` + `<mj-text>` (heading) + `<mj-button>` |
  | CONTENT | `<mj-section>` + `<mj-column>` + `<mj-text>` (body) |
  | CTA | `<mj-section>` + `<mj-button>` with brand colors |
  | FOOTER | `<mj-section>` + `<mj-text>` (small, muted) |
  | TWO_COLUMN | `<mj-section>` with 2x `<mj-column width="50%">` |
  | THREE_COLUMN | `<mj-section>` with 3x `<mj-column width="33.33%">` |
  | MULTI_COLUMN | `<mj-section>` with N x `<mj-column>` using proportional widths from `_calculate_column_widths()` |
  | IMAGE | `<mj-section>` + `<mj-image>` with `src`, `alt`, `width` |
  | SPACER | `<mj-section>` + `<mj-spacer height="Npx">` |

- **Token injection into MJML attributes:**
  - Colors: `background-color`, `color` attributes on `<mj-*>` elements from `palette`
  - Typography: `font-family`, `font-size`, `font-weight`, `line-height`, `letter-spacing` from `typography` dict
  - Spacing: `padding` on `<mj-section>` and `<mj-column>` from `section.padding_*` fields
  - Dark mode: `<mj-attributes>` with `<mj-all>` defaults + custom `<mj-class>` for dark-mode-aware elements
- **MJML wrapper template:**
  ```xml
  <mjml>
    <mj-head>
      <mj-attributes>
        <mj-all font-family="{body_font_stack}" />
        <mj-text font-size="{body_size}px" color="{text_color}" line-height="{line_height}" />
        <mj-button background-color="{primary}" color="{btn_text}" font-size="16px" inner-padding="12px 24px" />
      </mj-attributes>
      <mj-style>{dark_mode_css}</mj-style>
      <mj-style>{custom_styles}</mj-style>
    </mj-head>
    <mj-body width="{container_width}px" background-color="{bg_color}">
      {sections_mjml}
    </mj-body>
  </mjml>
  ```
- Preserve `data-slot-name` and `data-component-name` attributes via MJML's `mj-html-attributes` or by post-processing compiled HTML
- Call `self._maizzle_client.compile_mjml(mjml_str, target_clients=target_clients)` to compile
- Add `output_format: Literal["html", "mjml"] = "html"` parameter to `convert()` method — when `"mjml"`, use `_convert_mjml()` path
- Fallback logic: if MJML compilation returns errors with `validationLevel="strict"`, log warning and fall back to `_convert_recursive()`
**Security:** Generated MJML contains only values from validated `ExtractedTokens` (already passed through `validate_and_transform()`). Text content is HTML-escaped via `html.escape()`. No user-provided MJML. Compiled HTML still passes through `sanitize_html_xss()`.
**Verify:** Convert the 15 golden templates via MJML path → all produce valid email HTML. Compare MJML output vs. recursive output for the same Figma file → MJML output renders correctly in Litmus/EOA for 14 client profiles (Phase 27). Multi-column layouts stack on mobile (< 480px). VML buttons render in Outlook. `make test` passes.

### 35.4 MJML Email Section Templates `[Backend + Sidecar]`
**What:** Create a library of pre-built, token-injectable MJML section templates in `app/design_sync/mjml_templates/` for the 10 common email section types. These templates are used by `_convert_mjml()` and by `ComponentMatcher` as an alternative to the existing HTML component templates.
**Why:** The MJML generation in 35.3 builds MJML programmatically from section data. For well-known patterns (hero with background image, 2-column product grid, CTA with VML button), pre-built MJML templates produce higher-quality output than programmatic generation because they encode email-specific best practices (image-over-text layering, mobile-first CTA sizing, footer legal text patterns). Emailify and Stripo both use template libraries for their section types — this is the industry standard approach.
**Implementation:**
- Create `app/design_sync/mjml_templates/` directory with Jinja2-templated MJML files:
  - `hero.mjml.j2` — Full-width hero with background image/color, heading, subheading, CTA button. Supports: image `src`/`alt`/`width`, heading text + styling, body text, button text + URL + colors. `<mj-hero>` with `mode="fluid-height"` for responsive.
  - `content_single.mjml.j2` — Single-column text content. Heading + body paragraphs + optional image. Uses `<mj-text>` with heading detection from `TextBlock.is_heading`.
  - `content_two_col.mjml.j2` — Two equal columns. Each column: optional image + heading + text. Uses 2x `<mj-column width="50%">` with `<mj-image>` + `<mj-text>`.
  - `content_three_col.mjml.j2` — Three equal columns. Feature cards or product grid. 3x `<mj-column width="33.33%">`.
  - `content_multi_col.mjml.j2` — N columns with proportional widths from layout analysis. Uses `mj-column width="{{ col.width_pct }}%"`.
  - `cta.mjml.j2` — Centered call-to-action section. `<mj-button>` with brand colors, border-radius, inner-padding. 44px min touch target enforced via `height` attribute.
  - `header.mjml.j2` — Logo + optional navigation links. `<mj-image>` for logo with `href` link, `<mj-navbar>` for nav items.
  - `footer.mjml.j2` — Legal text, social links, unsubscribe. `<mj-social>` with `<mj-social-element>` for social icons. Small muted text for legal.
  - `image_full.mjml.j2` — Full-width image section. `<mj-image>` with `fluid-on-mobile="true"`, `alt`, `src`, `width`, `href`.
  - `spacer.mjml.j2` — Vertical spacer. `<mj-section><mj-column><mj-spacer height="{{ height }}px" /></mj-column></mj-section>`.
- All templates accept a `ctx` dict with: `palette` (BrandPalette), `typography` (heading/body font stacks + sizes), `spacing` (padding values), `dark_colors` (optional), `content` (section-specific: texts, images, buttons)
- Create `MjmlTemplateEngine` class in `app/design_sync/mjml_template_engine.py`:
  ```python
  class MjmlTemplateEngine:
      def render_section(self, section: EmailSection, ctx: MjmlTemplateContext) -> str:
      def render_email(self, sections: list[EmailSection], ctx: MjmlTemplateContext) -> str:
  ```
- Wire into `_convert_mjml()`: for each `EmailSection`, look up matching template → render with section data → assemble into full MJML document → compile
- Wire into `ComponentMatcher`: add `mjml_template` field to `ComponentMatch` alongside existing `component_slug` — when MJML mode active, use MJML template instead of HTML component
**Security:** Templates are Jinja2 with `autoescape=True` — all injected values are HTML-escaped. No user-provided template paths (templates are hardcoded in the engine). Template directory is read-only at runtime.
**Verify:** Each of the 10 templates renders valid MJML (pass MJML strict validation). Compiled HTML for each template renders correctly in Gmail Web + Outlook desktop + Apple Mail (3-client smoke test via local rendering). Templates with dark mode context produce `prefers-color-scheme` media queries. `make test` passes.

### 35.5 AI Layout Intelligence & Semantic Detection `[Backend + AI]`
**What:** Add AI-powered fallback for layout analysis when heuristic classification fails, plus semantic content detection (logo, social links, unsubscribe, legal text) from visual/structural cues rather than naming conventions alone. This is the biggest differentiator vs. tools like Emailify that require annotated layers.
**Why:** The current `layout_analyzer.py` classifies sections by matching frame names against `_SECTION_PATTERNS` regex patterns. This works for well-named designs (MJML convention, descriptive names) but fails for generic names (`Frame 1`, `Group 42`, auto-generated Figma names). Market analysis shows Kombai uses deep learning for similar intent detection. Our approach uses targeted LLM calls (cheaper, more controllable) as a fallback when heuristics fail, plus a vision model for content role detection.
**Implementation:**
- **AI Layout Classifier** — `app/design_sync/ai_layout_classifier.py`:
  ```python
  async def classify_section(
      section: EmailSection, *, node_data: DesignNode, siblings: list[EmailSection],
  ) -> SectionClassification:
  ```
  - Called only when `layout_analyzer.py` assigns `EmailSectionType.UNKNOWN` or confidence < 0.5
  - Builds a compact prompt with: node tree structure (types + dimensions + colors, not raw JSON), sibling section types (positional context — "this is between a HERO and a FOOTER"), text content snippets (first 100 chars per text block), image count + dimensions
  - Uses lightweight model (Haiku) with structured output: `{ section_type: EmailSectionType, column_layout: ColumnLayout, confidence: float, reasoning: str }`
  - Cost: ~200 tokens input + ~50 tokens output per unclassified section = ~$0.0001 per call
  - Cache classification by node tree hash — same structure won't trigger LLM twice
- **Semantic Content Detector** — `app/design_sync/ai_content_detector.py`:
  ```python
  async def detect_content_roles(sections: list[EmailSection]) -> list[ContentRoleAnnotation]:
  ```
  - Detects roles: `logo`, `social_links`, `unsubscribe_link`, `legal_text`, `navigation`, `preheader`, `view_in_browser`, `address`
  - Two-pass approach:
    1. **Heuristic pass** (free, fast): regex patterns on text content — "unsubscribe" → `unsubscribe_link`, "©" or "copyright" → `legal_text`, URL patterns for social platforms → `social_links`, image in first section with small height → `logo`
    2. **LLM pass** (only for undetected roles in sections where heuristics found nothing): send text content + position info → structured output with role annotations
  - Annotations stored in `EmailSection.content_roles: list[str]` — used by MJML template selection (footer template for sections with `legal_text` + `unsubscribe_link`, header template for sections with `logo`)
- **Section Position Intelligence:**
  - First section in email → boost `HEADER` probability
  - Last section → boost `FOOTER` probability
  - Section after `HERO` → boost `CONTENT` probability
  - Section with single large image and text overlay → boost `HERO` probability
  - These positional heuristics are added to `layout_analyzer.py` directly (no LLM needed)
- Wire into `layout_analyzer.py:analyze_layout()`:
  ```python
  # After heuristic classification
  unknown_sections = [s for s in sections if s.section_type == EmailSectionType.UNKNOWN]
  if unknown_sections:
      classifications = await classify_sections_batch(unknown_sections, node_data=...)
      for section, classification in zip(unknown_sections, classifications):
          section.section_type = classification.section_type
          section.column_layout = classification.column_layout
  ```
- Add `DESIGN_SYNC__AI_LAYOUT_ENABLED` config flag (default `True`) — disable for deterministic-only mode
**Security:** LLM receives only structural metadata (dimensions, types, text snippets) — no auth tokens, no user PII, no Figma API credentials. Structured output constrains LLM to enum values only. Content detection regex runs before LLM — most roles detected without AI.
**Verify:** Figma file with generic frame names (`Frame 1` through `Frame 6`) → AI classifier correctly identifies header/hero/content/cta/content/footer with confidence > 0.7. Section containing "© 2026 Acme Corp | Unsubscribe" → `legal_text` + `unsubscribe_link` roles detected by heuristic (no LLM call). Classification cache: same node tree hash → second call returns cached result, no LLM invocation. `DESIGN_SYNC__AI_LAYOUT_ENABLED=false` → no LLM calls, UNKNOWN sections stay UNKNOWN. `make test` passes.

### 35.6 AI Visual Fidelity Scoring Pipeline `[Backend + Rendering]`
**What:** After converting a Figma design to HTML, automatically capture a screenshot of the rendered HTML and compare it against the Figma frame image. Produce a per-section visual fidelity score (0–100%) and flag regions where the converter output drifts from design intent. Uses the existing rendering infrastructure (Phase 27) and Figma's image export API.
**Why:** No Figma-to-email tool currently offers automated visual fidelity scoring. Locofy claims 95%+ match scores for web conversion but doesn't publish their methodology. For email, visual fidelity is harder because table layout is inherently less precise than CSS flexbox — but measuring it is essential for knowing whether the converter is improving. This closes the feedback loop: design → convert → render → score → identify drift → fix converter. Without scoring, we only discover visual regressions when humans compare screenshots manually.
**Implementation:**
- **Figma frame capture** — extend `FigmaDesignSyncService` with:
  ```python
  async def export_frame_image(self, file_key: str, node_id: str, *, scale: float = 2.0, format: str = "png") -> bytes:
  ```
  Uses Figma REST API `GET /v1/images/{file_key}?ids={node_id}&scale=2&format=png` — returns CDN URL, download image bytes.
- **HTML rendering** — use existing `LocalRenderingProvider` from `app/rendering/local/`:
  ```python
  async def render_html_to_image(self, html: str, *, width: int = 600, device_scale_factor: float = 2.0) -> bytes:
  ```
  Playwright headless Chromium renders the converted email HTML at the container width. Returns PNG bytes.
- **Visual comparison engine** — `app/design_sync/visual_scorer.py`:
  ```python
  @dataclass(frozen=True)
  class FidelityScore:
      overall: float          # 0.0–1.0
      ssim: float             # Structural Similarity Index
      sections: list[SectionScore]  # Per-section breakdown
      diff_image: bytes | None      # Visual diff overlay (red = differences)

  async def score_fidelity(
      figma_image: bytes, html_image: bytes, *, sections: list[EmailSection],
  ) -> FidelityScore:
  ```
  - **SSIM comparison** (Structural Similarity Index): Uses `scikit-image` `structural_similarity()` — standard metric for image quality, returns 0–1. Handles different aspect ratios by padding shorter image.
  - **Per-section scoring**: Slice both images into horizontal bands matching section y-coordinates from `DesignLayoutDescription`. Compute SSIM per band. Identify which sections have lowest fidelity.
  - **Diff image generation**: Overlay red highlights on regions where pixel difference exceeds threshold (20% luminance delta). Store as PNG for frontend display.
  - **Tolerance adjustments**: Text anti-aliasing differences are normal (Figma uses Skia, Chromium uses different sub-pixel rendering). Apply Gaussian blur (σ=1.0) before comparison to smooth anti-aliasing artifacts. Color tolerance of ΔE < 3.0 (imperceptible to human eye).
- **Integration into conversion pipeline** — add optional `score_fidelity: bool = False` parameter to `DesignImportService.run_conversion()`:
  - When enabled: after conversion, fetch Figma frame images for each section → render HTML → compute fidelity scores → store in `ConversionResult.fidelity_scores`
  - Store scores in `DesignImport.metadata_json["fidelity"]` for historical tracking
  - Frontend: display fidelity badge (green > 85%, yellow 70–85%, red < 70%) on import results
- Add `GET /api/v1/design-sync/imports/{id}/fidelity` endpoint returning scores + diff image
- Add `scikit-image` to `requirements.txt` (BSD license, already a transitive dep via other scientific packages)
**Security:** Figma frame export requires existing auth token (already stored encrypted in `DesignConnection`). Screenshot rendering is local (Playwright in sandbox). Image comparison is pure computation — no network calls. Diff images contain design content only (no secrets). Fidelity endpoint requires same auth as import endpoint.
**Verify:** Convert a Figma file with known simple layout (single-column, 3 sections) → fidelity score > 85%. Intentionally break converter output (wrong colors, missing section) → score drops below 70%. Per-section scores correctly identify the broken section. Diff image highlights the difference region. `make test` passes.

### 35.7 AI Conversion Learning Loop `[Backend + AI]`
**What:** When AI agents (Outlook Fixer, Dark Mode, Code Reviewer) repeatedly fix the same converter output patterns, automatically extract those patterns as converter rules. This creates a self-improving pipeline where agent corrections feed back into the converter, reducing future agent work and improving first-pass quality.
**Why:** Currently, agents fix converter mistakes at runtime — every email goes through the same fix cycle. Example: if the converter consistently produces `<td style="padding:20px">` but the Outlook Fixer always rewrites it to `<td style="padding:20px 20px 20px 20px;">` (longhand for Word engine), that pattern should become a converter rule so the Outlook Fixer doesn't need to fix it every time. This is the "learning" part of the AI pipeline — moving validated corrections upstream. Locofy's "Design Optimizer" learns from user corrections in a similar feedback loop.
**Implementation:**
- **Correction pattern tracker** — `app/design_sync/correction_tracker.py`:
  ```python
  @dataclass(frozen=True)
  class CorrectionPattern:
      agent: str                    # "outlook_fixer", "dark_mode", etc.
      pattern_hash: str             # Hash of (input_pattern, output_pattern)
      input_pattern: str            # Regex matching converter output
      output_pattern: str           # Agent's correction
      occurrences: int              # How many times seen
      first_seen: datetime
      last_seen: datetime
      confidence: float             # Consistency score (same correction every time?)

  class CorrectionTracker:
      async def record_correction(self, agent: str, original_html: str, corrected_html: str) -> None:
      async def get_frequent_patterns(self, *, min_occurrences: int = 5, min_confidence: float = 0.9) -> list[CorrectionPattern]:
      async def suggest_converter_rules(self) -> list[ConverterRuleSuggestion]:
  ```
- **Diff extraction**: When an agent returns modified HTML, compute a structural diff (not text diff) using `htmldiff` — identifies which elements/attributes changed. Group changes by pattern (e.g., "shorthand padding → longhand padding on `<td>`" is one pattern regardless of which `<td>` or what values).
- **Pattern storage**: Store in `data/correction_patterns.jsonl` (append-only log). Periodic aggregation into `data/correction_rules.json` (deduplicated, ranked by frequency).
- **Rule suggestion engine**: When a pattern reaches threshold (5+ occurrences, 90%+ consistency), generate a `ConverterRuleSuggestion`:
  ```python
  @dataclass
  class ConverterRuleSuggestion:
      description: str              # Human-readable: "Expand shorthand padding to longhand on <td>"
      agent_source: str             # Which agent discovered this
      pattern: CorrectionPattern
      suggested_code: str           # Python snippet for converter.py
      status: Literal["suggested", "approved", "rejected", "applied"]
  ```
- **Integration points**:
  - Hook into `BaseAgentService.validate_output()` — after agent returns HTML, call `tracker.record_correction(agent_name, input_html, output_html)` if HTML changed
  - Add `GET /api/v1/design-sync/correction-patterns` endpoint (admin only) — list frequent patterns with suggested converter rules
  - Add `POST /api/v1/design-sync/correction-patterns/{id}/approve` — mark a suggestion as approved (developer reviews before applying)
  - Approved rules are NOT auto-applied to `converter.py` — they're surfaced as developer tasks. The system suggests, humans decide.
- **Dashboard integration**: Frontend card in design-sync settings showing: top 5 correction patterns, suggested rules, approval status. Links to specific converter code locations.
**Security:** Correction patterns contain HTML snippets from agent input/output — these are already sanitized. Pattern storage is local JSONL (no external calls). Admin-only endpoints require `admin` role. No auto-modification of converter code — human approval required.
**Verify:** Run 10 conversions where Outlook Fixer consistently expands shorthand padding → `get_frequent_patterns()` returns pattern with `occurrences=10`, `confidence=1.0`. `suggest_converter_rules()` generates a suggestion with Python snippet. Pattern with only 3 occurrences → not suggested (below threshold). Admin endpoint returns patterns with suggested code. `make test` passes.

### 35.8 W3C Design Tokens & caniemail.com Integration `[Backend]`
**What:** Add W3C Design Tokens v1.0 JSON as an alternative token input format (alongside Figma Variables API), and integrate caniemail.com's open-source CSS support data as a live data source for `compatibility.py` and `token_transforms.py`.
**Why:** The W3C Design Tokens spec reached v1.0 stable in October 2025. Figma announced native W3C import/export for November 2026. Supporting W3C tokens now future-proofs the pipeline for: (a) Figma's native export when it ships, (b) Tokens Studio users who already export W3C format, (c) any design tool that supports the standard (Penpot, Sketch via plugins). For caniemail.com: the existing `compatibility.py` uses our ontology YAML (`css_properties.yaml`, `support_matrix.yaml`) which requires manual updates. caniemail.com tracks 303 HTML/CSS features across all major email clients with community-maintained data on GitHub — syncing this data keeps our compatibility checks current.
**Implementation:**
- **W3C Design Tokens parser** — `app/design_sync/w3c_tokens.py`:
  ```python
  def parse_w3c_tokens(tokens_json: dict[str, Any]) -> ExtractedTokens:
  ```
  - Parses W3C Design Tokens v1.0 JSON format: `{ "color": { "$type": "color", "$value": "#ff0000" }, "spacing": { "sm": { "$type": "dimension", "$value": "8px" } } }`
  - Maps W3C types to `ExtractedTokens` fields: `color` → `ExtractedColor`, `dimension` → spacing, `fontFamily`/`fontWeight`/`fontSize` → `ExtractedTypography`, `duration`/`cubicBezier` → ignored (not email-relevant)
  - Resolves aliases: `{ "$value": "{color.primary}" }` → follow reference chain with cycle detection (max depth 10)
  - Handles composite tokens: `shadow`, `border`, `gradient` → map to relevant `ExtractedTokens` fields
  - Supports multi-file tokens: `$extensions.mode` for light/dark → `dark_colors` population
- **W3C token export** — `app/design_sync/w3c_export.py`:
  ```python
  def export_w3c_tokens(tokens: ExtractedTokens) -> dict[str, Any]:
  ```
  - Converts validated `ExtractedTokens` back to W3C v1.0 JSON for downstream tooling (Style Dictionary, Tokens Studio)
- **API endpoints**:
  - `POST /api/v1/design-sync/tokens/import-w3c` — accepts W3C JSON, validates, stores as `DesignTokenSnapshot`
  - `GET /api/v1/design-sync/connections/{id}/tokens/export-w3c` — export current tokens in W3C format
- **caniemail.com data sync** — `scripts/sync-caniemail.py`:
  - Fetches `https://github.com/hteumeuleu/caniemail` data files (JSON/YAML)
  - Parses feature support matrix: property → client → support level (yes/no/partial + notes)
  - Outputs `data/caniemail-support.json` — 303 features × N clients
  - `make sync-caniemail` command
- **Integration with compatibility.py**:
  - `ConverterCompatibility` gains `caniemail_data` parameter — when provided, supplements ontology data with caniemail.com data
  - Merge strategy: if both sources have data for a property+client, use the more restrictive support level (safer)
  - `check_property()` returns `source: "ontology" | "caniemail" | "both"` field for transparency
- **Integration with token_transforms.py**:
  - `validate_and_transform()` gains `caniemail_data` parameter — used for client-aware warnings alongside existing ontology checks
**Security:** W3C token import accepts JSON — validate schema strictly before parsing (reject unknown `$type` values, limit nesting depth to 20, limit file size to 1MB). caniemail sync is a developer script, not a runtime endpoint — data is committed to repo. No user input reaches the sync script.
**Verify:** Import W3C tokens JSON with 5 colors + 3 typography + 2 spacing → `parse_w3c_tokens()` returns `ExtractedTokens` with correct values. Alias resolution: `{color.primary}` → resolved hex. Export round-trip: `export_w3c_tokens(parse_w3c_tokens(input)) ≈ input` (normalized). `sync-caniemail` produces `data/caniemail-support.json` with 300+ features. `ConverterCompatibility` with caniemail data correctly identifies `gap` as unsupported in Outlook. `make test` passes.

### 35.9 Figma Webhooks & Live Preview Sync `[Backend + Frontend]`
**What:** Add Figma webhook handling for `FILE_UPDATE` events to trigger automatic token re-sync and conversion preview updates. Push changes to the frontend via WebSocket so designers see their Figma edits reflected in the email preview within seconds.
**Why:** The current workflow is: designer edits Figma → manually clicks "Sync" in the UI → waits for API call → views updated tokens. This breaks the design-to-code feedback loop. Figma webhooks (`FILE_UPDATE` event) fire within seconds of a save. Combined with the existing token diff engine (Phase 33.8 `_compute_token_diff()`) and WebSocket infrastructure (Phase 24 collaboration), this enables near-real-time preview: design change → webhook → token diff → re-convert changed sections → push preview update.
**Implementation:**
- **Webhook endpoint** — `app/design_sync/routes.py`:
  ```python
  @router.post("/webhooks/figma", status_code=200)
  async def handle_figma_webhook(request: Request) -> dict:
  ```
  - Verify webhook signature using `X-Figma-Signature` header with HMAC-SHA256 (Figma signs payloads with the webhook passcode)
  - Parse event: `{ "event_type": "FILE_UPDATE", "file_key": "abc123", "file_name": "...", "timestamp": "..." }`
  - Look up `DesignConnection` by `file_key` — if found, enqueue async sync job
  - Return `200 OK` immediately (Figma requires < 5s response)
- **Webhook registration** — `app/design_sync/service.py`:
  ```python
  async def register_figma_webhook(self, connection_id: int, *, team_id: str) -> str:
  ```
  - Calls Figma API `POST /v2/webhooks` with `event_type: "FILE_UPDATE"`, `team_id`, `endpoint`, `passcode`
  - Stores webhook ID in `DesignConnection.webhook_id` column (new nullable column, Alembic migration)
  - Returns webhook ID for management
- **Debounced sync job** — designers save frequently, so debounce webhook events:
  - On webhook received: set Redis key `figma_webhook:{file_key}` with 5s TTL
  - Background worker checks key expiry → only trigger sync after 5s of no new webhooks
  - Sync job: `sync_connection()` → `_compute_token_diff()` → if tokens changed, re-convert
- **WebSocket push** — extend existing collaboration WebSocket (`app/collaboration/`):
  - New message type: `{ "type": "design_sync_update", "connection_id": N, "diff": TokenDiffResponse, "preview_url": "..." }`
  - Frontend `useDesignSync` hook receives update → refreshes token display + email preview
- **Frontend live preview** — `cms/apps/web/src/hooks/use-design-sync-live.ts`:
  - Subscribes to `design_sync_update` WebSocket messages
  - Shows toast: "Design updated — 3 tokens changed" with diff summary
  - Auto-refreshes email preview if the preview panel is open
  - Debounces UI updates to avoid flickering
- **Config:** `DESIGN_SYNC__FIGMA_WEBHOOK_ENABLED` (default `False`), `DESIGN_SYNC__FIGMA_WEBHOOK_PASSCODE` (secret for HMAC validation), `DESIGN_SYNC__WEBHOOK_DEBOUNCE_SECONDS` (default `5`)
**Security:** Webhook endpoint validates HMAC-SHA256 signature before processing — rejects unsigned/tampered payloads. Passcode stored in settings (not in DB). Rate limit webhook endpoint to 60/min per IP. Webhook registration requires admin role. WebSocket messages only sent to authenticated users with access to the project.
**Verify:** Register webhook for a test connection → Figma API returns webhook ID, stored in DB. Simulate `FILE_UPDATE` event with valid signature → sync job enqueued after 5s debounce. Invalid signature → 401 rejected. Two rapid webhook events → only one sync job (debounce works). WebSocket client receives `design_sync_update` message with token diff. Frontend toast appears. `make test` passes.

### 35.10 Incremental Conversion & Section Caching `[Backend]`
**What:** Cache conversion results at the section level and only re-convert sections whose node tree or tokens changed. On re-conversion, assemble the email from cached + fresh sections.
**Why:** A full Figma-to-email conversion for a typical 6-section email takes 2–5 seconds (layout analysis + recursive HTML generation + MJML compilation + optional fidelity scoring). When a designer changes only one section's text, re-converting all 6 sections wastes 80% of the work. Section-level caching reduces re-conversion time to < 1 second for incremental changes — critical for the live preview sync (35.9) to feel responsive.
**Implementation:**
- **Section hash computation** — `app/design_sync/section_cache.py`:
  ```python
  def compute_section_hash(section: EmailSection, tokens: ExtractedTokens) -> str:
  ```
  - Hash inputs: section's node tree (types + dimensions + styles + text content), relevant tokens (colors used in section, typography, spacing), container_width, target_clients
  - Uses `hashlib.sha256` on a canonical JSON representation
  - Stable ordering: sort dict keys, round floats to 2 decimal places
- **Section cache storage**:
  - In-memory LRU cache: `functools.lru_cache` with 500 entries (covers ~80 emails × 6 sections)
  - Redis cache with 1-hour TTL for persistence across restarts: key = `section_cache:{connection_id}:{section_hash}`, value = rendered HTML + MJML
  - Cache entry: `{ html: str, mjml: str | None, fidelity_score: float | None, generated_at: datetime }`
- **Incremental conversion** — extend `DesignConverterService.convert()`:
  ```python
  # After layout analysis
  section_hashes = {s.id: compute_section_hash(s, tokens) for s in layout.sections}
  cached = await self._cache.get_many(connection_id, section_hashes)

  to_convert = [s for s in layout.sections if s.id not in cached]
  fresh_results = await self._convert_sections(to_convert, ...)  # Only convert changed sections

  all_sections_html = []
  for section in layout.sections:
      if section.id in cached:
          all_sections_html.append(cached[section.id].html)
      else:
          all_sections_html.append(fresh_results[section.id])
          await self._cache.set(connection_id, section_hashes[section.id], fresh_results[section.id])
  ```
- **Cache invalidation**: Clear all cache entries for a connection when: (a) token diff detects structural changes (not just value changes), (b) `target_clients` change, (c) `container_width` changes, (d) manual cache clear via admin endpoint
- **Metrics**: Log `design_sync.conversion_cache_hit_rate` — ratio of cached vs. fresh sections per conversion. Include in `ConversionResult.metadata`.
- Add `DELETE /api/v1/design-sync/connections/{id}/cache` admin endpoint for manual cache clear
**Security:** Cache keys are SHA-256 hashes — no user content in keys. Cache values are rendered HTML (already sanitized). Redis cache uses same auth as existing Redis connection. Admin-only cache clear endpoint.
**Verify:** Convert a 6-section email → all 6 sections cached. Change text in 1 section → re-convert → only 1 section re-converted, 5 from cache (`cache_hit_rate=0.83`). Change `target_clients` → full cache invalidation → all 6 re-converted. Cache TTL: wait 1 hour → entries expired → full re-conversion. `make test` passes.

### 35.11 Tests & Integration Verification `[Full-Stack]`
**What:** Comprehensive test suite covering all Phase 35 subtasks: MJML compilation, tree normalization, MJML generation, AI classification, visual fidelity, correction learning, W3C tokens, webhooks, and caching. Plus end-to-end integration test: Figma file → normalize → classify → convert (MJML) → compile → score fidelity → cache.
**Implementation:**
- **MJML sidecar tests** (`services/maizzle-builder/test/`):
  - `test-mjml-compile.js`: Valid MJML → HTML with tables. Invalid MJML → error array. Empty input → 400. Large MJML (100 sections) → compiles within 5s.
  - `test-mjml-postcss.js`: MJML output + `target_clients=["outlook_2019"]` → PostCSS strips unsupported CSS from compiled HTML.
- **Tree normalizer tests** (`app/design_sync/tests/test_tree_normalizer.py`):
  - Hidden node removal, GROUP flattening, auto-layout inference (vertical, horizontal, mixed), text merging, instance resolution. Edge: empty tree, single-node tree, max-depth tree.
- **MJML generation tests** (`app/design_sync/tests/test_mjml_generation.py`):
  - Each section type → valid MJML output. Token injection → correct attributes. Dark mode → `<mj-style>` block. Multi-column → correct `mj-column width`. Full email assembly → valid MJML document.
- **MJML template tests** (`app/design_sync/tests/test_mjml_templates.py`):
  - Each of 10 templates renders valid MJML. Autoescape prevents XSS in text content. Missing optional fields → graceful defaults.
- **AI layout tests** (`app/design_sync/tests/test_ai_layout.py`):
  - Mock LLM returns valid classification → section type updated. LLM error → graceful fallback to UNKNOWN. Cache hit → no LLM call. Config disabled → no LLM call. Heuristic content roles: unsubscribe, copyright, social links detected without LLM.
- **Visual fidelity tests** (`app/design_sync/tests/test_visual_scorer.py`):
  - Identical images → score 1.0. Completely different → score < 0.3. Known diff → per-section scores identify correct section. Anti-aliasing tolerance → minor rendering differences don't tank score.
- **Correction tracker tests** (`app/design_sync/tests/test_correction_tracker.py`):
  - Record 10 identical corrections → pattern with `occurrences=10`. Below threshold → not suggested. Approve pattern → status changes. Different corrections for same input → low confidence, not suggested.
- **W3C token tests** (`app/design_sync/tests/test_w3c_tokens.py`):
  - Parse valid W3C JSON → correct `ExtractedTokens`. Alias resolution → chain followed. Circular alias → error. Export round-trip → consistent. Unknown `$type` → skipped with warning.
- **Webhook tests** (`app/design_sync/tests/test_webhooks.py`):
  - Valid signature → accepted. Invalid signature → 401. Unknown file_key → 200 (acknowledged, no action). Debounce: 3 rapid events → 1 sync job.
- **Cache tests** (`app/design_sync/tests/test_section_cache.py`):
  - Cache miss → full convert. Cache hit → skip convert. Invalidation on token change. TTL expiry. Hash stability (same input → same hash).
- **E2E integration test** (`app/design_sync/tests/test_e2e_mjml_pipeline.py`):
  - Uses mock Figma API response (real structure from golden template)
  - Full pipeline: normalize → analyze → classify → MJML generate → compile → verify HTML output has tables + MSO conditionals + responsive media queries + dark mode
  - Verify section count matches layout analysis
  - Verify `data-slot-name` attributes preserved through MJML compilation
**Security:** Tests only — no production code paths, no real Figma API calls, no real LLM calls (all mocked).
**Verify:** `make test` — all new test files pass. `make check` — full suite green. `make bench` — MJML compilation benchmark added (target: < 500ms for 6-section email). Test count: estimated 80–100 new tests across all subtasks.

---

## Phase 36 — Universal Email Design Document & Multi-Format Import Hub

> **The pipeline has a coupling problem.** Design tool providers (Figma, Penpot) produce Python objects (`ExtractedTokens`, `DesignFileStructure`) consumed directly by the converter in-process. This means: (1) new input formats (MJML files, raw HTML, manual JSON) must produce these exact Python types, (2) the converter can't run independently or be tested without a provider, (3) there's no formal contract — any field can be missing or shaped differently per provider, and (4) tokens and structure flow through separate paths that must be kept in sync manually. Meanwhile, the import annotator agent (Phase 32.3) detects Stripo/Beefree/MJML/Mailchimp patterns but can't extract structural data, and ESP export covers 3 of the Big 5 (Braze + SFMC + Adobe Campaign — missing Klaviyo + HubSpot).
>
> This phase introduces the **`EmailDesignDocument`** — a single, formally specified JSON Schema that serves as the universal contract between ALL input sources and the converter. Every provider (Figma, Penpot, MJML import, HTML import, manual API) produces this JSON. The converter consumes ONLY this JSON. The schema is versioned, validated, cacheable, and testable with fixtures. Plus: MJML import adapter, AI-powered HTML reverse engineering adapter, and Klaviyo + HubSpot ESP export to complete the Big 5.
>
> **Why not import proprietary builder formats (Beefree JSON, Stripo modules, Chamaileon JSON, Unlayer JSON)?** Competitive analysis shows these are undocumented/proprietary schemas with tiny migration audiences and high maintenance burden. When enterprises leave those tools, they export HTML — which the HTML import adapter handles. MJML is the only structured email format worth parsing directly (open, formal schema, 17k GitHub stars, used by Email Love + Topol.io + Parcel).
>
> **Dependency note:** Builds on Phase 35 (MJML compilation service, node tree normalizer, AI layout intelligence). Requires 35.1 (MJML sidecar) for MJML round-trip and 35.5 (AI layout intelligence) for HTML reverse engineering. ESP export subtask (36.5) is independent — can start immediately using existing `ESPSyncProvider` protocol in `app/connectors/sync_protocol.py`.

- [ ] 36.1 EmailDesignDocument JSON Schema v1
- [ ] 36.2 Refactor converter to consume EmailDesignDocument
- [ ] 36.3 Refactor Figma + Penpot adapters to produce EmailDesignDocument
- [ ] 36.4 MJML import adapter
- [ ] 36.5 AI-powered HTML reverse engineering adapter
- [ ] 36.6 Klaviyo + HubSpot ESP export
- [ ] 36.7 Tests & integration verification

### 36.1 EmailDesignDocument JSON Schema v1 `[Backend]`
**What:** Define a formal JSON Schema (Draft 2020-12) for the `EmailDesignDocument` — the single canonical intermediate representation between any input source and the converter. Create the schema file, Python dataclass mirror, serialization/deserialization, and validation.
**Why:** The pipeline currently passes Python objects in-memory between providers and the converter. This creates tight coupling, makes testing harder (need a provider to test the converter), prevents external tools from feeding the pipeline, and has no validation (missing fields cause runtime errors deep in the converter). A formal JSON Schema makes the contract explicit, enables schema validation at the boundary, allows JSON fixtures for testing, supports caching/versioning/diffing of the full input, and opens the door for external tools to target the schema directly via API.
**Implementation:**
- Create `app/design_sync/schemas/email_design_document.json` — JSON Schema Draft 2020-12:
  ```json
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "email-design-document/v1",
    "type": "object",
    "required": ["version", "tokens", "sections", "layout"],
    "properties": {
      "version": { "const": "1.0" },
      "source": {
        "type": "object",
        "properties": {
          "provider": { "enum": ["figma", "penpot", "mjml", "html", "manual", "sketch", "canva"] },
          "file_ref": { "type": "string" },
          "synced_at": { "type": "string", "format": "date-time" }
        }
      },
      "tokens": { "$ref": "#/$defs/tokens" },
      "sections": { "type": "array", "items": { "$ref": "#/$defs/section" } },
      "layout": { "$ref": "#/$defs/layout" },
      "compatibility_hints": { ... },
      "token_warnings": { ... }
    }
  }
  ```
- **Tokens sub-schema** (`$defs/tokens`): maps directly to existing `ExtractedTokens` fields — `colors[]` (name, hex, opacity, role), `typography[]` (name, family, size, weight, line_height, letter_spacing, text_transform, text_decoration), `spacing[]` (name, value), `dark_colors[]`, `gradients[]` (angle, stops[], fallback_hex), `variables[]` (name, type, value, mode). All fields optional with sensible defaults — minimal valid document needs only `version` + empty `tokens` + empty `sections` + `layout.container_width`.
- **Section sub-schema** (`$defs/section`): maps to existing `EmailSection` dataclass — `id`, `type` (enum: header/preheader/hero/content/cta/footer/social/divider/spacer/nav/unknown), `column_layout` (enum: single/two-column/three-column/multi-column), `width`, `height`, `padding` (top/right/bottom/left), `item_spacing`, `background_color`, `texts[]` (content, is_heading, font_family, font_size, font_weight, color, line_height, letter_spacing), `images[]` (node_id, width, height, alt, src), `buttons[]` (text, url, background_color, text_color, border_radius, padding), `columns[]` (width_pct, texts, images, buttons — for multi-column), `content_roles[]`, `spacing_after`.
- **Layout sub-schema** (`$defs/layout`): `container_width` (int, 400–800, default 600), `naming_convention` (enum), `overall_width`.
- Create Python mirror in `app/design_sync/email_design_document.py`:
  ```python
  @dataclass(frozen=True)
  class EmailDesignDocument:
      version: str
      tokens: DocumentTokens
      sections: list[DocumentSection]
      layout: DocumentLayout
      source: DocumentSource | None = None
      compatibility_hints: list[CompatibilityHint] = field(default_factory=list)
      token_warnings: list[TokenWarning] = field(default_factory=list)

      @classmethod
      def from_json(cls, data: dict[str, Any]) -> EmailDesignDocument: ...
      def to_json(self) -> dict[str, Any]: ...
      @staticmethod
      def validate(data: dict[str, Any]) -> list[str]: ...  # Returns validation errors
  ```
- `DocumentTokens`, `DocumentSection`, `DocumentLayout`, `DocumentSource` — frozen dataclasses mirroring the JSON schema. These are thin wrappers, NOT duplicates of `ExtractedTokens`/`EmailSection` — they have `to_extracted_tokens()` and `to_email_sections()` bridge methods for backward compatibility during migration.
- Schema validation via `jsonschema` library (already a dependency via other packages) — validate at the boundary (when JSON arrives from adapter or API), not inside the converter.
- Add `POST /api/v1/design-sync/validate-document` endpoint — accepts JSON, returns validation errors. Useful for external tools testing their output.
- Add `GET /api/v1/design-sync/schema/v1` endpoint — serves the JSON Schema for external consumers.
- Store validated `EmailDesignDocument` JSON in `DesignTokenSnapshot.document_json` (new column, nullable — coexists with existing `tokens_json` during migration). Alembic migration adds column.
**Security:** Schema validation prevents malformed input from reaching the converter. Max document size: 5MB (enforced at API boundary). JSON Schema `maxItems` on arrays (sections: 100, texts per section: 50, colors: 500) prevents DoS via oversized documents. No `additionalProperties: true` on inner objects — unknown fields are rejected.
**Verify:** Valid EmailDesignDocument JSON → `validate()` returns empty list. Missing required field → validation error with path. Section with invalid type → rejected. Document with 101 sections → rejected (maxItems). `from_json(to_json(doc))` round-trips correctly. Schema endpoint returns valid JSON Schema. `make test` passes.

### 36.2 Refactor Converter to Consume EmailDesignDocument `[Backend]`
**What:** Modify `DesignConverterService.convert()` to accept `EmailDesignDocument` as its primary input, replacing the current `(DesignFileStructure, ExtractedTokens)` pair. The existing signature remains as a deprecated compatibility shim during migration.
**Why:** The converter currently accepts `DesignFileStructure` + `ExtractedTokens` + 8 keyword arguments (`raw_file_data`, `selected_nodes`, `target_clients`, `use_components`, `connection_config`, `image_urls`). This signature is Figma-centric (e.g., `raw_file_data` is the raw Figma API response). Moving to `EmailDesignDocument` as the single input: (a) makes the converter input-source-agnostic, (b) reduces the parameter surface from 10 args to 1 object, (c) enables testing with JSON fixtures instead of mock providers, (d) enables caching by document hash.
**Implementation:**
- Add new method `DesignConverterService.convert_document()`:
  ```python
  async def convert_document(
      self, document: EmailDesignDocument, *, target_clients: list[str] | None = None,
      output_format: Literal["html", "mjml"] = "html",
  ) -> ConversionResult:
  ```
- Internally: `document.tokens.to_extracted_tokens()` → feed to `validate_and_transform()`. `document.sections` → feed to `_convert_mjml()` (Phase 35.3) or `_convert_with_components()`. `document.layout.container_width` → thread through all rendering calls.
- The existing `convert()` method becomes a shim:
  ```python
  async def convert(self, structure, tokens, **kwargs) -> ConversionResult:
      # Build EmailDesignDocument from legacy inputs
      document = self._build_document_from_legacy(structure, tokens, **kwargs)
      return await self.convert_document(document, target_clients=kwargs.get("target_clients"))
  ```
- `_build_document_from_legacy()` bridges the old inputs → `EmailDesignDocument`:
  - Runs `analyze_layout(structure)` to get `EmailSection[]`
  - Maps `ExtractedTokens` → `DocumentTokens`
  - Maps `EmailSection[]` → `DocumentSection[]`
  - This is the ONLY place layout analysis happens for Figma/Penpot inputs (Option A from architecture discussion)
- Update `import_service.py:run_conversion()` to call `convert_document()` with the `EmailDesignDocument` stored in `DesignTokenSnapshot.document_json` when available, falling back to legacy path when not.
- Update `service.py:sync_connection()` to build and store `EmailDesignDocument` JSON in the snapshot after token extraction + layout analysis.
- **No changes to `converter.py` internals** (`node_to_email_html()`, `_render_semantic_text()`, etc.) — these receive `EmailSection` data from the document's `.to_email_sections()` bridge. The refactor is at the orchestration layer only.
**Security:** `convert_document()` requires a validated `EmailDesignDocument` — call `validate()` before passing. The shim validates legacy inputs by construction (they come from trusted provider code). No new user input paths.
**Verify:** `convert_document()` with a JSON fixture produces identical HTML to `convert()` with the same data via legacy path. All existing design_sync tests pass without modification (shim handles backward compatibility). `convert_document()` with invalid document → raises `AppError`. `make test` passes. `make check` all green.

### 36.3 Refactor Figma + Penpot Adapters to Produce EmailDesignDocument `[Backend]`
**What:** Modify `FigmaDesignSyncService` and `PenpotDesignSyncService` to output `EmailDesignDocument` JSON as their primary result, in addition to the existing `ExtractedTokens` + `DesignFileStructure` return types. Each adapter encapsulates all provider-specific logic — API calls, node parsing, layout analysis — and outputs the universal document.
**Why:** Currently, the Figma provider returns raw `ExtractedTokens` + `DesignFileStructure`, and the converter runs layout analysis. This means layout analysis is in the converter's responsibility, but it's really a provider-specific concern (Figma nodes need y-position grouping; MJML sections are explicit; HTML needs DOM traversal). Moving layout analysis into the adapter means each adapter can use the right analysis strategy for its format, and the converter receives pre-analyzed sections.
**Implementation:**
- Add `build_document()` method to `FigmaDesignSyncService`:
  ```python
  async def build_document(
      self, file_ref: str, access_token: str, *, selected_nodes: list[str] | None = None,
      connection_config: dict[str, Any] | None = None,
  ) -> EmailDesignDocument:
  ```
  - Calls existing `sync_tokens_and_structure()` → `ExtractedTokens` + `DesignFileStructure`
  - Calls `validate_and_transform(tokens)` → validated tokens + warnings
  - If Phase 35.2 available: calls `normalize_tree(structure)` → cleaned tree
  - Calls `analyze_layout(structure)` → `DesignLayoutDescription` with `EmailSection[]`
  - If Phase 35.5 available: calls `classify_unknown_sections()` for AI fallback
  - Assembles all results into `EmailDesignDocument`
  - Returns the document (also stores as JSON in snapshot)
- Add same `build_document()` to `PenpotDesignSyncService` — same flow, different API client.
- Update `DesignSyncService.sync_connection()`:
  ```python
  # New path: build full document
  provider = self._get_provider(connection.provider)
  if hasattr(provider, "build_document"):
      document = await provider.build_document(file_ref, token, ...)
      snapshot.document_json = document.to_json()
  else:
      # Legacy path for stub providers (Sketch, Canva)
      tokens, structure = await provider.sync_tokens_and_structure(file_ref, token)
      snapshot.tokens_json = tokens.to_dict()
  ```
- The `DesignSyncProvider` protocol gains an optional `build_document()` method (not required — stubs don't implement it). Use `hasattr` check, not protocol enforcement, so existing providers aren't broken.
- **Layout analysis moves from converter to adapter.** The converter no longer calls `analyze_layout()` — it receives pre-analyzed sections in the document. This is the key architectural shift.
**Security:** No new input paths. `build_document()` uses the same authenticated API calls as existing methods. Document JSON is validated before storage. Existing auth, rate limiting, and encryption unchanged.
**Verify:** `sync_connection()` for a Figma connection → stores `document_json` with valid EmailDesignDocument. `document_json` contains sections with types, texts, images, buttons. `convert_document(document)` produces same HTML as legacy `convert(structure, tokens)` path. Penpot connection → same flow. Stub providers (Sketch, Canva) → legacy path, no `document_json`. `make test` passes.

### 36.4 MJML Import Adapter `[Backend]`
**What:** Create `app/design_sync/mjml_import/adapter.py` — a parser that reads MJML markup (`<mjml>/<mj-body>/<mj-section>/<mj-column>/<mj-text>/<mj-button>/<mj-image>`) and produces an `EmailDesignDocument`. This enables importing existing MJML templates into the platform for editing, AI enhancement, and multi-client rendering. Combined with Phase 35.3 (MJML generation), this completes the MJML round-trip.
**Why:** MJML is the de facto standard intermediate representation for email. Enterprise email teams have hundreds of MJML templates from Maizzle, Parcel, Email Love, Topol.io, or hand-coded workflows. Importing these templates unlocks: (a) AI agent enhancement (dark mode, accessibility, outlook fixes) on existing MJML templates, (b) visual editing in the builder, (c) multi-client rendering via the emulators, (d) QA engine checks on legacy templates. MJML's XML structure maps cleanly to `EmailDesignDocument` — `<mj-section>` → section, `<mj-column>` → column, `<mj-text>` → text block, `<mj-button>` → button, `<mj-image>` → image. This is a 1:1 mapping, not heuristic inference.
**Implementation:**
- Create `app/design_sync/mjml_import/adapter.py`:
  ```python
  class MjmlImportAdapter:
      def parse(self, mjml_source: str) -> EmailDesignDocument: ...
  ```
- **MJML parsing** — use `lxml.etree` with MJML namespace handling:
  - Parse MJML as XML tree
  - Walk `<mj-head>` → extract tokens:
    - `<mj-attributes>/<mj-all>` → default typography (font-family, font-size, color)
    - `<mj-attributes>/<mj-text>` → text typography overrides
    - `<mj-attributes>/<mj-button>` → button defaults (background-color, color, font-size, inner-padding, border-radius)
    - `<mj-style>` → parse CSS for color variables, dark mode rules (`prefers-color-scheme`)
    - `<mj-font>` → web font references
  - Walk `<mj-body>` → extract sections:
    - Each `<mj-section>` → one `DocumentSection`:
      - `background-color` attr → `background_color`
      - `padding` attr → parse to `padding_top/right/bottom/left`
      - Count child `<mj-column>` → determine `column_layout` (1=SINGLE, 2=TWO_COLUMN, 3=THREE_COLUMN, 4+=MULTI_COLUMN)
    - Each `<mj-column>` → column group with `width` → `width_pct`
    - Each `<mj-text>` → `TextBlock`:
      - Inner HTML content (strip tags for plain text, detect headings from `<h1>`-`<h6>` tags or font-size)
      - `font-family`, `font-size`, `font-weight`, `color`, `line-height`, `letter-spacing` from attributes + inline style
    - Each `<mj-image>` → `ImagePlaceholder` with `src`, `alt`, `width`, `height`
    - Each `<mj-button>` → `ButtonElement` with `href`, inner text, `background-color`, `color`, `border-radius`, `inner-padding`
    - Each `<mj-spacer>` → section with type=SPACER and `height`
    - Each `<mj-divider>` → section with type=DIVIDER
    - `<mj-hero>` → section with type=HERO + background image from `background-url`
    - `<mj-social>/<mj-social-element>` → section with type=SOCIAL + content roles
    - `<mj-navbar>/<mj-navbar-link>` → section with type=NAV
  - **Section type inference**: MJML doesn't have explicit section types. Infer from position + content:
    - First section with image and no text → HEADER
    - Section with `<mj-hero>` or large background image + heading → HERO
    - Last section with small text or `<mj-social>` → FOOTER
    - Section with only `<mj-button>` → CTA
    - Everything else → CONTENT
  - `document.source.provider = "mjml"`
  - `document.layout.container_width` from `<mj-body width="600px">` or default 600
- **API endpoints**:
  - `POST /api/v1/design-sync/import/mjml` — accepts MJML string in request body, returns `EmailDesignDocument` JSON + conversion preview
  - Reuses auth + rate limiting from existing design_sync routes
- **Integration with visual builder**: imported `EmailDesignDocument` can be opened in the builder for editing, then exported as MJML (Phase 35.3) or HTML (converter)
- Max MJML size: 2MB (matches import annotator limit). Validate XML well-formedness before parsing.
**Security:** MJML input is parsed as XML via `lxml` with `resolve_entities=False`, `no_network=True` to prevent XXE attacks. Text content from `<mj-text>` is passed through `html.escape()` when extracting plain text. `src` URLs from `<mj-image>` are validated (http/https only, no `javascript:` or `data:` URIs). Import endpoint requires authentication.
**Verify:** Import the 10 MJML section templates from Phase 35.4 → each produces valid `EmailDesignDocument` with correct section types, column layouts, and content. Round-trip: MJML → import → `EmailDesignDocument` → MJML generation (35.3) → compile (35.1) → produces equivalent HTML. `<mj-hero>` → HERO section. 2-column section → TWO_COLUMN layout with 2 column groups. Dark mode `<mj-style>` → `dark_colors` tokens extracted. Malformed XML → descriptive error, no crash. XXE payload → rejected. `make test` passes.

### 36.5 AI-Powered HTML Reverse Engineering Adapter `[Backend + AI]`
**What:** Create `app/design_sync/html_import/adapter.py` — a parser that takes arbitrary email HTML and reverse-engineers an `EmailDesignDocument`. Uses the existing import annotator agent (Phase 32.3) for pattern detection, plus new DOM traversal logic to extract `EmailSection[]` with full content (texts, images, buttons, styling). This is the #1 enterprise migration feature — enterprises have thousands of legacy HTML templates that need to become editable.
**Why:** The import annotator agent already detects section boundaries and adds `data-section-id` attributes, identifies builder patterns (Stripo, Beefree, Mailchimp, MJML), and recognizes ESP tokens (AMPscript, Liquid, Handlebars). But it does NOT extract structured data — no `EmailSection` objects, no text blocks, no image metadata, no button detection. The gap is the 60% between "annotated HTML" and "structured EmailDesignDocument." Beefree launched their HTML Importer API in 2025 (rule-based). Chamaileon has an HTML import plugin. Both produce mediocre results on messy real-world email HTML. AI-powered extraction using the import annotator's pattern detection + LLM fallback for ambiguous structures would be a genuine differentiator.
**Implementation:**
- Create `app/design_sync/html_import/adapter.py`:
  ```python
  class HtmlImportAdapter:
      async def parse(self, html: str, *, use_ai: bool = True) -> EmailDesignDocument: ...
  ```
- **Phase 1 — DOM-based section extraction** (deterministic, no LLM):
  - Parse HTML via `lxml.html` (same library as import annotator)
  - Find the outermost content table (skip MSO wrapper tables via `<!--[if mso]>` detection)
  - Walk top-level `<tr>` rows → each row is a candidate section
  - For each candidate section:
    - **Text extraction**: Find all text-bearing elements (`<td>`, `<p>`, `<h1>`-`<h6>`, `<span>`, `<a>`) → create `TextBlock` objects with content + inline style parsing (font-family, font-size, font-weight, color, line-height from `style` attribute)
    - **Image extraction**: Find all `<img>` tags → create `ImagePlaceholder` with `src`, `alt`, `width`, `height` (from attributes or inline style)
    - **Button extraction**: Detect buttons via multiple patterns — `<a>` with background-color in style, `<table>` with single `<a>` child (bulletproof button pattern), VML `<v:roundrect>` (Outlook button), `role="button"` attribute → create `ButtonElement` with text, href, styling
    - **Column detection**: Count immediate child `<td>` elements in a row. 1 td = SINGLE, 2 = TWO_COLUMN, 3 = THREE_COLUMN, 4+ = MULTI_COLUMN. Also detect `display:inline-block` column pattern (fluid hybrid).
    - **Background color**: Extract from `bgcolor` attribute or `background-color` in style on `<td>`/`<table>`
    - **Padding**: Parse `padding` from inline style on section-level `<td>`
- **Phase 2 — Section type classification** (heuristic + AI fallback):
  - **Heuristic rules** (free, fast):
    - Section with image and no/little text in first position → HEADER
    - Section with large font heading (> 24px) + optional image + optional button → HERO
    - Section with only `<a>` button → CTA
    - Last section with small text (< 14px) or "unsubscribe"/"©" content → FOOTER
    - Section with social media image links (facebook/twitter/linkedin/instagram URL patterns) → SOCIAL
    - Section with `<hr>` or 1px-height element → DIVIDER
    - Section with no content, height-only → SPACER
  - **AI fallback** (only for sections classified as UNKNOWN after heuristics): reuse Phase 35.5 `classify_section()` with text snippets + position context → Haiku structured output
- **Phase 3 — Token extraction from CSS**:
  - Parse `<style>` blocks and inline styles → build color palette (deduplicate hex values, assign roles by frequency: most common bg = background, most common text = body_text, etc.)
  - Extract typography: find distinct font-family + font-size combinations → heading vs. body by size
  - Extract spacing: common padding values → spacing scale
  - Detect dark mode: `@media (prefers-color-scheme: dark)` rules → `dark_colors`
  - Detect web fonts: `@import` or `<link>` with font URLs
- **Integration with import annotator**: if import annotator was already run on this HTML (has `data-section-id` attributes), use those annotations as section boundaries instead of inferring from `<tr>` rows. This leverages the agent's builder-specific pattern detection.
- **API endpoint**: `POST /api/v1/design-sync/import/html` — accepts HTML string, returns `EmailDesignDocument` JSON
- **Config**: `DESIGN_SYNC__HTML_IMPORT_AI_ENABLED` (default `True`) — disable AI fallback for deterministic-only mode
**Security:** HTML input parsed via `lxml.html` (inherently sanitizes). `src` URLs validated (http/https only). Text content passed through `html.escape()` on extraction. AI fallback receives only structural metadata (dimensions, text snippets), not raw HTML. Import endpoint requires authentication. Max HTML size: 2MB.
**Verify:** Import a golden template HTML → produces `EmailDesignDocument` with correct section count, types, and content. Import a Stripo-exported HTML → section boundaries detected (leveraging import annotator skills). Import a Beefree-exported HTML → same. Import hand-coded email with bulletproof buttons → buttons correctly extracted. Import email with dark mode CSS → `dark_colors` populated. AI disabled → UNKNOWN sections stay UNKNOWN. Malformed HTML → best-effort parsing, no crash. `make test` passes.

### 36.6 Klaviyo + HubSpot ESP Export `[Backend]`
**What:** Add Klaviyo and HubSpot ESP export providers to complete the Big 5 coverage (joining existing Braze, SFMC, Adobe Campaign in `app/connectors/`). Implements the existing `ESPSyncProvider` protocol from `app/connectors/sync_protocol.py`.
**Why:** Braze, SFMC, and Adobe Campaign export already works. Klaviyo and HubSpot are the remaining two of the five most-used enterprise ESPs. Without them, enterprise prospects using these platforms can't push templates from the platform — a deal-breaker. The existing `ESPSyncProvider` protocol + `ConnectorService` dispatch pattern makes adding new providers straightforward (same pattern as `BrazeSyncProvider`, `SFMCSyncProvider`).
**Implementation:**
- **Klaviyo provider** — `app/connectors/klaviyo/`:
  - `service.py` — `KlaviyoConnectorService`:
    - Auth: API key (private key, `Authorization: Klaviyo-API-Key {key}`)
    - Base URL: `https://a.klaviyo.com/api`
    - API revision header: `revision: 2025-07-15` (Klaviyo requires version pinning)
  - `sync_provider.py` — `KlaviyoSyncProvider` implementing `ESPSyncProvider`:
    - `validate_credentials()` → `GET /api/accounts/` (returns account info if key valid)
    - `list_templates()` → `GET /api/templates/` with pagination (`page[cursor]`). Map response to `ESPTemplate` (id, name, html, updated_at). Klaviyo uses JSON:API format — unwrap `data[].attributes`.
    - `get_template(id)` → `GET /api/templates/{id}/`
    - `create_template(name, html)` → `POST /api/templates/` with `{ "data": { "type": "template", "attributes": { "name": name, "html": html } } }`
    - `update_template(id, html)` → `PATCH /api/templates/{id}/` with same JSON:API format
    - `delete_template(id)` → `DELETE /api/templates/{id}/`
  - Rate limit: Klaviyo allows 75 requests/sec for private API keys. Add `RateLimiter` with 60/sec safety margin.
- **HubSpot provider** — `app/connectors/hubspot/`:
  - `service.py` — `HubSpotConnectorService`:
    - Auth: Private app access token (`Authorization: Bearer {token}`)
    - Base URL: `https://api.hubapi.com`
  - `sync_provider.py` — `HubSpotSyncProvider` implementing `ESPSyncProvider`:
    - `validate_credentials()` → `GET /account-info/v3/details` (returns portal ID if valid)
    - `list_templates()` → `GET /marketing/v3/emails/` with pagination (`after` cursor). Map to `ESPTemplate`. Note: HubSpot's Marketing Email API is the modern path — the older Template API is for CMS templates, not email templates.
    - `get_template(id)` → `GET /marketing/v3/emails/{id}`
    - `create_template(name, html)` → `POST /marketing/v3/emails/` with `{ "name": name, "content": { "html": html }, "type": "REGULAR" }`
    - `update_template(id, html)` → `PATCH /marketing/v3/emails/{id}` with content update
    - `delete_template(id)` → `DELETE /marketing/v3/emails/{id}` (moves to trash, not permanent)
  - Rate limit: HubSpot allows 100 requests/10sec for private apps. Add `RateLimiter` with 8/sec safety margin.
- Register both in `ConnectorService`:
  ```python
  # app/connectors/service.py
  PROVIDERS["klaviyo"] = KlaviyoSyncProvider
  PROVIDERS["hubspot"] = HubSpotSyncProvider
  ```
- Add config: `ESPSyncConfig` gains `klaviyo_api_key`, `hubspot_access_token` fields
- Add pre-check support: both providers in `export_pre_check()` for dry-run validation
**Security:** API keys stored encrypted via existing `encrypt_credentials()` in `app/connectors/`. Keys never logged (structured logging excludes credential fields). Rate limiters prevent API abuse. HubSpot delete is soft-delete (trash) — not destructive. Klaviyo API key scopes validated on `validate_credentials()` (need `templates:read`, `templates:write`).
**Verify:** Klaviyo: `validate_credentials()` with valid key → `True`. `create_template("Test", "<html>...")` → returns `ESPTemplate` with Klaviyo ID. `list_templates()` → returns list including created template. `update_template(id, new_html)` → HTML updated. `delete_template(id)` → `True`. Invalid key → `validate_credentials()` returns `False`. HubSpot: same test matrix. Both providers work through existing `POST /api/v1/connectors/export` endpoint. `make test` passes (mocked API calls).

### 36.7 Tests & Integration Verification `[Full-Stack]`
**What:** Comprehensive test suite covering all Phase 36 subtasks plus end-to-end integration tests for the full multi-format pipeline.
**Implementation:**
- **Schema tests** (`app/design_sync/tests/test_email_design_document.py`):
  - Valid document → passes validation. Missing `version` → error. Invalid section type → error. `from_json(to_json())` round-trip. Max size limits enforced. Bridge methods: `to_extracted_tokens()`, `to_email_sections()` produce correct types.
- **Converter refactor tests** (`app/design_sync/tests/test_converter_document.py`):
  - `convert_document()` with JSON fixture → same HTML as legacy `convert()` with equivalent data. Invalid document → `AppError`. Empty sections → valid empty email skeleton. All existing converter tests pass via shim.
- **Figma adapter tests** (`app/design_sync/tests/test_figma_adapter.py`):
  - `build_document()` with mock Figma response → valid `EmailDesignDocument`. Document contains sections with classified types. Tokens validated and warnings present. Penpot adapter: same test matrix.
- **MJML import tests** (`app/design_sync/tests/test_mjml_import.py`):
  - Each MJML element type → correct mapping. `<mj-section>` with 2 `<mj-column>` → TWO_COLUMN. `<mj-button>` → button with href + styling. `<mj-hero>` → HERO type. `<mj-social>` → SOCIAL type. Dark mode `<mj-style>` → dark_colors. Malformed XML → error. XXE → rejected. Round-trip: import → generate (35.3) → compile (35.1) → valid HTML.
- **HTML import tests** (`app/design_sync/tests/test_html_import.py`):
  - Import golden template HTML (use real fixtures from `app/components/data/seeds.py`) → correct section count and types. Bulletproof button pattern → detected as button. Inline styles → tokens extracted. Dark mode CSS → dark_colors. Builder-specific HTML (Stripo/Beefree patterns) → correct section boundaries. AI disabled → UNKNOWN sections preserved. Empty HTML → empty document, no crash.
- **ESP export tests** (`app/connectors/tests/test_klaviyo.py`, `test_hubspot.py`):
  - Mock API: CRUD operations for both providers. Rate limiter: burst of 100 requests → throttled. Invalid credentials → `False`. JSON:API format handling (Klaviyo). Pagination (both).
- **E2E integration tests** (`app/design_sync/tests/test_e2e_document_pipeline.py`):
  - **Figma E2E**: Mock Figma API → `build_document()` → `convert_document()` → valid email HTML with tables + MSO conditionals.
  - **MJML E2E**: MJML template → `MjmlImportAdapter.parse()` → `EmailDesignDocument` → `convert_document(output_format="mjml")` → MJML compile (35.1) → valid email HTML. Verify round-trip fidelity.
  - **HTML E2E**: Golden template HTML → `HtmlImportAdapter.parse()` → `EmailDesignDocument` → `convert_document()` → valid email HTML. Verify section count matches original.
  - **Cross-format**: Import same email as MJML and as HTML → both produce `EmailDesignDocument` with same section count and types (content may differ in extraction precision).
  - **ESP push E2E**: `convert_document()` → HTML → `ConnectorService.export("klaviyo", html)` → mock API called with correct payload. Same for HubSpot.
**Security:** Tests only. No real API calls (all mocked). Golden template fixtures from existing seeds — no external data.
**Verify:** `make test` — all new test files pass. `make check` — full suite green. Estimated 60–80 new tests. Existing design_sync tests (514+) unchanged (backward compatibility via shim).

---
