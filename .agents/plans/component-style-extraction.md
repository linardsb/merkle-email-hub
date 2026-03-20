# Plan: Extract Component `<style>` Tags into Email Shell

## Context

All 10 modern email components (in both `email-templates/components/*.html` files and `app/components/data/seeds.py`) have inline `<style>` blocks containing:
- **Dark mode CSS** — component-specific class overrides for `@media (prefers-color-scheme: dark)` and Outlook `[data-ogsc]`/`[data-ogsb]` selectors
- **Responsive CSS** — `.column`, `.bannerimg`, `.hide` rules that **duplicate** what the shell already provides

Components should be pure HTML blocks. Their CSS belongs in the email shell's `<style>` block.

### Style Audit — What Each Component Contributes

| Component | Dark Mode Classes | Responsive (duplicates shell) |
|-----------|-------------------|-------------------------------|
| Email Header (#1) | `.header-bg`, `.header-link` | none |
| Email Footer (#2) | `.footer-bg`, `.footer-text`, `.footer-link` | none |
| CTA Button (#3) | `.cta-btn`, `.cta-btn a`, `.cta-ghost`, `.cta-ghost a` | none |
| Hero Block (#4) | `.hero-overlay`, `.hero-title`, `.hero-subtitle` | none |
| Product Card (#5) | `.product-card`, `.product-title`, `.product-price`, `.product-desc` | none |
| Social Icons (#7) | `.social-bg`, `.social-label` | none |
| Image Block (#8) | `.imgblock-caption` | `.bannerimg` (dup) |
| Text Block (#9) | `.textblock-bg`, `.textblock-heading`, `.textblock-body` | none |
| Divider (#10) | `.divider-line` | none |
| Column Layout 2 (#11) | `.col2-bg` | `.column` (dup) |
| Column Layout 3 (#12) | `.col3-bg` | `.column` (dup) |
| Column Layout 4 (#13) | `.col4-bg` | `.column` (dup) |
| Reverse Column (#14) | `.revcol-bg` | `.column` (dup) |
| Full-Width Image (#15) | none | `.bannerimg` (dup) |
| Preheader (#16) | `.preheader-bg`, `.preheader-link` | `.hide` (dup) |
| Article Card (#17) | `.artcard-bg`, `.artcard-heading`, `.artcard-body` | `.column` (dup) |
| Image Grid (#18) | none | `.column`, `.bannerimg` (dup) |
| Logo Header (#19) | `.logoheader-bg` | none |
| Navigation Bar (#20) | `.navbar-bg`, `.navbar-link` | `.hide` (dup) |

### What stays in the shell already
The shell's `<style>` block already has:
- `.column` responsive rules
- `.bannerimg` responsive rules
- `.hide` responsive rules
- `.dark-bg`, `.dark-text` dark mode base classes

### What needs to be ADDED to the shell
All component-specific dark mode classes + their Outlook `[data-ogsc]`/`[data-ogsb]` counterparts. These are deduplicated and grouped below in the implementation steps.

## Files to Modify

1. **`email-templates/components/email-shell.html`** — Add consolidated component dark mode styles to `<style>` block
2. **`app/components/data/seeds.py`** — Same change to the Email Shell seed (#0) `html_source`, plus strip `<style>` from all component seeds (#1-#20)
3. **`email-templates/components/navigation-bar.html`** — Remove `<style>` block
4. **`email-templates/components/logo-header.html`** — Remove `<style>` block
5. **`email-templates/components/image-grid.html`** — Remove `<style>` block
6. **`email-templates/components/article-card.html`** — Remove `<style>` block
7. **`email-templates/components/preheader.html`** — Remove `<style>` block
8. **`email-templates/components/full-width-image.html`** — Remove `<style>` block
9. **`email-templates/components/reverse-column.html`** — Remove `<style>` block
10. **`email-templates/components/column-layout-4.html`** — Remove `<style>` block
11. **`email-templates/components/column-layout-3.html`** — Remove `<style>` block
12. **`email-templates/components/column-layout-2.html`** — Remove `<style>` block

## Implementation Steps

### Step 1: Add component dark mode styles to the email shell

In **`email-templates/components/email-shell.html`**, expand the `<style>` block (lines 24-48). After the existing dark mode rules for `.dark-bg` / `.dark-text` (line 45-47), add all component-specific dark mode CSS. Group by concern:

```css
    /* ── Component dark mode overrides ── */
    @media (prefers-color-scheme: dark) {
      /* Structure */
      .header-bg, .footer-bg, .navbar-bg, .logoheader-bg,
      .preheader-bg, .col2-bg, .col3-bg, .col4-bg,
      .revcol-bg, .social-bg, .textblock-bg { background-color: #1a1a2e !important; }

      .artcard-bg, .product-card { background-color: #1a1a2e !important; }
      .product-card { background-color: #2d2d44 !important; }

      /* Text */
      .header-link, .navbar-link, .preheader-link,
      .footer-link { color: #8ecae6 !important; }
      .footer-text, .social-label, .imgblock-caption { color: #b0b0b0 !important; }
      .textblock-heading, .artcard-heading, .product-title,
      .hero-title { color: #e0e0e0 !important; }
      .textblock-body, .artcard-body,
      .hero-subtitle { color: #cccccc !important; }
      .product-price { color: #8ecae6 !important; }
      .product-desc { color: #b0b0b0 !important; }

      /* Interactive */
      .cta-btn { background-color: #4895ef !important; }
      .cta-btn a { color: #ffffff !important; }
      .cta-ghost { border-color: #8ecae6 !important; }
      .cta-ghost a { color: #8ecae6 !important; }

      /* Hero */
      .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }

      /* Divider */
      .divider-line { border-top-color: #444466 !important; }
    }

    /* Outlook dark mode selectors */
    [data-ogsc] .header-bg, [data-ogsc] .footer-bg, [data-ogsc] .navbar-bg,
    [data-ogsc] .logoheader-bg, [data-ogsc] .preheader-bg,
    [data-ogsc] .col2-bg, [data-ogsc] .col3-bg, [data-ogsc] .col4-bg,
    [data-ogsc] .revcol-bg, [data-ogsc] .social-bg,
    [data-ogsc] .textblock-bg, [data-ogsc] .artcard-bg { background-color: #1a1a2e !important; }
    [data-ogsc] .product-card { background-color: #2d2d44 !important; }

    [data-ogsc] .header-link, [data-ogsc] .navbar-link,
    [data-ogsc] .preheader-link, [data-ogsc] .footer-link { color: #8ecae6 !important; }
    [data-ogsc] .footer-text, [data-ogsc] .social-label,
    [data-ogsc] .imgblock-caption { color: #b0b0b0 !important; }
    [data-ogsc] .textblock-heading, [data-ogsc] .artcard-heading,
    [data-ogsc] .product-title, [data-ogsc] .hero-title { color: #e0e0e0 !important; }
    [data-ogsb] .textblock-body, [data-ogsb] .artcard-body,
    [data-ogsc] .hero-subtitle { color: #cccccc !important; }
    [data-ogsc] .product-price { color: #8ecae6 !important; }

    [data-ogsc] .cta-btn { background-color: #4895ef !important; }
    [data-ogsc] .cta-ghost { border-color: #8ecae6 !important; }
    [data-ogsc] .divider-line { border-top-color: #444466 !important; }
```

**Important details:**
- Note `[data-ogsb]` (not `[data-ogsc]`) for `.textblock-body`, `.artcard-body` — this matches the original component source
- `.product-card` uses `#2d2d44` (different from the standard `#1a1a2e`)
- Keep the existing `.dark-bg` / `.dark-text` rules — those are shell-level base classes

The `<slot data-slot="head_styles"></slot>` on line 50 can remain for future dynamic style injection.

### Step 2: Strip `<style>` from standalone HTML component files

For each of these 10 files, remove the entire `<style>...</style>` block (including the opening/closing tags):

1. `email-templates/components/navigation-bar.html` — Remove lines 2-12 (the `<style>` block)
2. `email-templates/components/logo-header.html` — Remove lines 2-7
3. `email-templates/components/image-grid.html` — Remove lines 2-7
4. `email-templates/components/article-card.html` — Remove lines 2-14
5. `email-templates/components/preheader.html` — Remove lines 2-12
6. `email-templates/components/full-width-image.html` — Remove lines 2-6
7. `email-templates/components/reverse-column.html` — Remove lines 2-10
8. `email-templates/components/column-layout-4.html` — Remove lines 2-10
9. `email-templates/components/column-layout-3.html` — Remove lines 2-10
10. `email-templates/components/column-layout-2.html` — Remove lines 2-10

Each file's first line (the HTML comment like `<!-- Navigation Bar — ... -->`) stays. The HTML content after the `<style>` block stays.

### Step 3: Update seeds.py — Email Shell seed (#0)

In `app/components/data/seeds.py`, update the Email Shell's `html_source` (seed #0, starts at line 34) to include the consolidated component dark mode styles. Add the same CSS block from Step 1 into the `<style>` tag (after line 77's `[data-ogsb] .dark-text` rule, before `</style>`).

### Step 4: Update seeds.py — Strip `<style>` from all component seeds

For each component seed that has a `<style>` block in its `html_source`, remove the `<style>...</style>` portion:

- Seed #1 (Email Header) — lines 141-148: remove `<style>` block
- Seed #2 (Email Footer) — lines 185-194: remove `<style>` block
- Seed #3 (CTA Button) — lines 232-241: remove `<style>` block
- Seed #4 (Hero Block) — lines 293-301: remove `<style>` block
- Seed #5 (Product Card) — lines 379-389: remove `<style>` block
- Seed #7 (Social Icons) — lines 456-463: remove `<style>` block
- Seed #8 (Image Block) — lines 507-515: remove `<style>` block
- Seed #9 (Text Block) — lines 548-557: remove `<style>` block
- Seed #10 (Divider) — lines 588-593: remove `<style>` block
- Seed #11 (Column Layout 2) — lines 622-630: remove `<style>` block
- Seed #12 (Column Layout 3) — lines 690-698: remove `<style>` block
- Seed #13 (Column Layout 4) — lines 776-784: remove `<style>` block
- Seed #14 (Reverse Column) — lines 880-888: remove `<style>` block
- Seed #15 (Full-Width Image) — lines 948-952: remove `<style>` block
- Seed #16 (Preheader) — lines 999-1009: remove `<style>` block
- Seed #17 (Article Card) — lines 1075-1087: remove `<style>` block
- Seed #18 (Image Grid) — lines 1196-1201: remove `<style>` block
- Seed #19 (Logo Header) — lines 1282-1287: remove `<style>` block
- Seed #20 (Navigation Bar) — lines 1334-1344: remove `<style>` block

### Step 5: Update seeds.py docstring

The module docstring (line 3-6) currently says:
> Each component includes dark mode CSS (@media prefers-color-scheme), Outlook dark mode selectors...

Update to reflect the new approach:
```python
"""Seed data for pre-tested email components.

Dark mode CSS and Outlook dark mode selectors are consolidated
in the Email Shell component. Individual components contain
only HTML markup with slot markers and inline styles.
"""
```

### Step 6: Verify no downstream breakage

Run `make check` to verify:
- The CSS compiler pipeline (`app/email_engine/css_compiler/`) still works — it extracts `<style>` blocks from assembled HTML, which now only exist in the shell
- `SectionAdapter` (`app/components/section_adapter.py`) still works — it sanitizes component HTML; removing `<style>` blocks simplifies its input
- `TemplateComposer` (`app/ai/templates/composer.py`) still works — it concatenates section blocks; they no longer carry duplicate styles
- File size analyzer (`app/qa_engine/file_size_analyzer.py`) still correctly measures `<style>` blocks in the final assembled output

## Security Checklist
No new endpoints, routes, or API changes in this plan. This is a static content refactor:
- [x] No new endpoints — not applicable
- [x] No user input changes — component HTML is static seed data
- [x] No auth changes
- [x] Dark mode CSS values are unchanged — visual parity maintained

## Verification
- [ ] `make check` passes (lint + types + tests + security)
- [ ] Assembled email output still contains all dark mode CSS (in `<head>`, not scattered in `<body>`)
- [ ] No duplicate `.column` / `.bannerimg` / `.hide` rules in final output
- [ ] Component `.html` files contain zero `<style>` tags (verified with `grep -l '<style' email-templates/components/ | grep -v email-shell`)
