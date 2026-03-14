# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–10):** See [docs/TODO-completed.md](docs/TODO-completed.md)

## Phase 11 — QA Engine Hardening & Agent Quality Improvements

**What:** Upgrade QA checks from shallow string matching to production-grade DOM-parsed validation, expand coverage with new checks, and fix the highest-failure agent skills. Current QA checks detect ~60% of real email issues; target is 95%+. Then migrate all 10 agents to deterministic architecture (structured JSON output + template assembly + cascading auto-repair) lifting eval pass rate from 16.7% → 99%+.
**Dependencies:** Phase 5 (eval framework operational), Phase 8-9 (ontology + graph available for enriched checks). All 10 QA checks exist and run end-to-end.
**Design principle:** Every check upgrade must be backward-compatible (same `QACheckResult` schema). New checks added to `ALL_CHECKS` list. Agent fixes validated via `make eval-run` before/after comparison. Deterministic architecture (11.22) uses PIV loop pattern: LLM decides (structured JSON) → code assembles (deterministic) → QA validates (deterministic) → LLM fixes (structured retry).

### ~~11.1 QA Check Configuration System~~ DONE
**What:** Replace hardcoded thresholds and trigger lists with a per-check configuration model. Currently values like `MAX_SIZE_KB=102`, spam triggers (10 words), and pass thresholds are baked into check implementations. Add `QACheckConfig` that supports per-project overrides and per-client tuning.
**Why:** Every check below needs configurable thresholds. Without this, improvements require code changes instead of config. Client-specific QA rules (e.g., stricter accessibility for healthcare) are impossible.
**Implementation:**
- ~~Create `app/qa_engine/check_config.py` — `QACheckConfig` Pydantic model with `enabled: bool`, `severity: str`, `threshold: float`, `params: dict[str, Any]`~~
- ~~Add `QAProfileConfig` model mapping check names → `QACheckConfig` instances~~
- ~~Default profile loaded from `app/qa_engine/defaults.yaml` (new file)~~
- ~~Per-project override via `qa_profile` JSON column on `Project` model~~
- ~~Service layer merges default + project overrides at runtime~~
- ~~Each check's `run()` method receives optional config parameter~~
**Security:** Config is project-scoped, validated by Pydantic. No raw user input reaches check logic.
**Verify:** ~~Create two projects with different QA profiles. Same HTML produces different scores based on project config. `make test` passes.~~ 72/72 tests pass, mypy + pyright clean.

### ~~11.2 HTML Validation — DOM Parser Upgrade~~ DONE
**What:** Replace string matching (`"<!DOCTYPE" in html`) with proper DOM parsing using `html.parser` or `lxml`. Current check only verifies DOCTYPE and `<html>` tag presence — misses malformed structure, missing `<head>`/`<body>`, invalid nesting, missing charset meta.
**Why:** Real emails with syntax errors pass the current check. Malformed HTML causes unpredictable rendering across clients. This is the foundation check — if HTML structure is broken, all other checks are unreliable.
**Implementation:**
- Replace string checks in `app/qa_engine/checks/html_validation.py` with `lxml.html` parser
- Validate: DOCTYPE is HTML5 (`<!DOCTYPE html>`), `<html>` contains `<head>` + `<body>`, `<head>` has `<meta charset="utf-8">`, no unclosed block-level tags, proper nesting order
- Return specific failure details: "Missing `<body>` tag", "Unclosed `<div>` at approximate position"
- Scoring: 1.0 = all structural checks pass, deduct 0.15 per structural issue, minimum 0.0
- Add `lxml` to dependencies (if not already present)
**Security:** Parser input is the HTML string already validated by Pydantic schema (1-500K chars). No external fetches.
**Verify:** Test with: valid HTML (1.0), missing DOCTYPE (0.85), missing body (0.85), multiple issues (cumulative deductions), malformed nesting (caught). Existing tests still pass.

### ~~11.2a Shared QA Rule Engine — YAML-Driven Check Definitions~~ DONE
**What:** Build a shared rule engine that loads check definitions from YAML files and evaluates them against lxml DOM trees. Replaces hardcoded Python check logic with data-driven rules. Both `html_validation.py` (11.2) and `accessibility.py` (11.3) are refactored to use this engine, and all subsequent check upgrades (11.4–11.12) will load their own YAML rule files.
**Why:** Currently each check hardcodes its validation logic in Python. Adding/tuning rules requires code changes. A rule engine lets us: (a) add rules by editing YAML, no Python needed, (b) share check types across all 10+ QA checks, (c) expose rules to agents via RAG knowledge base (`make seed-knowledge`), (d) let per-project config enable/disable individual rules by ID. The two research docs (`docs/email-accessibility-wcag-aa.md` — 250+ WCAG rules, `docs/html-email-components.md` — 280+ component rules) become machine-parseable YAML that powers both QA validation and agent knowledge.
**Implementation:**
- ~~Create `app/qa_engine/rule_engine.py` — `Rule` dataclass (id, group, check_type, selector, message, deduction_key, etc.), `RuleEngine` class, `load_rules(path)` YAML loader~~
- ~~Implement ~15 check type evaluators: `attr_present`, `attr_value`, `attr_empty`, `attr_pattern`, `attr_absent`, `element_present`, `element_absent`, `element_count`, `parent_has`, `children_match`, `text_content`, `sibling_check`, `style_contains`, `raw_html_pattern`, `custom` (delegates to named Python functions for complex logic)~~
- ~~Create `app/qa_engine/rules/` directory~~
- ~~Create `app/qa_engine/rules/email_structure.yaml` — convert 11.2's 20 hardcoded checks + new rules from `docs/html-email-components.md` (document structure, layout, images, buttons, footer, dark mode, MSO, etc.)~~
- Create `app/qa_engine/rules/accessibility.yaml` — all WCAG AA rules from `docs/email-accessibility-wcag-aa.md` (language, table semantics, images, headings, links, content semantics, dark mode contrast, AMP forms) *(deferred to 11.3)*
- ~~Refactor `html_validation.py` — replace 20 hardcoded methods with thin wrapper: parse DOM → `RuleEngine(load_rules("email_structure.yaml")).evaluate(doc)` → return `QACheckResult`. Move complex logic (unclosed tag counting, block-in-inline nesting) to `custom` check functions~~
- ~~Register custom check functions for logic too complex for declarative rules: `heading_hierarchy`, `tracking_pixel_alt`, `layout_table_heuristic`, `mso_balanced_conditionals`, `unclosed_tags`, `block_in_inline`, `preview_padding_aria`, `dark_unsafe_colors`, `unsubscribe_link_present`~~
- ~~Add both YAML files to RAG knowledge base sources in `make seed-knowledge`~~
- ~~Future checks (11.4–11.12) only need: write a YAML rule file + optionally register custom functions~~
**Security:** YAML files loaded from local filesystem only (hardcoded paths, no user-controlled input). `yaml.safe_load()` used (no arbitrary code execution). Rule evaluation is read-only DOM traversal.
**Verify:** ~~All existing `html_validation` tests pass identically (behavioral regression guard). Rule engine unit tests: `load_rules()` parses valid YAML, handles malformed YAML gracefully, each of 15 check types tested with minimal fixtures.~~ `python -c "import yaml; yaml.safe_load(open('rules/accessibility.yaml'))"` pending (11.3). `email_structure.yaml` validated. 1002/1002 tests pass.

### ~~11.3 Accessibility Check — WCAG AA Coverage~~ DONE
**What:** Expand from 3 checks (lang, alt, role) to comprehensive WCAG AA validation. Current eval data shows 70% alt text pass rate and 70% screen reader compatibility — the check is too lenient. Add: heading hierarchy, link text quality, color contrast estimation, alt text quality scoring, table semantics.
**Why:** Accessibility is the highest eval failure category across agents. The check should catch issues before agents attempt fixes, reducing retry loops. Healthcare/finance clients require strict WCAG compliance.
**Implementation:**
- Rewrite `app/qa_engine/checks/accessibility.py` using HTML parser (not regex)
- **Alt text quality**: Check ALL images (not just first). Validate: present, 5-125 chars for content images, `alt=""` for decorative images, not generic ("image", "photo", "picture", "logo")
- **Heading hierarchy**: Validate h1-h6 in order, no skipped levels, at most one `<h1>`
- **Link text quality**: Flag "click here", "read more", "learn more" — require descriptive text
- **Color contrast**: Extract foreground/background color pairs from inline styles, estimate contrast ratio (4.5:1 normal text, 3:1 large text per WCAG AA)
- **Table semantics**: Layout tables need `role="presentation"`, data tables need `<caption>`, `scope` attributes on `<th>`
- **Screen reader**: Check for `aria-label` on interactive elements, `aria-describedby` where appropriate
- Scoring: weight by severity (missing alt = -0.2, heading skip = -0.1, contrast fail = -0.15, etc.)
**Security:** Read-only HTML analysis. No DOM manipulation.
**Verify:** Test matrix: fully accessible HTML (1.0), missing alts (deducted), broken heading hierarchy (deducted), poor link text (deducted), low contrast (deducted). Test that decorative images with `alt=""` are not penalised.

