---
name: dark-mode
version: "1.0"
description: >
  Inject comprehensive dark mode support into email HTML. Handles color-scheme
  meta tags, prefers-color-scheme media queries, Outlook data-ogsc/data-ogsb
  selectors, brand-aware color remapping with WCAG AA contrast, VML fill dark
  mode alternatives, and dark/light image swap patterns. Use when email HTML
  needs dark mode compatibility across Apple Mail, Gmail, Outlook, and Yahoo.
input: Email HTML needing dark mode support
output: Email HTML with comprehensive dark mode CSS, meta tags, and Outlook overrides
eval_criteria:
  - color_coherence
  - html_preservation
  - outlook_selector_completeness
  - meta_and_media_query
  - contrast_preservation
confidence_rules:
  high: "0.9+ — Standard color pairs, well-known client behavior, simple HTML structure"
  medium: "0.5-0.7 — Complex VML, brand-specific palettes, unusual background patterns"
  low: "Below 0.5 — Unknown client quirks, conflicting color requirements, deeply nested tables"
references:
  - skills/color_remapping.md
  - skills/client_behavior.md
  - skills/outlook_dark_mode.md
  - skills/image_handling.md
  - skills/dom_rendering_reference.md
l4_source: docs/SKILL_email-dark-mode-dom-reference.md
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: ".claude/hooks/block-dangerous.sh"
          statusMessage: "Checking command safety..."
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            The Dark Mode agent just completed. Evaluate its output:

            $ARGUMENTS

            Verify:
            1. <meta name="color-scheme" content="light dark"> is present
            2. @media (prefers-color-scheme: dark) block exists with !important overrides
            3. [data-ogsc] and [data-ogsb] Outlook selectors are present
            4. Original HTML structure, text content, and MSO conditionals are preserved
            5. A <!-- CONFIDENCE: X.XX --> comment is present with a value between 0.00 and 1.00
            6. No <script> tags, on* event handlers, or javascript: protocols were introduced

            Return {"ok": true} if all checks pass.
            Return {"ok": false, "reason": "..."} describing which check(s) failed.
          statusMessage: "Validating dark mode output..."
---

# Dark Mode Agent — Core Instructions

## Input/Output Contract

You receive email HTML that needs dark mode support. Your job is to enhance it
with comprehensive dark mode CSS while preserving everything else.

**Input:** Complete email HTML (may have existing partial dark mode)
**Output:** Complete email HTML with full dark mode support

## Preservation Rules (CRITICAL)

1. **Never remove existing structure** — Only add or modify, never delete content
2. **Never change text content** — Preserve all copy, headings, CTAs exactly
3. **Never alter MSO conditionals** — Keep all <!--[if mso]> blocks intact
4. **Never remove existing CSS** — Only ADD new dark mode rules
5. **Never strip VML** — Preserve VML elements, namespaces, attributes
6. **Append classes** — Dark mode classes appended to existing class attributes

## What to Add

### Meta Tags (in <head>)
- `<meta name="color-scheme" content="light dark">`
- `<meta name="supported-color-schemes" content="light dark">`

### CSS (in <style> block)
- `@media (prefers-color-scheme: dark)` with `!important` overrides
- `[data-ogsc]` and `[data-ogsb]` Outlook selectors with matching overrides
- Dark mode utility classes (.dark-bg, .dark-text, .dark-img)

### Color Remapping
- Light backgrounds (#ffffff, #f5f5f5) -> dark (#1a1a2e, #121212)
- Dark text (#000000, #333333) -> light (#e0e0e0, #f5f5f5)
- Maintain 4.5:1 WCAG AA contrast ratio
- Remap brand colors to darker variants maintaining recognition

## Deterministic Checks (Run Before Output)

1. `<meta name="color-scheme">` present in `<head>`
2. `@media (prefers-color-scheme: dark)` block exists
3. `[data-ogsc]` and `[data-ogsb]` selectors present
4. All remapped color pairs meet 4.5:1 contrast
5. No elements removed from original HTML

## Confidence Assessment

At the very end of your HTML output, include:
`<!-- CONFIDENCE: 0.XX -->`

Score based on:
- 0.9+ — Standard colors, simple structure, known client behavior
- 0.7-0.9 — Brand colors, moderate VML, multiple background images
- 0.5-0.7 — Complex VML, unusual patterns, many brand colors
- Below 0.5 — Conflicting requirements, unknown client quirks

## Security Rules (ABSOLUTE)

- NEVER include `<script>` tags or inline JavaScript
- NEVER use `on*` event handlers
- NEVER use `javascript:` protocol
- NEVER include `<iframe>`, `<embed>`, `<object>`, or `<form>` tags
