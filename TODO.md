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

- [ ] 37.1 Expand golden component library with advanced patterns *(needs update after 37.4/37.5 — golden refs must reflect real component output)*
- [x] 37.2 Build golden reference loader & criterion mapping
- [x] 37.3 Wire golden references into judge prompts
- [x] 37.4 Re-run eval pipeline against file-based component output
- [x] 37.5 Complete human labeling with improved judges

---

### 37.1 Expand Golden Component Library `[Templates]` *(partial — 14 templates exist, need update after 37.4/37.5)*

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

### ~~37.4 Re-run Eval Pipeline Against File-Based Component Output~~ `[Evals]` DONE

**What:** Re-generate agent traces and re-run judges now that the converter produces HTML from file-based components (40.7) instead of inline seeds. The previous 37.4 run (verdict comparison script, flip rate analysis — delivered and tooling retained) was against inline-seed output. Those verdicts are stale because the converter now emits structurally different HTML: `data-slot` attributes, MSO conditional wrappers, semantic dark-mode classes, and VML button patterns that differ from the old hardcoded strings. Judges calibrated against inline-seed output may pass/fail differently on file-based output. Re-running establishes the true baseline for 37.5 human labeling.
**Why:** The 9 AI agents (scaffolder, dark mode, content, outlook fixer, accessibility, personalisation, code reviewer, knowledge, innovation) all receive converter output as input context. With 40.7, that output changed: (1) hero-block now has VML `v:rect` background pattern instead of simple `background-image`, (2) cta-button has `v:roundrect` Outlook fallback, (3) text-block has explicit `data-slot="heading"` and `data-slot="body"` markers, (4) new components like `editorial-2` and `nav-hamburger` appear in matcher output. Judges comparing agent output against golden references must see the file-based HTML to produce accurate verdicts. The existing `traces/pre_golden/` backup (from the first 37.4 run) serves as the pre-file-based baseline for comparison.
**Implementation:**
- **37.4.1 Back up current verdicts as pre-file-based baseline:**
  - Copy current `traces/*_verdicts.jsonl` → `traces/pre_file_based/` (9 agent verdict files)
  - These are the inline-seed-era verdicts for comparison after re-run
  - Keep `traces/pre_golden/` intact (original pre-golden-reference baseline)
- **37.4.2 Re-generate agent traces with file-based components:**
  - Run `make eval-run` — this invokes `runner.py --agent all --output traces/ --skip-existing`
  - The `--skip-existing` flag means only new/changed test cases generate new traces
  - To force full regeneration (recommended): `uv run python -m app.ai.agents.evals.runner --agent all --output traces/` (no `--skip-existing`)
  - Traces now contain file-based component HTML as agent input context
  - Verify: spot-check `traces/scaffolder_traces.jsonl` — input HTML should contain `data-slot` attributes and `<!-- Component: -->` markers, NOT the old inline seed patterns
- **37.4.3 Re-run judges against new traces:**
  - Run `make eval-rejudge` — overwrites all 9 verdict files with fresh judgments using golden-reference-enhanced prompts (hybrid mode, Claude Sonnet)
  - This uses the same golden references from 37.1–37.3 (unchanged) but evaluates agents against file-based component output
  - ~9 agents × ~60 traces × 5 criteria = ~2,700 LLM judge calls
- **37.4.4 Compare verdicts: inline-seed vs file-based:**
  - Run `make eval-compare` with updated pre-dir:
    ```bash
    uv run python scripts/eval-compare-verdicts.py \
      --pre-dir traces/pre_file_based \
      --post-dir traces \
      --output traces/verdict_comparison_file_based.json
    ```
  - Analyse flip rates per criterion — criteria where verdicts changed indicate judge sensitivity to HTML structure
  - Expected: scaffolder verdicts may improve (better template HTML to evaluate), code reviewer verdicts may shift (file-based HTML has different patterns to flag)
  - Flag criteria with >20% flip rate for priority review in 37.5
- **37.4.5 Run analysis and regression check:**
  - Run `make eval-analysis` — regenerate `traces/analysis.json` from new verdicts
  - Run `make eval-regression` — check per-agent pass rates against `AGENT_REGRESSION_TOLERANCE` (3pp)
  - If regression detected: investigate whether the flip is a true quality change (agent output genuinely worse on file-based HTML) or a judge calibration artifact (judge is more/less discriminating)
  - Document findings in `traces/verdict_comparison_file_based.json`
**Security:** No new external inputs. LLM judge calls use existing configured provider. Verdict files are local JSONL — no PII.
**Verify:** All 9 agents re-judged — `traces/*_verdicts.jsonl` timestamps updated. `traces/verdict_comparison_file_based.json` generated with per-criterion flip rates. `make eval-check` passes (analysis + regression). Spot-check: open `traces/scaffolder_verdicts.jsonl` — verdicts reference file-based component HTML (contains `data-slot` attributes). Comparison report identifies which criteria are sensitive to HTML source (inline vs file-based).

---

### ~~37.5 Complete Human Labeling with Improved Judges~~ `[Manual + Evals]` DONE

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
| ~~37.4 Re-run against file-based output~~ DONE | `traces/`, `eval-compare-verdicts.py`, Makefile | 37.3 + 40.7 (file-based components) | ~2,700 LLM judge calls, comparison report |
| ~~37.5 Human labeling~~ DONE | `docs/eval-labeling-tool.html`, `traces/*.jsonl` | 37.4 (re-calibrated verdicts) | ~2-4 hours manual |

> **Execution:** 37.1–37.3 done. 37.4 done (re-run against file-based component output from 40.7, verdict comparison complete). 37.5 done (540 rows labeled, calibration validated). **Phase 37 complete.**

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

---

## Phase 40 — Converter Snapshot & Visual Regression Testing

> **Problem:** Converter fixes keep regressing because tests use hand-crafted `DesignNode` objects, not real designs. A fix that passes synthetic tests breaks on real Figma data. This has happened 5+ times. The 1,449 existing converter tests check structure (`assert "<table" in html`) but never verify actual visual fidelity against the source design — spacing, colors, proportions, content hierarchy, and component matching are all invisible to the current test suite.
>
> **Solution:** Two-layer regression testing: (1) HTML text snapshots using real Figma inputs verify structural correctness, (2) visual pixel-diff against original Figma design screenshots catches layout/styling gaps. Every converter fix must pass both layers.

- [x] 40.1 Snapshot test infrastructure (done)
- [ ] 40.2 Collect and verify real design cases
- [ ] 40.3 Visual regression: Figma design screenshot capture
- [ ] 40.4 Visual regression: Playwright HTML rendering + pixel diff
- [ ] 40.5 Wire into CI gate
- [ ] 40.6 Flatten transparent PNG backgrounds to white on export
- [x] 40.7 Unified component resolution — map converter to existing file-based components, create only missing ones (~5 files), delete inline seeds

---

### ~~40.1 Snapshot Test Infrastructure `[Backend]`~~ DONE

**What:** Build a test harness that loads real Figma design inputs (`structure.json` + `tokens.json`) from `data/debug/{case}/`, runs the full `DesignConverterService.convert()` pipeline, and diffs the output against a hand-verified `expected.html`. Add a capture script to generate initial output for visual review, a YAML manifest to track case status, and Makefile targets.
**Why:** The existing 1,449 converter tests construct toy `DesignNode` trees with 3–5 nodes. Real Figma designs have 100+ nodes, 250+ color tokens, 234 typography styles, nested auto-layout frames, spacer columns, and section naming conventions that synthetic tests never exercise. A fix that works on a 3-node tree regularly breaks on real data because it hits different code paths in layout analysis, component matching, section classification, or slot filling.
**Implementation:**
- Create `app/design_sync/tests/test_snapshot_regression.py`:
  - `TestSnapshotRegression.test_snapshot_matches[case_id]` — parametrized over active cases in manifest. Loads `structure.json` via `load_structure_from_json()`, `tokens.json` via `load_tokens_from_json()`, runs `DesignConverterService().convert(structure, tokens)`, normalizes whitespace in both expected and actual HTML, diffs with `difflib.unified_diff()`. On mismatch: saves `actual.html` alongside for browser comparison, fails with first 100 lines of diff.
  - `TestSnapshotSanity.test_case_loads[case_id]` — parametrized over ALL cases (including pending). Verifies `structure.json` and `tokens.json` exist and deserialize without error. Catches broken fixtures.
  - `TestSnapshotSectionCount.test_section_count[case_id]` — parametrized over active cases. Verifies `result.sections_count` matches the `sections` field in manifest. Catches layout analysis regressions independently of HTML content.
  - `_normalize_html(html)` — collapses whitespace, normalizes self-closing tags, splits on `>` for readable diffs. Allows whitespace-only reformatting while catching real content/structure changes.
- Create `scripts/snapshot-capture.py`:
  - CLI: `python scripts/snapshot-capture.py <case_id> [--overwrite] [--output path]`
  - Loads inputs, runs converter, prints summary (node count, color count, section count, warnings), saves output to `expected.html`
  - Prints next-step instructions (open in browser, verify, activate in manifest)
- Create `data/debug/manifest.yaml`:
  - YAML registry of cases with `id`, `name`, `source`, `sections` (expected count), `status` (pending/active)
  - Only `active` cases run in `TestSnapshotRegression` and `TestSnapshotSectionCount`
  - `pending` cases still run in `TestSnapshotSanity` (validates fixtures are loadable)
- Fix `_node_from_dict()` in `app/design_sync/diagnose/report.py`:
  - Was missing 11 fields: `image_ref`, `hyperlink`, `corner_radius`, `corner_radii`, `text_align`, `primary_axis_align`, `counter_axis_align`, `stroke_weight`, `stroke_color`, `style_runs`, `visible`, `opacity`
  - Without these, replaying from saved `structure.json` silently drops data that affects conversion output (e.g., missing `image_ref` → no images, missing `visible` → invisible nodes rendered)
  - `style_runs` deserialized from list of dicts to `tuple[StyleRun, ...]`, `corner_radii` from list to tuple
- Add Makefile targets: `make snapshot-test` (runs pytest on test file), `make snapshot-capture CASE=N` (runs capture script with `--overwrite`)
- Add `data/debug/*/actual.html` to `.gitignore` (generated on test failure, not committed)
- Update `CLAUDE.md` Essential Commands section with new targets
**Verify:** `make snapshot-test` runs — sanity test passes for case 5 (MAAP x KASK, 123 nodes, 9 sections), snapshot and section count tests skip (case pending). `scripts/snapshot-capture.py 5 --overwrite` produces 20KB HTML with 9 sections. `_node_from_dict()` round-trips all 30+ fields from real `structure.json`.

**Delivered:**
- `app/design_sync/tests/test_snapshot_regression.py` — 3 test classes, parametrized over manifest
- `scripts/snapshot-capture.py` — CLI capture tool
- `data/debug/manifest.yaml` — case registry
- `data/debug/5/expected.html` — hand-corrected expected output for MAAP x KASK (9 sections, 123 nodes)
- `app/design_sync/diagnose/report.py` — `_node_from_dict()` fix (11 missing fields)
- `Makefile` — `snapshot-test`, `snapshot-capture` targets
- `.gitignore` — `data/debug/*/actual.html`

