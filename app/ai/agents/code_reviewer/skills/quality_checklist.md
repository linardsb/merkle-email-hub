<!-- L4 source: none (original content — pre-QA gate checklist) -->
# 40-Point Email Quality Checklist

## Document Structure (10 points)

1. [ ] `<!DOCTYPE html>` declaration present
2. [ ] `<html>` tag with `lang` attribute
3. [ ] `<meta charset="utf-8">` in `<head>`
4. [ ] `<meta name="viewport" content="width=device-width, initial-scale=1">` in `<head>`
5. [ ] `<title>` element in `<head>` (matches email subject)
6. [ ] `<meta name="color-scheme" content="light dark">` for dark mode
7. [ ] `xmlns:v` and `xmlns:o` on `<html>` if VML is used
8. [ ] XML processing instruction for Office settings (DPI, PNG)
9. [ ] No duplicate `<head>` or `<body>` tags
10. [ ] All tags properly nested and closed

## Tables & Layout (8 points)

11. [ ] All layout tables have `role="presentation"`
12. [ ] All tables have `cellpadding="0"` and `cellspacing="0"`
13. [ ] Content area constrained to 600px max
14. [ ] MSO ghost table wraps max-width content
15. [ ] No nested tables deeper than 4 levels
16. [ ] `border-collapse:collapse` on layout tables
17. [ ] `mso-table-lspace:0pt; mso-table-rspace:0pt` on tables
18. [ ] No flex/grid layout (table-based only)

## Images (6 points)

19. [ ] Every `<img>` has `alt` attribute (descriptive or empty for decorative)
20. [ ] Every `<img>` has `width` and `height` HTML attributes
21. [ ] All images have `style="display:block; border:0"`
22. [ ] All image `src` URLs use HTTPS
23. [ ] Placeholder images use `https://placehold.co/`
24. [ ] No `<img>` with empty `src` attribute

## Typography (4 points)

25. [ ] Web-safe font stacks with fallbacks on all text elements
26. [ ] `font-family` set on `<td>` elements (not inherited)
27. [ ] `mso-line-height-rule:exactly` where line-height is set
28. [ ] `mso-font-alt` for web fonts

## CSS & Styling (4 points)

29. [ ] Critical styles inlined (not relying on `<style>` block alone)
30. [ ] No CSS variables, calc(), clamp(), min(), max()
31. [ ] No `position`, `flexbox`, or `grid` for layout
32. [ ] Colors use 3 or 6 digit hex (not rgb(), hsl(), named colors)

## Accessibility (4 points)

33. [ ] `lang` attribute on `<html>`
34. [ ] `role="article"` + `aria-roledescription="email"` on wrapper
35. [ ] Heading hierarchy sequential (h1 → h2 → h3)
36. [ ] Minimum 4.5:1 contrast ratio for text

## Links & CTAs (4 points)

37. [ ] All links use HTTPS
38. [ ] All links have descriptive text (not "click here")
39. [ ] CTA buttons have VML fallback for Outlook
40. [ ] No `javascript:` protocol in any href

## Scoring

- **40/40**: Production ready
- **35-39**: Minor issues, production acceptable
- **30-34**: Needs fixes before production
- **25-29**: Significant issues
- **< 25**: Major rework needed
