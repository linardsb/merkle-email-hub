---
purpose: QA engine internals — 11 core checks, chaos testing, property testing, outlook analyzer, CSS compiler, resilience scoring
when-to-use: When adding new QA checks, modifying check behavior, working on chaos/property testing, or debugging QA failures
size: ~250 lines
source: app/qa_engine/
---

<!-- Scout header above. Sub-agents: read ONLY the header to decide relevance. Load full content only if needed. -->

# QA Engine Guide

## Overview

The QA engine validates email HTML quality through deterministic checks. No LLM calls — all checks are rule-based for speed and reproducibility.

## 11 Core Checks (`app/qa_engine/checks/`)

| Check | What it validates |
|-------|-------------------|
| `html_validation` | Valid HTML structure, no unclosed tags |
| `css_support` | CSS properties supported by target email clients (via ontology) |
| `file_size` | Total HTML size within email client limits |
| `link_validation` | All links valid, no broken hrefs |
| `spam_score` | Content patterns that trigger spam filters |
| `dark_mode` | Dark mode CSS and meta tag support |
| `accessibility` | Alt text, ARIA labels, color contrast |
| `fallback` | MSO conditional comments for Outlook |
| `image_optimization` | Image dimensions, format, size |
| `brand_compliance` | Colors/fonts match project design system |
| `personalisation_syntax` | Merge tag syntax valid for target ESP |

Each check: `async run(html: str, config: QACheckConfig) -> QACheckResult`

QACheckResult contains: `passed: bool`, `score: float`, `issues: list[QAIssue]`, `metadata: dict`

## Chaos Engine (Phase 18.1)

Simulates email client degradations to test resilience.

### 8 Degradation Profiles
1. **Gmail style strip** — removes `<style>` blocks
2. **Image blocked** — replaces images with alt text
3. **Dark mode inversion** — inverts colors
4. **Outlook Word engine** — applies Word rendering constraints
5. **Gmail clipping** — truncates at 102KB
6. **Mobile narrow** — constrains viewport to 320px
7. **Class strip** — removes all CSS classes
8. **Media query strip** — removes `@media` rules

### How it works
1. Apply degradation profile to HTML
2. Run 11 core QA checks on degraded HTML
3. Score each profile (0.0-1.0)
4. Compute aggregate resilience score
5. Optionally auto-document failures to knowledge base

Config: `QA_CHAOS__ENABLED`, `QA_CHAOS__DEFAULT_PROFILES`

### Knowledge Feedback (`chaos/knowledge_writer.py`)
Auto-generates knowledge documents from chaos failures. Deduplicates by title+domain. Non-blocking — write failures never break chaos tests.

## Property Testing (Phase 18.2)

Hypothesis-based fuzzing that generates random email configurations and validates invariants.

### 10 Invariants
SizeLimit, ImageWidth, LinkIntegrity, AltTextPresence, TableNestingDepth, EncodingValid, MSOBalance, DarkModeReady, ContrastRatio, ViewportFit

### How it works
1. `random_email_config()` generates random email parameters (seeded for CI reproducibility)
2. `build_email()` constructs synthetic HTML from config
3. Run all invariants against generated HTML
4. Report failures with the config that triggered them

Config: `QA_PROPERTY_TESTING__ENABLED`, `QA_PROPERTY_TESTING__DEFAULT_CASES`, `QA_PROPERTY_TESTING__SEED`

## Outlook Analyzer (Phase 19.1)

Detects Word-engine dependencies in email HTML.

### 7 Detection Rules
VML shapes, ghost tables, MSO conditionals, MSO CSS properties, DPI images, .ExternalClass, word-wrap hacks

### 3 Modernization Targets
- `new_outlook`: Aggressive removal of all legacy patterns
- `dual_support`: Keep MSO conditionals, remove VML
- `audit_only`: Report only, no changes

Output sanitized via `sanitize_html_xss()`.

## CSS Compiler (Phase 19.3)

Lightning CSS 7-stage pipeline for email-safe CSS compilation.

### Pipeline Stages
1. **Parse** — Extract CSS from HTML
2. **Analyze** — Identify unsupported properties via ontology
3. **Transform** — Apply ontology-driven conversions
4. **Eliminate** — Remove properties unsupported by all targets
5. **Optimize** — Minify via Lightning CSS
6. **Inline** — Inline styles into HTML elements
7. **Sanitize** — XSS sanitization

Config: `css_compiler_enabled`, `css_compiler_target_clients` on `EmailEngineConfig`

## Rendering Resilience Check (Phase 18.3)

Optional check #12 — NOT in `ALL_CHECKS` to prevent recursion.
Runs chaos engine internally, passes if `resilience_score >= threshold`.
`QAEngineService.run_checks()` runs it separately after the 11 core checks.

Config: `QA_CHAOS__RESILIENCE_CHECK_ENABLED`, `QA_CHAOS__RESILIENCE_THRESHOLD` (default 0.7)