---

### 40.2 Collect and Verify Real Design Cases `[Backend]`

**What:** Collect 3–5 diverse real Figma email designs as snapshot test cases. Each case needs: diagnostic extract (`structure.json` + `tokens.json`), exported images (`data/design-assets/{id}/`), and a hand-corrected `expected.html` verified against the Figma design. Activate all cases in manifest.
**Why:** A single test case (MAAP x KASK) only covers one design pattern (hero + text + 2-col + nav + buttons + footer). Real-world emails vary widely: Starbucks-style (hero image + promotional sections + deep footer), transactional (receipt table + order summary), newsletter (multi-article grid), minimal (single CTA). Each exercises different converter code paths — section classification (`_SECTION_PATTERNS`), component matching (`match_all()`), column layout detection, button extraction, and slot filling. A fix that works for MAAP x KASK (fashion/cycling) may break on a data-heavy transactional template.
**Implementation:**
- Extract 3–5 designs via `python -m app.design_sync.diagnose.extract --connection-id <N> --node-id <node>`:
  - Case 5: MAAP x KASK (done — 9 sections: hero, text, 2-col, divider, nav, buttons, 3-col, footer)
  - Case 6: Starbucks promotional (from connection 8, node 2833-1623 — 5 sections: hero, text+CTA, 2-col, 4-col nav, social+footer)
  - Case 7: Newsletter/multi-article (3+ article cards in grid layout)
  - Case 8: Transactional/receipt (table-heavy, minimal styling)
  - Case 9: Minimal single-CTA (header + hero + CTA + footer)
- For each case:
  1. Run extract → `data/debug/{id}/structure.json`, `tokens.json`, `report.json`
  2. Run `make snapshot-capture CASE={id}` → generates initial `expected.html`
  3. Open in browser with light mode, compare against Figma design
  4. Hand-correct `expected.html`: fix text hierarchy, button styles (pill/outlined/filled + VML), column gaps, section backgrounds, alt text, footer structure
  5. Update image paths to relative `../../design-assets/{id}/` for local browser preview
  6. Add to `data/debug/manifest.yaml` with `status: active`
- Verify each case passes `make snapshot-test` after activation
**Security:** No production data. Test cases use publicly available Figma community files or sanitized internal designs. No API keys or PII in committed fixtures.
**Verify:** `make snapshot-test` runs 5 active cases — all pass (HTML text match + section count match). Each `expected.html` visually matches the Figma design when opened in a browser (hero images load from `data/design-assets/`, correct backgrounds, text hierarchy, button styles, column proportions).

---

### 40.3 Visual Regression: Figma Design Screenshot Capture `[Backend]`

**What:** Extend the diagnostic extract script to automatically capture a full-frame PNG screenshot of the Figma design node via the Figma Images API. Save as `data/debug/{id}/design.png` alongside `structure.json` and `tokens.json`. This is the "source of truth" image that HTML output will be compared against.
**Why:** The manual workflow of screenshotting Figma, pasting into chat, and eyeballing differences doesn't scale and misses subtle issues (2px spacing gaps, slightly wrong colors, font-size mismatches). An automated pixel-level comparison needs both images in a standardized format at the same dimensions. The Figma Images API renders the exact frame at configurable scale, producing a pixel-perfect reference without browser rendering artifacts.
**Implementation:**
- Extend `app/design_sync/diagnose/extract.py`:
  - Add `--capture-image` flag (default True when extracting)
  - After `_fetch_figma_data()`, call Figma Images API:
    ```
    GET /v1/images/{file_key}?ids={node_id}&format=png&scale=2
    ```
    (scale=2 for retina-quality reference; 600px design → 1200px PNG)
  - Parse response: `response.json()["images"][node_id]` → temporary S3 URL
  - Download PNG via `httpx.get(image_url)` → save to `{output_dir}/design.png`
  - Handle errors gracefully: 403 (insufficient permissions), 404 (node not found), timeout → warn and continue without image
  - Log image dimensions and file size for diagnostic report
- Update `app/design_sync/diagnose/models.py`:
  - Add `design_image_path: str | None = None` to `DiagnosticReport`
  - Add `design_image_width: int | None` and `design_image_height: int | None`
- Update `data/debug/manifest.yaml` schema:
  - Add optional `design_image: bool` field per case (true if `design.png` exists)
- Add `--no-image` flag to extract script for offline/CI runs without Figma API access
**Security:** Figma Images API uses the same encrypted PAT from `DesignConnection.access_token`. The returned S3 URL is temporary (expires ~30 minutes). Downloaded PNGs contain rendered design content only — no metadata, no PII. Images committed to repo are from public Figma Community files.
**Verify:** `python -m app.design_sync.diagnose.extract --connection-id 5 --node-id 2833-1623` produces `data/debug/5/design.png` alongside existing `structure.json`. Image dimensions match expected (1200×5036 at scale=2 for 600×2518 design). `--no-image` flag skips image capture without error. Expired/invalid token → graceful fallback with warning log.

---

### 40.4 Visual Regression: Playwright HTML Rendering + Pixel Diff `[Backend]`