### ~~11.4 Fallback Check — MSO Conditional Parser~~ DONE
**What:** Replace presence-only detection (`"<!--[if mso" in html`) with a proper MSO conditional parser that validates syntax correctness, balanced pairs, VML nesting, and namespace declarations. Eval data shows **50% MSO conditional correctness failure** — the single worst failure cluster.
**Why:** Outlook rendering breaks silently when MSO conditionals are malformed. Current check passes HTML that will render incorrectly in Outlook (the largest email client by enterprise adoption). This is the highest-impact single check fix.
**Implementation:**
- ~~Rewrite `app/qa_engine/checks/fallback.py` with MSO-specific parser~~ DONE
- ~~**Balanced pair validation**: Count `<!--[if` openers == `<![endif]-->` closers. Report unbalanced pairs with approximate position~~ DONE
- ~~**VML nesting**: Verify all `<v:*>` and `<o:*>` elements are inside `<!--[if mso]>` blocks. Flag VML orphans~~ DONE
- ~~**Namespace validation**: If VML present, verify `xmlns:v="urn:schemas-microsoft-com:vml"` and `xmlns:o="urn:schemas-microsoft-com:office:office"` on `<html>` tag~~ DONE
- ~~**Ghost table structure**: Detect multi-column layouts and verify MSO ghost tables have proper `width` attributes~~ DONE
- ~~**Conditional targeting**: Validate version targeting syntax (`<!--[if gte mso 12]>`, `<!--[if !mso]><!--> ... <!--<![endif]-->`)~~ DONE
- ~~Extract reusable `validate_mso_conditionals(html) -> list[MSOIssue]` function for agents to call~~ DONE
- ~~Scoring: -0.25 per unbalanced pair, -0.2 per VML orphan, -0.15 per missing namespace, -0.1 per ghost table issue~~ DONE
**Security:** Read-only parsing. No code execution.
**Verify:** ~~Test: valid MSO HTML (1.0), unbalanced conditional (0.75), VML outside conditional (0.8), missing namespaces (0.85), complex nested conditionals (validates correctly). Eval re-run shows fallback check now catches issues that agents fail on.~~ DONE — 28 tests (18 parser unit + 10 integration), 195/195 QA tests pass.

### ~~11.5 Dark Mode Check — Semantic Validation~~ DONE
**What:** Upgrade from presence-only checks to semantic validation of dark mode implementation. Current check accepts empty `@media (prefers-color-scheme: dark)` blocks and HTML with `color-scheme` meta but no actual color remapping. Eval shows **50% meta tag failure rate**.
**Why:** Dark mode is the #1 rendering complaint from email clients. Passing the check with a broken dark mode implementation gives false confidence. The check should validate that dark mode actually works, not just that the syntax exists.
**Implementation:**
- ~~Rewrite `app/qa_engine/checks/dark_mode.py` with CSS parser~~
- ~~**Meta tag validation**: Both `<meta name="color-scheme" content="light dark">` AND `<meta name="supported-color-schemes" content="light dark">` must be in `<head>` (not body, not malformed)~~
- ~~**Media query validation**: `@media (prefers-color-scheme: dark)` block must contain at least one CSS rule with a color property (`color`, `background-color`, `background`, `border-color`)~~
- ~~**Outlook selector validation**: `[data-ogsc]` and `[data-ogsb]` selectors must contain actual color declarations (not empty)~~
- ~~**Color coherence**: Extract light mode colors and dark mode remapped colors. Flag obvious issues: white-on-white, black-on-black, text disappearing~~
- ~~**Apple Mail**: Check for `[data-apple-mail-background]` pattern (common Apple Mail dark mode fix)~~
- ~~Scoring: meta tags present (0.3), media query with rules (0.3), Outlook selectors with rules (0.2), color coherence (0.2)~~
**Security:** CSS parsing is read-only. Color extraction uses regex on style attributes.
**Verify:** ~~Test: complete dark mode (1.0), meta tags only (0.3), empty media query (0.3), Outlook selectors without rules (0.5), color coherence failure (flagged). Regression: existing passing HTML still passes.~~ 207/207 QA tests pass (47 parser unit + 16 integration + 144 other). Standalone `dark_mode_parser.py` with 6 sub-validators, `rules/dark_mode.yaml` (16 rules, 6 groups), 16 custom check functions, Dark Mode agent L3 skill file.

### ~~11.6 Spam Score Check — Production Trigger Database~~ DONE
**What:** Expand from 10 hardcoded trigger phrases to 50+ weighted triggers with case-insensitive word-boundary matching. Add formatting heuristics (excessive punctuation, all-caps words, obfuscation patterns). Current implementation misses most real spam patterns.
**Why:** Emails that pass current check may hit spam filters in Gmail, Outlook, Yahoo. SpamAssassin uses 100+ content rules. A flagged email wastes the entire campaign investment.
**Implementation:**
- ~~Rewrite `app/qa_engine/checks/spam_score.py`~~
- ~~**Trigger database**: Move triggers to `app/qa_engine/data/spam_triggers.yaml` — 50+ phrases with weights (0.05-0.30) and categories (urgency, money, action, clickbait)~~
- ~~**Case-insensitive word boundary matching**: Use `re.compile(rf"\b{trigger}\b", re.IGNORECASE)` — no more false positives from substrings~~
- ~~**Formatting heuristics**: Detect excessive punctuation (3+ `!` or `?`), all-caps words (>3 consecutive), mixed case obfuscation ("fR33", "d1scount")~~
- ~~**Subject line awareness**: If HTML contains `<title>` or known subject line meta, score it separately (subject is 3x more spam-prone)~~
- ~~**Weighted scoring**: `score = 1.0 - sum(trigger_weights)`, pass if score ≥ configurable threshold (default 0.5)~~
- ~~**Detail reporting**: List every matched trigger with weight and category for user transparency~~
**Security:** Trigger database is static YAML, not user-modifiable. Regex patterns are pre-compiled at module load.
**Verify:** ~~Test: clean copy (1.0), "Buy Now" (deducted), "FREE SHIPPING!!!" (multiple deductions), obfuscated "FR33" (caught), edge case "guarantee" in legitimate context (low weight).~~ 353/353 QA tests pass (11 spam tests). `data/spam_triggers.yaml` (59 triggers, 7 categories), `rules/spam_score.yaml` (6 rules, 4 groups), 6 custom check functions, rule engine integration.

### ~~11.7 Link Validation — HTML Parser + URL Format Check~~ DONE
**What:** Replace fragile regex extraction with proper HTML parser link extraction. Add URL format validation, ESP template variable syntax checking, and empty href detection.
**Why:** Current regex breaks on complex href syntax (mixed quotes, newlines, encoded characters). Malformed links cause broken emails that look unprofessional. ESP template variables like `{{ url }}` need syntax validation.
**Implementation:**
- Rewrite `app/qa_engine/checks/link_validation.py` using HTML parser
- **Proper extraction**: Parse all `<a>` tags, extract `href` attribute value properly (handles quotes, encoding)
- **URL format validation**: Use `urllib.parse.urlparse()` — verify scheme, netloc, path are well-formed
- **ESP template validation**: Detect `{{ }}` (Liquid), `%%[ ]%%` (AMPscript), `<%= %>` (JSSP). Validate balanced delimiters
- **Empty href detection**: Flag `href=""`, `href="#"` (except intentional anchors), `href="javascript:"`
- **URL encoding**: Flag unencoded spaces, special characters that will break in email clients
- **Tracking pixel whitelist**: Don't flag known tracking pixel patterns (1x1 images, `open.gif` etc.)
- Scoring: -0.15 per broken link, -0.10 per HTTP link, -0.05 per empty/suspicious href
**Security:** No HTTP requests to validate links (avoid SSRF). Validation is syntax-only.
**Verify:** Test: all valid HTTPS links (1.0), HTTP link (deducted), malformed URL (deducted), empty href (deducted), valid Liquid template var (not flagged), unbalanced `{{ url }` (flagged).

### ~~11.8 File Size Check — Multi-Client Thresholds~~ DONE
**What:** Extend beyond Gmail-only 102KB threshold to include client-specific limits from the ontology. Add content breakdown analysis (markup vs styles vs images).
**Why:** Emails may pass Gmail's threshold but clip in Yahoo (75KB) or hit issues in other clients. Without breakdown analysis, developers don't know what to trim.
**Implementation:**
- Update `app/qa_engine/checks/file_size.py`
- **Client-specific thresholds**: Load from ontology or config: Gmail (102KB), Yahoo (~75KB), Outlook.com (~100KB). Report per-client pass/fail
- **Content breakdown**: Calculate size of: inline styles, HTML markup (minus styles), embedded images (base64), total. Report as percentages
- **Gzip estimate**: Calculate gzip compressed size as secondary metric (actual transfer size)
- **Actionable guidance**: If over threshold, identify largest contributors: "Inline styles: 45KB (44%) — consider external stylesheet or removing unused rules"
- Scoring: 1.0 if under all client thresholds, deduct based on most impacted client's overage
**Security:** Read-only size calculation. No file system access.
**Verify:** Test: small HTML (1.0), 80KB HTML (passes Gmail, flags Yahoo), 110KB HTML (fails multiple), breakdown percentages are accurate.

