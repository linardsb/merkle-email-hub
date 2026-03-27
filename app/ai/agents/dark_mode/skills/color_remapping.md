---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md section 11 -->
<!-- Last synced: 2026-03-13 -->

# Color Remapping Strategies

## Strategy 1: Auto-Remapping (Default)

Automatically map light <-> dark based on luminance:

### Background Colors
| Light Mode | Dark Mode | Usage |
|-----------|-----------|-------|
| #ffffff | #1a1a2e | Primary background |
| #f5f5f5 | #16213e | Secondary background |
| #fafafa | #1e1e3a | Tertiary background |
| #f0f0f0 | #252540 | Card/section background |
| #e0e0e0 | #2d2d50 | Divider/border areas |
| #eeeeee | #1f1f35 | Alternate row background |

### Text Colors
| Light Mode | Dark Mode | Usage |
|-----------|-----------|-------|
| #000000 | #e0e0e0 | Primary text |
| #1a1a1a | #d4d4d4 | Heading text |
| #333333 | #cccccc | Body text |
| #666666 | #a0a0a0 | Secondary text |
| #999999 | #808080 | Muted/caption text |

### Accent/CTA Colors
| Light Mode | Dark Mode | Notes |
|-----------|-----------|-------|
| #007bff | #4da3ff | Blue: lighten 20% |
| #28a745 | #5fd97e | Green: lighten 20% |
| #dc3545 | #f06070 | Red: lighten 15% |
| #ffc107 | #ffd54f | Yellow: keep bright |

## Strategy 2: Brand-Aware Remapping

When brand colors are provided, follow these rules:
1. Primary brand color -> darken by 15-20% for backgrounds, lighten for text-on-dark
2. Secondary brand color -> similar treatment
3. Neutral palette -> use auto-remapping table above
4. Never fully invert brand colors -- maintain recognition

## Strategy 3: High-Contrast Mode

For maximum accessibility:
- Background: #000000 or #121212
- Text: #ffffff
- Links: #6cb4ff (light blue)
- Borders: #404040

## Forced Inversion Survival Patterns

How colors behave when email clients forcibly invert (Outlook desktop, Gmail):

### Background Survival
| Color | Inversion Behavior |
|-------|-------------------|
| #ffffff (pure white) | Always inverted to dark — avoid if preserving background |
| #f5f5f5 to #fafafa (off-white) | Sometimes inverted, sometimes not — less predictable |
| #e0e0e0 to #eeeeee (light gray) | Usually inverted |
| #666666 to #999999 (mid-gray) | **Unpredictable zone** — may or may not invert |
| #333333 to #444444 (dark gray) | Usually NOT inverted (already dark) |
| #1a1a1a to #222222 (near-black) | Never inverted |
| #000000 (pure black) | Never inverted |

### Text Survival
| Color | Inversion Behavior |
|-------|-------------------|
| #000000 (pure black) | Always inverted to light/white |
| #333333 (dark gray) | Usually inverted to light gray |
| #666666 (mid-gray) | Unpredictable |
| #cccccc (light gray) | Usually NOT inverted (already light) |
| #ffffff (white) | Never inverted |

### Accent Color Survival
| Pattern | Inversion Behavior |
|---------|-------------------|
| High saturation + high brightness (#ffcc00) | Likely inverted or muted |
| High saturation + medium brightness (#1a73e8) | May or may not be inverted |
| High saturation + low brightness (#0d47a1) | Usually NOT inverted |
| Low saturation / pastels (#e3f2fd) | Likely inverted |

## Magic Color Values

Specific color values that may cause Outlook to skip inversion:

- `#010101` vs `#000000` — Outlook may treat pure black differently from near-black; `#010101` is more reliably left alone
- `#fefefe` vs `#ffffff` — near-white may be treated differently from pure white; `#fefefe` avoids some forced-inversion triggers

**Warning:** These are anecdotal and version-dependent. Do not rely on them as the sole strategy — use as an additional defense alongside `[data-ogsc]`/`[data-ogsb]` overrides.

## WCAG AA Contrast Formula

Relative luminance: `L = 0.2126 * R + 0.7152 * G + 0.0722 * B`
(Where R, G, B are linearized: `c <= 0.03928 ? c/12.92 : ((c+0.055)/1.055)^2.4`)

Contrast ratio: `(L1 + 0.05) / (L2 + 0.05)` where L1 is lighter

**Minimum ratios:**
- Normal text (< 18px): 4.5:1
- Large text (>= 18px or >= 14px bold): 3:1
- UI components: 3:1

## Common Email Color Pairs (Pre-Verified)

These pairs all meet WCAG AA 4.5:1:
- `#1a1a2e` bg + `#e0e0e0` text = 10.2:1
- `#16213e` bg + `#f5f5f5` text = 11.8:1
- `#121212` bg + `#ffffff` text = 17.4:1
- `#1a1a2e` bg + `#4da3ff` link = 5.3:1
- `#121212` bg + `#5fd97e` link = 7.1:1

## CSS Implementation Pattern

```css
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a2e !important; }
  .dark-bg-secondary { background-color: #16213e !important; }
  .dark-text { color: #e0e0e0 !important; }
  .dark-text-heading { color: #f5f5f5 !important; }
  .dark-text-muted { color: #a0a0a0 !important; }
  .dark-border { border-color: #2d2d50 !important; }
  .dark-link { color: #4da3ff !important; }
}

/* Outlook overrides */
[data-ogsc] .dark-text { color: #e0e0e0 !important; }
[data-ogsc] .dark-text-heading { color: #f5f5f5 !important; }
[data-ogsb] .dark-bg { background-color: #1a1a2e !important; }
[data-ogsb] .dark-bg-secondary { background-color: #16213e !important; }
```