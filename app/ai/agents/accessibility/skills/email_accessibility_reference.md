# Email Accessibility — Complete WCAG AA Coverage

Every accessibility requirement, technique, and best practice specific to HTML email development, mapped to WCAG 2.1 AA success criteria. Each item includes why it matters in the email context specifically.

---

## 1. Email Document Language & Structure

### Language Declaration
- `lang` attribute on `<html>` tag (e.g., `lang="en"`) — screen readers in Apple Mail, iOS Mail, and Outlook switch pronunciation engines based on this; without it, screen readers guess the language incorrectly — WCAG 3.1.1 (Level A)
- `lang` attribute on inline content in a different language (e.g., `<span lang="fr">Bonjour</span>`) — common in international brand emails mixing languages — WCAG 3.1.2 (Level AA)
- `dir="rtl"` or `dir="ltr"` on `<html>` and on content blocks — email table layouts may need structural reversal for RTL languages
- Valid language subtags (e.g., `lang="en-GB"`, `lang="zh-Hans"`) — ensures correct screen reader pronunciation in multi-market email campaigns

### Document Title
- `<title>` tag in `<head>` with meaningful text — some email clients (Outlook.com, some webmail) expose this in the browser tab or reading pane title bar — WCAG 2.4.2 (Level A)
- Title should describe the email's purpose (e.g., "Order Confirmation — Company Name") — helps screen reader users identify the email when opened in a browser via "View in browser" link

### Reading Order
- Source code order must match visual reading order — email clients render table cells in DOM order, so mismatched visual/source order confuses screen readers — WCAG 1.3.2 (Level A)
- Content reordering via CSS (`table-header-group`, `table-footer-group`) must not break logical reading order — screen readers read the source order, not the CSS-reordered visual order
- Hidden preheader text appears first in source — this is the first thing screen readers announce when opening the email; make it meaningful
- Mobile column stacking order must maintain logical flow — when two-column email layouts collapse to single-column on mobile, the stacking order is determined by source order

---

## 2. Email Table Semantics & Roles

### Layout Tables (Email-Specific — Most Critical)
- `role="presentation"` on every layout table — email is built almost entirely on tables for layout; without this role, screen readers announce "table with X rows and Y columns" for every section of the email — WCAG 1.3.1 (Level A)
- No `<th>`, `<caption>`, `<thead>`, `<tbody>`, `<tfoot>` on layout tables — these signal data table semantics and confuse screen readers when used on layout tables
- No `summary` attribute on layout tables — another data table signal that must be absent from layout tables
- No `scope` attribute on layout table cells — reserved for data table headers only
- Nested layout tables must each individually have `role="presentation"` — email templates commonly have 5–10+ nested tables; every single one needs this role
- `border="0"` on layout tables — prevents visual table rendering that could mislead sighted users into thinking it's a data table

### Data Tables (In Email Body Content)
- `role="table"` on actual data tables (e.g., order line items, pricing tables, comparison grids) — distinguishes them from the surrounding layout tables
- `<caption>` element describing the table's purpose (e.g., "Your order summary") — WCAG 1.3.1
- `<th>` elements for header cells with `scope="col"` or `scope="row"` — so screen readers announce column/row headers when navigating data cells
- `id` and `headers` attributes for complex tables with multi-level headers (e.g., multi-product comparison emails) — WCAG 1.3.1
- Data table content must be understandable when linearized — email clients may strip table formatting in some views (plain text fallback, some mobile clients)

---

## 3. Email Image Accessibility

### Meaningful Images — WCAG 1.1.1 Non-text Content (Level A)
- `alt` attribute on every `<img>` tag — no exceptions; many corporate email clients block images by default, making `alt` text the primary content
- `alt` text must convey purpose and meaning, not appearance — describe what the image communicates in the email's context
- Product images: include product name, key details (e.g., `alt="Blue cotton t-shirt, front view — $29.99"`) — in e-commerce emails, this is the only product info visible with images off
- Hero/banner images: describe the scene AND any text overlay content — hero text baked into images is invisible to screen readers without this
- Chart/graph images: summarize the key data point or trend — data visualization in emails is almost always image-based
- Icon images: describe the action or meaning (e.g., `alt="Email us"` not `alt="envelope icon"`) — email templates rely heavily on icon images
- CTA image buttons: `alt` text must describe the action (e.g., `alt="Shop now"`) — if using an image-based button instead of bulletproof HTML button

### Decorative Images
- Empty `alt=""` (not missing `alt`) on purely decorative images — prevents screen readers from announcing the image file name — WCAG 1.1.1
- `role="presentation"` on decorative images — additional screen reader hint
- `aria-hidden="true"` on decorative images — belt-and-suspenders approach since email client ARIA support varies
- Spacer images must have `alt=""` — email templates still commonly use spacer GIFs
- Decorative divider images must have `alt=""` — ornamental separators between sections
- Tracking pixel images must have `alt=""` — 1x1 open tracking pixel should be invisible to screen readers