### ~~11.9 Image Optimization — Comprehensive Validation~~ DONE
**What:** Upgrade from first-image-only dimension check to all-image validation with format analysis, dimension value validation, and tracking pixel detection.
**Why:** Current check only catches the first missing dimension and only flags BMP format. WebP has limited email client support. Invalid dimension values (`width="auto"`, `width="0"`) cause layout breaks.
**Implementation:**
- Rewrite `app/qa_engine/checks/image_optimization.py` using HTML parser
- **All images**: Check every `<img>` tag, not just the first. Report per-image results
- **Dimension validation**: Verify `width` and `height` are positive integers, < 5000px, realistic aspect ratios. Flag `auto`, `100%`, negative values
- **Format support**: Flag formats with limited email support — WebP (poor), SVG (partial), BMP (never), AVIF (none). Recommend JPEG/PNG/GIF
- **Tracking pixels**: Detect 1x1 images — don't flag for missing dimensions (legitimate pattern)
- **Retina detection**: If `width` attribute differs significantly from intrinsic width hint, note potential retina image
- Scoring: -0.15 per image missing dimensions, -0.10 per unsupported format, cap at 0.0
**Security:** No image fetching (avoid SSRF). Attribute analysis only.
**Verify:** Test: all images with dimensions (1.0), missing dimensions on 3 images (deducted), WebP format (flagged), 1x1 tracking pixel without dimensions (not flagged), `width="auto"` (flagged).

### ~~11.10 CSS Support Check — Syntax Validation & Vendor Prefixes~~ DONE
**What:** Add CSS syntax validation and vendor prefix detection to the existing ontology-powered check. Current check scans for unsupported properties but doesn't catch malformed CSS or vendor prefixes that may not work.
**Why:** Malformed CSS rules silently fail in email clients. Vendor prefixes (`-webkit-`, `-moz-`) have inconsistent email client support but aren't in the ontology. Full issue list truncation at 10 hides real problems.
**Implementation:**
- Extend `app/qa_engine/checks/css_support.py`
- **CSS syntax validation**: Parse CSS blocks with `cssutils` or regex-based validator. Flag malformed rules (unclosed braces, missing semicolons, invalid property names)
- **Vendor prefix detection**: Flag `-webkit-`, `-moz-`, `-ms-`, `-o-` prefixes. Cross-reference with ontology for actual support data
- **Full issue reporting**: Remove 10-issue truncation. Return all issues in `details` field. Frontend can paginate
- **External stylesheet detection**: If `<link rel="stylesheet">` found, flag it (most email clients strip external CSS)
- Scoring: existing ontology scoring + deductions for syntax errors (-0.1 each) and unsupported vendor prefixes (-0.05 each)
**Security:** CSS parsing is read-only. No external fetches for linked stylesheets.
**Verify:** Test: valid CSS with supported properties (1.0), unsupported `display: flex` (deducted per ontology), malformed CSS `color: ` with no value (flagged), vendor prefix `-webkit-transform` (flagged), external stylesheet (flagged).

### ~~11.11 Brand Compliance Check — Per-Project Rules Engine~~ DONE
**What:** Replace the always-pass placeholder with a configurable brand rules engine. Validate colors, typography, logo presence, and footer requirements against per-project brand guidelines.
**Why:** Brand compliance is currently zero-enforced. Off-brand emails reaching clients damages credibility. This is the only check that's completely non-functional.
**Implementation:**
- Rewrite `app/qa_engine/checks/brand_compliance.py`
- Create `BrandRules` Pydantic model: `allowed_colors: list[str]`, `required_fonts: list[str]`, `required_elements: list[str]` (e.g., "footer", "logo"), `forbidden_patterns: list[str]`
- Load brand rules from project config (new `brand_rules` JSON column on `Project` model, or separate `BrandProfile` model)
- **Color validation**: Extract all CSS colors (hex, rgb, rgba, named), validate against brand palette. Flag off-brand colors with severity
- **Typography validation**: Extract font-family declarations, validate against brand-approved fonts
- **Required elements**: Check for required sections (footer with legal text, logo image, unsubscribe link)
- **If no brand rules configured**: Return `passed=True` with "No brand rules configured — set up brand profile for enforcement" (backward-compatible)
- Scoring: -0.2 per off-brand color, -0.15 per wrong font, -0.25 per missing required element
**Security:** Brand rules are project-scoped, validated by Pydantic. No code execution.
**Verify:** Test: HTML matching brand rules (1.0), off-brand color (deducted), wrong font (deducted), missing footer (deducted), no brand rules configured (1.0 with info message). Existing tests unchanged.
**Delivered:** `brand_analyzer.py` (CSS color/font extraction, required element detection, cached analysis); `rules/brand_compliance.yaml` (7 rules, 5 groups); rewritten `checks/brand_compliance.py` as rule engine wrapper; 7 custom check functions in `custom_checks.py`; backward-compatible (empty rules → pass); 27 new tests (12 analyzer + 15 integration).

### ~~11.12 New Check — Personalisation Syntax Validation (Check #11)~~ DONE
**What:** Add an 11th QA check that validates ESP-specific template syntax: Liquid (Braze), AMPscript (SFMC), JSSP (Adobe Campaign). No existing check covers personalisation correctness. Agent eval shows **58% logic match failure** for Personalisation agent.
**Why:** Broken template syntax causes runtime errors in ESPs — variables don't render, conditionals break, fallbacks fail. This is invisible until the email is sent to real subscribers. Catching syntax errors in QA prevents broken personalisation in production.
**Implementation:**
- ~~Create `app/qa_engine/checks/personalisation_syntax.py`~~
- ~~Add to `ALL_CHECKS` list in service~~
- ~~**Auto-detect platform**: Scan for `{{ }}` (Liquid), `%%[ ]%%` (AMPscript), `<%= %>` (JSSP). If none found, return `passed=True` ("No personalisation detected")~~
- ~~**Liquid validation**: Balanced `{% if %}...{% endif %}`, `{% for %}...{% endfor %}`, valid `{{ var | filter }}` syntax, `{% unless %}...{% endunless %}`~~
- ~~**AMPscript validation**: Balanced `%%[...]%%` blocks, valid function syntax (`Lookup()`, `Set @var`), `IF...ENDIF` balance~~
- ~~**JSSP validation**: Balanced `<%= %>` blocks, proper escaping~~
- ~~**Fallback detection**: For each dynamic variable, check if a default/fallback is provided (e.g., `{{ name | default: "there" }}`)~~
- ~~**Cross-platform conflict**: Flag if multiple ESP syntaxes detected in same HTML (likely error)~~
- ~~Scoring: -0.2 per unbalanced tag pair, -0.15 per missing fallback, -0.1 per syntax error~~
**Security:** Pure syntax parsing, no template execution. No variable interpolation.
**Verify:** ~~Test: valid Liquid with fallbacks (1.0), unbalanced `{% if %}` (deducted), missing fallback on `{{ first_name }}` (deducted), valid AMPscript (1.0), mixed Liquid+AMPscript (flagged). `make test` passes.~~

### ~~11.13 Outlook Fixer Agent — MSO Diagnostic Validator~~ DONE
**What:** Add deterministic MSO validation to the Outlook Fixer agent service. Before returning HTML, programmatically verify MSO conditional balance and VML nesting. Reuse the `validate_mso_conditionals()` function from 11.4. Current eval: **50% MSO conditional correctness failure**.
**Why:** LLMs consistently struggle with MSO conditional syntax — they see `<!--[if mso]>` as incomplete comments and "fix" them. A post-generation validator catches these errors before the agent returns output, converting a 50% failure to near-zero.
**Implementation:**
- Import `validate_mso_conditionals()` from `app/qa_engine/checks/fallback.py` into `app/ai/agents/outlook_fixer/service.py`
- After LLM generates HTML, call validator. If issues found:
  - Attempt programmatic fix: re-balance conditionals, inject missing namespaces
  - If programmatic fix insufficient, retry LLM with explicit error context: "Your output has 2 unbalanced MSO conditionals at positions X, Y. Fix these specific issues."
  - Max 1 programmatic retry to avoid infinite loops
- Update Outlook Fixer SKILL.md `mso_conditionals.md` with explicit pair-balance rules and common LLM mistakes
- Emit validator results in `AgentHandoff.warnings` for downstream agents
**Security:** Validator is read-only analysis. Programmatic fixes are limited to injecting closing tags and namespace attributes.
**Verify:** `make eval-run --agent outlook_fixer` shows MSO conditional pass rate improvement from 50% to 85%+. Manual test: intentionally unbalanced MSO HTML → agent fixes it. Existing tests pass.

