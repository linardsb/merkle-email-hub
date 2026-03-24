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

## Phase 31 — HTML Import Fidelity & Preview Accuracy

> Fix the 8 root causes that break imported pre-compiled email HTML: Maizzle double-processing, inline CSS not compiled through ontology, lost centering wrappers, dark mode text visibility, sandbox image blocking, wrapper metadata loss during section detection, incomplete typography/spacing token extraction, and missing image asset import.

- [x] ~~31.1 Maizzle passthrough for pre-compiled HTML~~ DONE
- [x] ~~31.2 Inline CSS compilation via ontology pipeline~~ DONE
- [x] ~~31.3 Preserve wrapper table metadata in section analyzer~~ DONE
- [x] ~~31.4 Wrapper reconstruction on template assembly~~ DONE
- [x] ~~31.5 Preview iframe dark mode text safety & sandbox fix~~ DONE
- [ ] 31.6 Enriched typography & spacing token pipeline
- [ ] 31.7 Image asset import & dimension preservation
- [ ] 31.8 Tests & integration verification

### 31.1 Maizzle Passthrough for Pre-Compiled HTML `[Backend + Sidecar]`
**What:** Add a detection heuristic to the Maizzle builder sidecar that identifies pre-compiled email HTML (already has inline styles, table layout, no Maizzle template syntax) and bypasses Maizzle's `render()` pipeline. Pre-compiled HTML goes through CSS optimization only (PostCSS ontology plugin + Lightning CSS minification on `<style>` blocks), then returns as-is without Juice re-inlining, Maizzle transformers, or prettification.
**Why:** When a user pastes or imports a fully-built email HTML template (exported from another tool, hand-coded, or from a client), the Maizzle `render()` pipeline double-processes it. Juice tries to re-inline `<style>` block CSS into elements that already have inline styles — producing duplicate/conflicting style attributes. Maizzle's transformers may modify URLs, reformat structure, and prettification introduces whitespace that can affect rendering in email clients. The result: scrambled HTML, broken spacing, lost font/color fidelity. Pre-compiled HTML should pass through untouched — the CSS optimization step (ontology-driven property elimination) is still valuable, but the template compilation pipeline is destructive for already-built HTML.
**Implementation:**
- Modify `services/maizzle-builder/index.js`:
  - Add `isPreCompiledEmail(source)` detection function with 4 heuristics (all must pass):
    - `hasNoMaizzleSyntax`: no `<extends`, no `<block`, no `<component`, no `<x-` custom tags, no `<fetch`, no `<outlook` Maizzle tags
    - `hasInlineStyles`: ≥3 elements with `style="..."` attributes (regex count of `style="` occurrences)
    - `hasTableLayout`: ≥2 `<table` tags with `role="presentation"` or layout attributes (`cellpadding`, `cellspacing`, `width`, `align`)
    - `hasDocumentShell`: contains `<!DOCTYPE` or `<html` + `<body` tags
  - Modify `/build` handler:
    - After CSS optimization (`optimizeCss()`), check `isPreCompiledEmail(html)`
    - If true: skip `render()`, return `{ html, build_time_ms, optimization, passthrough: true }`
    - If false: proceed with existing `render()` pipeline
  - Modify `/preview` handler: same logic — skip `render()` for pre-compiled HTML
  - Add `passthrough` boolean to response JSON so the backend can log/expose whether passthrough was used
- Modify `app/email_engine/service.py`:
  - `_call_builder()`: read `passthrough` from sidecar response, include in log event (`email_engine.preview_completed` / `email_engine.build_completed`)
  - No behavioral change needed — the sidecar decides passthrough, Python just logs it
- Modify `app/email_engine/schemas.py`:
  - Add `passthrough: bool = False` to `PreviewResponse` and `BuildResponse` schemas so the frontend can display a "passthrough" indicator if desired
**Security:** No security surface change. `sanitize_html_xss()` still runs in Python after the sidecar returns (line 127 in `service.py`). The sidecar passthrough skips Maizzle transforms but preserves the ontology-driven CSS optimization and the Python-side XSS sanitization. Pre-compiled HTML detection is read-only string analysis — no eval, no dynamic execution.
**Verify:** Paste pre-compiled email HTML (with inline styles, table layout, `<!DOCTYPE>`) into editor → press Ctrl+S → preview shows HTML faithfully without style scrambling. Same HTML sent to `/build` → response includes `passthrough: true`. Maizzle template HTML (with `<extends>`, Tailwind classes) → `passthrough: false`, normal Maizzle pipeline runs. CSS optimization still works on passthrough (unsupported properties removed from `<style>` blocks). `cd services/maizzle-builder && npm test` passes. `make test` passes.
- [x] ~~31.1 Maizzle passthrough for pre-compiled HTML~~ DONE

### 31.2 Inline CSS Compilation via Ontology Pipeline `[Backend + Sidecar]`
**What:** Route pre-compiled email HTML through proper CSS parsing and the ontology support matrix so that every CSS declaration — both in `<style>` blocks and inline `style=""` attributes — is parsed with a real CSS parser (not regex), analyzed against target email clients, optimized, shorthand-expanded, and **font-family stacks resolved per target client**. Replace the current regex-based `style=""` parsing (`_INLINE_STYLE_RE` + `line.split(":")`) with PostCSS synthetic stylesheet approach in the sidecar and CSSTree/Lightning CSS in the Python compiler. Add a client-specific font resolution layer that validates font-family values against each target client's supported font list and injects appropriate system font fallbacks.
**Why:** Pre-compiled email HTML has ~90% of its CSS in inline `style=""` attributes, not in `<style>` blocks. The sidecar's PostCSS plugin only processes `<style>` blocks. After 31.1 adds passthrough (skipping Maizzle's `render()`), inline styles bypass ALL CSS processing. Additionally, the existing `_process_css_block()` uses `line.split(":")` which breaks on CSS values containing colons (e.g., `url(https://...)`, `rgb(0, 0, 0)`) and cannot expand shorthand properties. A proper CSS parser fixes both problems: (a) all inline CSS goes through ontology optimization, and (b) shorthand properties like `font: 700 32px/40px Inter, sans-serif` and `padding: 16px 32px` are expanded into individual properties — directly improving design token extraction quality in 31.6. **Critically, font and typography handling is currently generic** — the token extractor captures whatever font-family, font-size, and spacing values it finds in the HTML and stores them as-is. But each project in the hub has its own `DesignSystem` (`app/projects/design_system.py`) with project-specific `Typography` (heading font, body font, font stacks), `BrandPalette` (colors), and spacing scales. When HTML is imported into a specific project, the extracted typography tokens should be **mapped against that project's design system** — not stored as hardcoded values from the imported HTML. Without this, an import of HTML with `font-family: Inter` into a project whose design system uses `font-family: Montserrat` will store `Inter` as the template default, and the assembler won't know to replace it with `Montserrat` during export. The same applies to font sizes, font weights, line heights, and spacing — the project's design system defines the canonical values, and imported tokens should be mapped to the nearest design system equivalent.

**The CSS parsing upgrade has three complementary layers:**

**Layer A — Sidecar (Node.js): PostCSS synthetic stylesheet approach**
The sidecar already has PostCSS and the ontology plugin loaded. Instead of adding a second regex-based inline parser, we leverage PostCSS's full CSS parser on inline styles by wrapping them in synthetic selectors.

**Layer B — Python compiler: CSSTree-equivalent via Lightning CSS**
The Python `EmailCSSCompiler._process_css_block()` currently splits on `:` and `;` (breaks on complex values). Replace with Lightning CSS's `process_stylesheet()` which handles all CSS syntax correctly (already available — `lightningcss` is a dependency).

**Layer C — Project design system font & typography mapping**
A new resolution step that runs after shorthand expansion and ontology optimization. When a project has a `DesignSystem` configured, map the imported HTML's font-family, font-size, font-weight, line-height, and spacing values to the project's design system tokens. This ensures the stored `DefaultTokens` reference the project's design system — not the arbitrary values from the imported HTML — so the assembler can correctly apply design system overrides during export.

