---
token_cost: 450
priority: 2
---

# Email Builder Recognition Patterns

## Stripo
- Classes: `esd-structure`, `esd-container`, `esd-block`, `es-content-body`, `es-p-default`
- Comments: `<!-- stripo-module: {name} -->` = section boundary
- Outer: `<div class="es-wrapper">`, nested 4-5 levels
- MSO: `mso-table-lspace:0pt; mso-table-rspace:0pt` on ghost tables
- Rule: preserve `stripo-module` comments as boundaries, map `esd-*` to semantic roles

## Bee Free
- Classes: `bee-row`, `bee-col`, `bee-block`, `bee-content`
- Structure: `bee-page-container` → `bee-row` → `bee-col`
- Div-heavy layout — flag for table conversion
- Rule: `bee-row` = section boundary, `bee-col` = column

## Mailchimp
- Merge tags: `*|MERGE|*`, `*|IF:MERGE|*...*|END:IF|*`
- Editable: `mc:edit="region_name"` attributes
- Classes: `mc-*`, `templateContainer`, `templateBody`, `templateFooter`
- Comments: `<!-- BEGIN MODULE: {name} -->` = section boundary
- Rule: preserve `mc:edit` as slot markers, `BEGIN MODULE` = boundaries, merge tags = ESP tokens

## MJML Compiled
- 3-table pattern per section: outer align → inner width → content
- No `mj-*` classes (removed at compile), replaced with inline styles
- Comments: `<!-- [mj-column] -->` (sometimes preserved)
- Width: every structural `<td>` has `width` + `style="width:Npx"`
- Rule: recognize 3-table nesting, collapse to single section in annotation

## Litmus Builder
- Clean table structure, minimal classes
- Comments: `<!-- MODULE: {name} -->` = section boundary
- Rule: map `MODULE` comments to boundaries

## Key Rules
- Builder-specific classes inform section boundary detection but should NOT be stripped
- Comment markers are the most reliable section boundary signal in builder exports
- When both class patterns AND comment markers are present, prefer comment markers