### ~~11.14 Dark Mode Agent — Deterministic Meta Tag Injector~~ DONE
**What:** Add deterministic meta tag injection to the Dark Mode agent service. Before returning HTML, check `<head>` for both required meta tags and inject if missing. Current eval: **50% meta tag failure**.
**Why:** The agent forgets one of the two required meta tags ~50% of the time. A simple programmatic check + inject eliminates this failure mode entirely without relying on the LLM.
**Implementation:**
- In `app/ai/agents/dark_mode/service.py`, after LLM generation:
  - Parse HTML, find `<head>` section
  - Check for `<meta name="color-scheme" content="light dark">` — inject if missing
  - Check for `<meta name="supported-color-schemes" content="light dark">` — inject if missing
  - Inject at end of `<head>` (before `</head>`) to avoid disrupting existing content
- Update Dark Mode SKILL.md with explicit meta tag checklist
- Add color coherence validation: extract light/dark color pairs, flag white-on-white or black-on-black combinations
**Security:** Meta tag injection is adding standard HTML tags to `<head>`. No script injection possible.
**Verify:** `make eval-run --agent dark_mode` shows meta tag pass rate improvement from 50% to 95%+. Test: HTML without meta tags → agent adds them. HTML with both tags → no change.

### ~~11.15 Scaffolder Agent — MSO-First Generation~~ DONE
**What:** Update Scaffolder SKILL.md and service to generate MSO-correct HTML from the first attempt. Load Outlook Fixer's MSO patterns as reference context. Current eval: **58% MSO conditional failure** — the scaffolder should never generate broken MSO.
**Why:** If the scaffolder generates correct MSO from the start, the entire blueprint pipeline avoids one retry loop. MSO fixes are the most common recovery router destination. Prevention > correction.
**Implementation:**
- Update `app/ai/agents/scaffolder/SKILL.md` with mandatory MSO section:
  - Every template MUST include MSO centering table wrapper
  - MUST include `xmlns:v` and `xmlns:o` on `<html>` when VML used
  - MUST balance all conditional comments
  - Reference Outlook Fixer's `mso_conditionals.md` patterns
- In `app/ai/agents/scaffolder/service.py`, load Outlook Fixer's L3 SKILL files into system prompt context (top 15 MSO patterns)
- Add same `validate_mso_conditionals()` post-generation check as 11.13
- Emit MSO validation status in `AgentHandoff.decisions` so downstream agents know MSO is verified
**Security:** Cross-agent SKILL file loading is read-only from local filesystem.
**Verify:** `make eval-run --agent scaffolder` shows MSO conditional pass rate improvement from 58% to 85%+. Blueprint pipeline test: scaffolder output passes fallback QA check on first attempt.

### ~~11.16 Personalisation Agent — Per-Platform Syntax Validator~~ DONE
**What:** Add deterministic per-platform template syntax validation to the Personalisation agent service. Before returning HTML, validate balanced tags and fallback presence. Current eval: **58% logic match failure**.
**Why:** LLMs generate plausible-looking but syntactically broken template code. Liquid `{% if %}` without `{% endif %}`, AMPscript `%%[` without `]%%`. A programmatic validator catches these mechanical errors.
**Implementation:**
- `ESPPlatform` expanded from 3 → 7 platforms (added klaviyo, mailchimp, hubspot, iterable)
- `SKILL_FILES` expanded from 4 → 8 L3 skill files (all 7 ESP skills + fallback_patterns)
- `platform_map` expanded to 7 entries; cross-platform references for all 7 ESPs with specific keywords
- `format_syntax_warnings(html)` shared helper in `service.py` — calls `analyze_personalisation()` from `personalisation_validator.py`, formats warnings with `[error]`/`[warning]` prefixes
- `PersonalisationService._post_process()` override with `contextvars.ContextVar` thread-safe warning storage
- `PersonalisationResponse.syntax_warnings` field exposes validator findings via API
- `PersonalisationNode` in blueprint emits `warnings=tuple(syntax_warnings)` in `AgentHandoff` for Recovery Router
- SKILL.md updated with post-generation validation annotations and balanced-tag emphasis
- 28 unit tests (formatter, service post-process, contextvar, all 7 platforms, all 8 skills, cross-platform refs)
**Security:** Syntax validation only. No template rendering or variable interpolation.
**Verify:** `make check` passes. All 28 tests pass. mypy + pyright clean (0 errors).

### ~~11.17 Code Reviewer Agent — Actionability Framework~~ DONE
**What:** Update Code Reviewer SKILL.md to require "change X to Y" format for every suggestion. Current eval: **67% suggestion actionability** — suggestions are too vague.
**Why:** Vague suggestions like "simplify CSS" don't help agents or developers. Actionable suggestions like "Replace `display: flex` with `<table>` layout (unsupported in Outlook 2019)" can be auto-applied.
**Implementation:**
- Update `app/ai/agents/code_reviewer/SKILL.md`:
  - Every suggestion MUST include: property/element name, current value, recommended replacement, affected clients
  - Format: `ISSUE: {property} on line {N} | CURRENT: {value} | FIX: {replacement} | CLIENTS: {list}`
  - Reference ontology data in suggestions (link CSS property to client support matrix)
- Expand "email allowlist" in SKILL.md: add `mso-` prefixes, `[data-ogsc]` selectors, MSO conditionals, VML elements as known-good patterns
- In service, validate output format: if suggestions don't match actionable format, retry with format correction prompt
- Add 75%+ coverage completeness target: reviewer should flag issues in at least 75% of categories (CSS, HTML structure, accessibility, performance)
**Security:** Output format validation is string matching. No code execution.
**Verify:** `make eval-run --agent code_reviewer` shows suggestion actionability improvement from 67% to 85%+. Manual review: every suggestion has concrete before/after values.

### ~~11.18 Accessibility Agent — Alt Text Quality Framework~~ DONE
**What:** Update Accessibility Auditor SKILL.md with structured alt text generation rules. Current eval: **70% alt text quality, 70% screen reader compatibility**.
**Why:** Generic alt text ("image", "photo") is worse than no alt text — it clutters screen readers without conveying information. The agent needs clear rules for decorative vs informative images and quality criteria.
**Implementation:**
- Update `app/ai/agents/accessibility/SKILL.md` with alt text framework:
  - **Decorative images** (borders, spacers, backgrounds): `alt=""`
  - **Content images** (product shots, photos): 5-15 words, describe what's shown, not the file name
  - **Functional images** (buttons, icons, CTAs): describe the action ("Submit form", "Download PDF"), not appearance
  - **Logo images**: company name only ("Acme Corp"), not "Acme Corp logo image"
  - **Complex images** (charts, infographics): `aria-describedby` pointing to text description
- Add WCAG AA contrast ratio rules to SKILL.md: 4.5:1 for normal text, 3:1 for large text (≥18pt or ≥14pt bold)
- Update service to validate alt text quality before returning: reject single-word alts, reject generic terms, verify length bounds
- Add screen reader landmark recommendations: `role="banner"`, `role="main"`, `role="contentinfo"` for email structure
**Security:** Alt text generation from image context. No image fetching or processing.
**Verify:** `make eval-run --agent accessibility` shows alt text quality improvement from 70% to 85%+. Test: image with no context → descriptive alt generated. Decorative spacer → `alt=""`.

### ~~11.19 Content Agent — Length Guardrails~~ DONE
**What:** Add token/character limits per operation type to the Content agent. Current eval: **71% length appropriate** — expand operations overshoot, shorten operations remove critical info.
**Why:** Email copy has strict length constraints. Subject lines (50 chars ideal), preheaders (85-100 chars), CTAs (2-5 words). Without guardrails, the LLM generates copy that doesn't fit.
**Implementation:**
- Update `app/ai/agents/content/SKILL.md` with length rules per operation:
  - Subject line: 30-60 chars (50 ideal), no truncation in mobile preview
  - Preheader: 85-100 chars (fills preview pane, prevents body text leak)
  - CTA text: 2-5 words, action verb first ("Get Started", "Download Now")
  - Body copy: respect original length ±20% for tone/rewrite operations
  - Expand: max 150% of original length
  - Shorten: min 50% of original, preserve all key information points
- In service, post-generation length validation:
  - If subject > 60 chars, retry with explicit "shorten to under 60 characters" instruction
  - If CTA > 5 words, retry with word count constraint
  - Max 1 retry per length violation
- Add excessive punctuation detection: strip `!!!`, `???`, `...` patterns from generated copy
**Security:** Length validation is character counting. No content injection.
**Verify:** `make eval-run --agent content` shows length appropriate improvement from 71% to 85%+. Test: "expand this paragraph" → output ≤ 150% original length. Subject line generation → ≤ 60 chars.