### Email-Specific: Image-Off Rendering
- Styled `alt` text (`font-family`, `font-size`, `font-weight`, `color` on `<img>` tag) — email-specific technique: when images are blocked, the `alt` text renders with these styles, making it readable and on-brand
- Email must be fully understandable with all images turned off — many corporate Outlook installations block images by default; this is far more common than on the web
- Critical information must not be conveyed solely through images — CTAs, pricing, key messages, deadlines must be in live text
- CTA buttons should not rely solely on images — use bulletproof HTML/CSS buttons so the call-to-action remains visible and clickable with images off
- Design "image-off first" — test every email template with images disabled before sign-off

### Linked Images in Email
- `alt` text on linked images must describe the link destination/action, not the image — WCAG 1.1.1, 2.4.4
- If a linked image is adjacent to a text link with the same destination, wrap both in a single `<a>` tag and use `alt=""` on the image — prevents screen readers from announcing the same link twice (common email pattern: product image + product name both linking to the same URL)
- Logo images linking to website: `alt="Company Name — visit website"` — not just `alt="logo"`

### Animated GIFs in Email
- Must not flash more than 3 times per second — WCAG 2.3.1 (Level A)
- First frame must be meaningful — Outlook desktop shows only the first frame; if first frame is blank, Outlook users see nothing
- Avoid conveying critical information solely through animation — the animation may not play in all clients
- Consider GIF file size impact on email load time — slow-loading GIFs leave blank spaces that affect comprehension

### Image Maps in Email
- Each `<area>` must have descriptive `alt` — WCAG 1.1.1
- Provide text-based alternative — Gmail apps don't support image maps; those users get a single linked image with no area distinction

### SVG in Email
- `role="img"` on `<svg>` elements — limited email client SVG support; always provide fallback
- `aria-label` or `<title>` inside `<svg>` for accessible name
- `aria-hidden="true"` on decorative SVGs
- Fallback `<img>` for clients that don't render inline SVG (most email clients) — the `<img>` fallback is the primary rendering path in email

### Bulletproof Background Images (VML)
- Never convey critical information via CSS `background-image` alone — Outlook requires VML for background images; if VML is missing, the background image doesn't render
- Always provide text content in the table cell on top of background images — the text must be readable without the background image
- VML background images for Outlook must have text overlaid — the VML `<v:rect>` fill is decorative; the `<td>` text content is the accessible content

---

## 4. Email Heading Hierarchy

### Structure — WCAG 1.3.1 (Level A), WCAG 2.4.6 (Level AA)
- Use proper heading tags (`<h1>` through `<h6>`), not just styled `<td>` or `<span>` — screen readers use headings for in-email navigation; many email developers skip heading tags entirely and just use styled table cells, which destroys this navigation
- One `<h1>` per email (the main subject/title of the email)
- Headings must follow logical descending hierarchy (h1 → h2 → h3) with no skipped levels — screen reader users navigate emails by heading level
- Every email content section should be introduced by a heading — allows screen reader users to jump between sections (e.g., "Order Details", "Shipping Info", "Recommended For You")
- Heading text must be descriptive (e.g., "Your Order Summary" not just "Details")

### Email-Specific Heading Styling
- All heading tags must have full inline styles — email clients apply wildly different default heading styles; without inline styles, headings may render inconsistently across Gmail, Outlook, Apple Mail
- Set `margin: 0` on all headings — email clients apply unpredictable default heading margins; control spacing with table cell padding instead
- `padding` on headings must be explicitly set — Outlook and Gmail apply different default padding to heading tags

### Common Email Heading Structure
- `<h1>` — email main title / hero text
- `<h2>` — major section headings (e.g., "Order Details", "Shipping Info", "Recommended For You")
- `<h3>` — subsection headings (e.g., individual product names within an order, article titles in a newsletter)
- `<h4>` — rarely needed in email; for fine-grained subsections in long-form email content

---

## 5. Email Link Accessibility

### Link Text — WCAG 2.4.4 Link Purpose in Context (Level A)
- Link text must describe the destination or action (e.g., "View your order" not "Click here") — email templates are notorious for "Click here" and "Read more" links
- Avoid generic link text: "Click here", "Read more", "Learn more", "Here", "This" — screen reader users often navigate by pulling up a list of all links in the email; a list of 8 "Read more" links is useless
- If generic text is unavoidable (design constraint), use `aria-label` for context (e.g., `aria-label="Read more about winter sale"`) — note: Gmail strips `aria-label`, so this is a partial solution
- Multiple links with same text must go to same destination, or be differentiated — common in product grid emails where every product has "Shop now"
- Tracked/redirected links (ESP click tracking) don't affect accessibility — the visible link text matters, not the underlying tracking URL

### Email-Specific Link Styling
- Links within body copy must be distinguishable by more than just color — WCAG 1.4.1; use `text-decoration: underline` as the default for body text links in email
- Link color must have 3:1 contrast against surrounding non-link text if underline is removed — WCAG 1.4.1
- Link color must meet 4.5:1 contrast against background — WCAG 1.4.3
- Visited/unvisited link styling is unreliable in email clients — don't depend on color change to indicate visited links
- `text-decoration: none` is acceptable for CTA buttons and navigation links where the link nature is visually obvious (button shape, navigation context)

