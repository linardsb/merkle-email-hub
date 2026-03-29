# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–36):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA). Phase 18 (rendering resilience & property-based testing). Phase 19 (Outlook transition advisor & email CSS compiler). Phase 20 (Gmail AI intelligence & deliverability). Phase 21 (real-time ontology sync & competitive intelligence). Phase 22 (AI evolution infrastructure). Phase 23 (multimodal protocol & MCP agent interface — 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks). Phase 25 (platform ecosystem & advanced integrations — 15 subtasks). Phase 26 (email build pipeline performance & CSS optimization — 5 subtasks). Phase 27 (email client rendering fidelity & pre-send testing — 6 subtasks). Phase 28 (export quality gates & approval workflow — 3 subtasks). Phase 29 (design import enhancements — 2 subtasks). Phase 30 (end-to-end testing & CI quality — 3 subtasks). Phase 31 (HTML import fidelity & preview accuracy — 8 subtasks). Phase 32 (agent email rendering intelligence — 12 subtasks: centralized client matrix, content rendering awareness, import annotator skills, knowledge lookup tool, cross-agent insight propagation, eval-driven skill updates, visual QA feedback loop, MCP agent tools, skill versioning, per-client skill overlays). Phase 33 (design token pipeline overhaul — 12 subtasks). Phase 34 (CRAG accept/reject gate — 3 subtasks). Phase 35 (next-gen design-to-email pipeline — 11 subtasks: MJML compilation, tree normalizer, MJML generation, section templates, AI layout intelligence, visual fidelity scoring, correction learning loop, W3C design tokens, Figma webhooks, section caching). Phase 36 (universal email design document & multi-format import hub — 7 subtasks: EmailDesignDocument JSON Schema, converter refactor, Figma/Penpot adapters, MJML import, HTML reverse engineering, Klaviyo + HubSpot ESP export). Phase 37 (golden reference library for AI judge calibration — 5 subtasks: expand golden component library with VML/MSO/ESP/innovation templates, reference loader & criterion mapping, wire into judge prompts, re-run pipeline & measure improvement, complete human labeling).

---

## Phase 37 — Golden Reference Library for AI Judge Calibration

> **The eval judges are grading blind.** All 9 AI judges (Scaffolder, Dark Mode, Content, Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Innovation, Knowledge) evaluate agent output using text-only criteria descriptions — no concrete HTML examples of what "correct" looks like. The 540 human labeling rows exist but can't be completed efficiently because there's no shared reference standard. Meanwhile, 17 Outlook-tested golden components sit in `email-templates/components/` completely disconnected from the eval system.
>
> **This phase builds a curated Golden Reference Library** and wires it into every judge's prompt as few-shot examples. Judges that can *see* correct patterns (proper table nesting, valid VML, real MSO conditionals, working dark mode) will be more accurate out of the box — reducing disagreements during human labeling and making the entire eval pipeline (skill updates, regression gates, production monitoring) trustworthy.
>
> **What exists today:** 17 components covering basic patterns (columns, buttons, heroes, footers, preheader, navigation, shell). **What's missing:** VML-heavy backgrounds, complex nested MSO conditionals, multi-ESP token examples (Braze/SFMC/Adobe Campaign/Klaviyo), and innovation technique references (CSS carousels, accordion dropdowns, AMP components, kinetic email).
>
> **Dependency note:** Independent of Phases 36/38/39. Uses existing judge infrastructure (`app/ai/agents/evals/judges/`). Golden components from `email-templates/components/` are the starting point. New reference templates can be added incrementally — the system is designed to grow.

- [x] 37.1 Expand golden component library with advanced patterns
- [x] 37.2 Build golden reference loader & criterion mapping
- [x] 37.3 Wire golden references into judge prompts
- [ ] 37.4 Re-run judge pipeline & measure calibration improvement
- [ ] 37.5 Complete human labeling with improved judges

---

### 37.1 Expand Golden Component Library `[Templates]`

**What:** Add 14 new golden reference templates to `email-templates/components/golden-references/` covering VML backgrounds, complex MSO conditionals, multi-ESP token syntax (Braze/SFMC/Adobe Campaign/Klaviyo), and CSS innovation techniques (carousels, accordions, AMP, kinetic hover). Each template is hand-verified, Outlook-tested, and annotated with which judge criteria it exemplifies.
**Why:** The 17 existing golden components cover basic patterns (columns, buttons, heroes, footers) but judges evaluating VML correctness, ESP token syntax, or innovation techniques have zero concrete examples. Without references, a judge can't distinguish valid `v:roundrect` from broken VML, correct Braze Liquid from invalid syntax, or a working CSS carousel from a broken one. Adding verified-correct templates for each gap area gives judges concrete ground truth to compare against — the same principle that makes few-shot prompting more accurate than zero-shot.
**Implementation:**
- Create 14 new templates in `email-templates/components/golden-references/`:
  - **VML / MSO (templates 1-4):**
    - `vml-background-image.html` — `v:image`/`v:fill type="frame"`, MSO conditional, CSS `background-image` fallback. Serves Scaffolder `mso_conditional_correctness`, Outlook Fixer `vml_wellformedness`
    - `vml-rounded-button-variants.html` — `v:roundrect` with `arcsize`, `fillcolor`, `strokecolor`, `href`; multiple size/style variants. Serves Outlook Fixer `vml_wellformedness`, Scaffolder `email_layout_patterns`
    - `nested-mso-conditionals.html` — nested `<!--[if mso]>`, `<!--[if gte mso 9]>`, `<!--[if !mso]><!-->`, version-targeted blocks. Serves Scaffolder + Outlook Fixer `mso_conditional_correctness`
    - `complex-hybrid-layout.html` — 3+ column hybrid with MSO ghost table + inline-block + `font-size:0` + `dir="rtl"` reversal. Serves Scaffolder `email_layout_patterns`, Code Reviewer `issue_genuineness`
  - **Dark mode / Accessibility (templates 5-6):**
    - `dark-mode-complete.html` — full dark mode: meta tags, `@media (prefers-color-scheme: dark)`, `[data-ogsc]`/`[data-ogsb]`, utility classes, contrast-safe palette. Serves Dark Mode all 5 criteria
    - `accessibility-compliant.html` — `lang`, `role="presentation"`, `role="article"`, heading hierarchy, descriptive alt text, ARIA, link text. Serves Accessibility all 5 criteria
  - **ESP tokens (templates 7-10):**
    - `esp-braze-liquid.html` — `{{ variable | default: 'fallback' }}`, `{% if %}` conditionals, `connected_content`, content blocks. Serves Personalisation `syntax_correctness`, `fallback_completeness`, `platform_accuracy`
    - `esp-sfmc-ampscript.html` — `%%[...]%%`, `%%=...=%%`, `Lookup()`, `IIF()`, `IF/ELSE` fallbacks, data extensions. Same criteria
    - `esp-adobe-campaign.html` — `<%= %>`, `<% %>`, `recipient.field`, ternary fallbacks. Same criteria
    - `esp-klaviyo-django.html` — `{{ variable|default:"fallback" }}`, `{% if %}`, `{% for %}`, catalog lookups. Same criteria
  - **Innovation techniques (templates 11-14):**
    - `innovation-css-carousel.html` — CSS-only carousel: hidden checkbox + label + sibling selectors, `@keyframes`, static fallback. Serves Innovation `technique_correctness`, `fallback_quality`
    - `innovation-accordion-dropdown.html` — CSS checkbox-hack accordion: `:checked` toggle, Outlook static fallback. Same criteria
    - `innovation-amp-email.html` — `<amp-carousel>`, `<amp-form>`, `<amp-bind>`, AMP boilerplate, MIME fallback note. Same criteria
    - `innovation-kinetic-hover.html` — `:hover` CTA reveal, animated underlines, color transitions, touch fallback. Serves Innovation `technique_correctness`, `innovation_value`
- Each template includes a frontmatter comment block:
  ```html
  <!-- golden-ref: criteria=[mso_conditional_correctness, vml_wellformedness], agents=[scaffolder, outlook_fixer], verified=2026-03-28 -->
  ```
