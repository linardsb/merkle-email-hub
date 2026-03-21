# Design Import Pipeline

Imports a design from Figma, builds an email from it via the AI blueprint engine, runs QA checks, and gates on admin approval.

**Flow ID:** `design-import-pipeline`
**Trigger:** Manual
**Namespace:** `merkle-email-hub`

## When to Use

- A designer has finalized an email design in Figma and you need to convert it to production HTML
- You want automated QA on the design-to-code conversion before it goes live
- Bridging the design-to-development handoff with quality gates

## Pipeline Steps

```
build (AI Blueprint from Design)
  │  retries: 3 × 30s
  ▼
qa (QA Checks)
  ▼
approval (Admin Gate)
```

1. **build** (`hub.blueprint_run`) — Runs the AI blueprint engine with the imported design context to generate email HTML. Retries up to 3 times.
2. **qa** (`hub.qa_check`) — Runs the full QA suite against the generated HTML to catch rendering issues, accessibility problems, and brand compliance violations.
3. **approval** (`hub.approval_gate`) — Pauses and waits for admin approval before the template is considered ready.

Note: This pipeline does **not** include an ESP push step — it stops at approval. The approved template can then be used in a campaign or newsletter workflow.

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `figma_file_ref` | string | Yes | — | Figma file reference (file key or URL) |
| `project_id` | integer | Yes | — | Project ID for design system context |

## Example JSON Input

```json
{
  "figma_file_ref": "abc123XYZ",
  "project_id": 42
}
```

With a full Figma URL (the system extracts the file key):

```json
{
  "figma_file_ref": "https://www.figma.com/file/abc123XYZ/Email-Campaign-Q3",
  "project_id": 42
}
```

## Outputs

| Output | Source | Description |
|--------|--------|-------------|
| `outputs.build.html` | build step | Generated email HTML from the Figma design |
| `outputs.build.run_id` | build step | Blueprint run ID |
| QA results | qa step | Pass/fail per check |
| Approval record | approval step | Who approved and when |

## Where to Find Input Values

- **`figma_file_ref`** — Open the design in Figma, copy the URL. The file key is the alphanumeric string after `/file/` in the URL. You can also find connected designs in **Ecosystem > Penpot/Figma**
- **`project_id`** — Found in the URL when viewing a project, or via `GET /api/v1/projects/`

## Critical: Full Design Token Extraction for Accurate HTML

For the Scaffolder agent to generate HTML that matches the Figma design as closely as possible, the design sync must extract **all visual properties** from the document tree — not just published styles.

### Current State

| Token type | Extraction method | Coverage |
|------------|-------------------|----------|
| Spacing | Auto-layout frame properties (padding, gap) | Works on any file |
| Colors | Published color styles only (`/v1/files/{key}/styles`) | Only files with explicitly published styles |
| Typography | Published text styles only (`/v1/files/{key}/styles`) | Only files with explicitly published styles |

**Problem**: Most Figma files (especially community templates and quick designs) apply colors and fonts **directly on nodes** without publishing them as reusable styles. This means the Scaffolder receives spacing tokens but **zero color and typography context**, producing HTML that doesn't match the design's visual identity.

### Required Enhancement: Node-Level Token Extraction

The `sync_tokens` method must walk the document tree and extract visual properties directly from nodes, the same way spacing extraction already works:

**Colors** — collect from:
- `fills` array on FRAME, RECTANGLE, COMPONENT nodes (solid fills → hex + opacity)
- `strokes` array (border colors)
- `backgroundColor` on CANVAS nodes
- Deduplicate by hex value, name by frequency/context (e.g., "primary", "background", "accent")

**Typography** — collect from:
- `style` property on TEXT nodes (`fontFamily`, `fontWeight`, `fontSize`, `lineHeightPx`, `letterSpacing`)
- Deduplicate by font family + size + weight combination
- Name by hierarchy (largest = "heading-1", next = "heading-2", body sizes = "body", etc.)

**Why this matters for the Scaffolder**:
- The Scaffolder's `DesignTokens` include `color_map` and `font_map` that drive HTML generation
- Without colors, the generated HTML uses default/brand palette instead of the design's actual colors
- Without typography, font families and sizes are guessed from the brief text, not from the design
- The design system constraint injection (`_design_pass_from_system`) relies on these tokens for palette replacement, font substitution, and dark mode color mapping

### Impact on Pipeline Accuracy

| With published styles only | With node-level extraction |
|---------------------------|---------------------------|
| Scaffolder guesses colors from brief | Scaffolder uses exact hex values from design |
| Font families default to project design system | Font families match the Figma text nodes |
| Dark mode colors are approximated | Dark mode maps from actual design palette |
| Brand compliance check may flag "off-palette" colors that are actually from the design | Brand compliance validates against the design's own palette |

This enhancement is a prerequisite for achieving design-to-HTML fidelity targets.