### Touch/Tap Target Size in Email
- Minimum 44x44px touch target for links on mobile email — mobile email is the primary reading context (60%+ of opens); small links cause mis-taps
- Adequate spacing between adjacent links (minimum 8px gap) — email footers commonly stack many small links close together
- Small text links in footers (unsubscribe, privacy, etc.) should still have adequate padding for touch targets
- Bulletproof buttons should have the entire button area clickable — padding-based and table-cell-based buttons achieve full-area click targets; border-based buttons do too

### Email-Specific Link Types
- Mailto links should clearly indicate their action (e.g., "Email us at support@company.com") — screen readers announce `mailto:` prefix
- Tel links should include the phone number in visible text (e.g., "Call us at 555-1234") — so users know what number they're about to call
- SMS links should indicate the action and number
- Deep links (to mobile apps) should indicate they open an app, not a webpage
- Calendar add links should describe the event being added

### Redundant Links in Email
- If a product image and adjacent product name both link to the same URL, wrap both in a single `<a>` and use `alt=""` on the image — extremely common email pattern that causes double announcements; one of the most frequent email accessibility failures
- Social media icon + text label linking to same destination: single `<a>` wrapper

---

## 6. Color & Contrast in Email

### Text Contrast — WCAG 1.4.3 Contrast Minimum (Level AA)
- Normal text: minimum 4.5:1 contrast ratio against background
- Large text (18pt/24px+ or 14pt/18.66px bold+): minimum 3:1 contrast ratio
- Preheader text: must meet 4.5:1 even if visually small — if preheader becomes visible in any context, it must be readable
- Footer text (unsubscribe, legal, address): must meet 4.5:1 — email footers are the most common contrast failure point; designers often use light gray on white
- Text on bulletproof background images: must meet contrast against all areas of the background image the text may overlap — add a semi-transparent overlay `<td>` behind text

### Non-Text Contrast — WCAG 1.4.11 (Level AA)
- Bulletproof button backgrounds: 3:1 contrast against surrounding email background — the button must be visually identifiable as a button
- Ghost/outline button borders: 3:1 contrast against surrounding email background
- Icon contrast: 3:1 against email background — social media icons, feature icons, etc.
- Divider lines: 3:1 contrast if they convey meaningful section separation (decorative dividers exempt)
- Form field boundaries in AMP emails: 3:1 contrast against email background
- Focus indicators in AMP emails: 3:1 contrast against adjacent colors

### Color Independence — WCAG 1.4.1 Use of Color (Level A)
- Never use color as the sole means of conveying information in email
- Sale/discount pricing: must use text labels like "Was $50, now $30" or "50% off" — not just red vs black price colors
- Order status indicators: must include text labels — not just colored dots (e.g., green = shipped, red = cancelled)
- Error states in AMP email forms: must use icon or text in addition to red color
- Links must be identifiable by more than just color — underline or bold in addition to color
- "Required" fields in AMP email forms: use text label, not just red asterisk

### Email Dark Mode Contrast
- Test contrast ratios in dark mode — email dark mode is not optional; Apple Mail, Gmail, Outlook all have dark modes that aggressively modify email colors
- Colors that pass contrast in light mode may fail after dark mode inversion
- `@media (prefers-color-scheme: dark)` styles must maintain all contrast ratios
- Forced color inversions by email clients (Outlook.com, Gmail) may break contrast unpredictably — use dark-mode-safe color pairs (avoid pure `#ffffff` and `#000000`)
- Off-white on near-black (`#f0f0f0` on `#1a1a1a`) is more comfortable than pure white on pure black in dark mode email
- `[data-ogsc]` / `[data-ogsb]` targeted Outlook.com dark mode styles must also maintain contrast

### High Contrast Mode
- `@media (prefers-contrast: high)` — provide enhanced contrast styles where email clients support it
- Ensure button borders and outlines remain visible in forced high contrast mode
- Text on background images must remain readable in high contrast mode (another reason to always have a solid-color fallback behind text)

---

## 7. Email Typography & Readability

### Font Sizing in Email — WCAG 1.4.4 (Level AA)
- Body copy: minimum 14px, recommended 16px — email is often read on small mobile screens; 12px body copy common in email but fails readability
- Small print / legal text in email footer: minimum 12px, push for 14px
- Preheader text: minimum 12px
- Mobile body copy: recommended 16px–18px (bumped up via media query `!important` override of inline styles)
- Line height: minimum 1.5x font size for body copy — WCAG 1.4.12; email clients apply inconsistent default line heights, so always set explicitly
- Paragraph spacing: minimum 2x font size between paragraphs — in email, control this with table cell padding rather than `margin` (Outlook ignores margin)
- Letter spacing: should not be constrained below 0.12x font size — WCAG 1.4.12
- Word spacing: should not be constrained below 0.16x font size — WCAG 1.4.12; `word-spacing: normal` on `<body>` fixes an Outlook.com bug that violates this

