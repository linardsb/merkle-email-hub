---
token_cost: 300
priority: 2
---

# CSS-Based Email Layout Patterns

## Generic Div-Based
```html
<div class="email-body">
  <div class="section header">...</div>   ← section
  <div class="section hero">...</div>     ← section
  <div class="section content">...</div>  ← section
  <div class="section footer">...</div>   ← section
</div>
```

Direct children of the email body container are sections.

## MJML-Compiled Output
```html
<div class="mj-body">
  <div class="mj-section">         ← section
    <div class="mj-column">        ← NOT a section (it's a column)
      <div class="mj-text">...</div>
    </div>
  </div>
</div>
```

`mj-section` = section boundary. `mj-column` = column within section.

## Foundation for Emails
```html
<wrapper>
  <container>
    <row>        ← section
      <columns>  ← NOT a section (it's a column)
        ...
      </columns>
    </row>
  </container>
</wrapper>
```

## Key Rules
- Look for semantic class names: section, row, block, module, component
- Container/wrapper elements with single children are NOT sections
- Each full-width block within the main container = one section