**Implementation:**
- **Layer A — Sidecar inline style optimization:**
  - Modify `services/maizzle-builder/index.js`:
    - Add `optimizeInlineStyles(html, targetClients)` function:
      - Parse HTML with a lightweight HTML parser (use `htmlparser2` npm package — fast, streaming, handles malformed HTML)
      - For each element with a `style="..."` attribute, collect as: `.__inline_${index} { ${styleContent} }`
      - Concatenate all synthetic rules into a single stylesheet string
      - Run through PostCSS with the existing `postcss-email-optimize` plugin — this applies the full ontology (property removal, fallback conversion) on inline styles with **proper CSS parsing** (PostCSS handles colons in URLs, `calc()`, complex values)
      - After PostCSS processes the synthetic stylesheet, extract each `.__inline_${index}` rule's declarations and write back to the corresponding element's `style` attribute
      - Report inline removals/conversions alongside `<style>` block optimization
    - Add `npm install htmlparser2` to `package.json` (already common in Node.js HTML processing, ~100KB, no native deps)
    - **Shorthand expansion** — add PostCSS plugin `postcss-merge-longhand` (or its inverse `postcss-shorthand-expand`) to expand shorthands before ontology checking:
      - `font: 700 32px/40px Inter, sans-serif` → `font-weight: 700; font-size: 32px; line-height: 40px; font-family: Inter, sans-serif`
      - `padding: 16px 32px` → `padding-top: 16px; padding-right: 32px; padding-bottom: 16px; padding-left: 32px`
      - `margin: 0 auto` → `margin-top: 0; margin-right: auto; margin-bottom: 0; margin-left: auto`
      - `background: #f2f2f2 url(...) no-repeat center` → `background-color: #f2f2f2; background-image: url(...); background-repeat: no-repeat; background-position: center`
      - `border: 1px solid #e0e0e0` → `border-width: 1px; border-style: solid; border-color: #e0e0e0`
      - Use PostCSS plugin `postcss-short` or custom visitor that calls `decl.replaceWith()` for known shorthands
    - **Media query extraction** — for `<style>` block processing, parse `@media` rules and extract responsive tokens:
      - Detect responsive breakpoints: `@media screen and (max-width: 600px)`, `@media (max-width: 480px)`
      - Extract mobile-specific overrides: font-size changes, padding changes, width changes, `display: none` (hidden elements)
      - Add to optimization response: `responsive: { breakpoints: ["600px", "480px"], mobile_overrides: { font_sizes: [...], spacing: [...] } }`
      - Preserve all `@media` rules intact in the output (don't remove or modify them — just extract data for token analysis)
    - Call `optimizeInlineStyles()` in the passthrough path after `optimizeCss()` (which handles `<style>` blocks)
    - Return combined optimization metadata: `{ removed_properties, conversions, warnings, inline_removed, inline_conversions, shorthand_expansions, responsive }`
  - Modify `services/maizzle-builder/package.json`:
    - Add dependencies: `htmlparser2`, `postcss-shorthand-expand` (or equivalent)

- **Layer B — Python compiler upgrade:**
  - Modify `app/email_engine/css_compiler/compiler.py`:
    - Replace `_process_css_block()` string splitting with Lightning CSS parsing:
      - Wrap declaration string in dummy rule: `.__dummy { ${css_text} }`
      - Call `lightningcss.process_stylesheet()` with custom visitor (already imported, line 9)
      - Lightning CSS correctly parses: colons in URLs, `calc()` expressions, `var()` references, complex color values (`rgb()`, `hsl()`, `oklch()`), shorthand properties
      - Extract individual declarations from parsed AST
      - Run each through ontology check (`should_remove_property`, `get_conversions_for_property`)
      - Rebuild CSS string from surviving declarations
    - Add shorthand expansion to `_process_inline_styles()`:
      - After Lightning CSS parsing, detect shorthand properties (`font`, `padding`, `margin`, `background`, `border`, `list-style`, `transition`, `animation`)
      - Expand to longhands using Lightning CSS's built-in shorthand expansion (enable via `lightningcss.process_stylesheet()` with appropriate flags)
      - This means the Python compiler produces the same expanded output as the sidecar PostCSS layer
    - Add `expand_shorthands(css_text: str) -> str` utility method — can be called independently by the token extractor (31.6)

- **Layer C — Project design system font & typography mapping:**
  - Create `app/templates/upload/design_system_mapper.py`:
    - `DesignSystemMapper` class:
      - `__init__(design_system: DesignSystem | None)` — accepts the project's design system (may be None if project has no design system configured)
      - `map_tokens(extracted: DefaultTokens) -> DefaultTokens` — maps extracted tokens to design system equivalents:
        - **Font-family mapping:**
          - Compare extracted `fonts.heading` against `design_system.typography.heading_font` / `design_system.fonts`
          - If they differ: store BOTH as a mapping pair in `DefaultTokens` — the extracted font becomes the "find" value, the design system font becomes the "replace" value for the assembler
          - Example: imported has `Inter, sans-serif`, project design system has `Montserrat, sans-serif` → `DefaultTokens.fonts = {heading: "Inter, sans-serif"}` (the default to find), and `plan.design_tokens.fonts = {heading: "Montserrat, sans-serif"}` (the replacement)
          - Same for `body` font role
        - **Font-size mapping:**
          - Compare extracted sizes against `design_system.font_sizes` scale
          - Map each extracted size to the nearest design system size: `32px` → project's heading size (`28px`), `16px` → project's body size (`14px`)
          - Use numeric proximity: for each extracted size, find the design system size with the smallest absolute difference, assign same role
        - **Font-weight mapping:**
          - Map extracted weights to design system weights (if specified)
          - Common pattern: design system says headings are `600` (semibold), imported HTML uses `700` (bold) → map heading weight to `600`
        - **Spacing mapping:**
          - Map extracted section/element padding to design system spacing scale
          - Nearest-match: extracted `32px` → project's section spacing (`24px`), extracted `16px` → project's element spacing (`12px`)
        - **Color mapping:**
          - Already handled by `DesignSystem.resolve_color_map()` + `design_system_to_brand_rules()` (Phase 11.25)
          - But enrich with new roles: map extracted `link` color → design system link color, `accent` → design system accent, etc.
      - `generate_diff(extracted: DefaultTokens, mapped: DefaultTokens) -> list[TokenDiff]` — produces a human-readable diff:
        - `TokenDiff(property: str, role: str, imported_value: str, design_system_value: str, action: str)`
        - Actions: `"will_replace"` (assembler will swap on export), `"compatible"` (values match), `"no_override"` (design system doesn't specify this token — imported value kept)
        - This diff is surfaced in the upload preview UI so the developer sees: "Heading font: `Inter` → `Montserrat` (from project design system)", "Body size: `16px` → `14px` (nearest match)"
    - `EmailClientFontOptimizer` class (handles email-client-specific font concerns alongside project mapping):
      - `optimize_font_stack(font_family: str, target_clients: list[str]) -> str`
        - Parse the font-family stack into individual font names
        - For each target email client, check if the primary font is supported:
          - Outlook Desktop (Word engine): only system fonts — `Arial, Helvetica, sans-serif`, `Georgia, Times, serif`, `Verdana, Geneva, sans-serif`, `Tahoma, sans-serif`, `Trebuchet MS, sans-serif`, `Courier New, Courier, monospace`, `Times New Roman, Times, serif`, `Comic Sans MS, sans-serif`, `Impact, sans-serif`, `Lucida Console, Monaco, monospace`
          - Gmail: web fonts work via `<link>` in `<head>` — check if `<link>` tag loading the font exists in HTML
          - Apple Mail: all fonts supported (no restriction)
          - Yahoo: web fonts partially supported (desktop yes, mobile strips `<link>`)
          - Samsung/Android: system + installed Google Fonts
        - If primary font not supported in a target client: ensure the fallback stack includes a safe system font that's visually similar
          - `Inter` → ensure `Arial, Helvetica, sans-serif` in stack
          - `Playfair Display` → ensure `Georgia, Times, serif` in stack
          - `Roboto` → ensure `Arial, Helvetica, sans-serif` in stack
          - `Montserrat` → ensure `Verdana, Geneva, sans-serif` in stack
        - Add `mso-font-alt` property for Outlook-specific fallback: `mso-font-alt: Arial` (tells Word engine which font to use)
        - Do NOT remove the primary web font — keep it for clients that support it. Only ensure fallbacks exist.
      - `inject_web_font_loading(html: str, font_names: list[str]) -> str`
        - Check if `<head>` contains a `<link>` tag loading the font from Google Fonts or other CDN
        - If not: inject `<link href="https://fonts.googleapis.com/css2?family={font_name}&display=swap" rel="stylesheet">` for Google Fonts, or leave a warning if font source is unknown
        - Skip injection if font is a system font (no loading needed)
      - Store client font support data in `data/email_client_fonts.yaml` (or extend the existing ontology):
        ```yaml
        outlook_desktop:
          supported_fonts: [Arial, Georgia, Verdana, "Times New Roman", Tahoma, "Trebuchet MS", "Courier New", "Comic Sans MS", Impact, "Lucida Console"]
          requires_mso_font_alt: true
        gmail_web:
          supported_fonts: "*"  # all, via <link>
          requires_link_tag: true
        apple_mail:
          supported_fonts: "*"  # all
        yahoo_web:
          supported_fonts: "*"  # desktop
        yahoo_mobile:
          supported_fonts: "system"  # strips <link>
        ```
  - Modify `app/templates/upload/service.py` — `upload_and_analyze()`:
    - After CSS compilation (Layer B), before token extraction:
    - Load project's `DesignSystem` (if `project_id` provided): `design_system = await ProjectService.get_design_system(project_id)`
    - Instantiate `DesignSystemMapper(design_system)` and `EmailClientFontOptimizer()`
    - Run font optimization: `html = font_optimizer.optimize_font_stack(html, target_clients)`
    - After token extraction: `mapped_tokens = mapper.map_tokens(extracted_tokens)`
    - Generate diff: `token_diff = mapper.generate_diff(extracted_tokens, mapped_tokens)`
    - Store both `extracted_tokens` (original from HTML) and `mapped_tokens` (design-system-aligned) in analysis
    - Store `token_diff` in `analysis_dict` for the upload preview UI
  - Modify `app/templates/upload/schemas.py`:
    - Add `TokenDiffPreview` model: `property`, `role`, `imported_value`, `design_system_value`, `action`
    - Add `token_diff: list[TokenDiffPreview] = []` to `AnalysisPreview`

- **Integration with preview/build flow:**
  - Modify `app/email_engine/service.py` — `preview()` method:
    - After the sidecar returns (line 121-126), check if response includes `passthrough: true`
    - If passthrough: the sidecar already optimized both `<style>` blocks AND inline styles (Layer A). Run Python `EmailCSSCompiler` as validation/second pass (Layer B) — catches anything the sidecar missed
    - If NOT passthrough: keep existing behavior (sidecar + Maizzle handled everything)
    - Replace the simple `sanitize_html_xss(compiled)` call (line 127) with the compiler's output (which includes XSS sanitization at stage 7)
  - Modify `app/email_engine/service.py` — `build()` method:
    - Same pattern: if passthrough, sidecar already handled inline optimization, Python compiler validates
    - Store `CompilationResult` metadata (removed_properties, conversions, shorthand_expansions) in build record
  - Modify `app/email_engine/service.py` — `_call_builder()`:
    - Return `passthrough` boolean from sidecar response alongside HTML and optimization metadata
    - Signature: `-> tuple[str, dict[str, Any] | None, bool]` (add passthrough return)

- **Integration with upload flow:**
  - Modify `app/templates/upload/service.py` — `upload_and_analyze()`:
    - After sanitization (line 78), before analysis (line 81):
    - Run `EmailCSSCompiler(target_clients=project_target_clients).compile(sanitized)` on the sanitized HTML
    - This ensures stored `sanitized_html` has ontology-optimized inline styles WITH shorthand expansion
    - The token extractor (31.6) then extracts design tokens from **expanded, optimized** inline styles — `font: 700 32px/40px Inter` is already split into `font-weight: 700`, `font-size: 32px`, `line-height: 40px`, `font-family: Inter, sans-serif`
    - Pass `compilation_result` data into `analysis_dict` for the upload preview UI

- **Schemas:**
  - Add to `app/templates/upload/schemas.py`:
    - `CSSOptimizationPreview` Pydantic model: `removed_properties: list[str]`, `conversions: list[CSSConversionPreview]`, `warnings: list[str]`, `shorthand_expansions: int`, `responsive_breakpoints: list[str]`
    - Add `css_optimization: CSSOptimizationPreview | None = None` to `AnalysisPreview`
    - This surfaces the CSS compiler's decisions in the upload preview UI — developer sees "Removed `border-radius` (unsupported in Outlook Desktop)", "Expanded 12 shorthand properties", "Detected responsive breakpoints: 600px, 480px"
  - Add to `app/email_engine/schemas.py`:
    - Add `passthrough: bool = False` to `PreviewResponse` and `BuildResponse`

**Security:** PostCSS and Lightning CSS are deterministic parsers — no eval, no code execution from CSS content. `htmlparser2` is a well-audited streaming parser used by Cheerio (millions of weekly downloads). Ontology data is static JSON. The compiler's output still passes through `sanitize_html_xss()`. No new input paths — same HTML that already went through XSS sanitization.
**Verify:** Import email with `font: 700 32px/40px Inter, sans-serif` → shorthand expanded to 4 individual properties, all visible in token extraction. Import email with `display: flex` → `removed_properties` includes it. Import email with `padding: 16px 32px` → expanded to 4 longhand properties, spacing tokens capture individual sides. Import email with `url(https://example.com)` in background → colon in URL doesn't break parser. Import email with `@media (max-width: 600px)` responsive rules → `responsive_breakpoints: ["600px"]` in optimization preview, media query preserved in output. Import email with `font-family: Inter, sans-serif` into project with `DesignSystem.typography.heading_font = "Montserrat"` → token diff shows `heading font: Inter → Montserrat (will_replace)`. Import with Outlook Desktop in target clients → `mso-font-alt: Arial` added to Inter elements, fallback stack includes `Arial, Helvetica, sans-serif`. Import into project with no design system → tokens stored as-is from HTML, no mapping. Import email with only email-safe CSS → no removals, no conversions. Sidecar (Layer A) and Python compiler (Layer B) produce equivalent optimization results. `cd services/maizzle-builder && npm test` passes. `make test` passes.
- [x] ~~31.2 Inline CSS compilation via ontology pipeline~~ DONE

### 31.3 Preserve Wrapper Table Metadata in Section Analyzer `[Backend]`
**What:** Modify the `TemplateAnalyzer._detect_sections()` method to preserve the outer centering wrapper table's attributes (width, align, style, bgcolor, cellpadding, cellspacing) as structured metadata when it unwraps the single-wrapper pattern to extract inner section tables. Currently, when the analyzer finds `<table wrapper><tr><td><table section1/><table section2/>...` it replaces the wrapper with the inner tables, irreversibly losing the centering context (width="600", align="center", max-width styles).
**Why:** Email HTML universally uses an outer wrapper table for centering: `<table width="600" align="center">` or `<div style="max-width:600px; margin:0 auto">` wrapping a table. The analyzer correctly identifies inner tables as sections, but discards the wrapper. Without the wrapper metadata, reassembled HTML lacks centering — the email renders full-width, left-aligned. This is the primary cause of "template not centered" after import. The fix preserves the wrapper as metadata so it can be reconstructed during assembly (31.3).
**Implementation:**
- Modify `app/templates/upload/analyzer.py`:
  - Add `WrapperInfo` dataclass:
    ```python
    @dataclass
    class WrapperInfo:
        """Preserved metadata from the outer centering wrapper table."""
        tag: str  # "table" or "div"
        width: str | None  # e.g. "600"
        align: str | None  # e.g. "center"
        style: str | None  # full inline style string
        bgcolor: str | None
        cellpadding: str | None
        cellspacing: str | None
        border: str | None
        role: str | None  # e.g. "presentation"
        inner_td_style: str | None  # style from the <td> inside the wrapper (may have max-width, margin)
        mso_wrapper: str | None  # raw MSO conditional wrapper HTML if present (<!--[if mso]>...<![endif]-->)
    ```
  - Add `wrapper: WrapperInfo | None` field to `AnalysisResult`
  - Modify `_detect_sections()`:
    - When the single-wrapper-table branch triggers (line 162-167), before replacing `candidates`:
      - Extract all relevant attributes from `wrapper` element into `WrapperInfo`
      - Extract the `<td>` child's style attribute (the `inner_td_style` — this often has `max-width: 600px; margin: 0 auto`)
      - Search the original HTML for MSO conditional wrapper before the main table — regex: `<!--\[if mso\]>.*?<table[^>]*>.*?<tr>.*?<td[^>]*>.*?<!\[endif\]-->` (capture for reconstruction)
      - Store as `self._wrapper_info`
    - Return `self._wrapper_info` alongside sections
  - Modify `analyze()`: pass `wrapper_info` into `AnalysisResult`
- Modify `app/templates/upload/service.py`:
  - `_serialize_analysis()`: serialize `WrapperInfo` into `analysis_dict["wrapper"]` (dict with all fields)
  - `_build_preview()`: include wrapper data in preview response
- Modify `app/templates/upload/schemas.py`:
  - Add `WrapperPreview` Pydantic model with same fields as `WrapperInfo`
  - Add `wrapper: WrapperPreview | None = None` to `AnalysisPreview`
**Security:** Read-only metadata extraction from already-sanitized HTML. No new input paths. The MSO wrapper content is extracted from `sanitized_html` (already passed through `sanitize_html_xss()`).
**Verify:** Upload email HTML with `<table width="600" align="center">` wrapper → analysis preview includes `wrapper.width="600"`, `wrapper.align="center"`. Upload email with `<td style="max-width: 600px; margin: 0 auto;">` → `wrapper.inner_td_style` captured. Upload email with MSO conditional wrapper → `wrapper.mso_wrapper` contains the `<!--[if mso]>` block. Upload email with no wrapper (multiple top-level tables) → `wrapper` is null. `make test` passes.
- [x] ~~31.3 Preserve wrapper table metadata in section analyzer~~ DONE

### 31.4 Wrapper Reconstruction on Template Assembly `[Backend]`
**What:** Modify the `TemplateBuilder` and the workspace preview flow to reconstruct the outer centering wrapper around section HTML when the template was imported with wrapper metadata (from 31.2). The wrapper is re-injected so that the assembled template renders centered at the correct width, matching the original imported email.
**Why:** After 31.2 captures wrapper metadata, it needs to be applied. The `TemplateBuilder.build()` stores `sanitized_html` directly — but when the analyzer unwrapped sections from the wrapper, the `sanitized_html` still contains the original structure (the analyzer's section detection is metadata-only, it doesn't modify the HTML). The real problem is the preview/compile flow: when the user presses Ctrl+S in the workspace, the HTML in the editor may lack the centering wrapper if it was stripped during import or if the editor content was assembled from sections. This subtask ensures that (a) `sanitized_html` stored in `GoldenTemplate` retains its original wrapper, and (b) if the wrapper was somehow lost, it can be reconstructed from the stored metadata.
**Implementation:**
- Modify `app/templates/upload/template_builder.py`:
  - Accept `wrapper: WrapperInfo | None` parameter in `build()`
  - Store wrapper metadata in `GoldenTemplate` — add `wrapper_metadata: dict[str, str | None] | None` field to `GoldenTemplate` (or use existing `extra` dict if available)
  - Add `ensure_wrapper(html: str, wrapper: WrapperInfo) -> str` static method:
    - Parses HTML via lxml, checks if outer centering structure exists (looks for wrapper table with width/align or div with max-width+margin:auto)
    - If missing: wraps the body content in a reconstructed wrapper table:
      ```html
      <!--[if mso]>
      <table role="presentation" cellpadding="0" cellspacing="0" width="{width}" align="center"><tr><td>
      <![endif]-->
      <div style="max-width: {width}px; margin: 0 auto;">
        {existing body content}
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
      ```
    - If `wrapper.mso_wrapper` is available, use the original MSO block verbatim instead of generating one
    - If wrapper already exists: no-op, return HTML unchanged
  - Call `ensure_wrapper()` on `sanitized_html` before storing in `GoldenTemplate` if wrapper metadata is present
- Modify `app/email_engine/service.py`:
  - In `preview()` and `build()`: no changes needed — the HTML stored in the template already has the wrapper, and HTML pasted directly into the editor retains its original structure
- Add `app/templates/upload/wrapper_utils.py`:
  - `detect_centering(html: str) -> bool` — checks if HTML body content has a centering wrapper (table with width+align="center", or div with max-width+margin:auto, or MSO conditional table wrapper)
  - `inject_centering_wrapper(html: str, width: int = 600) -> str` — if no centering detected, wraps body content in standard email centering pattern (div + MSO ghost table)
  - These utilities can be called independently from the template upload flow (e.g., by the design sync import service)
**Security:** Wrapper reconstruction uses hardcoded centering patterns — no user input in the wrapper HTML structure. Width value comes from the original imported template (already sanitized). `ensure_wrapper()` only adds structural wrapper elements (table, div, MSO conditional) — no scripts, no event handlers. Output still passes through `sanitize_html_xss()`.
**Verify:** Import email with `width="600" align="center"` wrapper → stored template retains centering → preview shows centered at 600px. Import email where wrapper was lost during processing → `ensure_wrapper()` adds centering → preview shows centered. Import email with MSO conditional wrapper → original MSO block preserved verbatim. Import email that already has centering → no double-wrapping. `make test` passes.
- [x] ~~31.4 Wrapper reconstruction on template assembly~~ DONE

### 31.5 Preview Iframe Dark Mode Text Safety & Sandbox Fix `[Frontend]`
**What:** Fix two issues in the preview iframe component: (1) dark mode injection makes text with hardcoded dark colors invisible by not providing sufficient contrast safety, and (2) `sandbox=""` (maximum restriction) may block loading external images. Add contrast-safety CSS injection when dark mode is active, and relax sandbox to allow image loading.
**Why:** When the preview iframe's dark mode is enabled, it injects `body { background-color: #121212 !important; }` and a `<meta name="color-scheme" content="dark">` tag. This triggers `@media (prefers-color-scheme: dark)` rules in the email HTML, which apply dark backgrounds (`.dark-bg`) to sections. But elements without a corresponding `.dark-text` class keep their original dark colors (e.g., `color:#101828` nav links) — becoming invisible on the dark background. The `sandbox=""` attribute with no tokens is maximally restrictive. While images should technically load, some browsers may restrict cross-origin resource loading in fully sandboxed iframes. Adding `allow-same-origin` enables reliable image loading while still blocking scripts, forms, popups, and navigation.
**Implementation:**
- Modify `cms/apps/web/src/components/workspace/preview-iframe.tsx`:
  - **Dark mode contrast safety** — add a CSS reset that ensures minimum text contrast when dark mode is forced:
    ```typescript
    const DARK_MODE_CONTRAST_SAFETY = `<style id="preview-dark-contrast">
    /* Safety net: ensure text is readable on dark backgrounds */
    /* Only applies when no explicit dark-text class overrides */
    [class*="dark-bg"] a:not([class*="dark-text"]):not([style*="color"]) {
      color: #93c5fd !important; /* light blue for links */
    }
    [class*="dark-bg"] td:not([class*="dark-text"]) {
      color: #e5e5e5 !important; /* light gray fallback */
    }
    </style>`;
    ```
  - Inject `DARK_MODE_CONTRAST_SAFETY` alongside `DARK_MODE_STYLE` when `darkMode` is true
  - **However**, this CSS-class-based approach is fragile — the real problem is that imported emails may use arbitrary class names or no classes at all. Better approach:
    - Add a general dark-mode safety rule in the injected style:
      ```css
      /* Invert text colors that would be invisible on dark backgrounds */
      body[style*="background"] a[style*="color:#1"],
      body[style*="background"] a[style*="color:#0"],
      body[style*="background"] a[style*="color: #1"],
      body[style*="background"] a[style*="color: #0"] {
        filter: invert(1) hue-rotate(180deg) !important;
      }
      ```
    - This is still fragile. **Simplest robust fix**: add a "dark mode preview may hide some text" warning tooltip on the dark mode toggle button, AND add a complementary approach:
    - Process the HTML in the `useMemo` when `darkMode` is true: scan for inline `color:` styles with dark values (luminance < 0.3) on elements inside dark-background containers, and inject `color: #e5e5e5 !important` on those elements
    - Better: use a small DOM-based contrast check in the `useMemo`:
      ```typescript
      function ensureDarkModeContrast(html: string): string {
        // Regex: find style attributes with color values
        // For each color, check if luminance < 0.3 (dark text)
        // If dark text found, append "; color: #e5e5e5 !important" to that style
        return html.replace(
          /style="([^"]*color:\s*#([0-9a-fA-F]{3,6})[^"]*)"/gi,
          (match, styleContent, hex) => {
            const lum = relativeLuminance(hex);
            if (lum < 0.3) {
              return `style="${styleContent}; color: #e5e5e5 !important"`;
            }
            return match;
          }
        );
      }
      ```
    - Add `relativeLuminance(hex: string): number` utility — standard WCAG luminance formula (sRGB → linear → 0.2126R + 0.7152G + 0.0722B)
  - **Sandbox fix** — change `sandbox=""` to `sandbox="allow-same-origin"`:
    - `sandbox=""` → `sandbox="allow-same-origin"` on the `<iframe>` element (line 111)
    - `allow-same-origin` enables: loading cross-origin images, accessing iframe cookies (needed for some image CDNs)
    - Still blocks: scripts (`allow-scripts` NOT added), form submission, popups, top navigation
    - Note: `allow-same-origin` without `allow-scripts` is safe — the iframe content cannot execute JavaScript, so same-origin access cannot be exploited
**Security:** `sandbox="allow-same-origin"` without `allow-scripts` is explicitly safe — the iframe content has no script execution capability, so same-origin access cannot be used for XSS or data exfiltration. The dark mode contrast fix only modifies inline `color` CSS values — no script injection. The regex operates on the already-XSS-sanitized compiled HTML.
**Verify:** Import email with dark nav links (`color:#101828`) + dark mode sections → toggle dark mode → nav links remain readable (light color applied). Toggle dark mode off → original colors restored. External placeholder images (`placehold.co`, `via.placeholder.com`) load in preview. Sandbox still blocks: JavaScript execution (test with `<script>alert(1)</script>` in HTML — no alert). `make check-fe` passes.
- [x] ~~31.5 Preview iframe dark mode text safety & sandbox fix~~ DONE

### 31.6 Enriched Typography & Spacing Token Pipeline `[Backend]`
**What:** Expand the token extraction to capture font-weight, line-height, letter-spacing, link/accent/muted color roles, responsive (mobile) design tokens, and **pixel-precise spacing from Figma layout data** from imported HTML and design sync. Leverage the shorthand-expanded CSS from 31.2 (where `font: 700 32px/40px Inter` is already split into individual properties) for accurate extraction. Extend the `DesignNode` data model to carry Figma auto-layout spacing (padding, itemSpacing, gap) and actual typography properties (font_family, font_size, font_weight, line_height) — replacing the current height-as-font-size proxy. Add font-size, line-height, font-weight, and **per-section/per-element spacing** replacement steps to the `TemplateAssembler` so that exported HTML matches the Figma design in exact dimensions.
**Why:** The current pipeline has three spacing/typography fidelity gaps:

**(a) Assembler doesn't apply typography/spacing tokens.** The `TemplateAssembler` never uses `DefaultTokens.font_sizes` or `.spacing` — they're extracted and stored but ignored during export. No replacement steps exist for font-size, line-height, font-weight, or spacing.

**(b) Figma spacing data is lost at the data model layer.** `DesignNode` (protocol.py) only captures `width`, `height`, `x`, `y`. Figma's API provides per-frame `paddingTop/Right/Bottom/Left`, `itemSpacing` (gap between auto-layout children), `counterAxisSpacing`, and `layoutMode` (horizontal/vertical) — but none of this reaches `DesignNode`. The layout analyzer computes section-to-section gaps from y-position deltas (`_calculate_spacing`), but cannot capture **internal** section padding or element-to-element spacing. This means: Figma says "32px padding inside this section, 16px gap between text blocks" → the HTML gets generic padding values that may not match.

**(c) Typography uses height as font-size proxy.** `TextBlock.font_size` is set to `node.height` (layout_analyzer.py line 335) — the bounding box height, not the actual font size. A 32px heading in a 48px-tall frame gets `font_size: 48`. This cascades: wrong font-size token → wrong replacement → wrong exported size.

Additionally, color role detection is too coarse, and responsive `@media` rules define mobile typography that should be captured as mobile-specific design tokens.

**Dependency on 31.2:** After 31.2, imported HTML has shorthand-expanded inline styles. This means `_extract_tokens()` no longer needs to parse shorthand `font` or `padding` — they're already individual properties (`font-size`, `font-weight`, `line-height`, `font-family`, `padding-top`, `padding-right`, etc.). Token extraction becomes simpler and more accurate.

**Implementation:**

**Part 1 — Figma spacing & typography data model enrichment:**
- Modify `app/design_sync/protocol.py` — `DesignNode`:
  - Add auto-layout spacing fields (populated from Figma API):
    - `padding_top: float | None = None`
    - `padding_right: float | None = None`
    - `padding_bottom: float | None = None`
    - `padding_left: float | None = None`
    - `item_spacing: float | None = None` — gap between children in auto-layout
    - `counter_axis_spacing: float | None = None` — gap in the cross-axis (wrap layouts)
    - `layout_mode: str | None = None` — `"HORIZONTAL"`, `"VERTICAL"`, or None (absolute)
  - Add actual typography fields (populated from Figma TEXT node style):
    - `font_family: str | None = None`
    - `font_size: float | None = None` — actual font size, NOT bounding box height
    - `font_weight: int | None = None` — numeric weight (100-900)
    - `line_height_px: float | None = None` — resolved line height in pixels
    - `letter_spacing_px: float | None = None` — resolved letter spacing in pixels
- Modify `app/design_sync/figma/service.py` — `_parse_node()` (or equivalent):
  - Extract auto-layout properties from Figma API response:
    - `node.get("paddingTop")`, `node.get("paddingRight")`, etc.
    - `node.get("itemSpacing")` — spacing between children
    - `node.get("counterAxisSpacing")`
    - `node.get("layoutMode")` — `"HORIZONTAL"` / `"VERTICAL"` / `"NONE"`
  - Extract typography from TEXT node `style` property:
    - `style.get("fontFamily")` → `font_family`
    - `style.get("fontSize")` → `font_size` (actual size, not bounding box)
    - `style.get("fontWeight")` → `font_weight`
    - `style.get("lineHeightPx")` → `line_height_px` (Figma provides resolved px value)
    - `style.get("letterSpacing")` → `letter_spacing_px` (resolve from Figma's value + unit)
  - This data is already in the Figma API response — just not extracted into `DesignNode`
- Modify `app/design_sync/penpot/service.py` — same pattern as Figma:
  - Extract auto-layout properties from Penpot API response:
    - Penpot uses `layout` property on frames with `layout-padding`, `layout-gap`, `layout-flex-dir`
    - Map to same `DesignNode` fields: `padding_top/right/bottom/left`, `item_spacing`, `layout_mode`
  - Extract typography from TEXT node properties:
    - Penpot stores `font-family`, `font-size`, `font-weight`, `line-height` on text content objects
    - Map to `DesignNode.font_family`, `.font_size`, `.font_weight`, `.line_height_px`
  - Both providers populate the same `DesignNode` model — the layout analyzer and spacing bridge work identically regardless of source
- Modify `app/design_sync/figma/layout_analyzer.py`:
  - **Fix `TextBlock.font_size`** — use `node.font_size` (actual) instead of `node.height` (bounding box proxy):
    ```python
    # BEFORE (line 335): font_size=node.height
    # AFTER:
    font_size=node.font_size if node.font_size is not None else node.height
    ```
  - **Add `TextBlock` typography fields:**
    - Add `font_family: str | None`, `font_weight: int | None`, `line_height: float | None`, `letter_spacing: float | None` to `TextBlock`
    - Populate from `DesignNode` typography fields
  - **Add `EmailSection` spacing fields:**
    - Add `padding_top: float | None`, `padding_right: float | None`, `padding_bottom: float | None`, `padding_left: float | None` to `EmailSection`
    - Add `item_spacing: float | None` — gap between children within the section
    - Populate from the section's `DesignNode` auto-layout properties
  - **Section-internal element spacing extraction:**
    - For each section, walk children and compute element-to-element spacing:
      - If parent has `layout_mode = "VERTICAL"`: element spacing = `item_spacing` (uniform) or computed from y-position deltas between consecutive children
      - If parent has `layout_mode = "HORIZONTAL"`: column gap = `item_spacing`
      - Store as `element_gaps: list[float]` on `EmailSection` — ordered list of gaps between consecutive child elements
  - **Spacing map generation:**
    - Add `generate_spacing_map(sections: list[EmailSection]) -> dict[str, dict[str, float]]` function:
      - For each section, produces: `{section_id: {padding_top: 32, padding_right: 24, padding_bottom: 32, padding_left: 24, item_spacing: 16, spacing_after: 24}}`
      - This is the authoritative spacing specification — what the exported HTML must match
    - Add this to `DesignLayoutDescription`: `spacing_map: dict[str, dict[str, float]]`

**Part 2 — Bridge Figma spacing to DefaultTokens:**
- Modify `app/design_sync/import_service.py` (or create `spacing_bridge.py`):
  - `figma_spacing_to_tokens(layout: DesignLayoutDescription) -> dict[str, str]`:
    - Convert per-section spacing map into `DefaultTokens.spacing` format:
      - Most common section padding → `"section_padding": "32px"`
      - Most common item spacing → `"element_gap": "16px"`
      - Most common horizontal padding → `"section_horizontal_padding": "24px"`
      - Section-to-section gap → `"section_gap": "24px"`
    - Per-section overrides for sections with non-standard spacing:
      - `"hero_padding_top": "48px"`, `"footer_padding_top": "24px"` (if different from default)
  - `figma_typography_to_tokens(layout: DesignLayoutDescription) -> dict[str, str]`:
    - Use actual `TextBlock.font_size` (now correct, not height proxy):
      - Heading size → largest font_size from heading TextBlocks
      - Body size → most common non-heading font_size
      - Small/caption size → smallest font_size
    - Font family from TextBlock.font_family
    - Font weight from TextBlock.font_weight
    - Line height from TextBlock.line_height
  - Store the **full spacing map** (per-section, pixel-precise) as extended metadata on `GoldenTemplate` — this is the source of truth for export fidelity
  - Store responsive spacing if Figma design has a mobile frame variant:
    - Detect mobile frame: frame named "mobile", "375", "phone", or width ≤ 414px
    - Extract mobile frame's spacing map → store as `responsive` tokens

**Part 3 — HTML token extraction (from imported HTML, not Figma):**
- Modify `app/templates/upload/analyzer.py` — `_extract_tokens()`:
  - **Inline style extraction** — since 31.2 expands shorthands, the existing regex patterns now capture individual properties reliably:
    - `font_weight_pattern = re.compile(r"font-weight:\s*(\d{3}|bold|normal|lighter|bolder)")` — already expanded from `font:` shorthand by 31.2
    - `line_height_pattern = re.compile(r"line-height:\s*(\d+(?:\.\d+)?(?:px|em|rem|%)?|\d+(?:\.\d+)?)")` — already expanded
    - `letter_spacing_pattern = re.compile(r"letter-spacing:\s*(-?\d+(?:\.\d+)?(?:px|em|rem)?)")` — extract with unit
    - Padding is now longhand (`padding-top`, `padding-right`, etc.) — extract individual sides for precise spacing tokens
  - **`<style>` block media query extraction** — parse `<style>` content for `@media` rules:
    - Use regex or lxml to extract `@media screen and (max-width: Npx)` blocks
    - Inside each media query block, extract CSS declarations that override typography:
      - `font-size` overrides → `mobile_font_sizes: dict[str, str]` (e.g., `{heading: "24px", body: "14px"}`)
      - `line-height` overrides → `mobile_line_heights: dict[str, str]`
      - `padding` overrides → `mobile_spacing: dict[str, str]`
      - `display: none` rules → `mobile_hidden_sections: list[str]` (classes/selectors hidden on mobile)
    - Store breakpoint values: `responsive_breakpoints: list[str]` (e.g., `["600px", "480px"]`)
  - Extend `TokenInfo` dataclass:
    - Add `font_weights: dict[str, list[str]]` — keyed by `"heading"` vs `"body"`
    - Add `line_heights: dict[str, list[str]]` — keyed by `"heading"` vs `"body"`
    - Add `letter_spacings: dict[str, list[str]]` — keyed by `"heading"` vs `"body"`
    - Add `responsive: dict[str, dict[str, list[str]]]` — keyed by breakpoint, then by property type (e.g., `{"600px": {"font_sizes": ["24px", "14px"], "spacing": ["16px"]}}`)
  - Color extraction enrichment — categorize by element context:
    - Inside `<a>` tags → `"link"` color role
    - On elements with large font-size (≥24px) or heading tags → `"heading_text"` role
    - On elements with font-size ≤12px or in footer-classified sections → `"muted"` role
    - Colors that appear exactly once in a prominent position (CTA, sale badge) → `"accent"` role
- Modify `app/templates/upload/token_extractor.py` — `TokenExtractor`:
  - Add `_resolve_font_weights()` → `dict[str, str]` with roles `"heading"`, `"body"`
  - Add `_resolve_line_heights()` → `dict[str, str]` with roles `"heading"`, `"body"`, `"small"`
  - Add `_resolve_letter_spacings()` → `dict[str, str]` with roles `"heading"`, `"body"` (if present)
  - Add `_resolve_responsive()` → `dict[str, dict[str, str]]` — flattened responsive tokens:
    - `{"mobile_heading_size": "24px", "mobile_body_size": "14px", "mobile_section_padding": "16px", "breakpoint": "600px"}`
    - These are separate from desktop tokens — the design system can override both independently
  - Enrich `_resolve_colors()`:
    - Add `"link"`, `"muted"`, `"accent"`, `"heading_text"` roles from enriched color data
    - Keep backward-compatible: `"text"`, `"secondary"`, `"cta"`, `"background"` still populated
- Modify `app/ai/templates/models.py` — `DefaultTokens`:
  - Add `font_weights: dict[str, str]` (default empty dict)
  - Add `line_heights: dict[str, str]` (default empty dict)
  - Add `letter_spacings: dict[str, str]` (default empty dict)
  - Add `responsive: dict[str, str]` (default empty dict) — flat map of mobile-specific token overrides
  - Add `responsive_breakpoints: tuple[str, ...] = ()` — detected breakpoints for reference
  - These are additive fields with defaults — no migration needed, backward compatible
- Modify `app/ai/agents/scaffolder/assembler.py` — `TemplateAssembler.assemble()`:
  - Add **Step 3b: Font-size replacement** after font replacement (Step 3):
    - `_apply_font_size_replacement(html, template.default_tokens, plan.design_tokens) -> str`
    - For each role in `default_tokens.font_sizes` (e.g., `heading: "32px"`), find all occurrences of that CSS value in `font-size:` declarations and replace with the corresponding value from `plan.design_tokens.font_sizes`
    - Only replace within inline `style="..."` attributes (not in `<style>` blocks — those handle responsive sizing)
  - Add **Step 3c: Line-height replacement**:
    - `_apply_line_height_replacement(html, template.default_tokens, plan.design_tokens) -> str`
    - Same pattern: match `line-height: {default}` → replace with design system value
    - Proportional safety: if default line-height was `40px` for `32px` font (1.25 ratio) and new font-size is `28px`, compute proportional line-height (`35px`) if no explicit line-height override in design tokens
  - Add **Step 3d: Pixel-precise spacing replacement**:
    - `_apply_spacing_replacement(html, template.default_tokens, plan.design_tokens, spacing_map: dict | None) -> str`
    - **If spacing_map is available** (from Figma import via Part 2): use the per-section spacing map as the source of truth. For each section in the HTML (identified by `data-section-id` or comment markers), apply the exact padding values from the map:
      - `padding-top: {spacing_map[section_id]["padding_top"]}px`
      - `padding-right: {spacing_map[section_id]["padding_right"]}px`
      - etc.
      - Element spacing within sections: if section has `item_spacing`, add/update `padding-bottom` or spacer `<tr>` on each child element to match the gap
    - **If no spacing_map** (raw HTML import): fall back to token-based replacement — match individual longhand properties: `padding-top: {default}`, `padding-right: {default}`, etc. with design system overrides
    - **Section-to-section spacing**: if `spacing_map` has `spacing_after` values, ensure the gap between sections matches — either via `padding-bottom` on the section's wrapper `<td>` or a spacer `<tr><td style="padding: 0; height: {gap}px; line-height: {gap}px; font-size: 1px;">&nbsp;</td></tr>`
    - Be conservative on fallback: only replace exact matches of the extracted default values
  - Add **Step 3e: Font-weight replacement**:
    - `_apply_font_weight_replacement(html, template.default_tokens, plan.design_tokens) -> str`
    - Match `font-weight: {default}` → replace for heading/body roles
  - Add **Step 3f: Responsive token replacement** (applies to `<style>` block `@media` rules):
    - `_apply_responsive_replacement(html, template.default_tokens, plan.design_tokens) -> str`
    - Inside `@media` blocks, replace mobile font-size/line-height/spacing defaults with design system mobile overrides
    - **If Figma mobile frame spacing was captured** (Part 2): use the mobile spacing map to set exact mobile padding/font-size values in `@media` rules
    - **Mobile font-size overrides**: if design specifies mobile heading at `24px` (vs desktop `32px`), update `@media (max-width: 600px) { .heading { font-size: 24px !important } }`
    - **Mobile spacing overrides**: if design specifies mobile section padding at `16px` (vs desktop `32px`), update corresponding `@media` rules
    - **Generate `@media` rules if none exist**: if the imported HTML has no responsive `@media` but the design system/Figma specifies mobile overrides, inject a new `<style>` block with responsive rules:
      ```css
      @media screen and (max-width: 600px) {
        .section-hero td { padding: 16px !important; }
        h1 { font-size: 24px !important; line-height: 30px !important; }
        /* ... generated from mobile spacing/typography tokens */
      }
      ```
    - Only if `plan.design_tokens.responsive` has overrides — otherwise leave `@media` rules untouched
    - Parse `<style>` blocks, find `@media` at-rules, apply replacements within those blocks only
  - Guard all new steps: only execute if `template.default_tokens` has the corresponding field populated AND `plan.design_tokens` has the override value
**Security:** All replacements are deterministic string substitution on sanitized HTML. No eval, no regex injection (default values are hex/numeric extracted from sanitized HTML). Media query parsing is read-only extraction, no CSS injection. No new input paths.
**Verify:**
- *Typography from HTML:* Import email with `Inter 32px/40px bold` headings + `16px/26px normal` body → `DefaultTokens` captures `font_sizes: {heading: "32px", body: "16px"}`, `font_weights: {heading: "700", body: "400"}`, `line_heights: {heading: "40px", body: "26px"}`.
- *Shorthand expansion:* Import email with `font: 700 32px/40px Inter` shorthand → after 31.2 expansion, tokens correctly capture all 4 individual properties.
- *Figma spacing fidelity:* Figma design with section padding `32px top, 24px sides` and `16px` item spacing → exported HTML has `padding: 32px 24px` on section `<td>` and `16px` gaps between child elements. Figma section-to-section gap of `24px` → spacer row or padding matches exactly.
- *Figma typography fidelity:* Figma TEXT node with `font_size: 32, font_weight: 700, line_height: 40px, font_family: Inter` → `TextBlock` captures actual values (not bounding box height proxy). Exported HTML `font-size: 32px; font-weight: 700; line-height: 40px; font-family: Inter, sans-serif`.
- *Responsive/mobile:* Figma mobile frame (width ≤ 414px) with `padding: 16px, heading font-size: 24px` → responsive tokens captured. Exported HTML has `@media (max-width: 600px) { h1 { font-size: 24px !important } td { padding: 16px !important } }`.
- *Responsive from HTML:* Import email with `@media (max-width: 600px) { h1 { font-size: 24px } }` → `responsive: {mobile_heading_size: "24px"}`, `responsive_breakpoints: ("600px",)`.
- *Design system overrides:* Apply design system with `font_sizes: {heading: "28px", body: "14px"}` → assembled HTML has `font-size: 28px` on headings, `14px` on body. Apply with `responsive: {mobile_heading_size: "22px"}` → `@media` block updated. If no `@media` existed, one is generated.
- *Color roles:* Link colors extracted as `link` role (not generic `text`). `make test` passes.
- [ ] 31.6 Enriched typography & spacing token pipeline

### 31.7 Image Asset Import & Dimension Preservation `[Backend]`
**What:** Add image asset downloading and re-hosting to the template upload pipeline, matching what the design-sync import service already does. Extract image dimensions (width/height) from `<img>` tags and store them as structured metadata alongside the template, so that images are reliably served from the hub's asset storage and their dimensions are preserved for layout fidelity.
**Why:** When a user uploads pre-compiled email HTML, the image `src` URLs point to external servers (CDNs, placeholder services, the user's staging server). These external URLs may be temporary, rate-limited, CORS-blocked, or unreachable from the preview iframe's sandbox. The design-sync import path (`import_service.py`) already downloads images via `_download_and_store_assets()` and replaces URLs with hub-hosted `/api/v1/design-sync/assets/...` URLs — but the template upload path (`upload/service.py`) does nothing with images. This means: (a) preview shows broken images when external URLs fail, (b) exported HTML references URLs the user may not control long-term, (c) image dimensions in the HTML may not match the actual image dimensions (e.g., `width="600"` on a 1200px source image — the attribute is the display dimension, not the intrinsic dimension).
**Implementation:**
- Create `app/templates/upload/image_importer.py`:
  - `ImageImporter` class:
    - `async import_images(html: str, project_id: int | None) -> tuple[str, list[ImportedImage]]`
    - Parses HTML via lxml, finds all `<img>` elements
    - For each image:
      - Skip tracking pixels (width ≤ 2 or height ≤ 2)
      - Skip data URIs (`src` starting with `data:`)
      - Skip already-hub-hosted URLs (matching `/api/v1/` pattern)
      - Download image via `httpx.AsyncClient` with timeout (5s per image, 30s total)
      - On download failure: log warning, keep original URL (don't break the template)
      - Store downloaded image in hub's asset storage (reuse `DesignAssetService` or `FileStorageService` from `app/shared/`)
      - Replace `src` URL with hub-hosted URL
      - Extract actual image dimensions from downloaded bytes (use Pillow `Image.open()` for raster, or parse SVG viewBox)
    - `ImportedImage` dataclass:
      - `original_url: str`
      - `hub_url: str`
      - `display_width: int | None` — from HTML `width` attribute
      - `display_height: int | None` — from HTML `height` attribute
      - `intrinsic_width: int` — actual image pixel width
      - `intrinsic_height: int` — actual image pixel height
      - `alt: str`
      - `file_size_bytes: int`
      - `mime_type: str`
    - Return modified HTML + list of `ImportedImage` for metadata storage
  - `_is_tracking_pixel(img_element) -> bool` — width ≤ 2 AND height ≤ 2 (both attributes present and tiny)
  - `_download_with_retry(url: str, max_retries: int = 2) -> bytes | None` — GET with User-Agent header, follow redirects, retry on 429/503
- Modify `app/templates/upload/service.py`:
  - In `upload_and_analyze()`, after sanitization (line 78) and before analysis (line 81):
    - Call `ImageImporter.import_images(sanitized, project_id)`
    - Replace `sanitized` with the modified HTML (hub-hosted URLs)
    - Store `imported_images` list in `analysis_dict["images"]`
  - In `confirm()`: images are already re-hosted in the `sanitized_html`, no additional work needed
- Modify `app/templates/upload/analyzer.py`:
  - In `_extract_tokens()`, add image dimension extraction:
    - For each `<img>` with `width` and `height` attributes, store in `TokenInfo` as `image_dimensions: dict[str, list[tuple[int, int]]]` keyed by section context
  - This is informational (not applied during assembly) but useful for layout token understanding
- Modify `app/templates/upload/schemas.py`:
  - Add `ImagePreview` Pydantic model: `original_url`, `hub_url`, `display_width`, `display_height`, `intrinsic_width`, `intrinsic_height`, `alt`, `file_size_bytes`
  - Add `images: list[ImagePreview] = []` to `AnalysisPreview`
- Config: `TEMPLATES__IMPORT_IMAGES: bool = True` — feature flag, disabled by default until verified. `TEMPLATES__MAX_IMAGE_DOWNLOAD_SIZE: int = 5_242_880` (5MB per image). `TEMPLATES__MAX_IMAGES_PER_TEMPLATE: int = 50`.
**Security:** Image downloads use `httpx.AsyncClient` with strict timeout (5s), max response size (5MB), and no cookie forwarding. Only HTTP/HTTPS schemes allowed (reject `file://`, `ftp://`, `data:` for download). Downloaded content is validated as an image (check magic bytes / content-type header before storing). Hub asset URLs go through existing asset serving endpoint with auth. Pillow image parsing uses `Image.open()` which is safe for untrusted input (no code execution). Rate-limit image imports: max 50 images per template, max 20MB total per upload.
**Verify:** Upload HTML with external placeholder images → analysis preview shows `images` list with hub URLs. Preview iframe loads images from hub URLs (no broken images). Upload HTML with tracking pixels → pixels skipped (not downloaded). Upload HTML with unreachable image URL → original URL kept, warning logged, template still works. Upload HTML with data URI images → data URIs preserved as-is (not downloaded). Image dimensions match: `display_width=600` from HTML `width` attribute, `intrinsic_width=1200` from actual image. `make test` passes.
- [ ] 31.7 Image asset import & dimension preservation

### 31.8 Tests & Integration Verification `[Full-Stack]`
**What:** End-to-end tests verifying the full HTML import pipeline: raw pre-compiled email HTML → upload/paste → preview → export, with assertions on centering, image loading, font/color preservation, dark mode readability, typography token fidelity, and structural integrity.
**Implementation:**
- **Sidecar tests** — `services/maizzle-builder/`:
  - Add to existing test file or create `passthrough.test.js`:
    - `isPreCompiledEmail()` returns true for: HTML with inline styles + table layout + DOCTYPE
    - `isPreCompiledEmail()` returns false for: Maizzle template with `<extends>`, raw HTML without inline styles, HTML fragment without DOCTYPE
    - `/build` with pre-compiled HTML → response has `passthrough: true`, HTML structure unchanged (no Juice re-inlining artifacts)
    - `/build` with Maizzle template → response has `passthrough: false`, CSS inlined normally
    - `/build` with pre-compiled HTML + `target_clients` → CSS optimization still applied (ontology removals), but no `render()` transforms
    - `/preview` with pre-compiled HTML → same passthrough behavior
- **Backend tests** — `app/templates/upload/tests/`:
  - `test_analyzer_wrapper.py`:
    - Analyzer detects single wrapper table → `wrapper_info` populated with width, align, style, cellpadding, cellspacing
    - Analyzer detects `<td style="max-width: 600px; margin: 0 auto;">` → `wrapper.inner_td_style` captured
    - Analyzer detects MSO conditional wrapper → `wrapper.mso_wrapper` captured
    - Analyzer with multiple top-level tables (no wrapper) → `wrapper` is None
    - Analyzer with `<center>` wrapper → sections detected inside, wrapper metadata from center element
    - Section count unchanged — wrapper detection doesn't affect section identification
  - `test_wrapper_utils.py`:
    - `detect_centering()` → true for: table with width+align, div with max-width+margin:auto, MSO ghost table wrapper
    - `detect_centering()` → false for: table without width/align, no wrapper at all
    - `inject_centering_wrapper()` → adds div+MSO wrapper, width defaults to 600
    - `inject_centering_wrapper()` on already-centered HTML → no double-wrapping (idempotent)
  - `test_template_builder_wrapper.py`:
    - `build()` with wrapper metadata → `ensure_wrapper()` preserves centering in stored HTML
    - `build()` without wrapper → HTML stored as-is
- **Frontend tests** — `cms/apps/web/src/components/workspace/__tests__/`:
  - `preview-iframe.test.tsx`:
    - Dark mode enabled → contrast safety styles injected
    - Dark mode disabled → no contrast modification
    - `relativeLuminance("#101828")` → value < 0.3 (dark)
    - `relativeLuminance("#e5e5e5")` → value > 0.7 (light)
    - `ensureDarkModeContrast()` replaces dark inline colors with light fallback
    - Sandbox attribute includes `allow-same-origin`
    - Sandbox attribute does NOT include `allow-scripts`
- **Backend tests (continued)** — `app/templates/upload/tests/`:
  - `test_token_extractor_enriched.py`:
    - HTML with `font-weight: 700` on headings → `font_weights: {heading: "700"}`
    - HTML with `line-height: 40px` on headings, `26px` on body → `line_heights: {heading: "40px", body: "26px"}`
    - HTML with `letter-spacing: 0.5px` → `letter_spacings: {heading: "0.5px"}`
    - Link colors (`<a style="color:#32A5DB">`) → `colors` includes `link: "#32A5DB"`
    - Muted footer text (`font-size: 12px; color: #999`) → `colors` includes `muted: "#999999"`
    - Accent color (`color:#EF3E5D` on single prominent element) → `colors` includes `accent: "#EF3E5D"`
    - Backward compatibility: `text`, `secondary`, `cta`, `background` roles still populated
  - `test_assembler_typography.py`:
    - `_apply_font_size_replacement()` replaces `font-size: 32px` → `font-size: 28px` for heading role
    - `_apply_line_height_replacement()` replaces `line-height: 40px` → proportional value
    - `_apply_spacing_replacement()` replaces `padding: 32px` → design system section spacing
    - `_apply_font_weight_replacement()` replaces `font-weight: 700` → design system heading weight
    - No replacement when design tokens don't have override → original values preserved
  - `test_image_importer.py`:
    - HTML with external image URL → image downloaded, URL replaced with hub URL
    - Tracking pixel (1x1) → skipped
    - Data URI image → preserved as-is
    - Already-hub-hosted URL → skipped
    - Unreachable URL → original URL kept, warning logged
    - Image dimensions extracted correctly (display vs intrinsic)
    - Max image count enforced (>50 → remaining skipped with warning)
- **E2E test** — `cms/apps/web/e2e/import-fidelity.spec.ts`:
  - Paste pre-compiled email HTML into code editor
  - Press Ctrl+S to compile
  - Assert: preview iframe renders (not blank)
  - Assert: email content is visually centered (not full-width)
  - Assert: no duplicate inline styles (no Juice re-inlining artifacts)
  - Assert: dark mode toggle → text remains readable (no invisible text)
  - Assert: images load (hub-hosted URLs or test fixture images)
  - Assert: typography tokens extracted (font-size, font-weight, line-height visible in analysis)
- Fixture: add `cms/apps/web/e2e/fixtures/pre-compiled-email.html` — a representative pre-compiled email HTML with inline styles, table layout, MSO conditionals, dark mode classes, external images, Inter font with multiple weights/sizes, and centering wrapper. Use a real-world-like template (not synthetic).
**Security:** Tests only. No production code changes. Test fixtures contain no real credentials or PII.
**Verify:** `cd services/maizzle-builder && npm test` passes (passthrough tests). `make test` passes (analyzer + wrapper + builder + token + image tests). `make check-fe` passes (iframe tests). `npx playwright test import-fidelity` passes (e2e). `make check` all green.
- [ ] 31.8 Tests & integration verification

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

## Success Criteria (Phase 31 — Current)

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