### ~~11.20 Recovery Router — Enriched Failure Context~~ DONE
**What:** Upgrade recovery router to pass detailed, structured failure information to fixer agents instead of generic check names. Currently sends `"fallback: failed"` — should send `"fallback: 2 unbalanced MSO conditionals at lines 45, 89; VML orphan at line 112"`.
**Why:** Agents with specific error context fix issues 3x faster than agents with generic "this check failed" messages. Reduces retry loops from 2-3 to 1. This amplifies every individual check improvement.
**Implementation:**
- Update `app/ai/blueprints/nodes/recovery_router_node.py`
- QA check results already contain `details: str` — pass the full details string (not just check name) to recovery context
- Structure failure context as: `{check_name: str, score: float, details: str, suggested_agent: str, priority: int}`
- Order failures by priority (MSO > accessibility > dark mode > spam > links > images > size)
- Inject into `NodeContext.metadata["qa_failure_details"]` — list of structured failure objects
- Recovery router selects agent based on highest-priority failure, but passes ALL failure details so agent can fix multiple issues in one pass
- Add cycle detection enhancement: if same check failed with same details twice, escalate to scaffolder (full regeneration) instead of same fixer
- **Scoped retry constraints:** On retry, constrain what each agent can modify to prevent cascading failures. Scaffolder: HTML structure only (no new CSS frameworks). Dark mode: CSS only (`<style>` + inline styles, no HTML restructuring). Content: text nodes + attributes only (`alt`, `title`, `aria-label`). Outlook fixer: add MSO/VML only (no HTML removal). Enforce via prompt constraints on retry + output diff validation (reject changes outside allowed scope).
**Security:** Failure details are derived from QA check output (already sanitised). No user input injection.
**Verify:** Blueprint test: intentionally broken HTML with 3 QA failures → recovery router passes all 3 with details → fixer agent receives structured context. Fewer retry loops than current generic routing. Retry output diff stays within allowed scope per agent.

### ~~11.21 Deterministic Micro-Judges — Codify Judge Criteria into QA Checks~~ DONE
**What:** Extract the subset of eval judge criteria that can be validated deterministically and add them as enhanced QA checks. ~60% of judge criteria across all 9 agents map to codifiable rules (e.g., "uses nested tables with 600px max-width" from ScaffolderJudge, "balanced MSO conditionals" from OutlookFixerJudge). This gives judge-quality detection at QA-gate speed (0 tokens, <50ms per check).
**Why:** Items 11.2–11.12 already upgrade individual QA checks. This task explicitly maps each judge criterion to its deterministic equivalent, ensuring QA checks cover what judges catch. After this, the QA gate catches ~90% of what LLM judges would flag, making inline judges (11.23) only necessary for the remaining ~10% that requires LLM reasoning (brief fidelity, tone accuracy, copy quality).
**Implementation:**
- Create `app/qa_engine/judge_criteria_map.py` — mapping of `{agent: {criterion: qa_check_name | None}}`:
  - ScaffolderJudge: `email_layout_patterns` → html_validation (11.2), `mso_conditionals` → fallback (11.4), `dark_mode_readiness` → dark_mode (11.5), `accessibility_baseline` → accessibility (11.3), `brief_fidelity` → None (requires LLM)
  - DarkModeJudge: `html_preservation` → html_validation, `outlook_selector_completeness` → fallback, `meta_and_media_query` → dark_mode, `contrast_preservation` → accessibility, `color_coherence` → None (requires LLM)
  - ContentJudge: `spam_avoidance` → spam_score (11.6), `operation_compliance` → None, `copy_quality` → None, `tone_accuracy` → None, `security_and_pii` → brand_compliance (11.11)
  - (Map remaining 6 agents similarly)
- For each mapped criterion, verify the upgraded QA check (11.2–11.12) covers the judge's specific validation logic. Add sub-checks where gaps exist.
- Add `make eval-qa-coverage` command: runs all judges + QA checks on same test set, reports criterion-vs-check agreement rate. Target: >85% agreement on mapped criteria.
- Update recovery router (11.20) — use criteria map to route QA failures to the correct fixer agent with judge-criterion-level specificity
**Security:** No new attack surface — extends existing deterministic checks only.
**Verify:** Run `make eval-qa-coverage` on all 9 agents' synthetic data. For each mapped criterion, QA check agrees with judge verdict >85% of the time. Unmapped criteria (brief_fidelity, tone_accuracy, etc.) documented as "LLM-only" — these are what 11.23 inline judges cover.

### 11.22 Template-First Hybrid Architecture — From 16.7% to 99%+ Overall Pass Rate

**What:** Replace LLM-generates-everything architecture with a hybrid model where deterministic code generates all structural HTML and the LLM makes content/design decisions only. The LLM never writes a `<table>` tag, `<!--[if mso]>` conditional, or `<meta>` tag — it selects templates, fills content slots, and chooses design tokens. Deterministic Python assembles the final HTML from tested, pre-validated building blocks.

**Why:** Current 16.7% pass rate (36 traces via claude-sonnet-4) fails because the LLM is asked to generate the hardest HTML that exists — table layouts, MSO conditionals, VML, 25-client compatibility. Even frontier models struggle (Sonnet: 0% on MSO conditionals, 8% on accessibility, 10% on html_preservation). The insight: **if deterministic code generates every structural element, QA checks are validating code we wrote and tested, not LLM output.** This eliminates entire failure categories by construction rather than correction. No model changes needed — this extracts maximum value from Claude Sonnet/Opus by giving the LLM the job it's actually good at (creative content decisions) and taking away the job it's bad at (syntax-precise structural HTML). Local/weaker models are not viable — email HTML generation is one of the hardest LLM tasks; substituting models would degrade quality further.

**Target ceiling:** 99%+ overall pass rate. Structural checks: deterministic guarantees via golden templates + cascading repair. Semantic quality (tone, copy): structured output schemas with per-field retry.

**Dependencies:** 11.1–11.21 (upgraded QA checks + deterministic micro-judges provide better feedback signals). Phase 8-9 (ontology for client compatibility data). Phase 7 (SKILL.md, BaseAgentService). Phase 2 (component library for golden template building blocks).

**Detailed implementation plan:** `.agents/plans/11.22-deterministic-agent-architecture.md`

**Key decisions:**
- **Golden templates:** Maizzle source (`app/ai/templates/maizzle_src/`) + pre-compiled HTML (`app/ai/templates/library/`). Templates extend existing `main.html` layout.
- **Slot markers:** `data-slot="{id}"` attributes on HTML elements (survives lxml parsing, easy to target).
- **Template metadata:** YAML companion files in `_metadata/*.yaml` (decoupled from HTML).
- **Structured output:** Provider-agnostic — Anthropic adapter uses tool_use, OpenAI adapter uses response_format, fallback to JSON-in-prompt + Pydantic validation. `CompletionResponse.parsed` field.
- **Repair pipeline:** Lives in `app/qa_engine/repair/` (paired with QA checks). 7 deterministic stages, reuses existing `mso_repair.py` and `meta_injector.py`.
- **Section blocks:** Reuse existing Maizzle components (`email-templates/components/`) as starting material, harden with MSO/a11y/dark mode for QA compliance.
- **Backward compatibility:** `output_mode: Literal["html", "structured"] = "html"` on all agent requests. `_process_structured()` hook in `BaseAgentService`.

**Execution order (4 weeks):**
| Week | Subtasks (parallel where possible) | Milestone |
|------|-------------------------------------|-----------|
| W1 | 11.22.1 + 11.22.2 (parallel — no deps) | Foundation: templates + schemas |
| W2 | 11.22.3 + 11.22.4 (depend on W1) | **M1: 70%** — pipeline + auto-repair |
| W3 | 11.22.5 + 11.22.6 (depend on W1-W2) | **M2: 85%** — architect prompts + context budget |
| W4 | 11.22.7 + 11.22.8 (depend on W1-W3) | **M3: 95%** — 5 HTML agents migrated |
| Ongoing | 11.22.9 (continuous) | **M4: 99%+** — iteration on failure modes |

**Architecture pattern (PIV loop):** Inspired by Stripe Minions + deterministic agentic coding workshop. LLM makes decisions (structured JSON) → deterministic code assembles HTML → deterministic QA validates → LLM retries with exact errors. Each agent gets per-agent decision schema (`DarkModePlan`, `OutlookFixPlan`, `AccessibilityPlan`, `PersonalisationPlan`, `CodeReviewPlan`, `ContentPlan`). Backward compatible via `output_mode: Literal["html", "structured"]` flag on each agent's request schema.

**Files (~62 new, ~30 modified):** Templates (~20 HTML + 4 Python), schemas (8 Python), pipeline (3 Python), repair stages (9 Python), SKILL.md rewrites (7 + 5 prompt.py), composer (15 HTML + 2 Python), agent migrations (14 service.py + nodes), tests (5 Python).

