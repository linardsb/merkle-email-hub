---
token_cost: 400
priority: 1
---

# Table-Based Email Layout Patterns

## Campaign Monitor Pattern
```
<table class="bodyTable">
  <tr>
    <td class="emailContainer">
      <table>  ← outermost content table
        <tr>...</tr>  ← EACH ROW = one section
        <tr>...</tr>
      </table>
    </td>
  </tr>
</table>
```

## Litmus Pattern
```
<table role="presentation" class="wrapper">
  <tr>
    <td class="wrapper-inner">
      <table class="content">  ← outermost content table
        <tr>...</tr>  ← sections here
      </table>
    </td>
  </tr>
</table>
```

## SFMC Deeply Nested (5+ levels)
```
<table><tr><td>
  <table><tr><td>
    <table><tr><td>
      <table><tr><td>
        <table>  ← ACTUAL content table (deepest)
          <tr>...</tr>  ← sections here
        </table>
      </td></tr></table>
    </td></tr></table>
  </td></tr></table>
</td></tr></table>
```

Navigate to the **innermost table** whose `<tr>` elements each contain a full-width visual section. `<tbody>` is transparent — step through it.

## Key Rules
- Each `<tr>` at the outermost content table = one section
- Wrapper/container tables (single `<td>` child) are NOT sections
- `<tbody>` is transparent — always step through
- `role="presentation"` tables are layout containers, not content
