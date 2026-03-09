# Color Contrast — WCAG AA for Email

## WCAG AA Contrast Thresholds

| Text Type | Minimum Ratio | Examples |
|-----------|--------------|----------|
| Normal text (< 18px) | 4.5:1 | Body copy, captions, disclaimers |
| Large text (>= 18px or >= 14px bold) | 3:1 | Headlines, subheadings |
| UI components | 3:1 | Buttons, form controls, icons |
| Decorative text | None | Logos, brand names in brand colors |

## Relative Luminance Calculation

```
For each sRGB channel (R, G, B) with value 0-255:
1. Convert to 0-1: c = value / 255
2. Linearize: c <= 0.03928 ? c/12.92 : ((c+0.055)/1.055)^2.4
3. Luminance: L = 0.2126*R + 0.7152*G + 0.0722*B
```

Contrast ratio: `(L_lighter + 0.05) / (L_darker + 0.05)`

## Common Email Color Pairs — Verified

### Passing Pairs (>= 4.5:1)
| Text | Background | Ratio | Use Case |
|------|-----------|-------|----------|
| #000000 | #ffffff | 21:1 | Maximum contrast |
| #333333 | #ffffff | 12.6:1 | Body text on white |
| #1a1a1a | #ffffff | 17.1:1 | Headings on white |
| #ffffff | #007bff | 4.6:1 | White on blue CTA (barely passes) |
| #ffffff | #28a745 | 4.5:1 | White on green CTA (borderline) |
| #ffffff | #dc3545 | 4.6:1 | White on red CTA |
| #1a1a1a | #f5f5f5 | 15.0:1 | Dark text on light gray |

### Failing Pairs (< 4.5:1)
| Text | Background | Ratio | Issue |
|------|-----------|-------|-------|
| #666666 | #ffffff | 5.7:1 | Passes, but poor readability |
| #999999 | #ffffff | 2.8:1 | Fails — too low contrast |
| #ffffff | #ffc107 | 1.2:1 | White on yellow — unreadable |
| #cccccc | #ffffff | 1.6:1 | Light gray on white — fails |
| #007bff | #f0f0f0 | 3.5:1 | Blue on light gray — fails for small text |

### Dark Mode Pairs — Verified
| Text | Background | Ratio |
|------|-----------|-------|
| #e0e0e0 | #1a1a2e | 10.2:1 |
| #f5f5f5 | #16213e | 11.8:1 |
| #ffffff | #121212 | 17.4:1 |
| #4da3ff | #1a1a2e | 5.3:1 |
| #a0a0a0 | #1a1a2e | 5.1:1 |

## Fixing Common Contrast Issues

### Issue: Light Gray Text on White
```
Before: color: #999999; background: #ffffff  (2.8:1 FAIL)
After:  color: #767676; background: #ffffff  (4.5:1 PASS)
```
`#767676` is the lightest gray that passes on white.

### Issue: White Text on Colored CTA
If the button color is too light for white text, darken the button:
```
Before: color: #ffffff; background: #5cb85c  (3.3:1 FAIL)
After:  color: #ffffff; background: #3d8b3d  (4.9:1 PASS)
```

### Issue: Placeholder/Muted Text
Use `#767676` as the minimum for muted text on white backgrounds.
For dark backgrounds (#1a1a2e), minimum is approximately `#8a8a8a` (4.5:1).

## Link Distinguishability

Links within body text must be distinguishable:
1. **Underline** (preferred) — `text-decoration: underline`
2. **OR** 3:1 contrast between link color and surrounding text color

Example: Body text #333333, link #007bff (contrast between them: 3.2:1 PASS)
