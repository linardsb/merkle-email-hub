---
purpose: Design system pipeline — brand identity, token mapping, template assembly, brand repair, component bridge
when-to-use: When modifying brand compliance, template assembly, design tokens, or the scaffolder pipeline's design pass
size: ~200 lines
source: app/projects/design_system.py, app/ai/blueprints/engine.py (LAYER 11), app/qa_engine/repair/brand.py
---

<!-- Scout header above. Sub-agents: read ONLY the header to decide relevance. Load full content only if needed. -->

# Design System Guide

## Overview

Per-project brand identity stored as a JSON column on the `Project` model. Flows through the AI pipeline as generation constraints, enforced post-generation by brand repair.

## Data Model (`app/projects/design_system.py`)

```
DesignSystem (frozen Pydantic)
├── BrandPalette: primary, secondary, accent, background, text, link colors
├── Typography: heading_font, body_font, font sizes
├── LogoConfig: url, width, height, alt_text
├── FooterConfig: legal_text, social_links[]
└── Token maps: colors{}, fonts{}, font_sizes{}, spacing{}
```

API: `GET/PUT/DELETE /api/v1/projects/{id}/design-system`

`resolve_color_map()` merges `BrandPalette` fields + explicit `colors` dict into unified lookup.

## Pipeline Integration

### LAYER 11 — Blueprint Engine Context
`BlueprintEngine._build_node_context()` injects into all agent node contexts:
- Full design system object
- Resolved color map (role → hex)
- Font map (role → font family)
- Template config (if set)

### Scaffolder Design Pass
`ScaffolderPipeline._design_pass_from_system()`:
1. Reads `DesignSystem` from project
2. Builds `DesignTokens` deterministically (zero LLM calls)
3. Maps brand palette roles to token slots
4. Builds locked fills for footer/logo components

### Template Assembly
`TemplateAssembler` applies:
1. **Role-based palette replacement**: Find default hex → replace with client hex
2. **Font replacement**: Swap template fonts with brand fonts
3. **Logo dimension enforcement**: Set width/height from `LogoConfig`
4. **Social link injection**: Add footer social links
5. **Dark mode color replacement**: Map light colors to dark variants
6. **Brand color sweep** (safety net): Euclidean RGB nearest-match for any remaining off-brand colors

### Brand Repair (Stage 8)
`BrandRepair` in `app/qa_engine/repair/brand.py`:
- Runs as stage 8 in the repair pipeline
- Deterministic off-palette color correction (Euclidean RGB distance)
- Footer legal text injection
- Logo URL correction
- `RepairPipeline` accepts `design_system` parameter

## Component → Section Bridge (`app/components/section_adapter.py`)

Converts `ComponentVersion` → `SectionBlock` via 5-stage pipeline:
1. Parse component HTML
2. Extract slot definitions
3. Map default tokens
4. Build section structure
5. Cache by version ID

`ComponentVersionLike` Protocol for duck-typing.

## Template Registry (`app/projects/template_config.py`)

`ProjectTemplateConfig`:
- `SectionOverride`: Per-section token overrides
- `CustomSection`: Project-specific sections
- `disabled_templates`: Hide templates from selection
- `preferred_templates`: Prioritize in selection UI

`TemplateRegistry.list_for_selection_scoped()` filters by project config.

## Adding Brand Rules

1. Add color/font to `BrandPalette`/`Typography` in `design_system.py`
2. Update `resolve_color_map()` if new role
3. Add replacement logic in `TemplateAssembler`
4. Add correction rule in `BrandRepair`
5. Update brand compliance QA check if new validation needed
