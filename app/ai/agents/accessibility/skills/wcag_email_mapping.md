---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-accessibility-wcag-aa.md section 17 -->
<!-- Last synced: 2026-03-13 -->

# WCAG 2.1 AA Success Criteria — Email Quick Reference

Every WCAG criterion below is relevant to HTML email. Each entry maps the
criterion to its email-specific implementation and common failure mode.

---

## Level A (Must Have)

### 1.1.1 Non-text Content
- **Requirement:** `alt` on every `<img>` tag — no exceptions
- **Email twist:** Corporate clients block images by default; styled `alt` text (`font-family`, `font-size`, `color` on `<img>`) renders when images are off
- **Common failure:** Tracking pixels without `alt=""`; hero images with baked-in text and no `alt`

### 1.3.1 Info and Relationships
- **Requirement:** Semantic structure conveyed in markup
- **Email twist:** `role="presentation"` on ALL layout tables (the #1 email a11y rule); proper `<h1>`–`<h6>` headings; `<th scope>` on data tables; `role="list"` / `role="listitem"` on table-faked lists
- **Common failure:** Layout tables without `role="presentation"` — screen readers announce grid dimensions for every section

### 1.3.2 Meaningful Sequence
- **Requirement:** Reading order matches visual order
- **Email twist:** Source order = screen reader order in table-based layouts; mobile stacking follows source order; CSS reorder (`table-header-group`) does not change SR reading order
- **Common failure:** Two-column layouts where left column content depends on right column context

### 1.3.3 Sensory Characteristics
- **Requirement:** Don't rely on shape, size, position, or sound alone
- **Email twist:** Avoid "click the red button" or "see the image on the left" — use text labels with the instruction

### 1.4.1 Use of Color
- **Requirement:** Color is not the sole means of conveying information
- **Email twist:** Sale pricing needs "Was/Now" labels not just red/black; order status needs text not just colored dots; links need underline or 3:1 contrast vs surrounding text
- **Common failure:** Strikethrough pricing with color change only

### 2.1.1 Keyboard
- **Requirement:** All interactive elements keyboard-reachable
- **Email twist:** Links via `<a href>` (never `<div onclick>`); buttons via `<a>` styled as buttons; AMP components fully keyboard operable

### 2.1.2 No Keyboard Trap
- **Requirement:** Can Tab past every element
- **Email twist:** Generally met in email; watch for AMP interactive components and CSS checkbox hacks

### 2.2.2 Pause, Stop, Hide
- **Requirement:** User can pause moving content
- **Email twist:** Animated GIFs cannot be paused in any email client — inherent limitation; keep animations short and non-essential

### 2.3.1 Three Flashes
- **Requirement:** No content flashes more than 3 times/second
- **Email twist:** Applies to animated GIFs, CSS `@keyframes`, server-generated countdown timer GIFs

### 2.4.2 Page Titled
- **Requirement:** Meaningful `<title>` in `<head>`
- **Email twist:** Exposed in browser tab for "View in browser" links and some webmail clients (Outlook.com)
- **Common failure:** Empty or generic `<title>` tag

### 2.4.3 Focus Order
- **Requirement:** Focus sequence follows logical order
- **Email twist:** Determined by table source code order; avoid `tabindex > 0`

### 2.4.4 Link Purpose in Context
- **Requirement:** Link text describes destination/action
- **Email twist:** CTAs must say "Shop the sale" not "Click here"; footer links must be descriptive; screen reader users navigate by link list
- **Common failure:** Multiple "Read more" links in product grids

### 3.1.1 Language of Page
- **Requirement:** `lang` attribute on `<html>`
- **Email twist:** Screen readers in Apple Mail, iOS, Outlook switch pronunciation engines based on this; without it, pronunciation is guessed
- **Common failure:** Missing `lang` attribute entirely

### 3.2.1 On Focus
- **Requirement:** No unexpected actions on focus
- **Email twist:** Generally met; watch for AMP components

### 3.2.2 On Input
- **Requirement:** No auto-submission on input change
- **Email twist:** AMP email forms must not auto-submit when a field changes

### 3.3.1 Error Identification
- **Requirement:** Errors described in text
- **Email twist:** AMP form errors: text description, not just red color

### 3.3.2 Labels or Instructions
- **Requirement:** Visible labels on form fields
- **Email twist:** AMP form `<input>` must have associated `<label>`; `placeholder` is not a substitute

### 4.1.1 Parsing
- **Requirement:** Valid markup
- **Email twist:** Well-formed HTML with proper nesting; MSO conditionals must be balanced

### 4.1.2 Name, Role, Value
- **Requirement:** Programmatic name/role for UI components
- **Email twist:** `role="presentation"` on layout tables; `role="article"` + `aria-roledescription="email"` on wrapper; `role="img"` on SVG/VML

---

## Level AA (Target Standard)

### 1.3.5 Identify Input Purpose
- **Requirement:** `autocomplete` on form fields
- **Email twist:** AMP email forms: `autocomplete` for name, email, address fields

### 1.4.3 Contrast Minimum
- **Requirement:** 4.5:1 for normal text; 3:1 for large text (18px+ or 14px+ bold)
- **Email twist:** Test in BOTH light mode and dark mode; email dark mode may invert colors unpredictably; footer/legal text is the most common failure point
- **Common failure:** Light gray footer text on white background

### 1.4.5 Images of Text
- **Requirement:** Use live text, not text baked into images
- **Email twist:** Bulletproof HTML/CSS buttons over image buttons; hero headlines in live text; logos are exempt
- **Common failure:** CTA buttons as images — invisible with images off

### 1.4.11 Non-text Contrast
- **Requirement:** 3:1 for UI components and graphical objects
- **Email twist:** Button backgrounds vs surrounding email background; ghost button borders; icon contrast; meaningful divider lines; AMP form field boundaries

### 1.4.12 Text Spacing
- **Requirement:** Content adapts to user text spacing preferences
- **Email twist:** Set `line-height`, paragraph spacing, `letter-spacing`, `word-spacing` explicitly in inline styles (email clients apply inconsistent defaults; Outlook ignores `margin`)

### 2.4.6 Headings and Labels
- **Requirement:** Descriptive headings that describe content
- **Email twist:** `<h1>` for main headline, `<h2>` for sections, `<h3>` for subsections; all headings need full inline styles (`margin:0`, explicit padding)
- **Common failure:** Skipped heading levels (h1 to h3)

### 2.4.7 Focus Visible
- **Requirement:** Visible focus indicator on all focusable elements
- **Email twist:** Don't use `outline: none` without a replacement; focus indicator needs 3:1 contrast; test across Gmail web, Outlook.com, Apple Mail

### 3.1.2 Language of Parts
- **Requirement:** `lang` on content in a different language
- **Email twist:** Common in multi-market emails: `<span lang="fr">Bonjour</span>`; screen readers switch pronunciation at `lang` boundaries

### 3.2.3 Consistent Navigation
- **Requirement:** Consistent navigation structure across related pages
- **Email twist:** Consistent header/footer structure across campaign sends; unsubscribe always in footer, same position

### 3.2.4 Consistent Identification
- **Requirement:** Same function labeled the same way
- **Email twist:** "Unsubscribe" not "Opt out" one week and "Remove me" the next; consistent CTA labeling across campaign emails

### 3.3.3 Error Suggestion
- **Requirement:** Error messages suggest how to fix
- **Email twist:** AMP form validation messages should explain the correction needed

### 3.3.4 Error Prevention
- **Requirement:** Confirmation for significant actions
- **Email twist:** AMP forms: confirmation step for unsubscribe or cancellation actions