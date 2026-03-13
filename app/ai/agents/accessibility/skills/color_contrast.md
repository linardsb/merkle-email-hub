<!-- L4 source: docs/SKILL_email-accessibility-wcag-aa.md section 6 -->
<!-- Last synced: 2026-03-13 -->

# Color & Contrast in Email — WCAG AA Requirements

Contrast ratios, color independence rules, dark mode considerations, and
email-specific challenges. Footer text is the #1 contrast failure in email.

---

## Text Contrast — WCAG 1.4.3 (Level AA)

| Text Type | Minimum Ratio | Email Context |
|-----------|--------------|---------------|
| Normal text (< 18px) | 4.5:1 | Body copy, captions, disclaimers, footer/legal |
| Large text (>= 18px or >= 14px bold) | 3:1 | Headlines, subheadings |
| Preheader text | 4.5:1 | Even if visually small — may become visible in some contexts |
| Footer/unsubscribe | 4.5:1 | Most commonly failed checkpoint in email |
| Text on background images | 4.5:1 | Against ALL areas the text may overlap — use overlay `<td>` |

### Lightest Passing Grays

- On white (`#ffffff`): `#767676` is the lightest gray that passes 4.5:1
- On dark background (`#1a1a2e`): minimum approximately `#8a8a8a` for 4.5:1

---

## Non-Text Contrast — WCAG 1.4.11 (Level AA)

All UI components and meaningful graphical objects need 3:1 minimum:

| Element | Requirement |
|---------|-------------|
| Button background vs surrounding email background | 3:1 — button must be identifiable |
| Ghost/outline button border vs surrounding background | 3:1 |
| Icons (social, feature) vs email background | 3:1 |
| Meaningful divider lines | 3:1 (decorative dividers exempt) |
| AMP form field boundaries | 3:1 |
| Focus indicators | 3:1 against adjacent colors |

---

## Common Email Color Pairs

### Passing (>= 4.5:1 for text)

| Text | Background | Ratio | Use Case |
|------|-----------|-------|----------|
| `#000000` | `#ffffff` | 21:1 | Maximum contrast |
| `#333333` | `#ffffff` | 12.6:1 | Body text on white |
| `#1a1a1a` | `#ffffff` | 17.1:1 | Headings on white |
| `#ffffff` | `#007bff` | 4.6:1 | White on blue CTA (barely passes) |
| `#ffffff` | `#dc3545` | 4.6:1 | White on red CTA |
| `#1a1a1a` | `#f5f5f5` | 15.0:1 | Dark text on light gray |

### Failing (< 4.5:1 for text)

| Text | Background | Ratio | Issue |
|------|-----------|-------|-------|
| `#999999` | `#ffffff` | 2.8:1 | Too low — use `#767676` minimum |
| `#ffffff` | `#ffc107` | 1.2:1 | White on yellow — unreadable |
| `#cccccc` | `#ffffff` | 1.6:1 | Light gray on white |
| `#007bff` | `#f0f0f0` | 3.5:1 | Blue on light gray — fails for small text |

---

## Relative Luminance Calculation

```
For each sRGB channel (R, G, B) with value 0-255:
1. Normalize: c = value / 255
2. Linearize: c <= 0.03928 ? c/12.92 : ((c + 0.055) / 1.055) ^ 2.4
3. Luminance: L = 0.2126*R + 0.7152*G + 0.0722*B

Contrast ratio = (L_lighter + 0.05) / (L_darker + 0.05)
```

---

## Color Independence — WCAG 1.4.1 (Level A)

Never use color as the sole means of conveying information:

| Pattern | Bad | Good |
|---------|-----|------|
| Sale pricing | Red vs black price colors only | "Was $50, now $30" text labels |
| Order status | Colored dots only | Text labels: "Shipped", "Cancelled" |
| Error states | Red color only | Icon + text message |
| Links in body text | Color change only | Underline + color change |
| Required fields (AMP) | Red asterisk only | "Required" text label |

---

## Link Distinguishability

Links within body text must be distinguishable by more than color alone:

1. **Preferred:** `text-decoration: underline` on body text links
2. **Alternative:** 3:1 contrast between link color and surrounding text color
   - Example: body `#333333`, link `#007bff` — contrast between them 3.2:1 (passes)

CTA buttons and navigation links: `text-decoration: none` is acceptable where
the link nature is visually obvious (button shape, navigation context).

---

## Email Dark Mode Contrast

Dark mode is NOT optional — Apple Mail, Gmail, Outlook all have dark modes that
aggressively modify email colors.

### Key Rules

- Colors passing in light mode may fail after dark mode inversion
- `@media (prefers-color-scheme: dark)` styles must maintain all contrast ratios
- Avoid pure `#ffffff` / `#000000` — use off-white on near-black (`#f0f0f0` on `#1a1a1a`)
- `[data-ogsc]` / `[data-ogsb]` (Outlook.com dark mode) styles must also maintain contrast
- Forced inversions by Gmail/Outlook.com may break contrast unpredictably

### Dark Mode Pairs — Verified

| Text | Background | Ratio |
|------|-----------|-------|
| `#e0e0e0` | `#1a1a2e` | 10.2:1 |
| `#f5f5f5` | `#16213e` | 11.8:1 |
| `#ffffff` | `#121212` | 17.4:1 |
| `#4da3ff` | `#1a1a2e` | 5.3:1 |

---

## High Contrast Mode

- `@media (prefers-contrast: high)` — provide enhanced contrast where clients support it
- Button borders/outlines must remain visible in forced high contrast mode
- Text on background images needs solid-color fallback behind text