### Font Choice in Email
- Use system/web-safe fonts as primary (Arial, Helvetica, Georgia, Verdana, Tahoma) — email font support is limited; custom web fonts only work in Apple Mail, iOS, Samsung, Thunderbird
- Avoid thin/light font weights (300 and below) for body copy — lower effective contrast, harder to read on mobile
- Avoid all-caps for large blocks of email text — reduces readability; some screen readers may spell out all-caps words letter by letter
- Ensure custom web fonts (`@font-face`) degrade to readable fallback fonts — the fallback font is what most email recipients actually see

### Text Alignment in Email
- Left-align body copy for LTR languages, right-align for RTL — `text-align` must be set explicitly in email inline styles; client defaults vary
- Avoid center-aligned body paragraphs — harder to read, especially on narrow mobile email layouts
- Justified text (`text-align: justify`) must be avoided in email — creates uneven word spacing; worse in email than on web because email layout widths change across clients and devices

### Line Length in Email
- Maximum 600px content width / ~70–80 characters per line — the standard 600px email container enforces this naturally on desktop
- On mobile, content reflows to viewport width — media queries should maintain readable line length
- Very narrow email columns (under 200px in multi-column layouts) are inherently harder to read — consider stacking to single-column on mobile

---

## 8. Email Content Structure & Semantics

### Meaningful Sequence — WCAG 1.3.2 (Level A)
- Visual layout order must match DOM/source order — email table cell order determines screen reader reading order; there's no CSS grid/flexbox `order` property to rearrange
- Two-column email layouts: left column reads first in source, then right column — ensure this sequence makes sense (e.g., image left + text right: text should not depend on seeing the image first)
- When columns stack on mobile, resulting single-column order must be logically sequenced — source order determines stacking order in fluid-hybrid layouts
- Hidden content (preheader, mobile-only, desktop-only) must not disrupt reading flow — screen readers may read content hidden with `max-height: 0; overflow: hidden` but skip `display: none` content

### Lists in Email
- Use proper `<ul>` / `<ol>` / `<li>` markup when possible — WCAG 1.3.1; gives screen readers list count and navigation
- When faking lists with tables (necessary for Outlook consistency), use `role="list"` on the table and `role="listitem"` on each row — maintains list semantics
- Bullet characters in table-faked lists: put the bullet in a cell with `aria-hidden="true"` — prevents screen readers from announcing "bullet" or the unicode character

### Paragraphs in Email
- Use `<p>` tags rather than `<br><br>` — screen readers pause between `<p>` elements but not at `<br>` tags; `<br><br>` creates visual spacing without semantic separation
- Empty `<p>` tags used for spacing should be replaced with table cell padding or spacer `<td>` — email-specific spacing technique that's also more accessible

### Emphasis in Email
- Use `<strong>` instead of `<b>` for important text — screen readers can announce `<strong>` with emphasis; `<b>` is purely visual
- Use `<em>` instead of `<i>` for stress emphasis — same distinction: semantic vs visual
- Don't rely solely on bold/italic to convey meaning — combine with text cues (e.g., "Important: your order ships tomorrow")

---

## 9. Email Interactive Element Accessibility

### Bulletproof Button Accessibility
- Button `<a>` tags must have descriptive text (e.g., "Shop the Sale" not "Click Here") — WCAG 2.4.4; email buttons are the primary CTA
- `role="button"` only if the link triggers an in-email action (rare outside AMP) — most email CTA links navigate to a webpage, so `role="button"` would be incorrect
- Button text must meet 4.5:1 contrast against button background color
- Button background must meet 3:1 contrast against surrounding email background — WCAG 1.4.11; the button must be visually identifiable
- Ghost/outline button border: 3:1 contrast against surrounding email background
- VML buttons for Outlook (`<v:roundrect>`): must have text content inside the VML structure, not rely on the shape alone
- Full-width mobile buttons (via media query): maintain all contrast and text requirements at mobile size

### AMP Email Form Accessibility
- All `<input>` elements must have associated visible `<label>` elements — WCAG 1.3.1, 4.1.2, 3.3.2
- `placeholder` text must not be the only label — disappears on input
- Error messages must be programmatically associated with fields (`aria-describedby`) — WCAG 3.3.1
- Error messages must describe the error in text, not just red color — WCAG 3.3.1, 1.4.1
- Required fields: indicate with text (not just color/asterisk) + `aria-required="true"` — WCAG 3.3.2
- `aria-invalid="true"` on fields with validation errors
- Form submission feedback must be announced to screen readers — `aria-live="polite"` on feedback region
- `autocomplete` attributes for name, email, address fields — WCAG 1.3.5 (Level AA); helps users fill out in-email forms

### AMP Email Interactive Component Accessibility
- `amp-accordion` — expanded/collapsed state must be conveyed to screen readers
- `amp-carousel` — navigation controls must be keyboard accessible and screen reader announced
- `amp-selector` — selected state must be programmatically determinable
- All AMP interactive components must be keyboard operable — WCAG 2.1.1 (Level A)
- All AMP interactive elements must have visible focus indicators — WCAG 2.4.7 (Level AA)

