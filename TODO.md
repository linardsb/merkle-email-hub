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

#### 11.22.5 SKILL.md Rewrite — Architect Prompts, Not Generator Prompts
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

#### 11.22.7 Novel Layout Fallback — Graceful Degradation for Edge Cases
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

#### 11.22.8 Agent Role Redefinition — Tighten Specialisation
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

### 11.23 Inline Eval Judges — Selective LLM Judge on Recovery Retries
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
