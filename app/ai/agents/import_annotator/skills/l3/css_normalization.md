---
token_cost: 350
priority: 2
version: "1.0.0"
---
# CSS Normalization Patterns in Imported Email HTML

## Shorthand Expansion
If raw HTML (no compiler step), flag unexpanded shorthands (`margin`, `padding`, `border`, `font`, `background`) for compiler. If post-compiler, shorthands already expanded — skip.

## Vendor Prefixes
`-webkit-`, `-moz-`, `-ms-`, `-o-` prefixes: map to standard property for annotation. Preserve in output (still needed for some clients).

## !important Density
High count (>20 per email): indicates Mailchimp/Stripo export (defensive `!important`). Don't strip. Annotate as "tool-generated defensive styles".

## Duplicate Properties
Same property twice in one `style=""`: progressive enhancement pattern.
```
background: #fff; background: linear-gradient(...);
```
First = fallback, second = progressive. Annotate intent.

## Class vs Inline Conflicts
When `<style>` block AND `style=""` both set same property: inline wins in email. `<style>` block is progressive enhancement only. Annotate which is authoritative.

## Key Rules
- Never strip vendor prefixes — they are needed
- High `!important` count is diagnostic (builder export), not a bug
- Duplicate properties are intentional progressive enhancement