### Kinetic/Interactive Email (CSS Checkbox Hack)
- `<label>` must be associated with its `<input>` and describe the action — screen readers announce the label
- Hidden `<input>` elements: use `aria-hidden="true"` if they're not meant to be directly interacted with by assistive technology
- Interactive CSS-only carousels, tabs, accordions: must have a static fallback that conveys ALL the same information — clients that strip `<input>` and `<style>` (Gmail) render the fallback, and that fallback must be accessible
- The static fallback is the primary accessible experience — most email clients don't support interactive CSS; the interactive version is the enhancement

---

## 10. Email Motion & Animation Accessibility

### Animation Safety — WCAG 2.3.1 Three Flashes (Level A)
- No email content flashes more than 3 times per second — applies to animated GIFs, CSS `@keyframes`, and server-generated countdown timer GIFs
- Animated GIFs must not contain flashing/strobing sequences — email GIFs cannot be paused by the user in any email client
- CSS `@keyframes` animations in email must not create rapid flashing

### Reduced Motion — Best Practice for AA
- `@media (prefers-reduced-motion: reduce)` in email `<style>` block — disable or reduce CSS animations for users who request it
- Set `animation: none !important` and `transition: none !important` in reduced motion media query — overrides inline animation styles
- Animated GIFs cannot be controlled by CSS in email — they always auto-play; keep them short (under 5 seconds) or limit loop count
- CSS-only countdown timers: provide a static text fallback in reduced motion context
- Live countdown timer GIFs (server-generated): cannot be paused — ensure countdown info is also in live text

### Auto-Playing Content in Email — WCAG 2.2.2 Pause, Stop, Hide (Level A)
- Animated GIFs auto-play and cannot be paused in any email client — this is an inherent email accessibility limitation; keep animations short and non-essential
- `<video>` in Apple Mail/iOS Mail: should not auto-play with sound; use `muted` attribute
- Moving/animated content must not be the only way to understand the email's message

---

## 11. Email Focus & Keyboard Navigation

### Keyboard Accessibility — WCAG 2.1.1 (Level A)
- All links and buttons in email must be reachable via keyboard Tab key — applies to webmail (Gmail, Outlook.com, Yahoo) and desktop clients (Outlook, Apple Mail, Thunderbird)
- Focus order must follow logical sequence matching visual layout — determined by source code order in email — WCAG 2.4.3 (Level A)
- No keyboard traps — users must be able to Tab past every element in the email — WCAG 2.1.2 (Level A)
- AMP email interactive elements (form fields, selectors, accordions) must be fully keyboard operable

### Focus Visibility — WCAG 2.4.7 (Level AA)
- All focusable elements must have a visible focus indicator — email developers sometimes add `outline: none` for visual cleanliness; this breaks keyboard navigation visibility
- Focus indicators must have 3:1 contrast against adjacent colors — WCAG 1.4.11
- In AMP emails: define custom focus styles for form elements and interactive components — default focus styles may not be visible against email background colors
- Email client native focus indicators vary — test across Gmail web, Outlook.com, Apple Mail to verify visibility

### Tab Order in Email
- Natural tab order follows source code order — in email, table cell order determines tab sequence
- Avoid `tabindex` values greater than 0 — disrupts natural tab order; especially problematic in email where the email is rendered within the client's own DOM with its own tab order
- `tabindex="-1"` on elements that should be programmatically focusable but not in the tab sequence (e.g., hidden preheader, skip link targets)

---

## 12. Screen Reader Behavior in Email

### Hidden Content in Email
- Visually hidden text for screen readers: `position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap;` — email-safe method that works across clients
- `mso-hide: all` — Outlook-only hide; does NOT affect screen readers; often confused as an accessibility tool but is purely visual for Outlook rendering
- `display: none` and `visibility: hidden` — hide from BOTH visual display AND screen readers; use for content that should be completely hidden (e.g., desktop-only content on mobile)
- `aria-hidden="true"` — hides from screen readers but remains visually visible; use on decorative elements
- Hidden preheader text: use `max-height: 0; overflow: hidden` rather than `display: none` if you want screen readers to read it as the email's opening context
- Preview text whitespace padding (`&zwnj;&nbsp;` repeated): must have `aria-hidden="true"` on the entire padding span — prevents screen readers from announcing dozens of blank characters