## Client Best Practices: Designing for Email Build Accuracy

Share these guidelines with designers and clients to ensure the best possible design-to-HTML conversion.

### Figma File Setup

| Practice | Why it matters |
|----------|---------------|
| **Publish color styles** (don't just apply fills directly) | Published styles are extracted as design tokens — the Scaffolder uses exact hex values instead of guessing |
| **Publish text styles** (heading, body, caption, etc.) | Gives the Scaffolder exact font families, weights, and sizes to match |
| **Use auto-layout on all sections** | Auto-layout padding and gap values are extracted as spacing tokens — absolute positioning is harder to convert |
| **Name frames descriptively** (e.g., "Hero Section", "CTA Block", "Footer") | Frame names become section identifiers in the generated brief — clear names produce better HTML structure |
| **Keep canvas width at 600px** | Email standard width — designs wider than 600px require scaling decisions that may not match intent |
| **Separate sections as top-level frames** | Each top-level frame inside the page becomes a distinct email section — don't nest everything inside one mega-frame |
| **Use components for repeated elements** (buttons, social icons, dividers) | Components can be extracted into the Hub's reusable component library via "Extract Components" |
| **Flatten complex vector illustrations to PNG** | Complex vectors with masks, blends, and boolean operations don't convert well to HTML — export them as images |
| **Avoid overlapping layers** | HTML email doesn't support CSS `position: absolute` in most clients — overlapping elements will be linearized |

### Typography Guidelines

| Do | Don't |
|----|-------|
| Use web-safe fonts or Google Fonts (Arial, Helvetica, Georgia, Inter, Roboto) | Use custom/local fonts without a web-safe fallback |
| Keep font sizes between 14px–32px | Use font sizes below 12px (unreadable on mobile) |
| Set line heights explicitly (not "Auto") | Leave line height as Auto — the Scaffolder can't infer the intended spacing |
| Limit to 2-3 font families per design | Use 5+ different fonts — email clients may not load them all |

### Color Guidelines

| Do | Don't |
|----|-------|
| Define a clear palette (primary, secondary, accent, background, text) | Use 20+ unique colors with no structure |
| Ensure sufficient contrast (WCAG AA: 4.5:1 for text) | Use light text on light backgrounds — accessibility checks will flag these |
| Provide dark mode alternatives if the brand allows | Assume light mode only — 40%+ of email opens are in dark mode |
| Use solid fills, not gradients, for backgrounds | Use complex gradients — most email clients render them as solid fallback |

### Image Guidelines

| Do | Don't |
|----|-------|
| Use placeholder frames with clear names (e.g., "Hero Image 1200×600") | Embed final images in the design — they'll be exported as assets but may be compressed |
| Set image frames to the intended display size | Use oversized images — the Hub exports at the frame dimensions |
| Add alt text to image frames (via Figma's accessibility plugin or frame description) | Leave image descriptions empty — accessibility checks require alt text |

### Design Tool Compatibility

| Tool | Import support | Component extraction | Token extraction |
|------|---------------|---------------------|------------------|
| **Figma** | Full (layout analysis + AI conversion) | Yes (published components) | Spacing from auto-layout; colors/typography from published styles |
| **Penpot** | Full (CSS-to-email converter) | Planned | Via Penpot's CSS export |
| **Sketch** | Stub (token sync only) | No | Basic |
| **Canva** | Stub (token sync only) | No | Basic |

### Recommended File Structure

```
📄 Email Campaign
├── 📐 Page 1: Email Template
│   ├── 🔲 Preheader (600×40, auto-layout)
│   ├── 🔲 Header / Logo Row (600×80, auto-layout)
│   ├── 🔲 Hero Section (600×400, auto-layout)
│   ├── 🔲 Content Block 1 (600×200, auto-layout)
│   ├── 🔲 CTA Section (600×120, auto-layout)
│   ├── 🔲 Content Block 2 (600×300, auto-layout)
│   └── 🔲 Footer (600×160, auto-layout)
├── 📐 Page 2: Components (optional)
│   ├── 🧩 Button/Primary (published component)
│   ├── 🧩 Button/Secondary (published component)
│   ├── 🧩 Social Icons Row (published component)
│   └── 🧩 Divider (published component)
└── 📐 Page 3: Color & Type Styles (optional)
    ├── Published color styles: primary, secondary, accent, bg, text
    └── Published text styles: heading-1, heading-2, body, caption, link
```

This structure gives the Hub maximum context for design-to-HTML conversion: clear section boundaries, reusable components, and explicit design tokens.

## Notes

- This pipeline focuses on design-to-code conversion and validation — it does not deploy
- To deploy the approved template, trigger the **Multilingual Campaign** or **Weekly Newsletter** workflow with the resulting template
- The build step uses a generic brief ("Build email from imported design") — the design file itself provides the visual context to the AI