#### ~~11.22.1 Golden Template Library — Pre-Validated Email Skeletons~~ DONE
**What:** Build 15 battle-tested email templates (Maizzle source + pre-compiled HTML) covering ~95% of real campaign briefs. Each template passes all 11 QA checks with score >= 0.9. Templates use `data-slot="{id}"` attribute markers on HTML elements — the LLM fills slots, never generates structural HTML.
**Why:** Highest-impact change. MSO conditionals go from 0% to ~99% (pre-written, pre-tested). Dark mode ~50% to ~99% (meta tags, media queries, Outlook selectors pre-wired). The LLM's job shrinks from "generate a complete email" to "pick a template and fill in the blanks."
**Implementation:**
- Create `app/ai/templates/` directory with dual-format template library:
  - `app/ai/templates/models.py` — `GoldenTemplate`, `TemplateSlot`, `TemplateMetadata` frozen dataclasses. `SlotType` Literal (headline/body/cta/image/etc), `LayoutType` Literal (newsletter/promotional/transactional/event/retention/announcement/minimal)
  - `app/ai/templates/registry.py` — `TemplateRegistry` class: `get(name)`, `search(layout_type, column_count, has_hero)`, `fill_slots(template, fills)`, `list_for_selection() -> list[TemplateMetadata]`. Module-level `get_template_registry()` singleton
  - `app/ai/templates/compiler.py` — `compile_template(name)` / `compile_all()` via maizzle-builder sidecar HTTP call. Caches compiled HTML in `library/`
  - `app/ai/templates/maizzle_src/` — 15 Maizzle source templates extending `src/layouts/main.html`, using `<component>` includes
  - `app/ai/templates/library/` — Pre-compiled HTML (committed, works without sidecar)
  - `app/ai/templates/library/_metadata/` — YAML companion files per template (name, display_name, layout_type, column_count, sections, ideal_for, description, slot definitions with slot_id/slot_type/selector/required/max_chars/placeholder)
- Build 15 initial templates:
  - **Newsletter** (2): single-column, two-column
  - **Promotional** (3): hero image, product grid, 50/50 split
  - **Transactional** (3): receipt, shipping, welcome/onboarding
  - **Event** (2): invitation, reminder
  - **Retention** (2): win-back, survey
  - **Announcement** (2): product launch, company news
  - **Minimal** (1): text-heavy minimal design
- Each template must:
  - Extend `src/layouts/main.html` (inherits MSO skeleton, dark mode meta, VML/Office namespaces)
  - Use `data-slot="{id}"` attributes on all content elements
  - Have `role="presentation"` on all layout tables, `alt` on all images, `scope` on `<th>`
  - Pass all 11 QA checks with score >= 0.9 (verified by parametrized pytest)
  - Use fluid hybrid layout (600px max-width, responsive to 320px)
- QA regression test: `app/ai/templates/tests/test_templates.py` — parametrized over all templates × all 11 checks
**Security:** Templates are static files in the repo. No user input in template structure. Slot fills validated by `TemplateSlot.max_chars` before assembly. HTML slot content sanitised by `sanitize_html_xss()`.
**Verify:** `make test -k test_templates` — all 15 templates pass all 11 QA checks >= 0.9. `make types` — zero errors.

#### ~~11.22.2 Structured Output Schemas — LLM Returns JSON, Not HTML~~ DONE
**What:** Define typed dataclass schemas for each agent's decisions (not HTML output). Extend LLM provider protocol for provider-agnostic structured output. Add `output_mode` flag to all agent requests and `_process_structured()` hook to `BaseAgentService`.
**Why:** Structured output is dramatically more reliable than freeform generation. JSON is parseable, validatable, and retryable at the field level — a malformed subject line doesn't require regenerating the entire email. Provider-agnostic approach lets each adapter use its best mechanism (Anthropic→tool_use, OpenAI→response_format).
**Implementation:**
- Create `app/ai/agents/schemas/` — 7 decision dataclass files:
  - `build_plan.py` — `EmailBuildPlan` (master scaffolder output): `TemplateSelection` (template_name, reasoning, section_order for compose, fallback), `SlotFill` (slot_id, content, is_personalisable), `DesignTokens` (primary/secondary/background/text colors, font families, border_radius, button_style), `SectionDecision` (section_name, background_color, hidden)
  - `dark_mode_plan.py` — `DarkModePlan`: `ColorMapping` (light/dark color, selector, property), meta_tag_strategy, outlook_override_strategy, preserve_brand_colors
  - `outlook_plan.py` — `OutlookFixPlan`: `MSOFix` (issue_type, location_hint, fix_description, fix_html), add_namespaces, add_ghost_tables
  - `accessibility_plan.py` — `AccessibilityPlan`: `AltTextDecision` (img_selector, category, alt_text, is_decorative), `A11yFix` (issue_type, selector, fix_value)
  - `personalisation_plan.py` — `PersonalisationPlan`: `PersonalisationTag` (slot_id, tag_syntax, fallback, is_conditional), `ConditionalBlock` (condition, true/false content, platform_syntax)
  - `code_review_plan.py` — `CodeReviewPlan`: formalises existing `CodeReviewIssue` as `CodeReviewFinding` (rule_name, severity, responsible_agent, current/fix values, selector, is_actionable)
  - `content_plan.py` — `ContentPlan`: `ContentAlternative` (text, tone, char/word count, reasoning), selected_index
- Extend `app/ai/protocols.py` — add `parsed: dict[str, object] | None = None` field to `CompletionResponse`
- Extend adapters (provider-agnostic):
  - `app/ai/adapters/anthropic.py` — detect `output_schema` in kwargs → define tool with schema, set `tool_choice`, parse tool_use response → `CompletionResponse.parsed`
  - `app/ai/adapters/openai_compat.py` — detect `output_schema` in kwargs → set `response_format` with json_schema → parse response → `CompletionResponse.parsed`
  - Both pass through gracefully when `output_schema` not provided (no behavioral change)
- Extend `app/ai/agents/base.py`:
  - Add `output_mode_default`, `_output_mode_supported` class attrs
  - Split `process()` into `_process_html()` (current) + `_process_structured()` (new hook, raises `NotImplementedError` by default)
  - Add `_get_output_mode(request)` helper
- Add `output_mode: Literal["html", "structured"] = "html"` to all 5 HTML agent request schemas
- Add `plan: dict[str, object] | None = None` to all 5 HTML agent response schemas
**Security:** JSON schema enforced by frozen dataclasses. Slot fill content sanitised by `sanitize_html_xss()` during assembly. Design token hex values validated. No raw dict access.
**Verify:** `make types` — zero errors. `make test` — existing tests pass (backward compatible, output_mode defaults to "html").

#### ~~11.22.3 Multi-Pass Generation Pipeline — Decompose for Reliability~~ DONE
**What:** Replace the single LLM call with 3 focused passes, each with a narrow scope and independent validation. Errors in one pass don't cascade — a bad CTA doesn't require regenerating the layout decision.
**Why:** Compound reliability: if each pass has 95% accuracy, a single pass = 95% overall, but the current single-call approach asks for 10+ correct decisions simultaneously (95%^10 = 60%). Three focused passes with 3-4 decisions each: (95%^4)^3 = 70% worst case, but with per-field retry the effective rate approaches 99%.
**Implementation:**
- Create `app/ai/agents/pipeline.py` — `MultiPassPipeline` orchestrator:
  - **Pass 1 — Layout Analysis** (cheap, Haiku-tier model via `_get_model_tier("lightweight")`):
    - Input: campaign brief
    - Output: `TemplateSelection` — which golden template, reasoning
    - Validation: template_id exists in library, layout matches brief intent
    - Retry: if invalid template_id, retry with available template list
    - Cost: ~500-1,000 tokens
  - **Pass 2 — Content Generation** (quality, Sonnet-tier model via `_get_model_tier("standard")`):
    - Input: brief + selected template's `SlotDef` list (tells LLM exactly what content is needed)
    - Output: `list[SlotFill]` + `subject_line` + `preheader`
    - Validation: all required slots filled, content within `SlotDef.constraints` (char limits, required fields)
    - Retry: per-slot — only regenerate slots that failed validation
    - Cost: ~2,000-4,000 tokens
    - **Parallelisable**: if template has independent slots, generate them in parallel
  - **Pass 3 — Design & Personalisation** (cheap, Haiku-tier):
    - Input: brief + template + filled slots summary
    - Output: `DesignTokens` + `PersonalisationConfig`
    - Validation: hex colors valid, contrast ratio ≥ 4.5:1 (computed deterministically), font stacks valid, ESP variables syntactically correct
    - Retry: if contrast fails, retry with "ensure dark_text on dark_background has ≥4.5:1 contrast ratio"
    - Cost: ~500-1,000 tokens
  - **Assembly** (deterministic, 0 tokens):
    - `assemble_from_plan()` combines all three pass outputs into final HTML
    - Run all 10 QA checks
    - If QA fails: identify which pass produced the failing element, retry ONLY that pass with QA feedback
- Wire into `BaseAgentService` — `MultiPassPipeline` replaces single `_call_llm()` for generation agents
- Existing single-call path preserved behind feature flag `AGENT__USE_MULTI_PASS` (default `True`, set `False` for A/B comparison)
**Security:** Each pass receives only the context it needs (principle of least privilege for LLM context). Pass outputs validated by Pydantic before assembly. No pass has access to credentials or system internals.
**Verify:** Run all 36 eval synthetic cases through multi-pass pipeline. Measure per-pass success rate (target: ≥95% per pass). Measure overall first-attempt QA pass rate (target: ≥85%). Measure token usage (target: ≤ 5,000 tokens total vs ~8,000-15,000 for current single-call). Measure latency (target: ≤ 8s wall time with parallel slots).

