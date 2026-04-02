# ESP Syntax Validation — Judge Reference

## Platform Delimiter Rules

### Liquid (Braze, Shopify)
- Output: `{{ variable_name }}`
- Logic: `{% if condition %}...{% endif %}`
- Filters: `{{ name | default: "Friend" }}`
- Nested brackets in attribute access are valid: `{{ user.custom_attributes["key_name"] }}`
- Nested `{{ }}` inside `{% %}` blocks are valid: `{% if {{ var }} == "x" %}` (Braze extension)

### AMPscript (Salesforce Marketing Cloud)
- Block: `%%[ SET @var = "value" ]%%`
- Inline output: `%%=v(@var)=%%`
- Functions: `%%=CONCAT("Hello ", v(@name))=%%`
- Nested quotes inside `CONCAT()` and other functions are valid: `%%=CONCAT("It's ", v(@name), "'s birthday")=%%`
- `TreatAsContent()` wrapping entire HTML blocks is valid

### Handlebars (Iterable, Mandrill)
- Output: `{{ variable }}`
- Block helpers: `{{#each items}}...{{/each}}`
- Conditionals: `{{#if condition}}...{{else}}...{{/if}}`
- Triple-stache for unescaped: `{{{ raw_html }}}` — valid, not a syntax error
- Nested paths: `{{ user.address.city }}` — valid dot notation

### HubL (HubSpot)
- Output: `{{ variable }}`
- Logic: `{% if condition %}...{% endif %}`
- HubSpot-specific: `{{ content.post_list_content }}`, `{% module "name" %}`

### Merge Language (Mailchimp)
- Merge tags: `*|FNAME|*`, `*|MC:SUBJECT|*`
- Conditional: `*|IF:FNAME|*Hello *|FNAME|**|ELSE:|*Hello Friend*|END:IF|*`
- Pipes inside merge tags are part of the syntax, not errors

## Common False Positives (Do NOT Flag)

1. **Nested brackets**: `{{ user.custom_attributes["plan_name"] }}` — the inner `["..."]` is valid JSON-style access
2. **Complex AMPscript expressions**: `%%=FormatDate(Now(), "MMMM d, yyyy")=%%` — nested parens and quotes are valid
3. **Triple braces in Handlebars**: `{{{ html_content }}}` — intentional unescaped output
4. **Mixed ESP syntax**: Templates may contain both Liquid AND HTML comments/conditionals — only flag if the ESP syntax itself is malformed
5. **ESP tags in HTML attributes**: `<a href="{{ url }}">` — this is the standard pattern

## Actual Errors (Must Flag)

- Unclosed blocks: `{% if %}` without `{% endif %}`
- Mismatched delimiters: `{{ var %}`  or `{% var }}`
- Empty output tags: `{{ }}` with no variable name
- Unclosed AMPscript blocks: `%%[` without `]%%`
