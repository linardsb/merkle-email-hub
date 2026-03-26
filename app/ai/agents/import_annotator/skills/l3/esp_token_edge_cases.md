---
token_cost: 400
priority: 1
---

# ESP Token Edge Cases

## AMPscript Advanced
Nested calls: `%%=Concat(Uppercase(FirstName), " ", LastName)=%%`
In attributes: `<a href="%%=RedirectTo(...)=%%">`
External content: `TreatAsContent`, `ContentBlockByKey("name")`
Multi-line: `%%[ SET @v = "x" IF @v == "x" THEN ... ENDIF ]%%` spanning lines

## Nested Liquid
Chained filters: `{{ name | capitalize | truncate: 20 }}`
In attributes: `<div style="color: {{ brand_color }};">`
Capture blocks: `{% capture var %}...{% endcapture %}` (defines variable for later use)
Connected Content (Braze): `{% connected_content https://api.example.com :save response %}`

## Handlebars Advanced
Partials: `{{> partial_name }}` (external template inclusion)
Each loops: `{{#each items}}...{{/each}}` with `{{@index}}`, `{{@first}}`, `{{@last}}`
Raw HTML: `{{{unescaped}}}` (triple-stache, no escaping)

## ERB (Ruby ESPs)
Output: `<%= expression %>`
Logic: `<% code %>`
Partials: `<%- include 'partial' %>`

## Mailchimp Merge Tags
Simple: `*|FNAME|*`, `*|LIST:COMPANY|*`
Conditional: `*|IF:FNAME|*...*|ELSE:|*...*|END:IF|*`
RSS: `*|RSSITEMS:|*...*|END:RSSITEMS|*`

## Key Rules
- ALL ESP tokens are opaque blocks — never parse internals
- Never split an ESP token across section boundaries
- When an ESP conditional (`{% if %}...{% endif %}`, `*|IF:|*...*|END:IF|*`) wraps multiple sections, annotate the conditional as spanning those sections
- Nested function calls (AMPscript) may contain balanced parens — match them correctly
- Tokens inside HTML attributes (`href`, `style`, `src`) are still opaque — don't modify the attribute