#### ~~11.22.4 Cascading Auto-Repair Pipeline — Belt-and-Suspenders Post-Processing~~ DONE
**What:** 7-stage deterministic repair pipeline in `app/qa_engine/repair/` (paired with QA checks). Runs between assembly and QA gate. Each stage is a pure function — no LLM. Wraps existing `mso_repair.py` and `meta_injector.py`. Replaces per-agent post-processing with a unified repair chain.
**Why:** Defense in depth. Golden templates + structured output should yield ~95% QA pass rate. Repair catches remaining structural issues (malformed slot content, edge cases in personalisation injection). The difference between 95% and 99%+.
**Implementation:**
- Create `app/qa_engine/repair/` directory with `RepairStage` Protocol and `RepairPipeline` orchestrator:
  - `pipeline.py` — `RepairPipeline.run(html) -> RepairResult(html, repairs_applied, warnings)`. Sequential stages, failure-safe (stage errors logged, not crashed).
  - `structure.py` — Stage 1: ensure DOCTYPE/html/head/body via lxml parse+serialize. Preserve MSO comments and `data-slot` attrs.
  - `mso.py` — Stage 2: wrap existing `app/ai/agents/outlook_fixer/mso_repair.repair_mso_issues()`. Add namespace injection (`xmlns:v`, `xmlns:o`).
  - `dark_mode.py` — Stage 3: wrap existing `app/ai/agents/dark_mode/meta_injector.inject_missing_meta_tags()`. Ensure `@media (prefers-color-scheme: dark)` block exists.
  - `accessibility.py` — Stage 4: add `lang="en"` if missing, `role="presentation"` on layout tables, `scope="col"` on `<th>`, `alt=""` on images missing alt.
  - `personalisation.py` — Stage 5: count ESP delimiter balance (Liquid `{{`/`}}`, AMPscript `%%`/`%%`). Warn on imbalance (don't auto-close).
  - `size.py` — Stage 6: strip HTML comments (except MSO `<!--[if`), collapse whitespace, remove empty `style=""`.
  - `links.py` — Stage 7: replace empty `href=""` with `href="#"`, warn on `javascript:` hrefs.
- Integrate into `app/ai/blueprints/engine.py` — run after agentic node returns HTML, before QA gate. Store `repair_log` and `repair_warnings` in `run.metadata`.
- Test idempotency: running pipeline twice = same output.
**Security:** All deterministic HTML manipulation via lxml/regex. No external fetches. No LLM calls. No `eval()`.
**Verify:** `make test -k test_repair_pipeline` — each stage independently tested + end-to-end. Pipeline is idempotent. Golden templates unchanged after repair (no-op). `make test` — no regressions.

#### ~~11.22.5 SKILL.md Rewrite — Architect Prompts, Not Generator Prompts~~ DONE
**What:** Add dual-mode structure to all 7 HTML agent SKILL.md files: a `## Output Mode: Structured (JSON)` section with schema examples and a `## Output Mode: HTML (Legacy)` section preserving current instructions. Update `prompt.py` files to detect `output_mode` and load the appropriate section.
**Why:** The prompt must match the architecture — "return JSON decisions" produces fundamentally different (better) output than "generate HTML."
**Implementation:**
- Each SKILL.md gets structured mode section: JSON schema, example input→output pairs, "Do NOT return HTML" instruction
- **Scaffolder**: "Select template + fill slots" with `EmailBuildPlan` schema example
- **Dark Mode**: "Return color mappings" with `DarkModePlan` schema example
- **Outlook Fixer**: "Return MSO fix plan" with `OutlookFixPlan` schema example
- **Accessibility**: "Return a11y fix plan" with `AccessibilityPlan` schema example (alt text decisions + structural fixes)
- **Personalisation**: "Return tag injection plan" with `PersonalisationPlan` schema example
- **Code Reviewer**: Tighten schema compliance (already structured, formalise `CodeReviewPlan`)
- **Content**: Add explicit JSON format spec (already text-based, formalise `ContentPlan`)
- Update `prompt.py` per agent: `build_system_prompt(skills, output_mode)` loads appropriate SKILL.md section
- Use `make eval-skill-test` for each rewrite to A/B compare pass rates
**Security:** SKILL.md files are prompt content only.
**Verify:** `make eval-skill-test AGENT={agent} PROPOSED=...` for each agent. Structured output compliance ≥95%.

#### ~~11.22.6 Context Assembly Optimisation — Token Budget Enforcement~~ DONE
**What:** Optimise what context each agent receives per pass. Multi-pass architecture enables pass-specific context — Pass 1 (layout) needs only the brief, Pass 2 (content) needs brief + slot definitions, Pass 3 (design) needs brief + template palette. No pass needs full SKILL.md + handoff history + failure warnings.
**Implementation:**
- Create `app/ai/agents/context_budget.py`:
  - `ContextBudget` dataclass: `max_tokens: int`, `sections: dict[str, int]` (per-section budgets)
  - `measure_context(prompt: str) -> ContextMetrics` — token counts per section
  - `enforce_budget(context: dict, budget: ContextBudget) -> dict` — trim lowest-priority sections to fit budget
- Per-pass budgets:
  - Pass 1 (layout): 2,000 tokens max (brief + template list summaries)
  - Pass 2 (content): 4,000 tokens max (brief + slot definitions + 2 few-shot examples)
  - Pass 3 (design): 1,500 tokens max (brief + brand guidelines + current template palette)
- **Selective SKILL.md loading**: Load only the L1 section for the current pass. L2/L3 loaded only if Pass fails and retries.
- **Handoff summarisation**: For multi-node blueprint chains, summarise handoffs >2 nodes back to a single paragraph.
- **Failure warning pruning**: Only inject warnings relevant to the current pass (e.g., MSO warnings only in Pass 1 layout selection, not in Pass 2 content generation).
**Security:** No new attack surface. Context trimming is deterministic.
**Verify:** Measure prompt token counts per pass. Target: total across 3 passes ≤ 8,000 tokens (vs current single-call ~10,000-15,000). Per-pass accuracy should not decrease from trimming (same or better signal-to-noise).

#### ~~11.22.7 Novel Layout Fallback — Graceful Degradation for Edge Cases~~ DONE
**What:** Handle the ~5% of briefs that don't match any golden template. Instead of falling back to unreliable full-HTML generation, compose new layouts by combining tested building blocks (sections from golden templates). This is the difference between 95% and 97-99%.
**Why:** Golden templates cover common layouts, but clients occasionally request unusual combinations (e.g., 3-column on mobile, accordion sections, gamification elements). Without a fallback, these briefs either fail or revert to the old unreliable pipeline.
**Implementation:**
- Create `app/ai/templates/composer.py` — `TemplateComposer`:
  - `decompose_templates() -> list[SectionBlock]` — break golden templates into reusable section blocks (hero, text_block, two_col, card_grid, cta, footer, spacer, divider)
  - `SectionBlock` dataclass: `block_type`, `html_skeleton`, `slot_definitions`, `mso_wrapper: bool`, `dark_mode_vars: list[str]`
  - `compose(blocks: list[str], order: list[str]) -> GoldenTemplate` — assemble a new template from section blocks, auto-generate MSO wrappers between adjacent blocks, merge dark mode variables
  - `validate_composition(template: GoldenTemplate) -> list[QACheckResult]` — run QA checks on composed template before use
- Update Scaffolder Pass 1 to support composition:
  - If no golden template matches brief (confidence < 0.7), return `CompositionPlan` instead of `TemplateSelection`
  - `CompositionPlan`: ordered list of `SectionBlock` IDs + per-block slot overrides
  - Assembler builds from `CompositionPlan` using `TemplateComposer.compose()`
- Composed templates validated by QA before slot filling — if composition fails QA, fall back to closest matching golden template with a warning
- Track composition frequency in `traces/` — if >10% of briefs require composition, build new golden templates for the common compositions
**Security:** Section blocks are derived from golden templates (pre-validated). Composition is deterministic concatenation + MSO wrapper generation. No LLM involvement in structural composition.
**Verify:** Create 5 "unusual" briefs that don't match any golden template. Verify: composer produces valid compositions, assembled HTML passes QA, fallback to closest template works when composition fails. Measure: composition QA pass rate ≥90%.

#### ~~11.22.8 Agent Role Redefinition — Tighten Specialisation~~ DONE
**What:** Redefine agent responsibilities to eliminate overlap and match the template-first architecture. Several agents become simpler or unnecessary when templates handle structure.
**Why:** Current agent overlap causes conflicting fixes — Scaffolder generates dark mode, then Dark Mode agent overwrites it. Template-first architecture means each agent owns a specific slice of the `EmailBuildPlan`, with no structural HTML generation.
**Implementation:**
- **Scaffolder**: Template selection + content slot filling only. No HTML generation. Owns Pass 1 + Pass 2.
- **Dark Mode**: Color remapping decisions only. Returns `DesignTokens.dark_*` values. Deterministic code handles all CSS/meta/Outlook injection. Owns Pass 3 color subset.
- **Content**: Subject line, preheader, CTA text, body copy editing. Operates on `SlotFill.body_text` fields only. Separate from Scaffolder (can run independently for copy-only tasks).
- **Outlook Fixer**: Reduced scope — only activated when repair pipeline detects MSO issues that golden templates shouldn't have (indicates template bug or unusual composition). Primarily a diagnostic agent that reports issues rather than generating HTML fixes.
- **Accessibility**: Alt text generation + heading hierarchy validation. Returns structured `{image_id: alt_text}` decisions. Code applies them. Does NOT generate or modify HTML.
- **Personalisation**: ESP variable placement decisions. Returns `PersonalisationConfig`. Code injects syntax-correct variables. Does NOT write Liquid/AMPscript directly.
- **Code Reviewer**: Reviews `EmailBuildPlan` for appropriateness (template choice, slot content quality, design token contrast, personalisation completeness). Does NOT review raw HTML.
- **Knowledge**: Unchanged — RAG Q&A.
- **Innovation**: Prototypes new `SectionBlock` types and `GoldenTemplate` compositions. Tests via `TemplateComposer.validate_composition()`. Does NOT generate freeform HTML.
- Update `app/ai/blueprints/definitions/` — blueprint node sequences reflect new agent scopes. Scaffolder node produces `EmailBuildPlan`, downstream agents modify specific plan fields, final assembly node is deterministic.
**Security:** No change — agents produce structured data, code handles HTML. Attack surface reduced (less raw HTML in LLM output).
**Verify:** Blueprint end-to-end test: brief → Scaffolder (plan) → Content (refine slots) → Dark Mode (dark tokens) → Personalisation (variables) → Assembly (deterministic) → QA → Export. Each agent's output is valid JSON matching its schema. No agent produces raw HTML.

#### 11.22.9 Eval-Driven Iteration Loop — Milestone Tracking to 99%
**What:** Establish the measurement framework for tracking progress from 16.7% to 99%+. Every change in 11.22.1–11.22.8 must be validated by the eval system before merging. Regression detection prevents backsliding.
**Implementation:**
- Define baseline: current `traces/baseline.json` (16.7% overall, per-agent and per-criterion breakpoints)
- After each 11.24.x subtask, run `make eval-run` + `make eval-analysis` + `make eval-regression`
- Use `make eval-skill-test` for every SKILL.md rewrite (A/B comparison)
- Track progress in `traces/improvement_log.jsonl` — append `{date, change_description, agent, criterion, before_rate, after_rate}`
- **Milestone targets:**
  - M1 (after 11.22.1 golden templates + 11.22.2 structured output): 70% overall — structural failures eliminated for template-covered briefs
  - M2 (after 11.22.3 multi-pass): 85% overall — per-field retry catches content generation errors
  - M3 (after 11.22.4 repair pipeline): 95% overall — cascading repair catches remaining structural edge cases
  - M4 (after 11.22.5 SKILL.md rewrites): 97% overall — LLM produces better structured decisions
  - M5 (after 11.22.6 context optimisation + 11.22.7 novel layout fallback): 99%+ structural, ~98% semantic, **99%+ overall**
  - M6 (after 11.22.8 agent redefinition): sustained 99%+ with reduced token cost and latency
- If a change decreases any agent's pass rate by >3 percentage points, revert and investigate
- **Autonomous eval loop:** Implement modify→run→measure→keep/revert cycle for prompt optimization. After each prompt/SKILL.md change: run agents against the same briefs, score via QA gate (deterministic) + LLM judge (subjective), record in `traces/improvement_log.jsonl`. Keep changes that improve pass rate, auto-revert those that don't. Can run overnight as unattended sweeps.
- **CI golden test cases:** Small set of email templates with known-correct QA outcomes that must pass in CI (`make eval-golden`). Catches regressions on model/prompt/check changes without running full eval suite. Golden cases derived from highest-confidence eval traces.
- **New eval dimensions for template-first**: add eval criteria for template selection accuracy (did LLM pick the right template?), slot fill quality (content appropriate for slot constraints?), design token coherence (colors accessible, on-brand?)
- Update synthetic test data: add 10 cases specifically testing template selection edge cases (ambiguous briefs, multi-intent briefs, novel layout requests)
**Verify:** After completing all 11.24.x subtasks:
- `make eval-analysis` shows ≥97% overall pass rate
- Per-agent minimums: no agent below 90%
- `mso_conditionals` ≥99% (from 0% — guaranteed by golden templates)
- `accessibility` ≥95% (from 8% — alt text + heading decisions are structured)
- `html_preservation` ≥99% (from 10% — assembler preserves template structure)
- Token usage per blueprint run: ≤ 8,000 tokens (from ~15,000-30,000 with self-correction loops)
- Latency per blueprint run: ≤ 10s (from ~30-60s with retry loops)

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
- [ ] 11.25.1 Client design system model

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
- [ ] 11.25.2 Component → section bridge

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
- [ ] 11.25.3 Project-scoped template registry

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
- [ ] 11.25.4 Agent pipeline constraint injection

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
- [ ] 11.25.5 Consistency enforcement

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

### 11.24 Production Trace Sampling for Offline Judge Feedback Loop
**What:** Sample a configurable percentage of successful production blueprint runs and judge them asynchronously in a background worker. Results feed back into `traces/analysis.json`, which `failure_warnings.py` reads to inject updated failure patterns into agent system prompts. This closes the eval feedback loop — agents continuously learn from production data, not just synthetic test cases.
**Why:** Current eval data is synthetic (12-14 cases per agent). Real production briefs have different distributions of complexity, client requirements, and edge cases. Without production sampling, `failure_warnings.py` only reflects synthetic test failures. With sampling, agents get warnings based on actual production quality — the feedback loop becomes self-improving.
**Implementation:**
- Create `app/ai/agents/evals/production_sampler.py`:
  - `enqueue_for_judging(trace: BlueprintTrace, sample_rate: float)` — probabilistic Redis enqueue
  - `ProductionJudgeWorker` — pulls from Redis queue, runs agent-specific judge, appends verdict to `traces/production_verdicts.jsonl`
  - `refresh_analysis()` — merges production verdicts with synthetic verdicts, regenerates `traces/analysis.json`
- Update `app/ai/blueprints/engine.py` — on successful blueprint completion, call `enqueue_for_judging()` with configured sample rate
- Add config: `EVAL__PRODUCTION_SAMPLE_RATE` (default `0.0` — disabled until opted in), `EVAL__PRODUCTION_QUEUE_KEY` (Redis key)
- Update `app/ai/agents/evals/failure_warnings.py` — read from merged analysis (production + synthetic)
- Add `make eval-refresh` command to manually trigger analysis refresh from production verdicts
- Worker runs via `DataPoller` pattern (same as `MemoryCompactionPoller`, `CanIEmailSyncPoller`)
**Security:** Production traces contain generated HTML + briefs (no raw user credentials). Sampling rate configurable to control LLM cost. Redis queue uses same auth as existing Redis config. Verdicts stored locally in `traces/` (not exposed via API).
**Verify:** Set sample rate to 1.0 (100%) in test. Run 5 blueprints → verify 5 traces enqueued → worker processes all 5 → `production_verdicts.jsonl` has 5 entries → `refresh_analysis()` produces updated `analysis.json` with production data merged. Agent prompt includes warnings derived from production failures.

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
- [ ] 12.1 Protocol extension + Figma API integration

### 12.2 Asset Storage Pipeline
**What:** Download images from Figma's temporary URLs (expire ~14 days), store locally, serve via authenticated endpoint.
**Files:** New `app/design_sync/assets.py`. Modify `app/core/config.py`, `app/design_sync/routes.py`.
**Implementation:**
- `DesignAssetService`: download via httpx, store at `data/design-assets/{connection_id}/{node_id}.{format}`
- Resize if >600px wide (standard email max), optional Pillow compression
- `GET /api/v1/design-sync/assets/{connection_id}/{filename}` — serve with BOLA check
- Path traversal prevention in `get_stored_path()`
- `asset_storage_path` config in `DesignSyncConfig`
**Security:** BOLA check on connection access. Path traversal guard. No directory listing.
**Verify:** Download mock URL → file stored → serve via endpoint returns correct bytes.
- [ ] 12.2 Asset storage pipeline

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
- [ ] 12.3 Design import models & migration

### 12.4 Layout Analyzer & Brief Generator
**What:** Convert Figma document structure into a Scaffolder-compatible campaign brief.
**Files:** New `app/design_sync/figma/layout_analyzer.py`, `app/design_sync/brief_generator.py`
**Implementation:**
- `LayoutAnalyzer`: pure function, no I/O. Input: `DesignFileStructure` (selected nodes). Detect email sections (header, hero, content, CTA, footer) by name conventions + position. Detect column layouts from sibling frames. Extract text from TEXT nodes. Identify image placeholders. Output: `DesignLayoutDescription` with typed `EmailSection` list.
- `BriefGenerator`: transform layout + images into structured markdown brief. Image refs point to local asset URLs. Includes design token summary. User can edit before conversion.
**Security:** Pure computation. No I/O, no user input in SQL or templates.
**Verify:** Mock Figma JSON → expected section detection. Layout with 2 columns → correct brief format.
- [ ] 12.4 Layout analyzer & brief generator

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
- [ ] 12.6 Component extraction

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