### ARIA Attributes in Email
- `role="presentation"` — on every layout table; the single most important ARIA attribute in email
- `role="article"` — on the main email content `<td>` wrapper; helps screen readers identify the email body vs surrounding client UI
- `role="img"` — on non-`<img>` elements acting as images (SVG, VML shapes)
- `role="separator"` — on decorative `<hr>` or divider `<td>` elements
- `role="list"` and `role="listitem"` — on table-faked lists (for Outlook compatibility while maintaining list semantics)
- `role="heading"` with `aria-level` — on elements acting as headings that can't use `<h1>`–`<h6>` tags (rare but sometimes necessary in complex email layouts)
- `aria-label` — provides accessible name for elements without visible text; note: Gmail strips this attribute, so don't rely on it as the sole accessible name
- `aria-labelledby` — references another element's text as the accessible name; also stripped by Gmail
- `aria-describedby` — references an element providing additional description; primarily useful in AMP email forms
- `aria-hidden="true"` — on decorative elements, spacer cells, spacer images, divider characters, preview text padding, tracking pixels
- `aria-live="polite"` — on regions that update dynamically in AMP emails (form feedback, live content updates)
- Note: Gmail, Yahoo, and some other clients strip many ARIA attributes — always ensure content is understandable without ARIA as a baseline

### Screen Reader Announcement Patterns in Email
- Spacer cells (`&nbsp;`, `&zwnj;`) must have `aria-hidden="true"` — otherwise screen readers announce "space" or "zero-width joiner" for every spacer cell
- `|` pipe separators between footer links: `aria-hidden="true"` — screen readers announce "vertical bar" for each one
- `•` bullet separators: `aria-hidden="true"` — screen readers announce "bullet" for each one
- Decorative characters (dashes, slashes, dots used as visual separators): `aria-hidden="true"` — with text alternatives if they convey meaning
- Emoji in email: should have descriptive text alternatives or `aria-label` — screen reader emoji support varies wildly across email clients
- Unicode symbols used for visual effect: `aria-hidden="true"` with adjacent visually hidden text describing the meaning

### Email-Specific Content Patterns for Screen Readers
- Strikethrough pricing: "Was $50, now $30" — screen readers may not convey `<del>` or `<s>` strikethrough; include explicit "Was" / "Now" text labels
- Discount badges: include text like "50% off" — not just a colored badge image
- Star ratings: include text like "Rated 4 out of 5 stars" — not just star images or unicode ★ characters alone
- Progress/status bars: include text description — not just a colored bar image
- "New" or "Sale" badges: include as real text or meaningful `alt` text — not decorative image-only
- Social proof ("1,234 people bought this"): real text, not image-only
- Countdown urgency ("Only 3 left!", "Offer ends in 2 hours"): real text, not image-only or animation-only
- Order status in transactional email: text label per status, not just a colored step indicator image

---

## 13. Email-Specific Accessibility Patterns

### Unsubscribe Accessibility
- Unsubscribe link must be clearly labeled and easy to find — not disguised as small, low-contrast footer text; this is both an accessibility and legal requirement
- Unsubscribe text must meet 4.5:1 contrast and minimum 12px font size — the most commonly failed accessibility checkpoint in email
- Unsubscribe link must not be image-only — must work with images off
- Unsubscribe link text: "Unsubscribe from these emails" or "Unsubscribe" — clear, descriptive, not hidden behind "Manage" or "Settings"
- `List-Unsubscribe` email header provides native client-level unsubscribe button — accessible by default in Gmail, Apple Mail, Outlook; the most accessible unsubscribe mechanism
- `List-Unsubscribe-Post: List-Unsubscribe=One-Click` — RFC 8058 one-click unsubscribe; reduces friction for all users including those using assistive technology

### Preference Center Link
- Must be clearly labeled (e.g., "Manage email preferences" not just "Preferences" or "Settings")
- Must meet all link accessibility requirements (contrast, size, descriptive text)
- Should be distinct from the unsubscribe link — users must understand the difference

### View in Browser Link
- Provides a critical fallback for email clients that render poorly — opening in a browser gives users access to full browser accessibility features
- Should be clearly labeled: "View this email in your browser"
- Place near the top of the email — first or second focusable element for easy keyboard/screen reader access
- The web-hosted version should also meet all accessibility requirements

### Plain Text MIME Part
- Every HTML email must include a `text/plain` MIME alternative — the ultimate accessible fallback; some users choose plain text clients specifically for accessibility
- Plain text version must contain all meaningful content from the HTML version
- All link URLs must be written out in full in plain text version
- Content must maintain logical order without table structure
- Alt text equivalents for key images should be included as text descriptions

### Forward / Share Accessibility
- "Forward to a friend" must be a text link, not image-only
- Social sharing links: descriptive text (e.g., "Share on Twitter") — not just an icon image with no alt text; if using icon images, provide meaningful `alt`

### Transactional Email Accessibility
- Order confirmation emails: all order details must be in live text (product names, prices, quantities, totals) — not in images or generated screenshots
- Shipping emails: tracking numbers must be selectable live text, not images
- Receipt emails: line-item data tables must use proper `<th>` with `scope` for screen reader navigation
- Account notification emails: critical action items must be prominently headed and in live text
- Password reset emails: the reset link must have clear, descriptive link text and be easily keyboard-accessible

---

## 14. Email Internationalization & Localization Accessibility

