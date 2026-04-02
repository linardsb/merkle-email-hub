# MSO Conditional Patterns — Judge Reference

## Valid Conditional Syntax

Standard MSO conditional:
```html
<!--[if mso]>
  <table><tr><td>Outlook-only content</td></tr></table>
<![endif]-->
```

Negated conditional (non-Outlook content). This looks unbalanced but is **correct**:
```html
<!--[if !mso]><!-->
  <div>Non-Outlook content</div>
<!--<![endif]-->
```

The `<!-->` after `<!--[if !mso]>` is intentional — it closes the HTML comment for non-MSO clients while keeping the conditional active for Outlook. Do NOT flag this as malformed.

Version-targeted conditionals:
```html
<!--[if gte mso 9]>  <!-- Outlook 2007+ -->
<!--[if gte mso 12]> <!-- Outlook 2007+ (alternative) -->
<!--[if gte mso 15]> <!-- Outlook 2013+ -->
<!--[if gte mso 16]> <!-- Outlook 2016+ -->
```

## Nesting Rules

- Maximum 3 levels of nesting depth
- Each conditional block MUST close (`<![endif]-->`) before its parent closes
- Nesting an `[if mso]` inside another `[if mso]` is valid but redundant — flag as warning, not failure

## Common False Positives (Do NOT Flag as Errors)

1. **Split conditionals across table cells**: A conditional opening in one `<td>` and closing in a sibling `<td>` is a valid ghost table pattern:
```html
<!--[if mso]><td width="300"><![endif]-->
  <div style="max-width:300px;">Content</div>
<!--[if mso]></td><![endif]-->
```

2. **Empty conditional blocks**: `<!--[if mso]><![endif]-->` with no content between — valid spacer/reset pattern.

3. **Conditionals wrapping `<table>` without `<tr>/<td>`**: Outlook ghost tables often wrap just the outer `<table>` element.

## Actual Errors (Must Flag)

- Missing closing `<![endif]-->` for any opening conditional
- `<!--[if mso]>` without the `>` before content (malformed: `<!--[if mso]content`)
- Nesting depth exceeding 3 levels (indicates structural confusion)
- Using `<!--[if !mso]>` without the `<!-->` suffix (breaks non-Outlook rendering)
