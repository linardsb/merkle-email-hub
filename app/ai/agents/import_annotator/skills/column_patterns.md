---
token_cost: 300
priority: 2
version: "1.0.0"
---
# Column Layout Detection Patterns

## Table-Based Columns
```html
<tr>
  <td width="50%">Column 1</td>   ← NOT a section
  <td width="50%">Column 2</td>   ← NOT a section
</tr>
```
The `<tr>` is the section with `data-section-layout="columns"`.

## Inline-Block Columns
```html
<div style="display:inline-block; width:50%; vertical-align:top;">Column 1</div>
<div style="display:inline-block; width:50%; vertical-align:top;">Column 2</div>
```
The **parent** element is the section with `data-section-layout="columns"`.

## Float-Based Columns
```html
<div style="float:left; width:33.33%;">Column 1</div>
<div style="float:left; width:33.33%;">Column 2</div>
<div style="float:left; width:33.33%;">Column 3</div>
```
The **parent** element is the section with `data-section-layout="columns"`.

## Fab Four (Responsive)
```html
<div style="display:inline-block; min-width:200px; max-width:50%; width:calc(50% - 20px);">
  Column 1
</div>
```
Uses `calc()` + `min()` + `max()` for responsive stacking. The parent is the section.

## Media Query Stacking
```css
@media (max-width: 480px) {
  .column { width: 100% !important; display: block !important; }
}
```
Columns that stack on mobile are still columns in the desktop layout.

## Key Rules
- Individual columns are NEVER separate sections
- The PARENT of side-by-side elements gets `data-section-layout="columns"`
- A section with columns gets ONE `data-section-id`, not one per column