### Bidirectional Text in Email — WCAG 1.3.2 (Level A)
- `dir="rtl"` on `<html>` for RTL languages (Arabic, Hebrew, Urdu, Farsi) — email table layouts may need structural reversal (rightmost column becomes first column)
- `dir="ltr"` on inline LTR content within RTL emails (brand names, product codes, URLs)
- Bidirectional text mixing (e.g., English product names within Arabic body text): use `&lrm;` / `&rlm;` direction marks or `<bdo>` elements — prevents text reordering bugs in email rendering
- Table layout direction: RTL emails may need to reverse column order in the source code since CSS `direction` is unreliable across email clients

### Character Encoding in Email
- `<meta charset="UTF-8">` — ensures all characters render correctly across email clients; some older clients default to different encodings
- Special characters in email subject lines must be properly encoded — subject line encoding affects how the email appears in the inbox list
- Emoji in subject lines and body: test across email clients as rendering varies significantly

### Multilingual Email Accessibility
- `lang` attribute on each content block in a different language — WCAG 3.1.2 (Level AA); screen readers switch pronunciation engines at these boundaries
- Font choices must support all character sets used — Arial/Helvetica cover Latin, Cyrillic; CJK and Arabic scripts need specific font fallback stacks
- Line height adjustment for different scripts: CJK typically needs 1.6x–1.8x; Arabic/Devanagari may need more than Latin
- Minimum font sizes may need to be larger for complex scripts (CJK detail requires larger rendering; Arabic cursive connections need minimum 16px+)

---

## 15. Email Cognitive Accessibility

### Clear Language in Email — Best Practice for AA
- Write email copy at an accessible reading level — emails compete for attention; clarity benefits everyone including users with cognitive disabilities
- Use short sentences and paragraphs — email body copy should be scannable
- Front-load important information — many users only read the first few lines of an email
- Use active voice: "We shipped your order" not "Your order has been shipped by us"
- CTA button text should state the action clearly: "Track your package" not "Click here"

### Consistent Email Templates — WCAG 3.2.3 Consistent Navigation (Level AA)
- Email campaigns should maintain consistent header/footer structure across sends — subscribers develop navigation expectations; changing layout between emails disorients users
- Unsubscribe and preference center links: always in the footer, same position across all campaigns
- Navigation links: same order across campaign emails
- Logo and branding: same position across emails

### Predictable Behavior in Email — WCAG 3.2.1 On Focus (Level A)
- AMP email forms should not auto-submit on field change without explicit user action — WCAG 3.2.2 (Level A)
- Interactive email elements (CSS checkbox hack) should behave predictably — toggling a checkbox should show/hide the associated content, nothing else
- Confirmation steps for significant email actions (e.g., unsubscribe, cancellation) — WCAG 3.3.4 (Level AA)

### Content Organization in Email
- Clear, descriptive headings for each email section — enables scanning and screen reader navigation
- Break long emails into distinct sections with headings — email is not a web page; users expect to process it quickly
- Visual hierarchy (size, weight, color) must match semantic hierarchy (heading levels)
- Use spacer cells and dividers to separate sections — visual grouping aids comprehension
- Consider email length: very long emails should potentially be split into multiple sends or link to web content — reduces cognitive load

---

## 16. Email Accessibility Testing & Validation

### Contrast Testing for Email
- Test all text/background combinations with a contrast checker
- Test button text vs button background AND button vs surrounding email background
- Test in light mode AND dark mode (Apple Mail dark mode, Gmail dark mode, Outlook dark mode)
- Test with forced color inversions — Outlook.com and Gmail app may invert colors unpredictably
- Test text on background images against all possible underlying image areas
- Test footer/legal text contrast — most commonly failed checkpoint

### Screen Reader Testing for Email
- VoiceOver (macOS) — test in Apple Mail (best email accessibility support)
- VoiceOver (iOS) — test in iOS Mail app
- NVDA or JAWS (Windows) — test in Outlook desktop (Word rendering engine)
- TalkBack (Android) — test in Gmail app
- Verify: reading order matches intended content flow
- Verify: all images announce appropriate `alt` text
- Verify: layout tables are NOT announced as data tables (check `role="presentation"`)
- Verify: data tables (order items, pricing) ARE announced as tables with headers
- Verify: headings announce at correct levels and in correct order
- Verify: links announce their destination/purpose (not "click here")
- Verify: hidden preheader text is read as the email's opening content
- Verify: preview text padding (`&zwnj;&nbsp;`) is NOT announced
- Verify: decorative elements (spacers, dividers, separators) are NOT announced
- Verify: strikethrough pricing has "was/now" text labels announced
- Verify: mobile-only and desktop-only content behaves correctly in each context

### Keyboard Testing for Email
- Tab through entire email in webmail (Gmail, Outlook.com) to verify logical focus order
- Verify all links and buttons are reachable via Tab
- Verify focus indicators are visible on all focusable elements
- Verify no keyboard traps
- Test AMP email interactive components for full keyboard operability
- Test that tracked/redirected links (ESP click tracking) don't create navigation issues

