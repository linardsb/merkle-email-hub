# WCAG 2.1 AA Criteria Mapped to Email HTML

## Applicable WCAG Criteria

### 1.1.1 Non-text Content (Level A)
**Email application:** All `<img>` tags must have `alt` attributes
- Informative images: descriptive `alt` text
- Decorative images: `alt=""`
- Functional images (in links): `alt` describes destination/action
- Image maps: each `<area>` has `alt`
- CSS background images with meaning: provide text alternative nearby

### 1.3.1 Info and Relationships (Level A)
**Email application:** Semantic structure conveyed in markup
- Use `<h1>` through `<h6>` for headings (not `<td style="font-size:24px">`)
- Layout tables: `role="presentation"` (no `<th>`, `<caption>`, `summary`)
- Data tables: `<th>`, `scope="col"` or `scope="row"`
- Lists: `<ul>`/`<ol>` with `<li>` (limited email support — use sparingly)
- `<p>` for paragraphs

### 1.3.2 Meaningful Sequence (Level A)
**Email application:** Reading order matches visual order
- Source order should match visual order (no CSS reordering)
- Table-based layouts: content flows left-to-right, top-to-bottom in source

### 1.4.1 Use of Color (Level A)
**Email application:** Color is not the only visual means of conveying information
- Links must be underlined OR have 3:1 contrast with surrounding text
- Error states: use icon/text in addition to red color
- Status indicators: use text labels alongside color

### 1.4.3 Contrast (Minimum) (Level AA)
**Email application:** Text contrast ratios
- Normal text: 4.5:1 minimum
- Large text (>=18px or >=14px bold): 3:1 minimum
- Applies to both light and dark mode

### 2.1.1 Keyboard (Level A)
**Email application:** Limited — focus on link access
- All interactive elements must be reachable via keyboard
- Links use `<a href>` (not `<div onclick>`)
- Buttons use `<a>` styled as buttons (email has no `<button>`)

### 2.4.2 Page Titled (Level A)
**Email application:** `<title>` in `<head>`
- Should match or relate to the email subject line

### 2.4.4 Link Purpose (Level A)
**Email application:** Link text is descriptive
- "Shop the collection" not "Click here"
- "Read the full article" not "Read more"
- Multiple "Read more" links must be distinguishable

### 2.4.6 Headings and Labels (Level AA)
**Email application:** Headings describe content
- `<h1>`: Main email headline
- `<h2>`: Section headings
- `<h3>`: Subsection headings
- No skipped levels

### 3.1.1 Language of Page (Level A)
**Email application:** `lang` attribute on `<html>`
- `<html lang="en">` for English
- Use correct BCP 47 language tag
- If content switches language: `<span lang="fr">Bonjour</span>`

### 4.1.2 Name, Role, Value (Level A)
**Email application:** ARIA roles on email elements
- Outermost wrapper: `role="article"` + `aria-roledescription="email"`
- Layout tables: `role="presentation"`
- Decorative images: `role="presentation"` + `alt=""`

## Not Applicable to Email (Skip These)
- 1.2.x Audio/Video (emails rarely have media)
- 2.1.2 No Keyboard Trap (not applicable)
- 2.2.x Timing (no timed content in email)
- 2.3.x Seizures (no animation concerns in most clients)
- 2.5.x Input Modalities (limited in email)
- 3.2.x Predictable Navigation (no navigation in email)
- 3.3.x Input Assistance (no forms in most emails)