**What:** Add a Playwright-based visual regression test that renders `expected.html` to a screenshot, then pixel-diffs it against `design.png` from the Figma export. Produces a diff image highlighting mismatches. Reuses the existing `app/rendering/tests/visual_regression/` infrastructure for image comparison.
**Why:** HTML text snapshots (40.1) catch structural regressions — missing sections, wrong text content, broken MSO conditionals. But they cannot catch the visual bugs that dominate real-world conversion issues: wrong column gap widths (8px vs 24px), incorrect section background colors, mismatched font sizes, buttons with wrong border-radius, text alignment off-by-one. These are exactly the issues found during manual review of case 5 (MAAP x KASK). A pixel-level comparison against the original design catches all of these automatically.
**Implementation:**
- Create `app/design_sync/tests/test_snapshot_visual.py`:
  - `@pytest.mark.visual_regression` marker (skip in normal `make test`, run via `make snapshot-visual`)
  - `TestSnapshotVisualRegression.test_visual_match[case_id]` — parametrized over active cases that have `design.png`:
    1. Load `expected.html` from case directory
    2. Rewrite image paths from relative (`../../design-assets/`) to absolute filesystem paths (Playwright needs absolute URLs or a local file server)
    3. Launch Playwright Chromium, set viewport to design width (600px × auto-height)
    4. Navigate to `file://{expected.html}` (or serve via `http://localhost` with a mini static server for image loading)
    5. Take full-page screenshot → `rendered.png`
    6. Load `design.png`, resize `rendered.png` to match dimensions if needed (Figma exports at scale=2)
    7. Run pixel diff using `pixelmatch` (via Pillow + numpy, or the existing `compare_images()` from `app/rendering/tests/visual_regression/conftest.py`):
       - Compute per-pixel color distance
       - Threshold: allow ≤5% pixel mismatch (anti-aliasing, font rendering differences)
       - Generate `diff.png` with mismatched pixels highlighted in red
    8. On failure: save `rendered.png` and `diff.png` to case directory, fail with mismatch percentage and diff image path
  - Helper: `_serve_case_directory(case_dir)` — starts a local HTTP server on a random port to serve HTML + images (Playwright can't load `file://` relative paths for images in some configurations)
  - Helper: `_rewrite_image_paths(html, case_dir)` — replaces relative image paths with `http://localhost:{port}/` paths
- Reuse existing visual regression infra:
  - `app/rendering/tests/visual_regression/conftest.py` has `compare_images()` and diff generation
  - Extend or adapt for design-vs-HTML comparison (may need different threshold since comparing design tool render vs browser render)
- Add to `data/debug/manifest.yaml`: `visual_threshold: 0.05` per case (configurable mismatch tolerance)
- Diff output on mismatch:
  ```
  data/debug/{id}/rendered.png   # Playwright screenshot of expected.html
  data/debug/{id}/diff.png       # Pixel diff (red = mismatch)
  ```
- Add `.gitignore` entries: `data/debug/*/rendered.png`, `data/debug/*/diff.png`
**Security:** Playwright runs in headless mode against local files only — no network access needed. Mini HTTP server binds to localhost only, random port, stopped after test.
**Verify:** Case 5 with correct `design.png` and `expected.html` → visual test passes (≤5% mismatch). Intentionally break `expected.html` (change a background color) → test fails with diff.png showing the changed region in red. `make snapshot-visual` runs all visual cases. Cases without `design.png` → skipped gracefully.

---

### 40.5 Wire into CI Gate `[DevOps]`

**What:** Add `make snapshot-test` to the `make check` target so HTML snapshot tests run as part of the standard CI gate. Add `make snapshot-visual` as an optional target (not in `make check` — requires Playwright + Figma images which may not be available in all CI environments).
**Why:** The snapshot tests are only useful if they actually block broken merges. Adding to `make check` means every PR that touches converter code must pass all snapshot cases. Visual regression stays optional because it requires Playwright browsers installed and `design.png` files committed (which may be large).
**Implementation:**
- Update `Makefile`:
  - Add `snapshot-test` to the `check` and `check-full` dependency lists
  - Add `snapshot-visual` as standalone target (not in `check`): `uv run pytest app/design_sync/tests/test_snapshot_visual.py -v -m visual_regression --tb=long`
- Update `CLAUDE.md`:
  - Add `make snapshot-visual` to Essential Commands
  - Document the visual regression workflow in the Roadmap section
- Verify `make check` now includes snapshot tests and they pass

**Verify:** `make check` runs snapshot tests alongside existing lint/types/test/conformance gates. Broken `expected.html` → `make check` fails. `make snapshot-visual` runs independently.

---

### 40.6 Export Images Exactly As-Is — No Background Color Added `[Backend]`

**What:** When the converter pipeline exports images from Figma designs, the exported image must be an exact pixel-for-pixel copy of what Figma renders for that node — same dimensions, same crop, same background. The pipeline must NEVER add, remove, or modify any colors in the image, and must NEVER add background colors to image container elements (`<td>`, `<div>`, `<a>`) in the generated HTML.
**Why:** Figma designers set the exact image appearance — including background fills on image frames (e.g., `#F0F0F0` gray behind product photos). The converter must export the `mj-image-Frame` node (which includes the designer's background) rather than just the raw `mj-image` fill. If the pipeline strips the frame background or exports only the image fill, the result is a transparent PNG that creates visual gaps in email. Conversely, if the pipeline adds its own background color via CSS (`background-color` on image `<td>`), that's wrong too — the image itself should contain all visual information. Observed on Mammut Eiger Nordwand product grid: raw image fills had transparent backgrounds, causing text to visually overlap the invisible transparent area.
**Rules:**
1. **Export the image frame node**, not just the image fill — this captures the designer's intended background
2. **Never add `background-color`** to image `<td>` or image container elements in generated HTML — the image is self-contained
3. **Never composite, alpha-flatten, or color-modify** exported images in the pipeline — export exactly what Figma renders
4. **Never add transparent padding** — export bounds must match the Figma node's exact bounds
5. Target `mj-image-Frame` (or equivalent container with fills) in Figma API requests, not the child `mj-image` node
**Implementation:**
- Audit the Figma image export path — ensure `GET /v1/images/{file_key}?ids={node_id}` targets the image frame node (which includes background fills), not the raw image fill node
- In generated HTML, image `<td>` cells must have NO `background-color` — only `padding`, `font-family`, etc.
- Add a lint rule: flag any `background-color` on elements containing `<img>` in converter output
- Add a validation step: compare exported image dimensions against the Figma node's `absoluteBoundingBox` — flag mismatches
**Verify:** Re-export Mammut product images from `mj-image-Frame` nodes → images have gray background baked in, 260×260 (@1x) / 520×520 (@2x). No `background-color` on any image `<td>` in converter output. Product grid renders identically to Figma design.

---

### ~~40.7 Unified Component Resolution — File-Based HTML as Source of Truth `[Backend]`~~ DONE

**Training data:** `email-templates/training_HTML/for_converter_engine/CONVERTER-REFERENCE.md` — 3 real campaign HTMLs (Starbucks, Mammut, MAAP) mapping every section back to its source component file, listing every slot fill, structural change, style override, and design reasoning. Documents 16 components in use, 5 bespoke patterns needing new components, and 10 key observations (VML buttons, asymmetric columns, vertical navs, product grid gutters, semantic dark mode classes). This is the ground truth for which component maps to which visual pattern and what modifications the converter must apply.
**What:** The conversion engine currently uses 24 inline HTML templates hardcoded as Python dicts in `seeds.py`, completely ignoring the 86 file-based HTML components in `email-templates/components/`. The two systems have different slugs (matcher emits `hero-block` → inline seed; files have `hero-text`), and where slugs overlap, inline seeds win. This means editing an HTML component file has zero effect on converter output. Fix this by extracting inline seeds to file-based components and flipping merge precedence so file-based HTML is the single source of truth.
**Why:** The file-based HTML components are **brand-agnostic, reusable building blocks** — they use `data-slot` attributes for dynamic content injection (images, text, CTAs, colors) and design token overrides for brand-specific styling. They are not tied to any brand's palette, fonts, or copy. The conversion engine fills slots with Figma-extracted content and applies token overrides from the project's design system at render time. Having a parallel set of 24 hardcoded Python HTML strings means: (1) component changes require editing Python code instead of HTML files, (2) the 86 file-based components are invisible to the conversion engine, (3) there's no single source of truth — the systems drift apart silently. Unifying on file-based components means any developer or designer can edit an HTML file and the conversion engine immediately uses the updated version for all brands.
**Implementation:**
- **40.7.1 Map converter matcher to existing file-based components:**
  - **Component library:** `email-templates/components/` (86 HTML files). **Manifest:** `app/components/data/component_manifest.yaml`. These are the source of truth — the converter must pull from here, not from inline Python seeds.
  - The matcher currently emits 20 slugs that only exist as inline seeds — map each to an existing file-based component instead. No new HTML files except for the few patterns that genuinely have no file equivalent.
  - **Already exist (remap matcher slug → file slug):** `preheader` → `preheader.html`, `logo-header` → `logo-header.html`, `hero-block` → `hero-text.html`, `email-header` → `header.html`, `email-footer` → `footer.html`, `cta-button` → `cta.html` / `button-filled.html` / `button-ghost.html`, `article-card` → `article-2.html` / `article-reverse.html`, `navigation-bar` → `nav-hamburger.html`, `image-block` → `image.html` / `image-responsive.html`, `text-block` → `heading.html` + `paragraph.html`, `divider` → `divider.html`, `social-icons` → `footer-social.html`, `product-card` → `product-showcase.html`
  - **Create only missing files (~5):** `column-layout-2.html`, `column-layout-3.html`, `column-layout-4.html`, `spacer.html`, `full-width-image.html` — these have no file equivalent
  - Ensure all mapped components have `data-slot` attributes and `<!-- Component: slug -->` tags
  - `email-shell` stays inline — it's a document wrapper, not a component
- **40.7.2 Add manifest entries with slot definitions:**
  - Add/update `component_manifest.yaml` entries for all converter-used slugs
  - Each entry needs `slot_definitions` matching the `data-slot` attributes in the HTML
- **40.7.3 Auto-detect slots from HTML in file_loader:**
  - Add `_extract_slots_from_html(html_source)` to `file_loader.py`
  - Parses `data-slot="name"` attributes from HTML via regex
  - Returns slot definitions as fallback when manifest has no `slot_definitions`
  - Prevents manifest from going stale when someone edits HTML
- **40.7.4 Delete inline seeds, file-based only:**
  - Remove all 23 inline seed HTML templates from `_INLINE_SEEDS` in `seeds.py` (keep only `email-shell`)
  - `_build_all_seeds()` becomes: load file-based components + append `email-shell` inline seed
  - No more merge precedence logic — file-based components are the only source
- **40.7.5 Expand matcher for file-based component richness:**
  - Add alternate matcher rules so the converter can emit file-based slugs beyond the original 20
  - Example: detect 2-column editorial layout → emit `editorial-2` instead of always `column-layout-2`
  - Start with 3–5 high-value expansions where file-based components are better than generic fallbacks
  - Use training data in `CONVERTER-REFERENCE.md` to identify which patterns need new matcher rules (vertical navs, product grid with gutters, VML button variants, subtitle+title pairs)
- **40.7.6 Document interactive CSS extraction architecture (defer implementation):**
  - Interactive components (accordion, carousel, `anim-*`) embed CSS directly in the HTML body — no mechanism to hoist it to `<head>` `<style>` block
  - Document the approach: parse CSS from component files, collect during render, inject into shell's `<slot data-slot="head_styles">`
  - Implementation deferred — requires `COMPONENT_SHELL` → email-shell migration (separate phase)
**Security:** No new external inputs. Component HTML files are committed to the repo. `_extract_slots_from_html()` uses regex on trusted HTML files, not user input.
**Verify:** `make test` — all existing converter tests pass (no regression). `make snapshot-test` — snapshot cases produce identical output (same HTML, now sourced from files). Delete an inline seed → converter still works (pulls from file). Edit a file-based component → converter output changes (proves file-based is live). `make types` + `make lint` clean.

**Delivered:**
- `app/components/data/seeds.py` — reduced from 1597→196 lines; 23 inline seeds removed, only `email-shell` remains inline; `_build_all_seeds()` simplified to shell + file-based
- `app/components/data/file_loader.py` — added `_extract_slots_from_html()` regex-based auto-detection of `data-slot` attributes as fallback for manifest entries
- `app/components/data/component_manifest.yaml` — expanded from 66→89 entries; 23 converter-emitted slugs added with slot definitions and default tokens
- `email-templates/components/` — 8 new HTML files (`email-header`, `email-footer`, `social-icons`, `image-block`, `text-block`, `image-gallery`, `category-nav`, `product-grid`); 5 existing files replaced with `data-slot` versions (`hero-block`, `cta-button`, `product-card`, `divider`, `spacer`)
- `app/design_sync/component_matcher.py` — 3 new matcher rules (subtitle+title hero→`hero-text`, vertical nav→`nav-hamburger`, editorial layout→`editorial-2`); 3 new slot fill builder aliases
- `app/components/tests/test_file_loader.py` — 4 new tests (inline seed check, converter slug resolution, slot extraction, auto-slot fallback)
- `app/design_sync/tests/test_component_matcher.py` — 5 new tests for expanded matcher rules
- `.agents/plans/40.7-unified-component-resolution.md` — implementation plan

---

### Phase 40 — Summary

| Subtask | Scope | Dependencies | Status |
|---------|-------|--------------|--------|
| 40.1 Snapshot test infrastructure | `test_snapshot_regression.py`, `snapshot-capture.py`, `manifest.yaml`, `report.py` fix | Phase 39 complete | Done |
| 40.2 Collect and verify design cases | `data/debug/{id}/`, `expected.html` per case | 40.1 | In progress (case 5 draft) |
| 40.3 Figma design screenshot capture | `diagnose/extract.py`, Figma Images API | 40.1 | Pending |
| 40.4 Playwright visual regression | `test_snapshot_visual.py`, pixelmatch, mini server | 40.2 + 40.3 | Pending |
| 40.5 CI gate wiring | `Makefile`, `CLAUDE.md` | 40.2 | Pending |
| 40.6 Preserve exact image dimensions — no transparent padding | Image export pipeline, Figma API node targeting | 40.1 | Pending |
| 40.7 Unified component resolution | `seeds.py`, `file_loader.py`, `component_manifest.yaml`, `component_matcher.py`, `email-templates/components/*.html` | 40.1 | Done |

> **Execution:** 40.2 in progress — case 5 (MAAP x KASK) expected.html being refined. 40.3 independent of 40.2 — can start immediately. 40.4 requires both 40.2 (verified expected.html) and 40.3 (design.png). 40.5 last — activates the gate after all cases are verified. 40.6 independent — can start anytime. 40.7 independent of 40.2–40.6 — can start immediately. 40.7.1 + 40.7.2 parallel → 40.7.3 → 40.7.4 → 40.7.5. 40.7.6 is documentation only.

---

## Phase 41 — Converter Background Color Continuity

> **Problem:** When a full-width image has a solid/dominant background color (e.g., Mammut Eiger Extreme blue `#0252B5`, brand orange `#E85D26`) and the adjacent HTML content block (heading, paragraph, CTA) continues the same visual section, the converter outputs `bgcolor="#ffffff"` — creating a jarring white gap that breaks the design's visual flow.
>
> **Solution:** After the converter emits a `full-width-image` component followed by a text section (or vice versa), sample the dominant edge color from the image and apply it as `bgcolor` on adjacent HTML content tables when the colors match. Also propagate text/link colors to white when the background is dark.

- [ ] 41.1 Image edge color sampler utility
- [ ] 41.2 Adjacent-section background propagation in converter
- [ ] 41.3 Text/link color inversion for dark backgrounds
- [ ] 41.4 Snapshot regression cases for background continuity

---

### 41.1 Image Edge Color Sampler Utility `[Backend]`

**What:** Add `sample_edge_color(image_path: Path, edge: Literal["top", "bottom"]) -> str | None` to `app/design_sync/` that reads the top or bottom pixel strip of a design asset image, computes the dominant color, and returns a hex string if ≥80% of edge pixels share that color (solid background). Returns `None` for photographic/gradient edges.
**Why:** The converter needs to know whether an image has a solid-color edge to propagate to adjacent HTML blocks. Sampling a 4px strip and checking color uniformity distinguishes solid backgrounds (brand blue, brand orange) from photographic content (mountain scene, product shots).
**Implementation:**
- Use Pillow to read a 4px strip from top or bottom edge
- Cluster pixels by RGB (tolerance ±10 per channel)
- If largest cluster ≥80%: return hex of cluster centroid
- Else: return `None` (non-uniform edge, no propagation)
**Verify:** `sample_edge_color("2833_1154.png", "bottom")` → `"#0252B5"`. `sample_edge_color("2833_1136.png", "bottom")` → `None` (photographic).

---

### 41.2 Adjacent-Section Background Propagation in Converter `[Backend]`

**What:** In the converter's HTML assembly pass, when a `full-width-image` section is adjacent to a text/heading/CTA section, sample the facing edge of the image. If a solid color is detected, set `bgcolor` on all adjacent content tables (heading, paragraph, button-ghost, text-link) to that color instead of `#ffffff`.
**Why:** Designs frequently use colored backgrounds that flow from an image into a text area (e.g., Mammut blue layering section, orange "Grab a Duvet Day" section). The converter currently ignores this and defaults every content block to white.
**Implementation:**
- After section ordering in `_assemble_html()`, iterate adjacent pairs
- For each `(image_section, text_section)` pair: call `sample_edge_color()` on the image's facing edge
- If solid color returned: inject `bgcolor="{color}"` on content tables
- Store the propagated color on the section metadata for downstream use (text color inversion)
**Verify:** Converting the Mammut design produces `bgcolor="#0252B5"` on the "A LAYERING SYSTEM" heading/paragraph/text-link tables, and `bgcolor="#E85D26"` on the "GRAB A DUVET DAY" heading/paragraph/button tables.

---

### 41.3 Text/Link Color Inversion for Dark Backgrounds `[Backend]`

**What:** When a content block receives a propagated dark background (luminance < 0.4), automatically set text color to `#ffffff` and link colors to `#ffffff` instead of the default dark colors.
**Why:** Without inversion, dark text on a dark background is unreadable. The converter must pair background propagation with appropriate text contrast.
**Implementation:**
- Calculate relative luminance of propagated bgcolor: `L = 0.2126*R + 0.7152*G + 0.0722*B` (sRGB)
- If `L < 0.4`: override heading color to `#ffffff`, body text to `#ffffff`, link color to `#ffffff`
- Apply to VML button fallbacks too (fillcolor, strokecolor, center text color)
**Verify:** Mammut blue section (`#0252B5`, luminance ≈ 0.10) → white text. White section (`#ffffff`, luminance = 1.0) → unchanged dark text.

---

### 41.4 Snapshot Regression Cases for Background Continuity `[Backend]`

**What:** Add snapshot test assertions that verify `bgcolor` values on content blocks adjacent to colored images. Extend existing snapshot cases to check background continuity.
**Why:** Prevents regressions — ensures the sampler + propagation + inversion pipeline stays correct as the converter evolves.
**Implementation:**
- Add `test_background_continuity[case_id]` to `test_snapshot_regression.py`
- For each active case: parse output HTML, find full-width-image tables, check that adjacent content tables have matching `bgcolor` when the image has a solid edge
- Add Mammut design as a new snapshot case (case 10) with background continuity as a key verification point
**Verify:** `make snapshot-test` includes background continuity checks. Breaking the sampler → test failure.

---

### Phase 41 — Summary

| Subtask | Scope | Dependencies | Status |
|---------|-------|--------------|--------|
| 41.1 Image edge color sampler | `design_sync/` utility, Pillow | Phase 40 complete | Pending |
| 41.2 Background propagation | Converter assembly pass | 41.1 | Pending |
| 41.3 Text color inversion | Converter assembly pass | 41.2 | Pending |
| 41.4 Snapshot regression | `test_snapshot_regression.py` | 41.2 + 41.3 | Pending |

> **Execution:** 41.1 first (standalone utility). 41.2 wires it into the converter. 41.3 handles the text contrast consequence. 41.4 locks it down with tests. All subtasks are sequential.

---

## Phase 42 — HTTP Caching, Smart Polling & Data Fetching Hardening

> **The platform polls aggressively but wastes bandwidth doing it.** 32 SWR hooks use `refreshInterval` to poll backend endpoints, but there is zero HTTP-level caching — every poll returns a full JSON response even when data hasn't changed. There is no visibility-aware polling — tabs left open in the background poll at the same rate as active tabs, wasting server capacity. And there is no centralized polling/stale-time configuration — each of the 56 custom hooks configures its own intervals, deduplication, and revalidation independently with no shared constants.
>
> **Measured impact (Archon case study):** The Archon project implemented ETag caching on polled endpoints and achieved ~70% bandwidth reduction for unchanged responses. They also implemented visibility-aware polling that pauses when tabs are hidden and slows to 1.5x interval when unfocused. Both patterns are directly applicable here — our polling-heavy endpoints (QA results, rendering tests, design sync, MCP status) return identical data on 90%+ of polls.
>
> **This is not a rewrite.** The SWR data layer is sound — conditional keys, centralized fetcher, per-hook deduplication. This phase adds three layers on top: (1) backend ETag generation for bandwidth reduction, (2) frontend visibility-aware polling for server load reduction, (3) centralized polling/stale constants to eliminate per-hook configuration drift. Each subtask is independently shippable and backward-compatible — no SWR-to-TanStack migration, no API contract changes.
>
> **Dependency note:** Independent of Phases 37–41. Uses existing SWR infrastructure and FastAPI middleware. No database changes. No new dependencies (uses stdlib `hashlib` for ETags, browser `document.visibilityState` for polling).

- [ ] 42.1 Backend ETag middleware for polling endpoints
- [ ] 42.2 Frontend ETag support in auth-fetch
- [ ] 42.3 Visibility-aware smart polling hook
- [ ] 42.4 Centralized polling and stale-time constants
- [ ] 42.5 Migrate high-traffic hooks to smart polling + constants
- [ ] 42.6 Unified progress tracking endpoint for long-running operations
- [ ] 42.7 Wire ETag + smart polling into CI validation

---

### 42.1 Backend ETag Middleware for Polling Endpoints `[Backend]`

**What:** Create a FastAPI middleware that generates ETag headers for JSON responses on GET endpoints, and returns `304 Not Modified` when the client's `If-None-Match` header matches. Apply to all `/api/v1/` GET routes. Uses MD5 hash of the serialized response body as the ETag value.
**Why:** Every poll to `/api/v1/rendering/tests/{id}`, `/api/v1/design-sync/imports/{id}`, `/api/v1/mcp/status`, `/api/v1/qa/reports/{id}` returns the full JSON body even when nothing changed. For a rendering test that polls every 3 seconds, that's 20 identical ~5KB responses per minute per open tab. With 5 developers and 3 open tabs each, that's 300 wasted responses/minute from rendering alone. ETag caching turns these into 304s with zero body — the browser serves the cached response. Archon measured ~70% bandwidth reduction with this exact pattern.
**Implementation:**
- Create `app/core/etag.py`:
  ```python
  import hashlib
  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.requests import Request
  from starlette.responses import Response

  class ETagMiddleware(BaseHTTPMiddleware):
      """Generate ETags for GET responses; return 304 when unchanged."""

      async def dispatch(self, request: Request, call_next):
          response = await call_next(request)

          # Only ETag GET requests with JSON responses
          if request.method != "GET" or not response.headers.get("content-type", "").startswith("application/json"):
              return response

          # Read response body, compute ETag
          body = b""
          async for chunk in response.body_iterator:
              body += chunk

          etag = f'"{hashlib.md5(body).hexdigest()}"'

          # Check If-None-Match
          if_none_match = request.headers.get("if-none-match")
          if if_none_match == etag:
              return Response(status_code=304, headers={
                  "ETag": etag,
                  "Cache-Control": "no-cache, must-revalidate",
              })

          # Return original response with ETag headers
          return Response(
              content=body,
              status_code=response.status_code,
              headers={
                  **dict(response.headers),
                  "ETag": etag,
                  "Cache-Control": "no-cache, must-revalidate",
              },
              media_type=response.media_type,
          )
  ```
- Register in `app/core/middleware.py` → `setup_middleware(app)`:
  ```python
  from app.core.etag import ETagMiddleware
  app.add_middleware(ETagMiddleware)
  ```
  Position: after CORS, before `RequestLoggingMiddleware` (so logging sees the 304 status)
- **Design decisions:**
  - MD5 is sufficient — this is cache validation, not security. Fast and collision-resistant for JSON payloads
  - `Cache-Control: no-cache, must-revalidate` — forces browser to always revalidate (never serve stale without checking), which is correct for polled data
  - Applied globally to all GET JSON responses — no per-endpoint opt-in needed. POST/PUT/DELETE/WebSocket unaffected
  - Response body is buffered in memory for hashing — acceptable for JSON responses (typically <100KB). The existing `BodySizeLimitMiddleware` already caps at 100KB for non-upload paths
**Security:** MD5 is used for cache fingerprinting only, not cryptographic signing. ETag values are opaque identifiers per RFC 7232 — no sensitive data exposed. `Cache-Control: no-cache` prevents proxies from serving stale data.
**Verify:** `curl -v GET /api/v1/projects` → response includes `ETag: "abc123..."` header. Second request with `If-None-Match: "abc123..."` → `304 Not Modified` with empty body. Modify a project → next request returns `200` with new ETag. POST/DELETE requests → no ETag headers. `make test` passes — no regressions. 8 tests: ETag generation, 304 response, ETag change on data change, non-GET bypass, non-JSON bypass, streaming response bypass, concurrent request safety, header format (RFC 7232 quoted string).

---

### 42.2 Frontend ETag Support in auth-fetch `[Frontend]`

**What:** Ensure the `authFetch` client correctly propagates `If-None-Match` headers and handles `304 Not Modified` responses. In standard browsers, `fetch()` handles this automatically via the HTTP cache. Add a fallback for non-browser runtimes (SSR, test environments) where 304 may surface as an empty response.
**Why:** The browser's HTTP cache automatically sends `If-None-Match` and interprets 304 responses — in production, this works out of the box once the backend sends ETag headers (42.1). However, Next.js SSR (`typeof window === "undefined"` path in `auth-fetch.ts`) uses Node.js `fetch()` which may not have a backing HTTP cache. In that case, a 304 response surfaces to JavaScript as an empty body, which would cause `res.json()` to throw. The fetcher must handle this edge case gracefully.
**Implementation:**
- Update `cms/apps/web/src/lib/swr-fetcher.ts`:
  ```typescript
  export async function fetcher<T>(url: string): Promise<T> {
    const res = await authFetch(url);

    // 304 Not Modified — browser cache served the response.
    // In non-browser runtimes, 304 may surface with empty body.
    // SWR treats undefined return as "no update" and keeps cached data.
    if (res.status === 304) {
      return undefined as unknown as T;
    }

    if (!res.ok) {
      // ... existing error handling unchanged
    }

    return res.json();
  }
  ```
- **SWR behavior on `undefined` return:** SWR's `fetcher` returning `undefined` does NOT clear cached data — it leaves the previous value in place. This is the correct behavior: a 304 means "data unchanged", so SWR should keep showing the cached version. Verify this in a test.
- **No changes needed to `authFetch`** itself — `fetch()` automatically sends `If-None-Match` when the browser cache has an ETag for that URL. The `Cache-Control: no-cache, must-revalidate` from the backend (42.1) ensures the browser always revalidates.
- Add `"304 handling"` section to SWR fetcher JSDoc explaining the caching flow
**Security:** No new attack surface. 304 responses contain no body — no data leakage. The existing JWT auth flow is unaffected (auth headers are orthogonal to cache validation headers).
**Verify:** Open Chrome DevTools → Network tab. Poll a rendering test endpoint → first response shows `ETag` header. Subsequent polls show `If-None-Match` request header → server returns `304` with empty body → UI still shows data (SWR cache). Modify data → next poll returns `200` with new body and new ETag → UI updates. SSR path: mock a 304 response in Vitest → fetcher returns `undefined` → SWR keeps previous data. 5 tests: 304 handling, undefined return preservation, ETag header forwarding, SSR fallback, error responses unaffected.

---

### 42.3 Visibility-Aware Smart Polling Hook `[Frontend]`

**What:** Create a `useSmartPolling(baseInterval: number)` hook that returns a dynamic `refreshInterval` value for SWR. The interval adjusts based on browser tab visibility: full speed when visible, 1.5x when window is unfocused, paused (0) when tab is hidden. Replaces hardcoded `refreshInterval` values across all polling hooks.
**Why:** The platform has 32 SWR hooks with `refreshInterval`. Tabs left open in the background poll at full speed — a developer with 3 tabs open has 3x the server load even though they're only looking at one. The `document.visibilityState` API (supported in all modern browsers) provides visibility information. Archon's `useSmartPolling` hook reduced background server load by ~60% in their testing. The hook is a drop-in replacement: instead of `refreshInterval: 3000`, use `refreshInterval: useSmartPolling(3000)`.
**Implementation:**
- Create `cms/apps/web/src/hooks/use-smart-polling.ts`:
  ```typescript
  import { useCallback, useEffect, useState } from "react";

  type VisibilityState = "visible" | "hidden" | "blurred";

  /**
   * Visibility-aware polling interval for SWR.
   * - visible: baseInterval (full speed)
   * - blurred: baseInterval * 1.5 (window unfocused but tab visible)
   * - hidden: 0 (paused — tab not visible)
   *
   * Usage: useSWR(key, fetcher, { refreshInterval: useSmartPolling(3000) })
   */
  export function useSmartPolling(baseInterval: number): number {
    const [visibility, setVisibility] = useState<VisibilityState>("visible");

    useEffect(() => {
      const onVisibilityChange = () => {
        setVisibility(document.hidden ? "hidden" : "visible");
      };
      const onFocus = () => setVisibility("visible");
      const onBlur = () => {
        if (!document.hidden) setVisibility("blurred");
      };

      document.addEventListener("visibilitychange", onVisibilityChange);
      window.addEventListener("focus", onFocus);
      window.addEventListener("blur", onBlur);

      return () => {
        document.removeEventListener("visibilitychange", onVisibilityChange);
        window.removeEventListener("focus", onFocus);
        window.removeEventListener("blur", onBlur);
      };
    }, []);

    if (baseInterval === 0) return 0;

    switch (visibility) {
      case "visible": return baseInterval;
      case "blurred": return Math.round(baseInterval * 1.5);
      case "hidden": return 0;
    }
  }
  ```
- **Design decisions:**
  - Returns a number, not a function — SWR accepts both `refreshInterval: number` and `refreshInterval: (data) => number`. The hook returns a number so it composes with SWR's function form: `refreshInterval: (data) => data?.status === "done" ? 0 : smartInterval`
  - `baseInterval === 0` → always returns 0. This preserves the existing pattern where `refreshInterval: 0` means "no polling"
  - Three states, not two — "blurred" (window lost focus but tab still visible, e.g., using another window on the same monitor) gets a slowdown, not a full pause. This handles the common case of a developer with the email preview in one window and their IDE in another
  - Cleanup on unmount — no leaked event listeners
  - SSR-safe — `document` access is inside `useEffect`, not at module level
**Security:** Read-only access to `document.visibilityState` and window focus events. No new permissions or APIs.
**Verify:** Open a polling page (rendering test with 3s interval). Switch to another tab → DevTools Network shows polling stops. Switch back → polling resumes at 3s. Unfocus window (click desktop) → polling slows to 4.5s. Refocus → back to 3s. `baseInterval: 0` → always 0 regardless of visibility. 6 tests: visible interval, hidden pause, blurred slowdown, zero passthrough, cleanup on unmount, SSR no-crash (no `document` access during render).

---

### 42.4 Centralized Polling and Stale-Time Constants `[Frontend]`

**What:** Create a shared constants module that defines all polling intervals and SWR configuration presets. Replaces the 32 scattered hardcoded `refreshInterval` values and per-hook `dedupingInterval` / `revalidateOnFocus` settings with named constants.
**Why:** Current state: `use-design-sync.ts` polls at 2000ms, `use-renderings.ts` at 3000ms, `use-mcp.ts` at 30000ms and 15000ms, `use-ontology.ts` at 60000ms — all hardcoded. When you need to tune polling (e.g., reduce server load during peak hours), you'd have to find and update 32 files. Archon solved this with a `STALE_TIMES` constant object and `POLLING_INTERVALS` — one file to change, all hooks follow. Additionally, `dedupingInterval` varies between 300ms and 600ms across hooks with no rationale for the difference.
**Implementation:**
- Create `cms/apps/web/src/lib/swr-constants.ts`:
  ```typescript
  /**
   * Centralized SWR configuration constants.
   * Single source of truth for polling intervals, deduplication, and stale times.
   */

  /** Polling intervals (milliseconds). Used with refreshInterval or useSmartPolling. */
  export const POLL = {
    /** Real-time operations: rendering tests, active builds, design sync imports */
    realtime: 3_000,
    /** Frequently changing: QA reports, blueprint runs, approval status */
    frequent: 5_000,
    /** Moderate: MCP connections, agent status */
    moderate: 15_000,
    /** Status checks: MCP server status, ontology sync */
    status: 30_000,
    /** Background: plugin health, ontology, penpot sync */
    background: 60_000,
    /** Disabled: no polling */
    off: 0,
  } as const;

  /** Deduplication intervals (milliseconds). Prevents duplicate requests within window. */
  export const DEDUP = {
    /** Standard deduplication for most hooks */
    standard: 500,
    /** Extended deduplication for expensive queries (search, AI) */
    expensive: 2_000,
  } as const;

  /** SWR option presets for common patterns. Spread into useSWR options. */
  export const SWR_PRESETS = {
    /** Polling endpoint: dedup + no revalidate on focus (polling handles freshness) */
    polling: {
      dedupingInterval: DEDUP.standard,
      revalidateOnFocus: false,
    },
    /** Static data: long dedup, no polling, no focus revalidation */
    static: {
      dedupingInterval: DEDUP.expensive,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    },
    /** User-triggered: no dedup delay, revalidate on focus */
    interactive: {
      dedupingInterval: 0,
      revalidateOnFocus: true,
    },
  } as const;
  ```
- **Migration mapping** (documents which constant replaces which hardcoded value):
  | Hook | Current interval | New constant |
  |------|-----------------|-------------|
  | `use-renderings.ts` (polling) | `3000` | `POLL.realtime` |
  | `use-design-sync.ts` (polling) | `2000` | `POLL.realtime` |
  | `use-mcp.ts` (connections) | `15000` | `POLL.moderate` |
  | `use-mcp.ts` (status) | `30000` | `POLL.status` |
  | `use-ontology.ts` | `60000` | `POLL.background` |
  | `use-penpot.ts` | `60000` | `POLL.background` |
  | `use-plugins.ts` | `60000` | `POLL.background` |
  | `use-email-clients.ts` (dedup) | `300` | `DEDUP.standard` |
  | `use-agent-skills.ts` (dedup) | `600` | `DEDUP.standard` |
**Security:** Pure constants file. No runtime behavior, no external dependencies.
**Verify:** All constants are `as const` (TypeScript enforces literal types). Importing `POLL.realtime` in a hook → TypeScript resolves to `3_000`. No default exports — tree-shaking works. `make check-fe` passes (type check + lint). 3 tests: constant values match expected, presets contain required keys, POLL.off === 0.

---

### 42.5 Migrate High-Traffic Hooks to Smart Polling + Constants `[Frontend]`

**What:** Update the 10 highest-traffic polling hooks to use `useSmartPolling` (42.3) and centralized constants (42.4). These are the hooks that generate the most server load due to short polling intervals or high usage frequency. Remaining hooks migrate in a follow-up (not blocking).
**Why:** Migrating all 32 hooks at once is risky and hard to review. The top 10 by traffic cover ~80% of polling load. Each migration is a 2-line change (import constant, wrap interval), so the PR stays reviewable. The remaining 22 hooks can migrate incrementally — they're longer-interval or lower-traffic.
**Implementation:**
- **Priority 1 — Real-time polling (3s, always active when page open):**
  1. `cms/apps/web/src/hooks/use-renderings.ts` → `useRenderingTestPolling()`:
     ```typescript
     // Before:
     refreshInterval: (data) => data && (data.status === "pending" || data.status === "processing") ? 3000 : 0,
     // After:
     const smartInterval = useSmartPolling(POLL.realtime);
     refreshInterval: (data) => data && (data.status === "pending" || data.status === "processing") ? smartInterval : POLL.off,
     ```
  2. `cms/apps/web/src/hooks/use-design-sync.ts` → `useDesignImport()`:
     ```typescript
     // Before: refreshInterval: polling ? 2000 : 0,
     // After:
     const smartInterval = useSmartPolling(POLL.realtime);
     refreshInterval: polling ? smartInterval : POLL.off,
     ```
  3. `cms/apps/web/src/hooks/use-blueprint-runs.ts` — if polling active builds
  4. `cms/apps/web/src/hooks/use-qa-reports.ts` — if polling active QA checks

- **Priority 2 — Moderate polling (15-30s, always on):**
  5. `cms/apps/web/src/hooks/use-mcp.ts` → connections (15s) and status (30s):
     ```typescript
     const connInterval = useSmartPolling(POLL.moderate);
     const statusInterval = useSmartPolling(POLL.status);
     ```
  6. `cms/apps/web/src/hooks/use-approval.ts` — if polling approval status

- **Priority 3 — Background polling (60s):**
  7. `cms/apps/web/src/hooks/use-ontology.ts` → `POLL.background`
  8. `cms/apps/web/src/hooks/use-penpot.ts` → `POLL.background`
  9. `cms/apps/web/src/hooks/use-plugins.ts` → `POLL.background`
  10. `cms/apps/web/src/hooks/use-email-clients.ts` → dedup to `DEDUP.standard`

- **Each hook migration:**
  1. Import `useSmartPolling` and relevant `POLL`/`DEDUP`/`SWR_PRESETS` constants
  2. Replace hardcoded `refreshInterval` with `useSmartPolling(POLL.xxx)`
  3. Replace hardcoded `dedupingInterval` with `DEDUP.standard` or `DEDUP.expensive`
  4. Add `...SWR_PRESETS.polling` spread where appropriate
  5. Remove per-hook `revalidateOnFocus: false` (now in preset)
- **Do NOT change:** Hook signatures, return types, conditional key patterns, error handling. This is a config-only migration — no behavior change when tab is visible and focused.
**Security:** No new attack surface. Polling behavior change is client-side only. Server sees fewer requests from background tabs — reduced load, not increased.
**Verify:** Open rendering test page, start a test → polls at 3s (visible in Network tab). Switch tab → polling pauses. Come back → resumes. Unfocus window → slows to ~4.5s. All 10 migrated hooks use constants from `swr-constants.ts` (grep confirms no hardcoded intervals remain in those files). `make check-fe` passes. Existing Vitest tests for each hook still pass. 10 tests (one per hook): verify correct `refreshInterval` value at each visibility state.

---

### 42.6 Unified Progress Tracking for Long-Running Operations `[Backend + Frontend]`

**What:** Create a lightweight in-memory progress tracker for long-running operations (rendering tests, QA scans, design sync imports, connector exports, blueprint runs). Exposes a single `GET /api/v1/progress/{operation_id}` endpoint that returns operation status, progress percentage, and log messages. Frontend polls this single endpoint instead of per-feature status endpoints.
**Why:** Currently, each long-running operation has its own polling pattern: rendering tests poll `/api/v1/rendering/tests/{id}` for status, design sync polls `/api/v1/design-sync/imports/{id}`, QA polls its own endpoint. Each returns the full entity just to check a `status` field. A dedicated progress endpoint returns only status + progress + log (tiny payload, ~200 bytes), is ETag-friendly (42.1), and provides a consistent UX across all operation types. Archon's `ProgressTracker` pattern proved this — simple in-memory dict with progress callbacks, polled via a single endpoint.
**Implementation:**
- Create `app/core/progress.py`:
  ```python
  from dataclasses import dataclass, field
  from datetime import datetime, UTC
  from enum import StrEnum

  class OperationStatus(StrEnum):
      PENDING = "pending"
      PROCESSING = "processing"
      COMPLETED = "completed"
      FAILED = "failed"

  @dataclass
  class ProgressEntry:
      operation_id: str
      operation_type: str  # "rendering", "qa_scan", "design_sync", "export", "blueprint"
      status: OperationStatus = OperationStatus.PENDING
      progress: int = 0  # 0-100
      message: str = ""
      started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
      updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
      error: str | None = None

  class ProgressTracker:
      """In-memory progress store for long-running operations."""
      _store: dict[str, ProgressEntry] = {}

      @classmethod
      def start(cls, operation_id: str, operation_type: str) -> ProgressEntry:
          entry = ProgressEntry(operation_id=operation_id, operation_type=operation_type)
          cls._store[operation_id] = entry
          return entry

      @classmethod
      def update(cls, operation_id: str, *, progress: int | None = None,
                 status: OperationStatus | None = None, message: str | None = None,
                 error: str | None = None) -> ProgressEntry | None:
          entry = cls._store.get(operation_id)
          if not entry:
              return None
          if progress is not None: entry.progress = progress
          if status is not None: entry.status = status
          if message is not None: entry.message = message
          if error is not None: entry.error = error
          entry.updated_at = datetime.now(UTC)
          return entry

      @classmethod
      def get(cls, operation_id: str) -> ProgressEntry | None:
          return cls._store.get(operation_id)

      @classmethod
      def cleanup_completed(cls, max_age_seconds: int = 300) -> int:
          """Remove completed/failed entries older than max_age. Call periodically."""
          now = datetime.now(UTC)
          to_remove = [
              k for k, v in cls._store.items()
              if v.status in (OperationStatus.COMPLETED, OperationStatus.FAILED)
              and (now - v.updated_at).total_seconds() > max_age_seconds
          ]
          for k in to_remove:
              del cls._store[k]
          return len(to_remove)
  ```
- Create `app/core/progress_routes.py`:
  ```python
  @router.get("/api/v1/progress/{operation_id}")
  async def get_progress(operation_id: str) -> dict:
      entry = ProgressTracker.get(operation_id)
      if not entry:
          raise HTTPException(404, f"Operation {operation_id} not found")
      return {
          "operation_id": entry.operation_id,
          "operation_type": entry.operation_type,
          "status": entry.status,
          "progress": entry.progress,
          "message": entry.message,
          "error": entry.error,
      }

  @router.get("/api/v1/progress/active")
  async def get_active_operations() -> list[dict]:
      """List all in-flight operations."""
      return [...]
  ```
- Register router in `app/core/__init__.py` or `main.py`
- **Integration points** (wire into existing services — one at a time, not all at once):
  - `app/rendering/service.py` → call `ProgressTracker.start()` when test begins, `.update()` on each client render, `.update(status=COMPLETED)` when done
  - `app/design_sync/service.py` → start on import, update per-stage (fetching → converting → saving)
  - `app/qa_engine/service.py` → start on scan, update per-check (1/10 → 2/10 → ...)
  - `app/connectors/` → start on export, update per-ESP
- Frontend: Create `cms/apps/web/src/hooks/use-progress.ts`:
  ```typescript
  export function useProgress(operationId: string | null) {
    const smartInterval = useSmartPolling(POLL.realtime);
    return useSWR<ProgressEntry>(
      operationId ? `/api/v1/progress/${operationId}` : null,
      fetcher,
      {
        refreshInterval: (data) =>
          data && (data.status === "pending" || data.status === "processing")
            ? smartInterval : POLL.off,
        ...SWR_PRESETS.polling,
      },
    );
  }
  ```
- **This does NOT replace per-feature detail endpoints** — those still return full entity data. The progress endpoint is an optimization for the "is it done yet?" polling pattern.
**Security:** Progress entries are in-memory — lost on restart (acceptable, operations restart too). No PII in progress messages. Operation IDs should be UUIDs (not sequential integers) to prevent enumeration. Auth middleware applies to `/api/v1/progress/` like all other routes.
**Verify:** Start a rendering test → `GET /api/v1/progress/{id}` returns `{"status": "processing", "progress": 30, "message": "Rendering Gmail..."}`. Poll with ETag → 304 when progress unchanged. Operation completes → status becomes `"completed"`, progress 100. After 5 minutes → entry cleaned up, 404 returned. `GET /api/v1/progress/active` → lists all in-flight operations. 12 tests: start, update, get, 404, cleanup, active list, concurrent operations, status transitions, error capture, auth required, UUID validation, ETag compatibility.

---

### 42.7 Wire ETag + Smart Polling into CI Validation `[DevOps]`

**What:** Add validation to the CI pipeline that ensures: (1) no new SWR hooks use hardcoded `refreshInterval` numbers (must use `POLL.*` constants), (2) the ETag middleware is registered and responding, (3) the `useSmartPolling` hook is used for all polling intervals > 0.
**Why:** Without CI enforcement, new hooks will inevitably introduce hardcoded intervals, bypassing the centralized configuration. A lint rule catches this at PR time — much cheaper than discovering drift months later. The ETag middleware integration test catches accidental removal during refactoring.
**Implementation:**
- **Frontend lint rule** — add to `cms/apps/web/eslint.config.mjs` (or create a custom rule):
  - Pattern: flag `refreshInterval: <number_literal>` where number > 0 in any `.ts`/`.tsx` file under `src/hooks/`
  - Allowed: `refreshInterval: POLL.xxx`, `refreshInterval: smartInterval`, `refreshInterval: (data) => ...`, `refreshInterval: 0`
  - Implementation option A: ESLint `no-restricted-syntax` rule with AST selector
  - Implementation option B: Simple grep-based check in Makefile:
    ```makefile
    lint-polling:
    	@echo "Checking for hardcoded polling intervals..."
    	@! grep -rn 'refreshInterval.*[0-9]\{3,\}' cms/apps/web/src/hooks/ \
    		--include='*.ts' --include='*.tsx' \
    		| grep -v 'POLL\.' | grep -v '// legacy-ok' \
    		&& echo "FAIL: Hardcoded refreshInterval found" && exit 1 \
    		|| echo "OK: All polling intervals use POLL constants"
    ```
- **Backend integration test** — add to `tests/test_etag.py`:
  ```python
  async def test_etag_middleware_active(client):
      """ETag middleware responds with ETag header on GET."""
      resp = await client.get("/api/v1/health")
      assert "etag" in resp.headers

  async def test_etag_304_on_match(client):
      """304 returned when If-None-Match matches."""
      resp1 = await client.get("/api/v1/health")
      etag = resp1.headers["etag"]
      resp2 = await client.get("/api/v1/health", headers={"If-None-Match": etag})
      assert resp2.status_code == 304
  ```
- **Wire into Makefile:**
  - Add `lint-polling` to the `check-fe` target
  - Add `test_etag.py` to the standard `test` target (it's a unit test, not integration)
- Update `CLAUDE.md` Essential Commands section:
  - Add `make lint-polling` — "Check for hardcoded polling intervals"
  - Document ETag + smart polling architecture in a new "HTTP Caching" section
**Security:** CI rules are read-only checks. No new permissions or external access.
**Verify:** Add a new hook with `refreshInterval: 5000` → `make lint-polling` fails. Change to `refreshInterval: POLL.frequent` → passes. `make check` includes `lint-polling` and ETag tests. Remove ETag middleware → `test_etag_304_on_match` fails. All green when properly configured.

---

### Phase 42 — Summary

| Subtask | Scope | Dependencies | Effort |
|---------|-------|--------------|--------|
| 42.1 ETag middleware | `app/core/etag.py`, `middleware.py` | None — start immediately | ~120 LOC + 8 tests |
| 42.2 Frontend ETag support | `swr-fetcher.ts`, `auth-fetch.ts` | 42.1 (backend sends ETags) | ~20 LOC + 5 tests |
| 42.3 Smart polling hook | `use-smart-polling.ts` | None — independent | ~60 LOC + 6 tests |
| 42.4 Polling constants | `swr-constants.ts` | None — independent | ~50 LOC + 3 tests |
| 42.5 Hook migration (top 10) | 10 hook files | 42.3 + 42.4 | ~5 LOC per hook + 10 tests |
| 42.6 Progress tracker | `app/core/progress.py`, `use-progress.ts` | 42.1 + 42.3 + 42.4 | ~200 LOC + 12 tests |
| 42.7 CI validation | `Makefile`, `eslint.config`, `test_etag.py` | 42.1 + 42.4 | ~80 LOC + lint rule |

> **Execution:** 42.1, 42.3, and 42.4 are fully independent — start all three in parallel. 42.2 depends on 42.1 (needs backend ETags). 42.5 depends on 42.3 + 42.4 (needs smart polling hook + constants). 42.6 depends on 42.1 + 42.3 + 42.4 (uses all three). 42.7 depends on 42.1 + 42.4 (validates both). **Critical path:** 42.1 → 42.2, then 42.3 + 42.4 → 42.5 → 42.6 → 42.7.
>
> **This is NOT a major refactoring.** No SWR-to-TanStack migration. No API contract changes. No database schema changes. Each subtask is backward-compatible — existing hooks work unchanged until individually migrated. The heaviest subtask (42.6 progress tracker) is optional and can be deferred. The core value (42.1–42.5) is ~250 LOC of new code + config changes to 10 hook files.

---

## Phase 43 — Judge Feedback Loop & Self-Improving Calibration

> **Judges are stateless — they make the same mistakes every run.** After Phase 37.5 human labeling, we know exactly which traces each judge got wrong and why. But this knowledge lives in `traces/*_calibration.json` files and is never fed back into judge prompts. Agents already benefit from a feedback loop (`failure_warnings.py` injects eval failures into agent prompts), but judges have no equivalent mechanism. Every re-run repeats the same false positives and false negatives.
>
> **Solution:** Mirror the agent feedback pattern for judges. After each calibration cycle, auto-generate per-criterion correction examples from disagreements (human said X, judge said Y) and inject them into judge prompts as few-shot corrections. Judges also get progressive skill files — like agents' `SKILL.md` + `skills/` — accumulating domain knowledge about email evaluation patterns. The Knowledge agent's RAG base stores calibration learnings as searchable docs, enabling cross-agent knowledge sharing.
>
> **Dependency:** Phase 37.5 complete (human labels exist). No database changes. No API changes. ~400 LOC of new code + YAML config.

- [ ] 43.1 Judge correction generator from calibration data
- [ ] 43.2 Inject corrections into judge prompt template
- [ ] 43.3 Judge skill files for domain knowledge accumulation
- [ ] 43.4 Knowledge agent integration for cross-judge learnings
- [ ] 43.5 Calibration delta tracking and regression gate
- [ ] 43.6 End-to-end validation: re-judge with corrections, measure TPR/TNR improvement

---

### 43.1 Judge Correction Generator from Calibration Data `[Backend, Evals]`

**What:** Add `app/ai/agents/evals/judge_corrections.py` that reads calibration results (`traces/*_calibration.json`) and human label files (`traces/*_human_labels.jsonl`), extracts disagreement cases (judge verdict != human label), and generates structured correction YAML files per agent at `traces/corrections/{agent}_judge_corrections.yaml`.
**Why:** After 37.5, each calibration file contains TP/TN/FP/FN counts per criterion. The FP (judge said PASS, human said FAIL) and FN (judge said FAIL, human said PASS) cases are the judge's mistakes. Formatting these as concrete "you got this wrong" examples with the trace context and reasoning is the most direct way to improve the next run — same principle as `failure_warnings.py` but for judges instead of agents.
**Implementation:**
- Read `traces/{agent}_calibration.json` for per-criterion confusion matrices
- Read `traces/{agent}_human_labels.jsonl` + `traces/{agent}_verdicts.jsonl` to find specific disagreement traces
- For each FP/FN case, extract: `trace_id`, `criterion`, `judge_verdict`, `human_verdict`, `judge_reasoning`, `trace_brief` (first 200 chars)
- Generate `traces/corrections/{agent}_judge_corrections.yaml`:
  ```yaml
  agent: scaffolder
  generated: "2026-03-30T12:00:00Z"
  corrections:
    - criterion: brief_fidelity
      trace_id: scaff-003
      judge_said: PASS
      correct_answer: FAIL
      judge_reasoning: "The output includes a hero section and product grid..."
      correction: "The brief requested 3 product cards at 180x220px but output has 2 at default size. Count and dimension mismatches are FAIL."
      pattern: "Always verify exact counts and dimensions against brief, not just section presence."
  ```
- Cap at 3 corrections per criterion (most impactful FP/FN cases, sorted by reasoning length — shorter reasoning = less confident judge = more useful correction)
- CLI: `python -m app.ai.agents.evals.judge_corrections --traces-dir traces/ --output traces/corrections/`
- Add `make eval-corrections` Makefile target

**Security:** No external inputs. Reads existing local trace/label files only. YAML output is local.
**Verify:** After 37.5 labels exist, `make eval-corrections` generates 7 YAML files (one per LLM-judged agent — accessibility and outlook_fixer are fully deterministic, skip them). Each file contains 1–15 corrections (3 max per criterion × 5 criteria). Spot-check: correction `pattern` field is actionable guidance, not just restating the disagreement. 10 tests.

---

### 43.2 Inject Corrections into Judge Prompt Template `[Backend, Evals]`

**What:** Add `format_corrections_section(agent_name: str) -> str` to `app/ai/agents/evals/judges/base.py` that reads the agent's correction YAML and formats it as a prompt section injected between the criteria block and the golden references in `SYSTEM_PROMPT_TEMPLATE`. Each judge's `build_prompt()` calls this automatically.
**Why:** The correction examples act as few-shot "anti-examples" — they show the judge its own past mistakes with the correct answer. This is empirically more effective than adjusting criterion descriptions because it addresses specific failure modes (e.g., "counting items" or "checking exact dimensions") rather than general criteria wording.
**Implementation:**
- `format_corrections_section(agent_name)` in `base.py`:
  - Load `traces/corrections/{agent}_judge_corrections.yaml` (cache with `@lru_cache` keyed on file mtime)
  - Format as prompt block:
    ```
    ## CORRECTION EXAMPLES (from prior calibration)
    You previously made these mistakes. Learn from them:

    1. **brief_fidelity** on trace scaff-003:
       You said: PASS. Correct answer: FAIL.
       Your reasoning was: "The output includes a hero section..."
       The mistake: Always verify exact counts and dimensions against brief.
    ```
  - Token budget: 1500 tokens max (~6000 chars). Prioritize FP corrections over FN (false positives are more damaging — they let bad output through).
  - Return empty string if no corrections file exists (graceful degradation — judges work fine without corrections, just less accurately)
- Update `SYSTEM_PROMPT_TEMPLATE` to include `{corrections_block}` placeholder
- Each judge's `build_prompt()` calls `format_corrections_section(self.agent_name)` — zero changes needed in individual judge files if base class handles it
- Add `--no-corrections` flag to `judge_runner.py` for A/B comparison runs

**Security:** Correction files are local YAML. No user input reaches prompt injection surface — corrections are generated from our own calibration data.
**Verify:** Judge prompt for scaffolder includes correction section when YAML exists. Judge prompt without YAML file has no correction section (empty string). Token budget respected — correction section ≤1500 tokens even with 15 corrections. `--no-corrections` flag suppresses injection. 8 tests.

---

### 43.3 Judge Skill Files for Domain Knowledge Accumulation `[Backend, Evals]`

**What:** Add `app/ai/agents/evals/judges/skills/` directory with per-domain skill files that accumulate email evaluation expertise, mirroring the agent `SKILL.md` + `skills/` pattern. Each judge loads relevant skills via a `JUDGE_SKILL.md` manifest.
**Why:** Corrections address specific past mistakes. Skills address systemic knowledge gaps — patterns the judge consistently struggles with across multiple traces and calibration cycles. For example, if the scaffolder judge repeatedly misjudges MSO conditional nesting depth, a skill file `mso_conditional_evaluation.md` teaches it the structural rules once. This separates ephemeral corrections (from one calibration run) from durable knowledge (accumulated across runs).
**Implementation:**
- Create `app/ai/agents/evals/judges/skills/` with initial skill files derived from 37.4 flip-rate analysis:
  - `mso_conditional_patterns.md` — valid MSO nesting rules, common false positives (e.g., `<!--[if !mso]><!-->` is correct despite looking unbalanced)
  - `email_layout_detection.md` — how to distinguish layout divs (FAIL) from wrapper divs inside `<td>` (PASS)
  - `dark_mode_completeness.md` — minimum viable dark mode (meta + media query + Outlook selectors) vs partial implementation
  - `esp_syntax_validation.md` — platform-specific delimiter rules, common false positives (nested Liquid tags, AMPscript CONCAT)
  - `copy_quality_boundaries.md` — where "good enough" meets "compelling" — calibrated pass/fail boundary examples
- Add `JUDGE_SKILL.md` per judge agent mapping criteria → relevant skill files:
  ```yaml
  name: scaffolder_judge
  skills:
    mso_conditional_correctness: [mso_conditional_patterns.md]
    email_layout_patterns: [email_layout_detection.md]
    dark_mode_readiness: [dark_mode_completeness.md]
  ```
- `load_judge_skills(agent_name: str, criterion: str) -> str` utility loads and concatenates relevant skills
- Injected into prompt after golden references, before corrections (knowledge → examples → mistakes)
- Token budget: 1000 tokens per skill file, 2000 total skill budget per judge call

**Security:** Skill files are local markdown. Static content, no dynamic generation from user input.
**Verify:** Scaffolder judge prompt includes MSO pattern skill when evaluating `mso_conditional_correctness`. No skill injection for criteria with no mapped skills. Token budget enforced. Initial 5 skill files authored. 6 tests.

---

### 43.4 Knowledge Agent Integration for Cross-Judge Learnings `[Backend, Evals]`

**What:** After each calibration cycle, auto-generate a knowledge base document from calibration results and disagreement patterns, and store it in the Knowledge agent's RAG corpus (`data/knowledge/`). This makes judge calibration learnings queryable by the Knowledge agent — developers can ask "what do our judges struggle with?" and get grounded answers.
**Why:** Judge corrections (43.1) and skills (43.3) improve judges directly. But the calibration data also has value for humans — it reveals which email patterns are ambiguous, which criteria need clearer definitions, and where agent output quality is genuinely poor vs where judges are miscalibrating. Storing this in the Knowledge agent's RAG base makes it searchable and citable.
**Implementation:**
- Add `scripts/generate-calibration-knowledge.py`:
  - Read all `traces/*_calibration.json` files
  - Generate `data/knowledge/judge_calibration_insights.md` with sections:
    - Per-agent calibration summary (TPR/TNR per criterion)
    - Common disagreement patterns (grouped by criterion type)
    - Criteria approaching failure threshold (TPR < 0.90 or TNR < 0.85 — early warning)
    - Cross-agent patterns (e.g., "html_preservation is hard for all agents that modify HTML")
  - Include concrete examples from disagreement traces (anonymized trace IDs, not full HTML)
- Add `make eval-knowledge` Makefile target (runs after `make eval-calibrate`)
- Knowledge agent indexes the doc automatically on next `KnowledgeService.search()` call (existing indexing pipeline)

**Security:** No PII in calibration data. Knowledge doc contains trace IDs and criterion names only — no full HTML or user content.
**Verify:** `make eval-knowledge` generates `judge_calibration_insights.md`. Knowledge agent query "which judges have low accuracy" returns grounded answer with citations. Document regenerated cleanly after re-calibration. 4 tests.

---

### 43.5 Calibration Delta Tracking and Regression Gate `[Backend, Evals]`

**What:** Add `app/ai/agents/evals/calibration_tracker.py` that compares current calibration results against the previous run and flags regressions. Wire into `make eval-check` as a calibration regression gate: if any criterion's TPR drops >5pp or TNR drops >5pp from the baseline, the gate fails.
**Why:** Without tracking, judges can silently degrade — a prompt tweak that fixes one criterion may break another. The improvement tracker (`improvement_tracker.py`) tracks agent pass rates but not judge accuracy. This closes the gap: every calibration run is compared to baseline, and regressions are caught before they propagate.
**Implementation:**
- `calibration_tracker.py`:
  - `load_baseline(path: Path) -> dict[str, CalibrationResult]` — reads `traces/calibration_baseline.json`
  - `compare_calibration(current: list[CalibrationResult], baseline: dict) -> list[CalibrationDelta]` — computes per-criterion TPR/TNR deltas
  - `CalibrationDelta(agent, criterion, tpr_before, tpr_after, tpr_delta, tnr_before, tnr_after, tnr_delta, regressed: bool)`
  - `save_baseline(results: list[CalibrationResult], path: Path)` — snapshots current as new baseline
- CLI: `python -m app.ai.agents.evals.calibration_tracker --current traces/ --baseline traces/calibration_baseline.json`
- `make eval-calibration-gate` target: fails if any criterion regressed >5pp
- Wire into `make eval-check` (existing CI gate)
- First run after 37.5: save initial baseline, no comparison

**Security:** Local file comparison. No external services.
**Verify:** Baseline saved on first run. Simulated regression (manually edit calibration) triggers gate failure. Improvements pass gate. Delta report shows per-criterion changes. 8 tests.

---

### 43.6 End-to-End Validation: Re-Judge with Corrections `[Evals, Manual]`

**What:** Re-run the full judge pipeline with corrections enabled (from 43.1–43.2) and compare TPR/TNR against the 37.5 baseline. This validates that the feedback loop actually improves accuracy. Run a second pass without corrections (`--no-corrections`) for A/B comparison.
**Why:** The entire phase is pointless if corrections don't improve judge accuracy. This subtask measures the delta and identifies any criteria where corrections made things worse (over-correction). It also establishes the first calibration baseline for the regression gate (43.5).
**Implementation:**
- Run `make eval-corrections` to generate correction YAMLs from 37.5 labels
- Run `make eval-judge` (with corrections) → new verdicts
- Run `make eval-calibrate` → new calibration against same 37.5 human labels
- Compare: `make eval-calibration-gate --baseline traces/calibration_baseline_37_5.json`
- Run `make eval-judge -- --no-corrections` → verdicts without corrections
- Run `make eval-calibrate` again → calibration without corrections
- Document delta per criterion in `traces/correction_impact_report.json`:
  ```json
  {
    "scaffolder:brief_fidelity": {
      "tpr_without": 0.82, "tpr_with": 0.91,
      "tnr_without": 0.78, "tnr_with": 0.85,
      "verdict": "improved"
    }
  }
  ```
- If any criterion worsened with corrections: review and adjust the correction YAML, re-run
- Save final calibration as new baseline for 43.5 gate

**Security:** Same as 37.4 — LLM judge calls use existing configured provider. ~$2.50 per full run on Sonnet, ~$5 total for A/B comparison.
**Verify:** Correction impact report generated for all 7 LLM-judged agents. Majority of criteria show TPR/TNR improvement or no change. No criterion regressed >3pp (if so, adjust corrections and re-run). Final calibration meets TPR ≥ 0.85 and TNR ≥ 0.80 for all criteria. Baseline saved for future regression gate.

---

### Phase 43 — Summary

| Subtask | Scope | Dependencies | Effort |
|---------|-------|--------------|--------|
| 43.1 Correction generator | `judge_corrections.py`, YAML output | 37.5 complete (human labels) | ~120 LOC + 10 tests |
| 43.2 Prompt injection | `base.py` update, `judge_runner.py` flag | 43.1 (corrections exist) | ~80 LOC + 8 tests |
| 43.3 Judge skill files | `judges/skills/`, `JUDGE_SKILL.md`, loader | None — independent | ~5 skill files + 60 LOC + 6 tests |
| 43.4 Knowledge integration | `generate-calibration-knowledge.py` | 37.5 complete (calibration data) | ~100 LOC + 4 tests |
| 43.5 Calibration regression gate | `calibration_tracker.py`, Makefile | 37.5 complete (first baseline) | ~80 LOC + 8 tests |
| 43.6 End-to-end validation | Re-judge + A/B comparison | 43.1 + 43.2 + 43.5 | ~$5 API cost, manual review |

> **Execution:** 43.1 first (generates the data). 43.2 wires it into prompts (depends on 43.1). 43.3 is independent — can run in parallel with 43.1/43.2. 43.4 is independent — can run in parallel. 43.5 is independent — can run in parallel. 43.6 is the integration test — depends on 43.1 + 43.2 + 43.5. **Critical path:** 43.1 → 43.2 → 43.6. **Parallel track:** 43.3 + 43.4 + 43.5 (all independent).
>
> **This completes the judge feedback loop.** After Phase 43, every calibration cycle automatically generates corrections that improve the next judge run. The pattern mirrors the existing agent feedback loop (`failure_warnings.py`) but for judges. Combined with golden references (Phase 37) and judge skills (43.3), judges have three layers of improving context: durable knowledge (skills), verified examples (golden refs), and mistake corrections (calibration feedback). Total new code: ~440 LOC + 5 skill files. API cost per validation run: ~$5.

---

## Phase 44 — Workflow Hardening, CI Gaps & Operational Maturity

> **The codebase is well-engineered but the workflow around it has gaps.** Strict types, 26 ruff rules, pre-commit hooks, SAST scanning, and a rich eval pipeline protect code quality — but UI regressions ship uncaught (Playwright tests don't run in CI), dependencies accumulate silent CVEs (no automated update tooling), 50+ feature flags have no expiry tracking, 47 Alembic migrations have no squash strategy, and there are zero operational runbooks for production incidents. These are the gaps between "well-built" and "well-operated."
>
> **This phase closes them systematically.** 10 subtasks across CI hardening, dependency hygiene, operational documentation, adversarial agent evaluation, CRDT testing, SDK drift detection, and contributor onboarding. Most subtasks are independent — high parallelism possible. No architectural changes. Total effort: ~1200 LOC + config + documentation.
>
> **Dependency note:** Independent of Phases 37–43. Uses existing CI infrastructure (`.github/workflows/ci.yml`), Makefile targets, Docker Compose services, and eval pipeline. No new external services required except Renovate (GitHub App, free for open source / self-hosted).

- [x] ~~44.1 E2E smoke tests in CI~~ DONE
- [x] ~~44.2 Dependency update automation (Renovate)~~ DONE
- [x] ~~44.3 Feature flag lifecycle management~~ DONE
- [ ] 44.4 Adversarial agent evaluation pass
- [x] ~~44.5 Operational runbooks~~ DONE
- [x] ~~44.6 Migration squash strategy & tooling~~ DONE
- [x] ~~44.7 CRDT collaboration test coverage~~ DONE
- [x] ~~44.8 SDK drift detection in CI~~ DONE
- [x] ~~44.9 Observability stack for local development~~ DONE
- [x] ~~44.10 Contributing guide & new-feature scaffolding~~ DONE

---

~~44.1–44.3 archived to `docs/TODO-completed.md`~~

---

### 44.4 Adversarial Agent Evaluation Pass `[Backend, Evals]`

**What:** Add an adversarial evaluation stage to the eval pipeline that generates hostile inputs designed to break agent output — long strings, RTL text, nested Liquid/AMPscript, missing images, extreme viewport widths, emoji-heavy content. Each agent's eval traces include adversarial test cases alongside normal ones. Failures feed back as regression test cases.
**Why:** The current eval pipeline tests agents against representative inputs — well-formed Figma designs, standard email briefs, typical component HTML. But production inputs are adversarial by nature: clients paste Word-formatted text, Figma designs have 200+ layers, ESP templates nest 5 levels of conditionals. The adversarial-dev harness (GAN-inspired planner/generator/evaluator architecture) demonstrates that separate adversarial evaluation dramatically improves output quality. Adapting this principle: an adversarial input generator creates inputs designed to trigger known failure modes, and agents must survive them.
**Implementation:**
- Create `app/ai/agents/evals/adversarial.py`:
  ```python
  @dataclass(frozen=True)
  class AdversarialCase:
      name: str
      agent: str
      input_html: str
      attack_type: str  # "long_string" | "rtl_injection" | "nested_conditionals" | "missing_assets" | "extreme_width" | "emoji_heavy" | "malformed_html"
      description: str

  def generate_adversarial_cases(agent: str) -> list[AdversarialCase]:
      """Generate adversarial test cases for an agent."""
      cases = []
      cases.extend(_long_string_cases(agent))      # 500+ char subject, 10KB paragraph
      cases.extend(_rtl_injection_cases(agent))     # Arabic/Hebrew mixed with LTR
      cases.extend(_nested_conditional_cases(agent)) # 5-level Liquid nesting
      cases.extend(_missing_asset_cases(agent))     # broken image URLs, missing fonts
      cases.extend(_extreme_dimension_cases(agent)) # 200px and 1200px viewports
      cases.extend(_emoji_cases(agent))             # emoji in headings, alt text, CTA
      cases.extend(_malformed_html_cases(agent))    # unclosed tags, invalid nesting
      return cases
  ```
- Add adversarial cases to `app/ai/agents/evals/test_cases/adversarial/` as YAML fixtures:
  ```yaml
  - name: scaffolder_long_heading
    agent: scaffolder
    attack_type: long_string
    input_html: "<h1>{{ 'A' * 500 }}</h1><p>Normal body text</p>"
    expect: "heading truncated or wrapped, no layout break"
  ```
- Extend `runner.py` to include adversarial cases: `--include-adversarial` flag
- Extend `make eval-run` to generate adversarial traces alongside normal traces
- Add `make eval-adversarial` target for adversarial-only runs
- Failed adversarial cases auto-generate regression YAML entries in `test_cases/regression/` for permanent inclusion
- Judge verdicts on adversarial cases tracked separately in `traces/*_adversarial_verdicts.jsonl`

**Security:** Adversarial inputs are controlled test fixtures, not user-supplied. `malformed_html` cases sanitized through `nh3` before agent processing (same as production path). No XSS vectors in adversarial HTML — all use the same sanitization pipeline.
**Verify:** `generate_adversarial_cases("scaffolder")` returns 10+ cases across 7 attack types. `make eval-adversarial` generates traces for all 9 agents. Adversarial verdicts stored separately from normal verdicts. At least 1 failed adversarial case auto-generates a regression entry. `make eval-check` includes adversarial pass rate (warn if <60%, fail if <40%). 15 tests.

---

~~44.5–44.10 archived to `docs/TODO-completed.md`~~

---

### Phase 44 — Summary

| Subtask | Scope | Status |
|---------|-------|--------|
| 44.1 E2E smoke in CI | `.github/workflows/ci.yml`, Playwright | DONE |
| 44.2 Renovate | `renovate.json5` | DONE |
| 44.3 Feature flag lifecycle | `feature-flags.yaml`, `scripts/flag-audit.py` | DONE |
| 44.4 Adversarial eval pass | `app/ai/agents/evals/adversarial.py`, YAML fixtures | TODO |
| 44.5 Operational runbooks | `docs/operations/` (4 documents) | DONE |
| 44.6 Migration squash | `scripts/squash-migrations.sh`, `alembic/CLAUDE.md` | DONE |
| 44.7 CRDT collaboration tests | `app/streaming/tests/` | DONE |
| 44.8 SDK drift detection | `scripts/export-openapi.py`, CI job | DONE |
| 44.9 Observability stack | `docker-compose.observability.yml`, `observability/` | DONE |
| 44.10 Contributing guide | `CONTRIBUTING.md`, `scripts/scaffold-feature.sh` | DONE |

> 9/10 subtasks complete. Remaining: **44.4 Adversarial eval pass** — depends on eval pipeline (Phases 37-43).