**Security:** Read-only template files. No executable code. ESP token templates use syntactically valid but non-functional placeholder syntax (no real API keys or endpoints).
**Verify:** 14 new templates in `golden-references/`. Each has frontmatter `<!-- golden-ref: ... -->`. VML templates (#1-4) validate in Outlook (manual spot-check). ESP templates (#7-10) use syntactically valid platform syntax. Innovation templates (#11-14) include working static fallback HTML. `make test` passes.

---

### ~~37.2 Build Golden Reference Loader & Criterion Mapping~~ `[Backend]` DONE

**What:** Create `app/ai/agents/evals/golden_references.py` — a loader that reads golden reference templates from `email-templates/components/golden-references/`, parses their frontmatter annotations, and maps them to judge criteria. Create `index.yaml` as the registry that controls which snippet from which file serves which criterion.
**Why:** Judges need to query "show me examples for `mso_conditional_correctness`" and get the relevant HTML snippets. Without a structured loader, each judge would need hardcoded paths and manual snippet extraction — unmaintainable as the library grows. The loader provides a single API: `get_references_for_criterion(name) → list[(name, html_snippet)]`. YAML-based registry means new templates are auto-discovered without code changes. Snippet extraction (not full files) keeps prompts within token budget.
**Implementation:**
- Create `app/ai/agents/evals/golden_references.py`:
  ```python
  @dataclass(frozen=True)
  class GoldenReference:
      name: str
      html: str  # extracted snippet, not full file
      criteria: list[str]
      agents: list[str]
      verified_date: str

  @lru_cache(maxsize=1)
  def load_golden_references() -> list[GoldenReference]:
      """Discover and load all golden reference templates."""
      index = _load_index()  # reads index.yaml
      refs = []
      for entry in index["references"]:
          html = _extract_snippet(entry["file"], entry.get("selector"))
          refs.append(GoldenReference(
              name=entry["name"], html=html[:_MAX_SNIPPET_LINES],
              criteria=entry["criteria"], agents=entry["agents"],
              verified_date=entry.get("verified", "unknown"),
          ))
      return refs

  def get_references_for_criterion(criterion_name: str) -> list[tuple[str, str]]:
      """Return (name, html_snippet) pairs for a criterion. Max 3 snippets."""
      refs = load_golden_references()
      matches = [(r.name, r.html) for r in refs if criterion_name in r.criteria]
      return matches[:3]  # budget cap

  def get_references_for_agent(agent_name: str) -> list[GoldenReference]:
      """Return all references relevant to an agent."""
      return [r for r in load_golden_references() if agent_name in r.agents]
  ```
- Create `email-templates/components/golden-references/index.yaml`:
  ```yaml
  references:
    - name: VML Background Image
      file: vml-background-image.html
      selector: "v:rect...v:textbox"  # extract just the VML block
      criteria: [mso_conditional_correctness, vml_wellformedness]
      agents: [scaffolder, outlook_fixer]
      verified: "2026-03-28"
    - name: CTA Button (VML + HTML)
      file: ../../cta-button.html  # reference existing golden component
      criteria: [vml_wellformedness, email_layout_patterns]
      agents: [scaffolder, outlook_fixer]
    # ... 14+ entries
  ```
- **Design decisions:**
  - Snippets not full files — 80-line cap per snippet, CSS-like selector or line range to extract relevant portion
  - YAML registry, not hardcoded Python — new templates auto-discovered
  - Budget: max 3 snippets per criterion, ~2000 tokens total golden reference injection per judge call
  - `@lru_cache` — no startup cost, loaded on first judge call

**Security:** Read-only file operations. `_extract_snippet()` uses line ranges or regex selectors — no eval/exec. Template paths validated against `golden-references/` directory to prevent path traversal.
**Verify:** `load_golden_references()` discovers all templates in `golden-references/`. `get_references_for_criterion("mso_conditional_correctness")` returns snippets from `nested-mso-conditionals.html`, `email-shell.html`, `cta-button.html`. Snippets respect 80-line cap. `get_references_for_agent("outlook_fixer")` returns VML-related refs. Cache works (second call doesn't re-read files). 15 tests: loading, criterion mapping, agent mapping, snippet extraction, budget cap, cache behavior.

---

### ~~37.3 Wire Golden References into Judge Prompts~~ `[Backend, Evals]` DONE

**What:** Modify all 7 HTML-evaluating judge `build_prompt()` methods to inject golden reference snippets from the loader (37.2). Each judge sees verified-correct examples alongside the agent's output. Content, Knowledge, and Visual QA judges are excluded (text-only/screenshot-based criteria — golden HTML not applicable).
**Why:** Zero-shot judging (criteria description only) forces judges to infer what "correct" looks like from text descriptions alone. Few-shot judging (criteria + concrete examples) is empirically more accurate — the judge can pattern-match against known-good HTML instead of guessing. This is the core calibration improvement: judges that can *see* proper VML, valid MSO conditionals, or correct Liquid syntax will produce more consistent verdicts, reducing the human labeling burden in 37.5.
**Implementation:**
- Add `golden_references: list[tuple[str, str]] | None` param to `BaseJudge.build_prompt()` in `app/ai/agents/evals/judges/base.py`
- Inject golden references into `SYSTEM_PROMPT_TEMPLATE`:
  ```
  ## GOLDEN REFERENCE EXAMPLES
  The following are verified-correct email HTML patterns. Use them as your standard for what "correct" looks like when evaluating the criteria above.

  {golden_snippets}
  ```
- Per-judge wiring:
  - **Scaffolder judge:** inject for `email_layout_patterns`, `mso_conditional_correctness`, `dark_mode_readiness`, `accessibility_baseline` — after brief, before agent HTML
  - **Dark Mode judge:** inject for `color_coherence`, `outlook_selector_completeness`, `meta_and_media_query` — after input HTML, before output HTML
  - **Outlook Fixer judge:** inject for `mso_conditional_correctness`, `vml_wellformedness`, `fix_completeness`, `outlook_version_targeting` — after input, before output
  - **Accessibility judge:** inject for `wcag_aa_compliance`, `alt_text_quality`, `semantic_structure`, `screen_reader_compatibility` — after input, before output
  - **Personalisation judge:** inject for `syntax_correctness`, `fallback_completeness`, `platform_accuracy` — **platform-conditional**: only inject matching ESP template (Braze → `esp-braze-liquid.html`, SFMC → `esp-sfmc-ampscript.html`)
  - **Code Reviewer judge:** inject for `issue_genuineness`, `severity_accuracy` — **inverted framing**: "These are correct patterns — do NOT flag them as issues"
  - **Innovation judge:** inject for `technique_correctness`, `fallback_quality` — **category-conditional**: inject matching technique template (carousel → `innovation-css-carousel.html`)
- Each judge's `build_prompt()` calls `get_references_for_criterion()` for its relevant criteria, concatenates snippets, respects 2000-token total budget

**Security:** Golden reference HTML is static, verified content from the repository — not user-supplied. No injection risk. Token budget cap prevents prompt overflow.
**Verify:** All 7 HTML-evaluating judges inject golden references. Prompt token budget ≤2000 tokens for golden section. Personalisation judge with `platform="braze"` → only `esp-braze-liquid.html` injected. Code Reviewer prompt contains "do NOT flag them as issues". Innovation judge with `category="carousel"` → only carousel template injected. Judge with no matching references → graceful fallback (no golden section in prompt). 14 tests: prompt injection, platform filtering, category filtering, budget cap, inverted framing, no-references fallback.

---

### ~~37.4 Re-run Judge Pipeline & Measure Calibration Improvement~~ DONE `[Evals]`

**What:** Re-run the eval pipeline with golden-reference-enhanced judges against the existing traces. Create a comparison script that diffs verdicts before/after to measure improvement and identify criteria with high flip rates for priority human review.
**Delivered:** `scripts/eval-compare-verdicts.py` (comparison CLI with per-criterion flip rate analysis, priority review flagging at >20% threshold, JSON report output, 14 tests). `make eval-rejudge` (re-run without `--skip-existing`) and `make eval-compare` Makefile targets. Pre-golden verdicts backed up in `traces/pre_golden/`. All 9 agents re-judged with golden-reference-enhanced prompts (hybrid mode, Claude Sonnet). **Results:** 15 of 35 criteria flagged for priority human review — golden references made judges significantly more discriminating (e.g. `code_reviewer:output_format` flipped 100% P→F, `scaffolder:brief_fidelity` 83% P→F against mock output). Report at `traces/verdict_comparison.json`.

---

### 37.5 Complete Human Labeling with Improved Judges `[Manual + Evals]`

**What:** Label all 540 evaluation rows using `docs/eval-labeling-tool.html`, prioritizing criteria where judges changed verdicts (high-flip from 37.4). Run calibration to validate that golden-reference-enhanced judges meet TPR ≥ 0.85 and TNR ≥ 0.80 per criterion.
**Why:** The eval pipeline's trustworthiness depends on calibrated judges. Without human labels, we can't measure judge accuracy (TPR/TNR), which means we can't trust the eval gates that control skill updates, regression detection, or production monitoring. The golden references (37.1-37.3) should improve judge accuracy — but only human labels can confirm this. Labeling 540 rows (36 traces × 5 criteria × 3 agent groups) takes ~2-4 hours with the labeling tool. Prioritizing high-flip criteria from 37.4 ensures the most uncertain verdicts get reviewed first.
**Implementation:**
- Regenerate label templates from new verdicts: `make eval-labels`
- Update `docs/eval-labeling-tool.html` with fresh data
- Label 540 rows using the tool:
  - Priority 1: criteria with >20% flip rate from 37.4 verdict comparison
  - Priority 2: criteria with >10% flip rate
  - Priority 3: remaining criteria (spot-check)
- Export JSONL files back to `traces/`
- Run calibration:
  ```bash
  make eval-calibrate      # TPR/TNR per judge criterion
  make eval-qa-calibrate   # Agreement per QA check
  ```
- If TPR < 0.85 or TNR < 0.80 on any criterion → iterate: add more golden references for that criterion, adjust judge prompt, re-run 37.4

**Security:** Human labels are stored locally in `traces/` JSONL files. No external transmission. Labeling tool runs client-side in browser.
**Verify:** All 540 rows labeled (`human_pass` != null in all 3 JSONL files). `make eval-calibrate` reports TPR ≥ 0.85 and TNR ≥ 0.80 per judge criterion. `make eval-qa-calibrate` reports agreement ≥ 75% per QA check. Any alternatives from labeling tool exported and reviewed. Calibration results documented.

---

### Phase 37 — Summary

| Subtask | Scope | Dependencies | Effort |
|---------|-------|--------------|--------|
| 37.1 Expand golden library | `email-templates/components/golden-references/` | None — start immediately | 14 new templates |
| ~~37.2 Golden reference loader~~ DONE | `app/ai/agents/evals/golden_references.py`, `index.yaml` | 37.1 (templates exist) | ~200 LOC + 18 tests |
| ~~37.3 Wire into judge prompts~~ DONE | 7 judge files + `base.py` | 37.2 (loader ready) | ~150 LOC + 22 tests |
| ~~37.4 Re-run & measure~~ DONE | `scripts/eval-compare-verdicts.py`, Makefile | 37.3 (judges updated) | Script + pipeline run, 15/35 criteria flagged |
| 37.5 Human labeling | `docs/eval-labeling-tool.html`, `traces/*.jsonl` | 37.4 (improved judges) | ~2-4 hours manual |

> **Execution:** 37.1 is independent — start immediately (template authoring). 37.2–37.3 are sequential (loader → wiring). 37.4 depends on 37.3. 37.5 depends on 37.4. **The golden templates (37.1) are the long pole** — everything else is mechanical wiring.

---

## Phase 38 — Design-to-Email Pipeline Fidelity Fix

> **The pipeline is structurally sound but loses data fidelity at every stage.** A full audit found 67 bugs across the Figma parser, tree normalizer, layout analyzer, converter, MJML generator, template engine, section cache, import service, and HTML import adapter. The root cause is NOT an architectural flaw — it's accumulated implementation bugs: Python falsy traps (`0.0 or default`), incomplete property copying, fragile heuristics, and two divergent MJML output paths. Every stage silently drops or corrupts data, and the errors compound.
>
> **Is this fixable?** Yes. No rewrites needed. The data model (`DesignNode`, `EmailSection`, `EmailDesignDocument`) is correct. The pipeline stages are correctly ordered. The bugs are all local — wrong conditionals, missing fields, off-by-one thresholds. This phase fixes them bottom-up: parser first (so downstream stages receive correct data), then normalization, then layout analysis, then output. Each subtask is independently shippable and testable.
>
> **Phasing rationale:** 8 subtasks ordered by data flow. 38.1 fixes the data source (Figma parser) — everything depends on this. 38.2 fixes normalization — depends on 38.1. 38.3 fixes layout analysis — depends on 38.2. 38.4 fixes HTML/MJML output — depends on 38.3. 38.5 fixes the HTML import path (independent of 38.1–38.4) and adds regression tests. 38.6 fixes the component matcher & renderer — the layer that maps sections to component templates and fills slots. 38.7 fixes column HTML structure to match golden components. 38.8 fixes image alt text quality and font family preservation. Validated against real Mammut Figma conversion (see `docs/html_converted_from_figma.html`).
>
> **Golden standard:** All converter output is validated against `email-templates/components/*.html` — 16 battle-tested component templates that render correctly across all email clients. These components define the exact HTML patterns the converter must produce. See the **Golden HTML Reference** section below for the canonical patterns.

### Golden HTML Reference (from `email-templates/components/`)

> These patterns are the **source of truth** for converter output. Every subtask in Phase 38 must produce HTML that matches these structures. The 16 golden components (`email-shell.html`, `hero-block.html`, `full-width-image.html`, `column-layout-2.html`, `column-layout-3.html`, `column-layout-4.html`, `article-card.html`, `image-grid.html`, `product-card.html`, `cta-button.html`, `preheader.html`, `logo-header.html`, `navigation-bar.html`, `header.html`, `footer.html`, `reverse-column.html`) are already tested for cross-client rendering. The converter must emit HTML that is structurally identical to these patterns.

**G-REF-1: Column layout — hybrid `<div class="column">` pattern (NOT `<table><tr><td>` wrapping)**
```html
<!-- from column-layout-2.html — the ONLY correct column wrapper pattern -->
<td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
  <!--[if mso]>
  <table role="presentation" width="100%"><tr><td width="300" valign="top">
  <![endif]-->
  <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td data-slot="col_1" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
        <!-- column content here -->
      </td></tr>
    </table>
  </div>
  <!--[if mso]>
  </td><td width="300" valign="top">
  <![endif]-->
  <!-- second column ... -->
</td>
```
**Why:** `<div class="column">` enables mobile stacking via `.column { display: block !important; }`. The converter currently wraps columns in `<table><tr><td style="display:inline-block">` which does NOT respond to mobile CSS.

**G-REF-2: Image — block display, full-width, explicit dimensions, meaningful alt**
```html
<!-- from full-width-image.html + hero-block.html -->
<img data-slot="image_url" class="bannerimg" src="..." alt="Full width image"
     width="600" style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
```
Required: `display: block`, `width: 100%`, `height: auto`, `border: 0`, HTML `width` attribute, meaningful `alt` (not `"mj-image"`).

**G-REF-3: CTA button — dual VML + HTML**
```html
<!-- from cta-button.html -->
<td align="center" style="padding: 30px 0;">
  <!--[if mso]>
  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{{ href }}"
    style="height:48px;v-text-anchor:middle;width:220px;" arcsize="10%"
    strokecolor="{{ color }}" fillcolor="{{ color }}">
    <w:anchorlock/><center style="color:#ffffff;font-size:16px;font-weight:bold;">{{ text }}</center>
  </v:roundrect>
  <![endif]-->
  <!--[if !mso]><!-->
  <a href="{{ href }}" style="display: inline-block; background-color: {{ color }};
     color: #ffffff; font-size: 16px; font-weight: bold; line-height: 48px;
     text-align: center; text-decoration: none; width: 220px; border-radius: 4px;">{{ text }}</a>
  <!--<![endif]-->
</td>
```

**G-REF-4: Text — proper heading/body separation**
```html
<!-- from hero-block.html + article-card.html -->
<h2 class="textblock-heading" style="margin: 0 0 8px; font-size: 20px; font-weight: bold; color: #333333; line-height: 1.3;">HEADING</h2>
<p class="textblock-body" style="margin: 0 0 16px; font-size: 14px; color: #555555; line-height: 1.5;">Body text.</p>
```
Headings in `<h1>`-`<h3>`, body in `<p>`, `margin: 0` reset, `color` from design (not hardcoded when Figma says white).

**G-REF-5: Product card — structured column content**
```html
<!-- from product-card.html -->
<td style="padding: 20px;">
  <img src="{{ image }}" alt="{{ name }}" width="280" style="display: block; width: 100%; height: auto; border: 0;">
  <h3 style="margin: 0 0 8px; font-size: 18px; font-weight: bold; color: #0c2340;">{{ name }}</h3>
  <p style="margin: 0; font-size: 14px; color: #666666; line-height: 1.5;">{{ description }}</p>
</td>
```
Current converter dumps column content as raw text — each content type needs its own HTML element.

**G-REF-6: Email shell — required meta/MSO/dark mode**
```html
<!-- from email-shell.html -->
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no">
<div style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">Preheader</div>
@media (prefers-color-scheme: dark) { .dark-bg { background-color: #1a1a2e !important; } }
[data-ogsc] .dark-bg { background-color: #1a1a2e !important; }  /* Outlook.com */
```

---

- [x] 38.1 Figma parser data fidelity fixes ~~DONE~~
- [x] 38.2 Tree normalizer & normalization pipeline fixes ~~DONE~~
- [x] 38.3 Layout analyzer & section classification fixes ~~DONE~~
- [x] 38.4 Converter, MJML generator & template engine fixes ~~DONE~~
- [x] 38.5 Import service, HTML import adapter & regression tests ~~DONE~~
- [x] 38.6 Component matcher & renderer fidelity fixes ~~DONE~~
- [x] 38.7 Column HTML structure — `<div class="column">` pattern ~~DONE~~
- [x] 38.8 Image alt text, font family preservation & background images ~~DONE~~

---

### ~~38.1 Figma Parser Data Fidelity Fixes `[Backend]`~~ DONE

**What:** Fix 5 bugs in `figma/service.py:_parse_node()` that corrupt `DesignNode` data before it reaches any downstream stage. Add text color extraction from TEXT node fills so that text-on-colored-background scenarios produce readable output.
**Why:** Every downstream stage depends on `_parse_node()` producing accurate data. Python falsy traps (`0.0 or 1.0`) corrupt opacity, auto-layout extraction ignores COMPONENT/INSTANCE nodes (losing spacing), and fill extraction is order-dependent. TEXT node fills (carrying text color) are never extracted — causing the most visible bug: dark `#333333` text on colored backgrounds where Figma specifies white. The Mammut email has white text on orange `#FE5117` — currently rendered as dark gray.
**Implementation:**
- Fix Bug 1 (CRITICAL) — opacity falsy trap in `figma/service.py:1190`:
  ```python
  # BEFORE: opacity=0.0 → 0.0 or 1.0 → 1.0
  opacity = _float_or_none(node_data.get("opacity")) or 1.0
  # AFTER:
  raw_opacity = node_data.get("opacity")
  opacity = float(raw_opacity) if raw_opacity is not None else 1.0
  ```
- Fix Bug 2 (HIGH) — auto-layout scope in `figma/service.py:1075`:
  ```python
  # BEFORE: if raw_type == "FRAME":
  # AFTER:
  if raw_type in ("FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"):
      layout_mode = node_data.get("layoutMode")
      padding_top = _float_or_none(node_data.get("paddingTop"))
      # ... paddingRight/Bottom/Left, itemSpacing, counterAxisSpacing
  ```
- Fix Bug 3 (MEDIUM) — fill order in `figma/service.py:1123`: single-pass collection, no `break` on IMAGE for VECTOR — collect `fill_color` from last visible SOLID, `image_ref` from first IMAGE, gradient from first gradient
- Fix Bug 4 (LOW) — `GRADIENT_RADIAL` → extract midpoint color as fallback
- Fix Bug 5 (LOW) — `visible: null` → `bool(node_data.get("visible", True))`
- **NEW — Text color extraction** (CRITICAL for visual correctness, not in original audit):
  ```python
  # In TEXT node branch of _parse_node():
  if raw_type == "TEXT":
      text_fills = node_data.get("fills", [])
      for fill in reversed(text_fills):
          if fill.get("type") == "SOLID" and fill.get("visible", True):
              c = fill["color"]
              text_color = _rgba_to_hex(c["r"], c["g"], c["b"], fill.get("opacity", 1.0))
              break
  ```
  - Foundation for Bug #50 (38.6) — without this, text color can never reach output HTML
  - Validate: TEXT nodes on Mammut orange section have white fills → must extract `#FFFFFF`

| # | Severity | File:Line | Bug | Fix |
|---|----------|-----------|-----|-----|
| 1 | CRITICAL | `figma/service.py:1190` | `opacity 0.0 or 1.0` — falsy trap | `float(x) if x is not None else 1.0` |
| 2 | HIGH | `figma/service.py:1075` | Auto-layout only for FRAME | Extend to COMPONENT/COMPONENT_SET/INSTANCE |
| 3 | MEDIUM | `figma/service.py:1123` | Fill order-dependent | Single-pass, no `break` |
| 4 | LOW | `figma/service.py:820` | Only `GRADIENT_LINEAR` | Add `GRADIENT_RADIAL` midpoint |
| 5 | LOW | `figma/service.py:1189` | `visible: null` treated as visible | `bool(node_data.get("visible", True))` |
| NEW | CRITICAL | `figma/service.py` (TEXT branch) | TEXT node fills never extracted | Extract `text_color` from TEXT `fills[]` |

**Security:** No new input paths. Existing validation unchanged.
**Verify:** `opacity=0.0` → `DesignNode(opacity=0.0)` (NOT `1.0`). COMPONENT with `layoutMode: "VERTICAL"` → spacing populated. `[IMAGE, SOLID]` fill order → both extracted. TEXT on orange bg → `text_color="#FFFFFF"`. Existing tests pass + 15 new tests.

---

### ~~38.2 Tree Normalizer & Normalization Pipeline Fixes `[Backend]`~~ DONE

**What:** Fix 5 bugs in `figma/tree_normalizer.py` that corrupt spacing calculations, drop INSTANCE node data, and lose dimensions during group flattening.
**Why:** The normalizer sits between parser and layout analyzer. Wrong `item_spacing` (absolute coordinates instead of gaps), skipped INSTANCE normalization (dead code), and lost `width`/`height` during group flattening cause wrong column grouping, inflated spacing, and misclassified sections downstream.
**Implementation:**
- Fix Bug 6 (HIGH) — item_spacing in `tree_normalizer.py:188`:
  ```python
  # BEFORE: gap = sorted_ys[i+1] - sorted_ys[i]  (includes child height!)
  # AFTER:
  gap = next_child.y - (current.y + (current.height or 0))
  gaps.append(max(0.0, gap))  # clamp overlaps to 0
  item_spacing = statistics.median(gaps) if gaps else 0.0
  ```
- Fix Bug 7 (MEDIUM) — dead code in `tree_normalizer.py:92`: remove `raw_file_data` guard, resolve INSTANCE→FRAME unconditionally
- Fix Bug 8 (MEDIUM) — group flattening in `tree_normalizer.py:141`: inherit `width`/`height` from parent GROUP when child has `None`
- Fix Bug 9 (MEDIUM) — text merge in `tree_normalizer.py:249`: use `current_node.height or current.line_height_px` as spacing estimate
- Fix Bug 10 (LOW) — prune childless containers in `tree_normalizer.py:90`: after removing invisible children, remove empty GROUP/FRAME nodes that have no visual content (`fill_color`, `image_ref`)

| # | Severity | File:Line | Bug | Fix |
|---|----------|-----------|-----|-----|
| 6 | HIGH | `tree_normalizer.py:188` | item_spacing includes child height | Compute gap between bounding boxes, clamp ≥0 |
| 7 | MEDIUM | `tree_normalizer.py:92` | `_resolve_instances` gated on unused param | Remove guard, resolve unconditionally |
| 8 | MEDIUM | `tree_normalizer.py:141` | Group flattening drops width/height | Inherit from parent GROUP |
| 9 | MEDIUM | `tree_normalizer.py:249` | Text merge uses CSS line_height | Use node.height or line_height_px |
| 10 | LOW | `tree_normalizer.py:90` | Empty containers not pruned | Remove childless GROUP/FRAME without visual content |

**Security:** Internal tree transformations only. No new input paths.
**Verify:** Vertically stacked children with 20px gaps → `item_spacing=20.0` (not `120.0`). INSTANCE → resolved to FRAME. Group children inherit parent dimensions. Adjacent TEXT merged. Empty GROUP pruned. Existing tests pass + 10 new tests.

---

### ~~38.3 Layout Analyzer & Section Classification Fixes `[Backend]`~~ DONE

**What:** Fix 9 bugs in `figma/layout_analyzer.py` covering heading detection, footer classification, column grouping, and button detection. Add button text exclusion from body text extraction to prevent CTA labels appearing as body paragraphs (root cause of Bug #49).
**Why:** The layout analyzer classifies `DesignNode` trees into `EmailSection` objects. When heading detection over-triggers, body text gets wrapped in `<h3>` tags. When button text isn't excluded from `_walk_for_texts()`, labels like "SHOP THE COLLECTION" appear as body paragraphs instead of CTAs — violating G-REF-3. When column grouping is order-dependent, the same design produces different HTML each time.
**Implementation:**
- Fix Bug 11-12 (HIGH) — heading threshold in `layout_analyzer.py:897-922`:
  ```python
  def _detect_content_hierarchy(self, texts: list[TextBlock]) -> None:
      sizes = [t.font_size for t in texts if t.font_size]
      if not sizes or len(set(sizes)) == 1:
          return  # Bug 12: uniform sizes → no headings
      median_size = statistics.median(sizes)
      for text in texts:
          if text.font_size and text.font_size >= median_size * 1.3:  # Bug 11: 1.3x median
              text.is_heading = True
  ```
- Fix Bug 13 (MEDIUM) — footer false positive: require position in bottom 30% AND legal text
- Fix Bug 14 (MEDIUM) — pattern matching: word-boundary `re.search(rf'\b{pattern}\b', name_lower)`
- Fix Bug 15 (MEDIUM) — image child detection: recurse 2 levels deep
- Fix Bug 16 (MEDIUM) — column grouping: sort by Y first, greedy non-overlapping bands, sort each row by X
- Fix Bug 17 (MEDIUM) — field preservation: `dataclasses.replace()` instead of constructor
- Fix Bug 18-19 (LOW) — CTA classification + ghost button detection
- **NEW — Button text exclusion** (root cause of Bug #49):
  ```python
  def _extract_texts(self, node, *, exclude_node_ids: set[str] | None = None) -> list[TextBlock]:
      if exclude_node_ids and node.id in exclude_node_ids:
          return []
      # ... existing logic
  ```
  - Call `_extract_buttons()` first → collect button parent IDs → pass to `_extract_texts(exclude_node_ids=...)`
  - Prevents "SHOP THE COLLECTION", "BUILD YOUR LAYERS →" from appearing as body text

| # | Severity | File:Line | Bug | Fix |
|---|----------|-----------|-----|-----|
| 11 | HIGH | `layout_analyzer.py:907` | Heading threshold too low (0.8x max) | 1.3x median + early return for uniform sizes |
| 12 | HIGH | `layout_analyzer.py:907` | Uniform sizes → all headings | `len(set(sizes)) == 1: return` |
| 13 | MEDIUM | `layout_analyzer.py:526` | Footer false positive on "all rights reserved" | Require bottom 30% position AND legal text |
| 14 | MEDIUM | `layout_analyzer.py:140` | Substring pattern too broad | Word-boundary matching |
| 15 | MEDIUM | `layout_analyzer.py:881` | Image child only direct children | Recurse 2 levels |
| 16 | MEDIUM | `layout_analyzer.py:722` | Column Y-grouping order-dependent | Sort Y first, greedy bands, sort X |
| 17 | MEDIUM | `layout_analyzer.py:939` | Fields lost in section rebuild | `dataclasses.replace()` |
| 18 | LOW | `layout_analyzer.py:597` | CTA by height alone | Require button-like content |
| 19 | LOW | `layout_analyzer.py:863` | Ghost buttons missed | Check border-color + text heuristic |
| NEW | CRITICAL | `layout_analyzer.py:751` | Button text in body text | Exclude button node IDs from `_extract_texts()` |

**Security:** No new input paths. Classification heuristics don't affect data boundaries.
**Verify:** 16px body + 18px heading → body NOT heading (ratio 1.125 < 1.3). Uniform 16px → zero headings. "SHOP THE COLLECTION" in `section.buttons`, NOT in `section.texts`. Column grouping of 2×2 grid → deterministic. Footer in mid-email → CONTENT type. Existing tests pass + 18 new tests.

---

### ~~38.4 Converter, MJML Generator & Template Engine Fixes~~ `[Backend]` DONE

**What:** Fix 16 bugs in `converter.py`, `mjml_generator.py`, `mjml_template_engine.py`, and `section_cache.py`. Enforce golden template quality patterns (G-REF-1 through G-REF-6) in all converter output.
**Why:** The converter is the final HTML generation stage. `_sanitize_css_value` strips `()` from `rgb()` (Bug 20). `padding_top or 0` treats `0.0` as falsy (Bug 21). Templates use `typo.base_size` for all text (Bug 23-24). The golden components define exactly how output must look — `role="presentation"` on tables (G1), `display: block` on images (G-REF-2), `[data-ogsc]` dark mode selectors (G-REF-6), `mso-hide: all` on preheader (G-REF-6). Output that doesn't match these patterns breaks in real email clients.
**Implementation:**
- Fix Bug 20 (CRITICAL) — CSS sanitizer: allow balanced parens, strip `; {} \ < >` only
- Fix Bug 21 (HIGH) — replace ALL `x or default` with `x if x is not None else default` across converter, mjml_generator
- Fix Bug 22 (HIGH) — duplicate Outlook button: wrap HTML in `<!--[if !mso]>` per G-REF-3
- Fix Bug 23-24 (HIGH) — per-text properties in MJML templates: thread `text.font_size`, `text.font_weight`, `text.font_family`, `text.text_color` into Jinja2 context
- Fix Bug 25 (HIGH) — section cache hash: add `font_size`, `font_weight`, `font_family`, `text_color`, `is_heading`
- Fix Bugs 26-35 (MEDIUM/LOW) — p style injection, VML font, dark mode bg, section markers, multi-column fallback, MJML padding, preheader filter, mj-body placement, last p margin, padding rounding
- **Golden pattern enforcement:**
  - G1: `role="presentation"` on every `<table>` in `_render_table_open()`
  - G-REF-2: `display: block; width: 100%; height: auto; border: 0;` + HTML `width` on all `<img>` in `_render_image()`
  - G-REF-6: `<meta name="format-detection">` in head, `mso-hide: all` on preheader, `[data-ogsc]`/`[data-ogsb]` alongside `@media` dark mode
  - G12: `font-size: 0` on column container `<td>`

| # | Severity | Bug | Fix |
|---|----------|-----|-----|
| 20 | CRITICAL | `_sanitize_css_value` strips `()` | Allow balanced parens |
| 21 | HIGH | `padding_top or ...` falsy trap | `x if x is not None else default` |
| 22 | HIGH | Duplicate Outlook button | VML + `<!--[if !mso]>` per G-REF-3 |
| 23-24 | HIGH | Templates ignore per-text styling | Thread per-text props into Jinja2 |
| 25 | HIGH | Cache ignores text styling | Add font/color fields to hash |
| 26-35 | MED-LOW | p style, VML font, dark mode, markers, column fallback, padding | Individual fixes per bug table |
| G1 | — | Missing `role="presentation"` | Add to `_render_table_open()` |
| G-REF-2 | — | Images missing `display:block` / `width` | Enforce in `_render_image()` |
| G-REF-6 | — | Missing meta/preheader/Outlook dark mode | Add to shell output |
| G12 | — | Column container missing `font-size:0` | Add to column `<td>` |

**Security:** CSS sanitizer must still strip `expression()`, `url(javascript:)`. Test XSS payloads blocked.
**Verify:** `rgb(255, 0, 0)` survives sanitizer. `padding: 0` → `padding="0"` in MJML. Per-text fonts in templates. Cache invalidates on `text_color` change. Single Outlook button. Every `<table>` has `role="presentation"`. Every `<img>` has `display: block` + `width`. Dark mode has `[data-ogsc]`. Preheader has `mso-hide: all`. `format-detection` meta present. Column `<td>` has `font-size: 0`. Existing tests pass + 28 new tests.

---

### 38.5 Import Service, HTML Import Adapter & Regression Tests `[Backend]`

**What:** Fix 13 bugs in `import_service.py`, `service.py`, `html_import/`, and `ai_layout_classifier.py`. Add E2E regression tests using golden components (`email-templates/components/`) as round-trip ground truth.
**Why:** The import service is the alternate entry point. When `_get_direct_text` drops `<b>` content, bold disappears. When `_filter_structure` strips `fill_color`, sections lose backgrounds. The 16 golden components are the ground truth — if a golden template round-trips (import → `EmailDesignDocument` → convert) and the output doesn't match the original patterns, something is broken.
**Implementation:**
- Fix Bug 36 (CRITICAL) — `_get_direct_text`: add `b`, `strong`, `em`, `i` to `_TEXT_TAGS`
- Fix Bug 37 (HIGH) — `_filter_structure`: `dataclasses.replace(node, children=filtered_children)`
- Fix Bugs 38-48 — spacing tokens, fidelity commit, layout classifier, synthetic IDs, transparent color, text color extraction, line-height, column detection, max-width parsing, preheader detection, social classification
- **Golden template regression suite:**
  - Round-trip 5 golden components: `hero-block.html`, `column-layout-2.html`, `article-card.html`, `product-card.html`, `footer.html` → import → `EmailDesignDocument` → convert → validate:
    - `role="presentation"` on tables (G1)
    - `display: block` on images (G-REF-2)
    - Headings in `<h1>`-`<h3>` (G-REF-4)
    - Body in `<p>` (G-REF-4)
    - Buttons as `<a>` (G-REF-3)
    - Text content preserved, color palette ±5%, section count matches

| # | Severity | Bug | Fix |
|---|----------|-----|-----|
| 36 | CRITICAL | `_get_direct_text` drops `<b>` content | Add to `_TEXT_TAGS` |
| 37 | HIGH | `_filter_structure` drops rich properties | `dataclasses.replace()` |
| 38 | HIGH | Spacing tokens dropped | Add `spacing=` to `ExtractedTokens` |
| 39 | HIGH | Fidelity `flush()` not `commit()` | Change to `commit()` |
| 40 | HIGH | `_build_prompt` IndexError | Pass per-position types |
| 41-48 | MED-LOW | Synthetic IDs, transparent, text color, line-height, columns, max-width, preheader, social | Individual fixes |

**Security:** `_get_direct_text` changes don't introduce XSS — caller sanitizes via `sanitize_html_xss()`.
**Verify:** `<b>Bold</b>` preserved. `fill_color` preserved through filtering. Spacing tokens present. Fidelity persisted. Golden round-trip: `hero-block.html` → import → convert → has `<h1>`, `display:block` images, `role="presentation"`. 5 golden template regression + 18 unit tests.

---

### ~~38.6 Component Matcher & Renderer Fidelity Fixes `[Backend]`~~ DONE

**What:** Fix 11 bugs in `component_matcher.py`, `component_renderer.py`, and `layout_analyzer.py` that cause buttons as body text, unreadable text colors, raw text dumps in columns, and placeholder text leaks. Generate structured semantic HTML in column fills matching G-REF-4 and G-REF-5.
**Why:** The component matcher bridges design data to rendered HTML. The Mammut conversion shows every failure: "SHOP THE COLLECTION" as body text (not CTA per G-REF-3), `#333333` text on `#FE5117` orange (Figma says white), product cards as raw text dumps (should be `<img>` + `<h3>` + `<p>` per G-REF-5), and "Image caption — describe..." placeholder text. Compare broken `docs/html_converted_from_figma.html` section_5:212-216 (raw text) against `product-card.html` (structured HTML).
**Implementation:**
- Fix Bug 49 (CRITICAL) — buttons as body text: with button exclusion from 38.3, render `section.buttons` as CTA elements matching G-REF-3:
  ```python
  for btn in section.buttons:
      url = btn.url or "#"
      bg = btn.fill_color or "#0066cc"
      btn_html = (f'<a href="{html_escape(url)}" style="display:inline-block;'
                  f'padding:10px 24px;background-color:{bg};color:#ffffff;'
                  f'text-decoration:none;font-size:14px;font-weight:bold;'
                  f'border-radius:4px;">{html_escape(btn.text)}</a>')
  ```
- Fix Bug 50 (CRITICAL) — text color: with `TextBlock.text_color` from 38.1, add to `_build_token_overrides()`:
  ```python
  if heading and heading.text_color:
      overrides["heading_color"] = heading.text_color  # e.g., #FFFFFF on orange bg
  ```
- Fix Bug 51 (HIGH) — semantic column HTML matching G-REF-5:
  ```python
  def _build_column_fill_html(self, group: ColumnGroup) -> str:
      parts = []
      for img in group.images:
          parts.append(f'<img src="{url}" alt="{alt}" style="display:block;width:100%;height:auto;border:0;" />')
      for text in group.texts:
          color = text.text_color or "#333333"
          if text.is_heading:
              parts.append(f'<h3 style="margin:0 0 8px;font-size:{text.font_size or 18}px;font-weight:bold;color:{color};">{html_escape(text.content)}</h3>')
          else:
              parts.append(f'<p style="margin:0 0 8px;font-size:{text.font_size or 14}px;color:{color};line-height:1.5;">{html_escape(text.content)}</p>')
      for btn in group.buttons:
          parts.append(f'<a href="{html_escape(btn.url or "#")}" style="display:inline-block;padding:10px 24px;background-color:{btn.fill_color or "#0066cc"};color:#ffffff;text-decoration:none;font-size:14px;font-weight:bold;border-radius:4px;">{html_escape(btn.text)}</a>')
      return "\n".join(parts)
  ```
- Fix Bug 52 (HIGH) — article-card over-matching: >2 images → `image-grid`/`multi-column`, column groups → `multi-column`
- Fix Bug 53 (HIGH) — multi-paragraph: join all body texts as separate `<p>` elements
- Fix Bug 54 (HIGH) — placeholder suppression: post-render strip + explicit empty `SlotFill` for optional slots
- Fix Bugs 55-59 (MEDIUM/LOW) — multi-wrapper extraction, partial padding, spatial column assignment, CTA URLs, footer sub-elements

| # | Severity | Bug | Fix |
|---|----------|-----|-----|
| 49 | CRITICAL | Button text as body paragraphs | Render buttons as `<a>` per G-REF-3 |
| 50 | CRITICAL | No text color → dark on colored bg | Thread `TextBlock.text_color` to overrides |
| 51 | HIGH | Column fills = raw text dump | Structured HTML per G-REF-5 |
| 52 | HIGH | Article-card for ANY images+texts | Structural checks: ≤2 images, no columns |
| 53 | HIGH | Only first body paragraph | Join all as `<p>` elements |
| 54 | HIGH | Placeholder text leaks | Post-render strip + empty SlotFill |
| 55-59 | MED-LOW | Multi-wrapper, padding, spatial, URLs, footer | Individual fixes |

**Security:** `html.escape()` on all text in `_build_column_fill_html()`. Button URLs validated (http/https only).
**Verify:** "SHOP THE COLLECTION" renders as `<a style="...background-color:...">`. Text on `#FE5117` renders as `color:#FFFFFF`. Product columns have `<img>` + `<h3>` + `<p>` per G-REF-5. 4 images → NOT article-card. All paragraphs in output. Zero placeholder text. All 12+ Mammut sections appear. E2E: section count ≥11, button count ≥4, heading count ≥5. Existing tests pass + 22 new tests.

---

### ~~38.7 Column HTML Structure — `<div class="column">` Pattern `[Backend]`~~ DONE

**What:** Replace the converter's column wrapper from `<table><tr><td style="display:inline-block">` to `<div class="column" style="display:inline-block">`, matching G-REF-1. Structural change to `converter.py:_render_multi_column_row()`.
**Why:** All 16 golden components use `<div class="column">` for multi-column. The CSS `.column { display: block !important; }` forces mobile stacking. The current `<table><tr><td>` wrapper does NOT respond to this mobile CSS — columns stay side-by-side on phones. Additionally, the extra table nesting adds 2+ unnecessary levels (7+ deep vs 5).
**Implementation:**
- Modify `converter.py:_render_multi_column_row()`:
  ```python
  def _render_multi_column_row(self, children, container_width, gap):
      col_widths = self._calculate_column_widths(children, container_width, gap)
      parts = []
      # MSO ghost table
      parts.append('<!--[if mso]>\n<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>')
      for i, (child, width) in enumerate(zip(children, col_widths)):
          mso_w = round(width)
          if i == 0:
              parts.append(f'<td width="{mso_w}" valign="top">\n<![endif]-->')
          else:
              parts.append(f'<!--[if mso]>\n</td><td width="{mso_w}" valign="top">\n<![endif]-->')
          # Golden pattern: <div class="column">
          parts.append(f'<div class="column" style="display:inline-block;max-width:{mso_w}px;width:100%;vertical-align:top;">')
          parts.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">')
          col_html = self._render_node(child, depth + 1, mso_w)
          padding = self._col_padding(i, len(children))
          parts.append(f'<tr><td style="padding:{padding};">{col_html}</td></tr>')
          parts.append('</table></div>')
      parts.append('<!--[if mso]>\n</td></tr></table>\n<![endif]-->')
      return '\n'.join(parts)
  ```
- Add asymmetric gutter padding per G11:
  ```python
  def _col_padding(self, i: int, count: int, gutter: float = 8.0) -> str:
      if count <= 1: return "0"
      if i == 0: return f"0 {gutter}px 0 0"
      if i == count - 1: return f"0 0 0 {gutter}px"
      return f"0 {gutter/2}px 0 {gutter/2}px"
  ```
- Column container `<td>` must have `font-size: 0; text-align: center;` (G12)

**Security:** `<div class="column">` is already used in all golden components and the email shell. No new patterns.
**Verify:** 2-column section → `<div class="column" style="display:inline-block;...">` (NOT `<table><tr><td>`). Mobile CSS → columns stack. MSO ghost table wraps columns. Asymmetric gutter padding. `font-size: 0` on container. Nesting depth ≤5. Matches `column-layout-2.html`. Existing tests pass + 8 new tests.

---

### 38.8 Image Alt Text, Font Family Preservation & Background Images `[Backend]`

**What:** Fix 3 cross-cutting data fidelity issues: (1) images get meaningless `alt="mj-image"` from Figma layer names, (2) per-text font families are replaced with hardcoded stack, (3) background images (hero sections with overlaid text) are not rendered.
**Why:** The Mammut output shows `alt="mj-image"` on every image — terrible for accessibility and visible as broken text. The golden components use meaningful alt: `alt="Full width image"` (G-REF-2), `alt="Article image"`, `alt="Grid image 1"`. Figma specifies Helvetica for headings but the converter hardcodes `Arial`. Background images (hero sections) are extracted as `image_ref` but never rendered as CSS `background-image` or VML `v:fill`.
**Implementation:**
- **Alt text quality** — add `_meaningful_alt()` to `converter.py`:
  ```python
  def _meaningful_alt(node: DesignNode, section: EmailSection | None = None) -> str:
      name = node.name or ""
      cleaned = re.sub(r'^(mj-|figma-|frame-|group-|image-)', '', name, flags=re.IGNORECASE).strip()
      if cleaned and cleaned.lower() not in ("image", "frame", "group", "rectangle", "vector"):
          return cleaned
      if section and section.texts:
          heading = next((t for t in section.texts if t.is_heading), None)
          if heading: return heading.content[:80]
      if section: return f"{section.section_type.value.replace('_', ' ').title()} image"
      return "Email image"  # never "mj-image"
  ```
- **Font family preservation** — update `converter.py:_font_stack()`:
  ```python
  def _font_stack(family: str | None) -> str:
      if not family: return "Arial, Helvetica, sans-serif"
      known = _FALLBACK_MAP.get(family.lower())
      if known: return known
      return f"'{family}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif"
  ```
  - Use actual `node.font_family` from Figma in TEXT rendering, not hardcoded default
- **Background images** — in `converter.py:_render_frame()` for FRAME with `image_ref` + text children:
  ```python
  if node.image_ref and node.children:
      bg_url = self._resolve_asset_url(node.image_ref)
      # CSS background for modern clients
      bg_style = f'background-image:url({bg_url});background-size:cover;background-position:center;'
      # VML background for Outlook
      vml_open = (f'<!--[if gte mso 9]>\n<v:rect fill="true" stroke="false"'
                  f' style="width:{width}px;height:{height}px;">\n'
                  f'<v:fill type="frame" src="{bg_url}" />\n'
                  f'<v:textbox inset="0,0,0,0"><![endif]-->')
      vml_close = '<!--[if gte mso 9]></v:textbox></v:rect><![endif]-->'
  ```

**Security:** Alt text via `html.escape()`. Background URLs validated (http/https only). Font names sanitized.
**Verify:** Mammut hero → `alt="Full width image"` (NOT `"mj-image"`). Product image → alt from adjacent heading. `fontFamily: "Helvetica"` → `font-family: 'Helvetica', -apple-system, ...`. FRAME with `image_ref` + children → CSS `background-image` + VML. FRAME with `image_ref` only → `<img>` tag. Zero `alt="mj-image"` in any output. Existing tests pass + 12 new tests.

---

### Phase 38 — Summary

| Subtask | Scope | Count | Dependencies |
|---------|-------|-------|--------------|
| 38.1 Parser + text color | `figma/service.py` | 5 bugs + text color | None |
| 38.2 Tree normalizer | `figma/tree_normalizer.py` | 5 bugs | 38.1 |
| 38.3 Layout analyzer + button exclusion | `figma/layout_analyzer.py` | 9 bugs + button exclusion | 38.2 |
| 38.4 Converter + golden patterns | `converter.py`, `mjml_*.py`, `section_cache.py` | 16 bugs + G-REF enforcement | 38.3 |
| 38.5 Import + regression tests | `import_service.py`, `html_import/` | 13 bugs + golden round-trip | Independent |
| 38.6 Component matcher | `component_matcher.py`, `component_renderer.py` | 11 bugs + semantic HTML | 38.3 |
| ~~38.7 Column structure~~ | `converter.py` | 1 structural fix | 38.4 | DONE |
| 38.8 Alt text, fonts, bg images | `converter.py`, `component_matcher.py` | 3 cross-cutting | 38.1 + 38.4 |
| **Total** | | **63 fixes + ~130 new tests** | |

> **Execution:** 38.1 → 38.2 → 38.3 → 38.4 → 38.7 (sequential). 38.5 parallel from start. 38.6 after 38.3. 38.8 after 38.1 + 38.4.
>
> **Validation:** All output validated against `email-templates/components/*.html` golden patterns. Regression tests cover: hero-heavy (Mammut), product grid (e-commerce), newsletter, transactional, navigation-heavy.

---

## Phase 39 — Pipeline Hardening, Figma Enrichment & Quality Infrastructure

> **Phase 38 fixes the bugs. Phase 39 prevents them from recurring and enriches the pipeline.** The audit revealed systemic gaps: ~12 ignored Figma API fields (hyperlinks, corner radius, rich text, alignment), anemic data models (no text_color, no URL), zero property-based tests, zero real Figma fixtures, zero visual regression tests, and two divergent MJML generation paths. These are architectural debts that continuously spawn bugs.
>
> **Phasing:** 7 subtasks. 39.1 enriches Figma parser + data models. 39.2 adds testing infrastructure. 39.3 eliminates dual MJML path. 39.4 adds quality contracts. 39.5 adds lint rules. 39.6 improves component matcher. 39.7 adds golden template conformance gate. Most independent — parallel execution possible.

- [x] 39.1 Figma API enrichment & data model gaps ~~DONE~~
- [x] 39.2 Testing infrastructure (fixtures, property-based, contracts, visual regression) ~~DONE~~
- [x] 39.3 Eliminate dual MJML generation path ~~DONE~~
- [x] 39.4 Automated quality contracts (contrast, completeness, placeholders) ~~DONE~~
- [x] 39.5 Custom lint rules for pipeline anti-patterns ~~DONE~~
- [x] 39.6 Component matcher architectural improvements ~~DONE~~
- [x] 39.7 Golden template conformance gate ~~DONE~~

---

### ~~39.1 Figma API Enrichment & Data Model Gaps `[Backend]`~~ DONE

**What:** Extract ~12 conversion-relevant Figma API fields currently ignored. Enrich `DesignNode`, `TextBlock`, `ButtonElement` with hyperlinks, corner radius, rich text style runs, alignment, and borders. Unlocks functional CTA buttons, rounded corners, mixed-format text, and correct alignment.
**Why:** `style.hyperlink` (buttons link nowhere — all `href="#"`), `characterStyleOverrides` (bold/italic words lost), `cornerRadius` (buttons render sharp — should be `border-radius: 4px` per G-REF-3), `primaryAxisAlignItems` (alignment guessed). The golden `cta-button.html` shows `border-radius: 4px` + VML `arcsize="10%"` — impossible without `cornerRadius` extraction. `product-card.html` has `border: 1px solid #e0e0e0` — impossible without `strokes`/`strokeWeight`.
**Implementation:**
- **Hyperlink** in `_parse_node()` TEXT branch: `style.hyperlink.url` → `DesignNode.hyperlink` → `TextBlock.hyperlink` → `ButtonElement.url` → `SlotFill("cta_url", btn.url)`
- **Rich text** via `characterStyleOverrides` + `styleOverrideTable` → `TextStyleRun(start, end, bold, italic, color, link)` → `TextBlock.style_runs` → converter splits into `<strong>`, `<em>`, `<span style="color:">`, `<a href="">`
- **Corner radius**: `cornerRadius` / `rectangleCornerRadii` → `DesignNode.corner_radius` → `ButtonElement.border_radius` → CSS `border-radius` + VML `arcsize`
- **Alignment**: `primaryAxisAlignItems` / `counterAxisAlignItems` → `DesignNode` fields → `text-align` in converter
- **Strokes**: `strokes` + `strokeWeight` → `DesignNode.stroke_weight/stroke_color` → `border: Npx solid color` (enables `product-card.html:5` pattern)

| Model | New Field | Source |
|-------|-----------|--------|
| `DesignNode` | `hyperlink`, `corner_radius`, `primary_axis_align`, `counter_axis_align`, `layout_align`, `clips_content`, `stroke_weight`, `stroke_color` | Figma API |
| `TextBlock` | `hyperlink`, `style_runs` | `DesignNode` threading |
| `ButtonElement` | `url`, `border_radius`, `fill_color` | `DesignNode` + child TEXT |

**Security:** Hyperlink URLs validated: http/https only, no `javascript:`. Rich text content escaped via `html.escape()`.
**Verify:** Figma TEXT with `style.hyperlink.url` → CTA links to URL (not `"#"`). Bold style run → `<strong>`. `cornerRadius: 8` → `border-radius: 8px` + VML `arcsize="16%"`. `primaryAxisAlignItems: "CENTER"` → `text-align: center`. `strokeWeight: 1` → `border: 1px solid`. `javascript:` URL → rejected. 25 new tests.

---

### ~~39.2 Testing Infrastructure `[Backend]`~~ DONE

**What:** Add 5 testing layers: real Figma API fixtures, Hypothesis property-based tests, pipeline contract tests, email HTML validity assertion, and visual regression testing.
**Why:** Phase 38 found 63 bugs. Most were trivially detectable — `0.0 or 1.0`, missing fields, wrong thresholds. They accumulated because: (1) parser tests use synthetic objects, not real API responses, (2) no property-based testing catches `opacity=0.0`, (3) no contracts between stages catch field-dropping, (4) no validator catches missing `role="presentation"` or `alt="mj-image"`, (5) no visual regression catches "email looks different."
**Implementation:**
- **39.2.1 Real Figma fixtures** — 3-5 sanitized API responses in `figma/tests/fixtures/`: mammut hero, ecommerce grid, newsletter, transactional, navigation. Test `_parse_node()` against real JSON.
- **39.2.2 Hypothesis tests** — `@given(opacity=st.floats(0.0, 1.0))` → assert opacity preserved. Random `DesignNode` trees → converter never crashes, balanced HTML, no `<div>` layout.
- **39.2.3 Contract tests** — validate normalize output → valid analyze input, analyze output → valid converter input, button IDs not in text IDs.
- **39.2.4 Email HTML validity** — `assert_valid_email_html(html)` checks:
  - Every `<table>` has `role="presentation"` (G1)
  - Every `<img>` has `display: block` + meaningful `alt` (G-REF-2)
  - No `<div>` with layout CSS (width/flex/float)
  - Columns use `<div class="column">` (G-REF-1)
  - Headings in `<h1>`-`<h3>`, body in `<p>` (G-REF-4)
- **39.2.5 Visual regression** — Playwright render at 600px → SSIM compare against baselines → fail if < 0.92. Wire into `make rendering-regression`.

**Security:** Fixtures sanitized — no API tokens, personal data, proprietary content.
**Verify:** 3+ real Figma fixtures tested. Hypothesis runs 100+ examples. Contract tests catch broken normalize output. `assert_valid_email_html` catches `alt="mj-image"`, missing `role="presentation"`. Visual baseline for 2+ archetypes. 45+ new tests.

---

### ~~39.3 Eliminate Dual MJML Generation Path~~ `[Backend]` DONE

**What:** Unified `mjml_generator.py` (programmatic) and `mjml_template_engine.py` (Jinja2) into single template-based path. Deleted programmatic generator.
**Delivered:** `mjml_generator.py` deleted (454 LOC). `inject_section_markers()` relocated to `mjml_template_engine.py`. `converter_service.py` fallback path + `use_templates` param removed. Template engine covers all 11 section types. 74 tests pass. ~1000 LOC net reduction.
**Security:** Template engine uses Jinja2 autoescaping. `inject_section_markers` uses `html.escape()`.
**Verified:** Single MJML path. All 11 section types have templates. Per-text fonts/colors in template output. MJML compilation succeeds. `make test` passes. Pyright baseline unchanged (43 errors).

---

### ~~39.4 Automated Quality Contracts `[Backend]`~~ DONE

**What:** Add 3 post-conversion quality checks: WCAG contrast validation, section completeness, placeholder detection. Warnings in `ConversionResult` for UI display.
**Delivered:**
- `app/design_sync/quality_contracts.py` — `QualityWarning` dataclass + 3 pure sync check functions + `run_quality_contracts()` orchestrator
- **Contrast:** `check_contrast()` parses inline `color:`/`background-color:` from HTML via lxml, walks ancestors for bg, computes WCAG 2.1 ratio via `_relative_luminance()`/`_contrast_ratio()` (reused from `converter.py`), warns if <4.5:1 normal text or <3.0:1 large text (18px+ or bold 14px+)
- **Completeness:** `check_completeness()` counts `<!-- section:... -->` markers vs input count, counts `<a style="display:inline-block;padding:...">` + `v:roundrect` patterns vs input button count
- **Placeholders:** `check_placeholders()` reuses `_PLACEHOLDER_PATTERNS` from `component_matcher.py`, deduplicates matches
- `ConversionResult.quality_warnings` field added (frozen dataclass, `list[QualityWarning]`, default empty)
- Wired into all 3 conversion paths: `_convert_mjml_from_layout`, `_convert_with_components`, `_convert_recursive`
- 19 tests: 6 contrast, 6 completeness, 4 placeholder, 3 integration

---

### ~~39.5 Custom Lint Rules for Pipeline Anti-Patterns~~ `[Backend]` DONE

**What:** Semgrep rule + pre-commit hook + Makefile target flagging `$X or <numeric>` in `app/design_sync/`. Prevents Phase 38's most common bug class from recurring.
**Delivered:**
- Semgrep rule `.semgrep/rules/falsy-numeric-trap.yaml` — AST-aware `$X or $NUMERIC` detection, scoped to `app/design_sync/`, severity ERROR
- Semgrep test suite `.semgrep/tests/` — 7 true positives + 5 true negatives, all passing
- Pre-commit regex fallback hook (grep-based, excludes comments and test files)
- `make lint-numeric` target wired into `make check` and `make check-full`
- CI: `./.semgrep/rules` added to `.github/workflows/semgrep.yml` `SEMGREP_RULES`
- `.semgrep/` excluded from ruff in `pyproject.toml`
- **45 existing violations fixed** across 13 files — all `x or N` → `x if x is not None else N`
- Special case: `len(names) or 1` → `max(len(names), 1)` (divide-by-zero protection)

---

### ~~39.6 Component Matcher Architectural Improvements `[Backend]`~~ DONE

**What:** Replace first-match template selection with multi-candidate scoring, add spatial column assignment, post-render slot validation, 3 new component types (`product-grid`, `category-nav`, `image-gallery`), and match confidence scores.
**Delivered:** `_score_candidates()` replaces `_match_content()` with multi-candidate scoring — product-grid (0.95), article-card (0.9), image-gallery (0.88), image-grid (0.85), category-nav (0.7). 3 new component seeds (`product-grid`, `category-nav`, `image-gallery`) with table-based HTML, MSO conditionals, data-slot markers. 3 new `_fills_*` functions registered in dispatch. `_validate_slot_fill_rate()` in `component_renderer.py` warns when <50% of template slots filled. `match_confidences: dict[int, float]` on `ConversionResult`, propagated from `match_all()`. Column assignment uses `column_groups.column_idx` (spatial structure from Phase 35). 22 tests (18 new + 2 updated + 2 fixes), 1522 design_sync tests pass.

---

### ~~39.7 Golden Template Conformance Gate `[Backend]`~~ DONE

**What:** Permanent CI quality gate validating all converter output against `email-templates/components/` patterns. `make golden-conformance` target wired into `make check`.
**Delivered:** `app/design_sync/tests/test_golden_conformance.py` — 12 conformance checks (G1 role=presentation, G2 display:block on images, G3 meaningful alt text, G5 no div layout CSS, G6 MSO conditionals, G7 cellpadding/cellspacing, G10 email-safe meta tags, G11 MSO table reset, plus column class, VML fallback). 26 tests pass, 9 skipped (components without images). `make golden-conformance` wired into `make check` and `make check-full`. Runs in <1s.

---

### Phase 39 — Summary

| Subtask | Scope | Dependencies |
|---------|-------|--------------|
| 39.1 Figma API enrichment | `figma/service.py`, `protocol.py` | 38.1 (clean parser) |
| 39.2 Testing infrastructure | New test files, `hypothesis` | Phase 38 complete |
| 39.3 Eliminate dual MJML path | `mjml_generator.py`, `mjml_template_engine.py` | 38.4 (templates fixed) |
| 39.4 Quality contracts | `converter_service.py` | 38.6 (correct output) |
| 39.5 Custom lint rules | `.semgrep/` | Independent |
| 39.6 Component matcher arch | `component_matcher.py` | 38.6 (bugs fixed) |
| 39.7 Golden conformance gate | `tests/test_golden_conformance.py`, `Makefile` | Phase 38 complete |

> **Execution:** 39.5 independent — start immediately. 39.1 after 38.1. 39.2 after Phase 38 complete. 39.3, 39.4, 39.6 depend on respective 38 subtasks. 39.7 last — codifies the final quality bar.
