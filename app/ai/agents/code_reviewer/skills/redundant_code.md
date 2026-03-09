# Redundant Code Detection — L3 Reference

## Patterns to Detect

### Duplicate Inline Styles
- Same `style` attribute value repeated on adjacent/sibling elements
- Identical `background-color` + `color` pairs that could use a CSS class
- Rule: `redundant-duplicate-style`

### Unused CSS Classes
- Classes defined in `<style>` block but never referenced in HTML body
- Rule: `redundant-unused-class`

### Dead MSO Conditionals
- `<!--[if mso]>` blocks with empty content or only whitespace
- Nested MSO conditionals that target the same version (e.g., nested `[if gte mso 9]`)
- Rule: `redundant-dead-mso`

### Repeated Table Attributes
- `cellpadding="0" cellspacing="0" border="0"` on every nested table — only needed on outermost
- `role="presentation"` repeated on layout tables already inside a presentation table (though not wrong, it's redundant at inner levels if outer already has it — classify as `info`)
- Rule: `redundant-table-attrs`

### Empty Elements
- `<td>&nbsp;</td>` spacers that could use `height` on `<td>` (info only)
- Empty `<style>` blocks
- Rule: `redundant-empty-element`

## False Positive Prevention
- Multiple inline styles are NORMAL in email — only flag when truly identical on siblings
- MSO conditionals with different version targeting are NOT redundant
- Tables with `cellpadding="0"` at every level is defensive and often intentional — severity: info
