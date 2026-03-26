---
token_cost: 450
priority: 2
---

# Email Client Rendering Constraints for Content

## Preheader Length by Client

| Client | Visible Chars | Notes |
|--------|--------------|-------|
| Gmail (web/mobile) | ~100-110 | After subject line; rest hidden |
| Apple Mail | ~140 | List view |
| Outlook Desktop | ~50-60 | Narrow preview pane |
| Yahoo | ~100 | |
| Samsung Mail | ~90 | |

**Rule:** Critical message in first 50 chars (universal safe). Supporting detail 51-100 (most clients). Optional detail 101-140 (Apple Mail bonus).

## Subject Line Truncation

| Context | Visible Chars |
|---------|--------------|
| Mobile notification (all) | ~35-40 |
| Mobile inbox list (all) | ~50-55 |
| Desktop Gmail | ~70 |
| Desktop Outlook | ~55-60 |
| Desktop Apple Mail | ~70-80 |

**Rule:** Front-load value proposition in first 35 chars. Keep total under 60 for universal safety.

## CTA Button Text

- VML `<v:roundrect>` (Outlook): fixed-width element — text overflows/clips if too long
- **Rule:** 2-5 words maximum, prefer action verbs
- Target 120-200px button widths
- Bad: "Learn More About Our Latest Features" — Good: "See Features" or "Learn More"

## Body Copy in Table Cells

- `<td>` cells have fixed widths (300-560px depending on layout)
- Outlook's Word engine doesn't hyphenate — long words overflow
- **Rule:** Avoid words >20 characters without `&shy;` soft hyphens
- Outlook ignores `word-break` CSS; only `word-wrap: break-word` partially works

## Character Encoding Safety

| Character | Issue | Safe Alternative |
|-----------|-------|-----------------|
| Smart quotes `\u201C\u201D\u2018\u2019` | `?` or mojibake in older Outlook / non-UTF-8 ESPs | Straight quotes `"` `'` |
| Em dash `\u2014` | Breaks in some legacy systems | ` - ` or ` -- ` |
| Ellipsis `\u2026` | Safe in modern clients | `...` universally safe |
| Non-ASCII (accented, CJK) | Requires `charset=UTF-8` in `<head>` | Flag if generating non-ASCII |

**Rule:** When audience includes Outlook Desktop or unknown clients, prefer ASCII-safe alternatives.

## Line Length and Readability

| Layout | Chars/Line | Guidance |
|--------|-----------|----------|
| 600px width, 32px padding, 16px font | ~50-60 | Standard sentence length |
| 300px column (2-col), 16px font | ~25-35 | Shorter sentences required |
| Optimal reading | 45-75 | Target range |

**Rule:** Adapt sentence length to column width context when provided in metadata.
