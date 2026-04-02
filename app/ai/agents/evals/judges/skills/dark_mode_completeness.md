# Dark Mode Completeness — Judge Reference

## Minimum Viable Dark Mode (All Three Required)

### 1. Meta Tags
```html
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
```
Both meta tags are required. `color-scheme` is the standard; `supported-color-schemes` is the Apple Mail legacy variant.

### 2. CSS Media Query
```css
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a1a !important; }
  .dark-text { color: #f0f0f0 !important; }
}
```
Must contain actual color overrides — an empty media query is incomplete.

### 3. Outlook Dark Mode Selectors
```css
[data-ogsc] .dark-text { color: #f0f0f0 !important; }
[data-ogsb] .dark-bg { background-color: #1a1a1a !important; }
```
Outlook ignores `@media (prefers-color-scheme)` entirely. Without `[data-ogsc]`/`[data-ogsb]` selectors, Outlook users get broken dark mode. Every color override in the media query should have a corresponding Outlook selector.

## Pass/Fail Matrix

| Meta tags | Media query | Outlook selectors | Verdict |
|-----------|-------------|-------------------|---------|
| Yes | Yes | Yes | **PASS** |
| Yes | Yes | No | **FAIL** — Outlook users get broken dark mode |
| Yes | No | Yes | **FAIL** — Non-Outlook clients get no dark mode |
| No | Yes | Yes | **FAIL** — Apple Mail/iOS won't activate dark mode |
| Partial | Yes | Yes | **FAIL** — Missing one of the two meta tags |

## Common Edge Cases

- **Already-dark emails**: If the email is designed with a dark background by default, dark mode support may be minimal (just preserving existing dark colors). Judge should verify the meta tags are present but not require extensive color remapping.
- **Selective dark mode**: Some sections may intentionally remain unchanged in dark mode (e.g., brand-colored hero banners). This is acceptable if other sections are properly adapted.
- **`!important` usage**: Required in dark mode CSS to override inline styles. Do not flag `!important` as bad practice in dark mode context.
