<!-- L4 source: docs/esp_personalisation/ (all 7 ESP files) -->
<!-- L3 source: app/ai/agents/personalisation/skills/*.md -->
# Personalisation Syntax — Code Review Reference

## Quick-Reference Delimiter Table

| ESP | Language | Output Delimiters | Logic Delimiters | Conditional Close |
|-----|----------|-------------------|------------------|-------------------|
| Braze | Liquid | `{{ }}` | `{% %}` | `{% endif %}` |
| SFMC | AMPscript | `%%=v()=%%` | `%%[ ]%%` | `ENDIF` |
| Adobe Campaign | JSSP | `<%= %>` | `<% %>` | `<% } %>` |
| Klaviyo | Django | `{{ }}` | `{% %}` | `{% endif %}` |
| Mailchimp | Merge Tags | `*|TAG|*` | `*|IF:TAG|*` | `*|END:IF|*` |
| HubSpot | HubL | `{{ }}` | `{% %}` | `{% endif %}` |
| Iterable | Handlebars | `{{ }}` | `{{#if}}` | `{{/if}}` |

## Common Syntax Errors to Flag

### Liquid (Braze, Klaviyo, HubSpot)
- Unclosed `{{ }}` or `{% %}` — mismatched brace count
- Dangling pipe: `{{ name | }}` — filter name missing after `|`
- Unclosed conditional: `{% if %}` without `{% endif %}`
- Empty filter chain: `{{ name | | upcase }}`

### AMPscript (SFMC)
- `SET name = "x"` — missing `@` prefix on variable
- Unclosed `%%[ ]%%` code block
- `IF` without `ENDIF` inside code block
- Unbalanced parentheses in function calls: `Lookup("DE", "field", "key", "val"`

### JSSP (Adobe Campaign)
- Unclosed `<%= %>` or `<% %>` tags
- Missing semicolons in JavaScript blocks
- Unbalanced braces in control flow: `<% if() { %>` without `<% } %>`

### Merge Tags (Mailchimp)
- Unclosed `*|TAG` — missing closing `|*`
- `*|IF:FIELD|*` without `*|END:IF|*`
- AND/OR operators inside single condition (not supported)

### Handlebars (Iterable)
- `{{#if}}` without `{{/if}}`
- `{{#each}}` without `{{/each}}`
- Missing quotes in comparison: `{{#ifEq a value}}` should be `{{#ifEq a "value"}}`

## Fallback Pattern Checklist

| ESP | Fallback Pattern | Example |
|-----|-----------------|---------|
| Braze | `| default:` filter | `{{ ${name} \| default: "Friend" }}` |
| SFMC | `IIF(Empty())` or `IF Empty()` | `%%=IIF(Empty(@name),"Friend",@name)=%%` |
| Adobe | Ternary `\|\|` or `? :` | `<%= recipient.name \|\| 'Friend' %>` |
| Klaviyo | `|default:` filter | `{{ name\|default:'Friend' }}` |
| Mailchimp | IF/ELSE wrapper | `*\|IF:FNAME\|*…*\|ELSE:\|*Friend*\|END:IF\|*` |
| HubSpot | `| default()` filter | `{{ contact.name \| default('Friend') }}` |
| Iterable | `defaultIfEmpty` helper | `{{defaultIfEmpty firstName "Friend"}}` |

## Mixed-Platform Detection

Flag when a template contains syntax from multiple ESPs — this indicates copy-paste errors:
- Liquid `{{ }}` alongside AMPscript `%%[ ]%%`
- Merge tags `*|TAG|*` alongside Handlebars `{{#if}}`
- JSSP `<%= %>` alongside Liquid `{% if %}`

**Exception:** Generic `{{ }}` templates without platform-specific markers may be intentional and should not trigger mixed-platform warnings.

## QA Rule IDs

| Rule ID | Check | Deduction |
|---------|-------|-----------|
| `ps-delimiter-unbalanced` | Delimiter pairs balanced | -0.15 |
| `ps-conditional-unbalanced` | Conditional blocks balanced | -0.15 |
| `ps-fallback-missing` | Output tags have defaults | -0.05 |
| `ps-fallback-empty` | Fallback values non-empty | -0.03 |
| `ps-syntax-liquid` | Liquid syntax well-formed | -0.10 |
| `ps-syntax-ampscript` | AMPscript syntax well-formed | -0.10 |
| `ps-syntax-jssp` | JSSP syntax well-formed | -0.10 |
| `ps-syntax-other` | Other syntax well-formed | -0.10 |
| `ps-nesting-depth` | Nesting ≤ 3 levels | -0.03 |
| `ps-platform-mixed` | Single platform per file | -0.30 |
| `ps-platform-unknown` | Platform detected | -0.10 |