### Client-Specific Accessibility Testing
- Gmail (web) — strips `<style>` blocks (breaking some screen reader optimizations), strips `aria-label`, strips `role` on some elements; test with reduced accessibility expectations
- Gmail (Android/iOS app) — different rendering from web; test separately
- Outlook desktop (Windows) — Word rendering engine; limited CSS support; test VML components with NVDA/JAWS
- Outlook (new) — better rendering than classic Outlook desktop; test separately
- Outlook.com — better accessibility support than desktop; forced dark mode may break contrast
- Apple Mail (macOS) — best overall accessibility support; test as the baseline
- iOS Mail — good VoiceOver support; primary mobile testing target
- Yahoo Mail — variable accessibility support; strips some ARIA attributes
- Thunderbird — good accessibility support; good NVDA testing companion

### Automated Testing Tools for Email
- Axe email accessibility checker
- Email on Acid accessibility check
- Litmus accessibility features
- Parcel.io email code editor (has accessibility hints)
- Manual review always required — automated tools catch ~30% of email accessibility issues; the rest require human judgment

### Most Common Email Accessibility Failures
- Missing `alt` text on images (including tracking pixels)
- Layout tables without `role="presentation"` — the #1 email-specific failure
- Insufficient color contrast in footers and legal text
- Generic link text ("Click here", "Read more", "Learn more")
- Missing `lang` attribute on `<html>` tag
- Critical content conveyed only through images (invisible with images off)
- Skipped heading levels (h1 → h3 with no h2)
- Missing `text/plain` MIME alternative
- Color as sole indicator of meaning (sale pricing, order status)
- Too-small touch targets for mobile links (especially in footers)
- Redundant links (image + text linking to same URL as separate `<a>` tags)
- Decorative elements not hidden from screen readers (spacers, dividers, separators)
- Preview text padding announced by screen readers (missing `aria-hidden`)
- Strikethrough pricing without "was/now" text labels
- Low-contrast unsubscribe link
- `<br><br>` used instead of `<p>` tags for paragraphs

---

## 17. WCAG AA Success Criteria — Email-Relevant Quick Reference

### Level A (Must Have)
- 1.1.1 Non-text Content — `alt` text on all email images; styled `alt` for image-off rendering
- 1.3.1 Info and Relationships — `role="presentation"` on layout tables; heading hierarchy; form labels in AMP; list semantics
- 1.3.2 Meaningful Sequence — source order matches visual reading order in table-based layout
- 1.3.3 Sensory Characteristics — don't reference "the red button" or "the image on the left" as sole instructions
- 1.4.1 Use of Color — links distinguished by more than color; status/error conveyed with text not just color
- 2.1.1 Keyboard — all email links/buttons keyboard reachable; AMP components keyboard operable
- 2.1.2 No Keyboard Trap — can Tab through entire email without getting stuck
- 2.2.2 Pause, Stop, Hide — animated GIFs can't be paused in email (limitation); keep them short and non-essential
- 2.3.1 Three Flashes — no GIF or CSS animation flashes more than 3 times per second
- 2.4.2 Page Titled — meaningful `<title>` tag for "View in browser" and webmail tab display
- 2.4.3 Focus Order — focus sequence follows table source code order
- 2.4.4 Link Purpose in Context — descriptive CTA button text; descriptive footer link text
- 3.1.1 Language of Page — `lang` on `<html>` for screen reader pronunciation
- 3.2.1 On Focus — no unexpected actions when tabbing to email elements
- 3.2.2 On Input — AMP forms don't auto-submit on field change
- 3.3.1 Error Identification — AMP form errors described in text
- 3.3.2 Labels or Instructions — AMP form fields have visible labels
- 4.1.1 Parsing — valid email HTML markup
- 4.1.2 Name, Role, Value — `role="presentation"` on layout tables; ARIA roles on interactive elements

### Level AA (Target Standard)
- 1.3.5 Identify Input Purpose — `autocomplete` on AMP email form fields
- 1.4.3 Contrast Minimum — 4.5:1 text contrast; test in light mode AND dark mode
- 1.4.5 Images of Text — use live text, not text-as-image (except logos); bulletproof buttons over image buttons
- 1.4.11 Non-text Contrast — 3:1 for button backgrounds, ghost button borders, icons, dividers
- 1.4.12 Text Spacing — set line height, paragraph spacing, letter/word spacing explicitly in email inline styles
- 2.4.6 Headings and Labels — descriptive `<h1>`–`<h4>` headings throughout email sections
- 2.4.7 Focus Visible — visible focus indicators on all focusable elements; don't use `outline: none` without replacement
- 3.1.2 Language of Parts — `lang` on content blocks in different languages within multilingual emails
- 3.2.3 Consistent Navigation — consistent email template structure across campaign sends
- 3.2.4 Consistent Identification — same function labeled the same way across emails (e.g., "Unsubscribe" not "Opt out" one week and "Remove me" the next)
- 3.3.3 Error Suggestion — AMP form error messages suggest how to fix the error
- 3.3.4 Error Prevention — confirmation step for significant AMP form submissions (unsubscribe, cancellation)

---

*Total email-specific accessibility items: 250+*
