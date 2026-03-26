---
token_cost: 400
priority: 1
---

# Wrapper Structure Detection

## Centering Wrappers
Pattern 1 (classic): `<table width="600" align="center">`
Pattern 2 (modern): `<div style="max-width:600px; margin:0 auto;">` (needs Outlook table fallback)
Pattern 3 (legacy): `<center>` tag
Pattern 4 (MSO ghost): `<!--[if mso]><table align="center"><tr><td><![endif]-->` around `<div>`
Pattern 5 (nested): MSO ghost outside, div inside, content table innermost

## Background Wrappers
Full-width: `<table width="100%" bgcolor="#f2f2f2">` wrapping centered content table
VML: `<!--[if gte mso 9]><v:rect>...<v:fill>...</v:fill>...<![endif]-->` wrapping content
Rule: identify background wrappers SEPARATELY from centering — different reconstruction purposes

## Preheader Wrappers
Hidden: `<div style="display:none; max-height:0; overflow:hidden;">` or `<span style="display:none;">`
Rule: annotate as `preheader_wrapper`, preserve for reconstruction

## Key Rules
- Centering wrappers are NOT sections — they are layout infrastructure
- Background wrappers are NOT sections — they provide visual context
- Preheader is a special-purpose wrapper, annotate but don't treat as visible section
- When multiple wrapper types are nested, identify each layer's purpose separately
- MSO ghost table wrappers always come in open/close pairs across `<!--[if mso]>` blocks
