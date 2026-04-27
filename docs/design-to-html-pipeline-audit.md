# Design-to-HTML Conversion Pipeline — Engineering Audit

> **Generated:** 2026-04-03  
> **Scope:** Full end-to-end pipeline from Figma design input to email-safe HTML output  
> **Files covered:** `app/design_sync/` (converter, matcher, verifier, diagnostics, Figma integration)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [High-Level Architecture](#2-high-level-architecture)
3. [End-to-End Pipeline Flow](#3-end-to-end-pipeline-flow)
4. [Stage 1 — Figma API Ingestion](#4-stage-1--figma-api-ingestion)
5. [Stage 2 — Token Extraction & Validation](#5-stage-2--token-extraction--validation)
6. [Stage 3 — Structure Analysis & Section Classification](#6-stage-3--structure-analysis--section-classification)
7. [Stage 4 — Component Matching](#7-stage-4--component-matching)
8. [Stage 5 — Slot Filling](#8-stage-5--slot-filling)
9. [Stage 6 — Component Rendering](#9-stage-6--component-rendering)
10. [Stage 7 — Document Assembly](#10-stage-7--document-assembly)
11. [Stage 8 — VLM Verification Loop](#11-stage-8--vlm-verification-loop)
12. [Stage 9 — Post-Processing & Sanitization](#12-stage-9--post-processing--sanitization)
13. [Alternative Path — MJML Compilation](#13-alternative-path--mjml-compilation)
14. [Alternative Path — Recursive Converter](#14-alternative-path--recursive-converter)
15. [Custom Component Generation (AI Fallback)](#15-custom-component-generation-ai-fallback)
16. [Diagnostic Pipeline](#16-diagnostic-pipeline)
17. [Webhook & Trigger Flow](#17-webhook--trigger-flow)
18. [Data Model Reference](#18-data-model-reference)
19. [Configuration Reference](#19-configuration-reference)
20. [Caching Strategy](#20-caching-strategy)
21. [Error Handling & Fallbacks](#21-error-handling--fallbacks)
22. [Quality Contracts](#22-quality-contracts)
23. [Thresholds & Magic Numbers](#23-thresholds--magic-numbers)

---

## 1. Executive Summary

The pipeline transforms Figma design files into email-safe HTML through a multi-stage process. Three conversion paths exist:

| Path | Entry Point | Use Case |
|------|-------------|----------|
| **Component-based** (primary) | `convert_document()` | Section matching → pre-built templates → slot filling |
| **MJML** | `convert_document_mjml()` | Jinja2 MJML generation → Maizzle sidecar compilation |
| **Recursive** (legacy fallback) | `_convert_recursive()` | Direct design tree traversal → HTML generation |

The component-based path includes an optional VLM verification loop (Phase 47) that compares rendered HTML against design screenshots and iteratively applies corrections until fidelity reaches 97%+.

**Key files:**

| File | Lines | Role |
|------|-------|------|
| `converter_service.py` | ~1,381 | Orchestrator — routes to component/MJML/recursive paths |
| `converter.py` | ~1,200 | Core HTML generator — node-to-HTML, sanitization, buttons |
| `component_matcher.py` | ~900 | Section → component matching with 15+ heuristics |
| `component_renderer.py` | ~600 | Template slot filling and token override application |
| `figma/layout_analyzer.py` | ~1,151 | Structure analysis — section classification, column detection |
| `figma/service.py` | ~1,669 | Figma API client — tokens, structure, assets |
| `visual_verify.py` | ~400 | VLM verification loop — ODiff + VLM comparison |
| `correction_applicator.py` | ~300 | Deterministic HTML correction via lxml |
| `custom_component_generator.py` | ~200 | AI-generated components via Scaffolder agent |
| `token_transforms.py` | ~500 | Token validation, normalization, client-aware checks |
| `diagnose/runner.py` | ~200 | Diagnostic report orchestrator |
| `diagnose/analyzers.py` | ~550 | 6-stage diagnostic analyzers |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL INPUTS                              │
├─────────────┬───────────────────┬───────────────────────────────────┤
│ Figma API   │ Webhook (FILE_    │ Manual Trigger                   │
│ (REST v1)   │ UPDATE event)     │ (API / CLI)                      │
└──────┬──────┴────────┬──────────┴───────────┬───────────────────────┘
       │               │                      │
       ▼               ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    FIGMA INGESTION LAYER                             │
│  figma/service.py                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ sync_tokens_  │  │ get_file_    │  │ export_frame_            │   │
│  │ and_structure │  │ structure    │  │ screenshots              │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│         │                 │                        │                  │
│         ▼                 ▼                        ▼                  │
│  ExtractedTokens   DesignFileStructure      dict[str, bytes]         │
└──────────┬─────────────────┬──────────────────────┬──────────────────┘
           │                 │                      │
           ▼                 ▼                      │
┌──────────────────────────────────────────────┐    │
│          TOKEN PROCESSING LAYER              │    │
│  token_transforms.py                         │    │
│  ┌──────────────────────────────────────┐    │    │
│  │ validate_and_transform()             │    │    │
│  │  • Color normalization (hex/hsl/rgb) │    │    │
│  │  • Typography validation             │    │    │
│  │  • Spacing clamping                  │    │    │
│  │  • Gradient validation               │    │    │
│  │  • Dark mode contrast checks         │    │    │
│  └──────────────┬───────────────────────┘    │    │
│                 │                             │    │
│        ExtractedTokens (validated)            │    │
└─────────────────┬────────────────────────────┘    │
                  │                                  │
                  ▼                                  │
┌──────────────────────────────────────────────┐    │
│        STRUCTURE ANALYSIS LAYER              │    │
│  figma/layout_analyzer.py                    │    │
│  ┌──────────────────────────────────────┐    │    │
│  │ analyze_layout()                     │    │    │
│  │  • Section extraction                │    │    │
│  │  • 5-tier type classification        │    │    │
│  │  • Column layout detection           │    │    │
│  │  • Content extraction (text/img/btn) │    │    │
│  │  • Hierarchy & spacing               │    │    │
│  │  • VLM merge (optional)              │    │    │
│  └──────────────┬───────────────────────┘    │    │
│                 │                             │    │
│      DesignLayoutDescription                 │    │
│        └─ list[EmailSection]                 │    │
└─────────────────┬────────────────────────────┘    │
                  │                                  │
       ┌──────────┴──────────┐                      │
       ▼                     ▼                      │
┌─────────────┐    ┌──────────────┐                 │
│ COMPONENT   │    │ MJML PATH    │                 │
│ PATH        │    │ (alternate)  │                 │
│ (primary)   │    │              │                 │
└──────┬──────┘    └──────┬───────┘                 │
       │                  │                          │
       ▼                  ▼                          │
┌──────────────────────────────────────────────┐    │
│          COMPONENT MATCHING LAYER            │    │
│  component_matcher.py                        │    │
│  ┌──────────────────────────────────────┐    │    │
│  │ match_all(sections)                  │    │    │
│  │  • Type-based dispatch               │    │    │
│  │  • Base candidate scoring (8 types)  │    │    │
│  │  • Extended scoring (7 regex types)  │    │    │
│  │  • VLM fallback (optional)           │    │    │
│  └──────────────┬───────────────────────┘    │    │
│                 │                             │    │
│        list[ComponentMatch]                  │    │
│          └─ slot_fills, token_overrides       │    │
└─────────────────┬────────────────────────────┘    │
                  │                                  │
                  ▼                                  │
┌──────────────────────────────────────────────┐    │
│          RENDERING LAYER                     │    │
│  component_renderer.py                       │    │
│  ┌──────────────────────────────────────┐    │    │
│  │ render_section(match)                │    │    │
│  │  1. Load template HTML               │    │    │
│  │  2. Fill slots (text/image/cta)      │    │    │
│  │  3. Apply token overrides            │    │    │
│  │  4. Update MSO widths                │    │    │
│  │  5. Strip placeholders               │    │    │
│  │  6. Add section markers              │    │    │
│  └──────────────┬───────────────────────┘    │    │
│                 │                             │    │
│       list[RenderedSection]                  │    │
└─────────────────┬────────────────────────────┘    │
                  │                                  │
                  ▼                                  │
┌──────────────────────────────────────────────┐    │
│          ASSEMBLY LAYER                      │    │
│  converter_service.py                        │    │
│  ┌──────────────────────────────────────┐    │    │
│  │ _convert_with_components()           │    │    │
│  │  • Join sections with spacers        │    │    │
│  │  • Bgcolor propagation (optional)    │    │    │
│  │  • Build CSS style block             │    │    │
│  │  • Wrap in COMPONENT_SHELL           │    │    │
│  │  • Run quality contracts             │    │    │
│  └──────────────┬───────────────────────┘    │    │
│                 │                             │    │
│          ConversionResult (initial)          │    │
└─────────────────┬────────────────────────────┘    │
                  │                                  │
                  ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│          VLM VERIFICATION LOOP (optional, Phase 47)              │
│  visual_verify.py + correction_applicator.py                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ run_verification_loop(html, design_screenshots)          │    │
│  │                                                          │    │
│  │   ┌─────────┐    ┌──────────┐    ┌──────────────────┐   │    │
│  │   │ Render   │───▶│ Compare  │───▶│ Apply            │   │    │
│  │   │ HTML     │    │ (ODiff + │    │ Corrections      │   │    │
│  │   │ screenshot│◀──│  VLM)    │    │ (lxml + CSS)     │   │    │
│  │   └─────────┘    └──────────┘    └──────────────────┘   │    │
│  │                                                          │    │
│  │   Repeat until: fidelity ≥ 0.97 OR converged OR         │    │
│  │                 regression detected OR max iterations    │    │
│  └──────────────────────┬───────────────────────────────────┘    │
│                         │                                        │
│              VerificationLoopResult                               │
│                (final_html, fidelity)                             │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────┐
│       POST-PROCESSING & SANITIZATION         │
│  converter.py                                │
│  ┌──────────────────────────────────────┐    │
│  │ sanitize_web_tags_for_email()        │    │
│  │  • Stash MSO conditionals            │    │
│  │  • Preserve <p> inside <td>          │    │
│  │  • Convert layout <div> to <table>   │    │
│  │  • Strip non-layout <div>/<p>        │    │
│  │  • Restore MSO blocks                │    │
│  └──────────────┬───────────────────────┘    │
│                 │                             │
│       Final Email HTML                       │
└─────────────────┬────────────────────────────┘
                  │
                  ▼
           ConversionResult
```

---

## 3. End-to-End Pipeline Flow

### Sequence Diagram (Component Path)

```
User/Webhook          ConverterService       LayoutAnalyzer     ComponentMatcher     ComponentRenderer    VisualVerify
     │                      │                      │                   │                    │                 │
     │──convert_document()─▶│                      │                   │                    │                 │
     │                      │──analyze_layout()───▶│                   │                    │                 │
     │                      │                      │                   │                    │                 │
     │                      │◀─DesignLayout────────│                   │                    │                 │
     │                      │   Description        │                   │                    │                 │
     │                      │                      │                   │                    │                 │
     │                      │──match_all()────────────────────────────▶│                    │                 │
     │                      │                      │                   │                    │                 │
     │                      │◀─list[ComponentMatch]────────────────────│                    │                 │
     │                      │                      │                   │                    │                 │
     │                      │  for each match:     │                   │                    │                 │
     │                      │──render_section()───────────────────────────────────────────▶│                 │
     │                      │◀─RenderedSection────────────────────────────────────────────│                 │
     │                      │                      │                   │                    │                 │
     │                      │  assemble + wrap     │                   │                    │                 │
     │                      │  in COMPONENT_SHELL  │                   │                    │                 │
     │                      │                      │                   │                    │                 │
     │                      │──run_verification_loop()───────────────────────────────────────────────────────▶│
     │                      │                      │                   │                    │                 │
     │                      │  [iterative: render → compare → correct → repeat]            │                 │
     │                      │                      │                   │                    │                 │
     │                      │◀─VerificationLoopResult────────────────────────────────────────────────────────│
     │                      │                      │                   │                    │                 │
     │                      │  sanitize + finalize │                   │                    │                 │
     │◀─ConversionResult────│                      │                   │                    │                 │
```

---

## 4. Stage 1 — Figma API Ingestion

**File:** `app/design_sync/figma/service.py` (~1,669 lines)

### Entry Points

```python
# Full extraction (tokens + structure in one call)
async def sync_tokens_and_structure(
    self, file_ref: str, access_token: str
) -> tuple[ExtractedTokens, DesignFileStructure]

# Structure only (lighter call)
async def get_file_structure(
    self, file_ref: str, access_token: str, *, depth: int | None = 2
) -> DesignFileStructure

# Asset export
async def export_frame_screenshots(
    self, file_key: str, access_token: str, node_ids: list[str], *, scale: float = 2.0
) -> dict[str, bytes]
```

### Data Flow

```
Figma REST API
  │
  ├── GET /v1/files/{file_ref}              → Full document JSON
  ├── GET /v1/files/{file_ref}/styles       → Published styles
  ├── GET /v1/files/{file_ref}/variables    → Variables (if enabled)
  └── GET /v1/images/{file_ref}             → Export URLs (CDN)
       │
       ▼
  _parse_node() — Recursive descent (max depth 30)
       │
       ├── Maps Figma node types → DesignNodeType enum
       ├── Extracts: dimensions, position, text, fills, strokes, corner radii
       ├── Extracts: auto-layout properties (direction, spacing, padding)
       ├── Extracts: style runs (bold, italic, color, links)
       └── Returns: DesignNode tree
```

### Figma URL Parsing

```python
def extract_file_key(url: str) -> str
    # Regex: r"figma\.com/(?:design|file|proto|board|embed)/([a-zA-Z0-9]+)"
    # Supports: /design/, /file/, /proto/, /board/, /embed/ paths
```

### Asset Batching

- Figma API limit: 100 node IDs per export request
- Auto-batched: `[node_ids[i:i+100] for i in range(0, len(node_ids), 100)]`
- Scale clamped: `max(0.01, min(scale, 4.0))`
- CDN URLs expire in 14 days

---

## 5. Stage 2 — Token Extraction & Validation

### 5.1 Extraction (figma/service.py)

#### Color Extraction (3-phase strategy)

```
Phase 1: Published Styles          Phase 2: Node Walk              Phase 3: Variables API
(highest fidelity)                 (catches unpublished)           (Figma Variables, if enabled)
  │                                  │                                │
  ├─ styles.meta.styles[]            ├─ Recursive tree walk          ├─ GET /v1/files/.../variables
  ├─ Filter: FILL type               ├─ depth limit: 500             ├─ Collection → mode mapping
  ├─ Extract color.r/g/b/a           ├─ Extract fill colors          ├─ COLOR type variables
  └─ Opacity compositing vs bg       ├─ Extract stroke colors        ├─ Recursive alias resolution
                                     └─ Gradient stop extraction     │   (max depth 10)
                                                                     └─ Dark mode color detection
```

**Opacity Compositing Formula:**
```python
def _rgba_to_hex_with_opacity(r, g, b, fill_alpha=1.0, node_opacity=1.0, bg_hex="#FFFFFF"):
    alpha = fill_alpha * node_opacity
    # Blend against background: c_out = c_fg * alpha + c_bg * (1 - alpha)
    return "#RRGGBB"
```

#### Typography Extraction

```python
def _walk_for_typography(node, typography, seen_keys, depth=0):
    # Extracts from TEXT nodes:
    #   fontFamily, fontWeight, fontSize, lineHeightPx,
    #   textCase, textDecoration, letterSpacing
    # Deduplication key: (family, weight, size)
```

#### Spacing Extraction

```python
def _walk_for_spacing(node, spacing, seen, depth=0):
    # From auto-layout frames:
    #   itemSpacing, paddingLeft, paddingTop, paddingRight, paddingBottom
```

### 5.2 Validation & Transformation (token_transforms.py)

```python
def validate_and_transform(
    tokens: ExtractedTokens, *,
    target_clients: list[str] | None = None,
    caniemail_data: CanieMailData | None = None,
) -> tuple[ExtractedTokens, list[TokenWarning]]
```

**Validation pipeline per token type:**

| Token Type | Normalizations | Validations |
|------------|---------------|-------------|
| **Color** | `#RGB` → `#RRGGBB`, CSS named → hex, `rgba()` → hex, `hsl()` → hex, `#000000` → `#010101` (Outlook dark mode safety) | Opacity ∈ [0.0, 1.0], warn if opacity < 0.01 |
| **Typography** | `"normal"` → `"400"`, `"bold"` → `"700"`, empty family → `"Arial"`, unitless line-height × size | Size > 0, warn if > 200, weight snapped to nearest 100 |
| **Spacing** | None | ≥ 0 (no negative), warn if > 500 |
| **Gradient** | Angle clamped [0, 360] | Stop hex validated, position clamped [0.0, 1.0] |
| **Dark Mode** | None | WCAG AA contrast check (4.5:1) for text/bg pairs |

---

## 6. Stage 3 — Structure Analysis & Section Classification

**File:** `app/design_sync/figma/layout_analyzer.py` (~1,151 lines)

### Main Entry

```python
def analyze_layout(
    structure: DesignFileStructure, *,
    naming_convention="auto",
    section_name_map: dict[str, str] | None = None,
    button_name_hints: list[str] | None = None,
    vlm_classifications: dict[str, VLMSectionClassification] | None = None,
) -> DesignLayoutDescription
```

### Algorithm Steps

```
DesignFileStructure
  │
  ├── 1. Find primary page
  │     Prefer page with "email"/"design" in name
  │
  ├── 2. Extract section candidates
  │     Unwrap single wrapper with 2+ children
  │
  ├── 3. Auto-detect naming convention
  │     MJML | Descriptive | Generic | Custom
  │
  ├── 4. For each candidate node:
  │     │
  │     ├── 4a. Classify section type (5-tier)
  │     │     │
  │     │     ├── Tier 1: Custom name map (confidence=1.0)
  │     │     ├── Tier 2: MJML rules (0.85-0.95)
  │     │     ├── Tier 3: Name pattern regex (0.90)
  │     │     ├── Tier 4: Content heuristics (0.65-0.85)
  │     │     └── Tier 5: Position fallback (0.40-0.55)
  │     │
  │     ├── 4b. VLM merge (if vlm_classifications provided)
  │     │     Rule > 0.9 → keep rule
  │     │     UNKNOWN + VLM ≥ threshold → use VLM
  │     │     VLM > rule confidence → use VLM
  │     │
  │     ├── 4c. Detect column layout
  │     │     Strategy 1: MJML (mj-column children)
  │     │     Strategy 2: Auto-layout HORIZONTAL
  │     │     Strategy 3: Y-grouping (tolerance=10px)
  │     │
  │     ├── 4d. Extract content
  │     │     _extract_texts() → list[TextBlock]
  │     │     _extract_images() → list[ImagePlaceholder]
  │     │     _extract_buttons() → list[ButtonElement]
  │     │
  │     └── 4e. Detect content hierarchy
  │           Mark heading if font_size ≥ median × 1.3
  │
  ├── 5. Sort sections by y-position
  │
  ├── 6. Calculate inter-section spacing
  │     spacing_after = next.y - (current.y + current.height)
  │
  └── 7. Generate spacing map
        Per-section: {padding_top, padding_bottom, item_spacing, spacing_after}
```

### Section Type Classification Details

**Tier 3 — Name Patterns:**

| Pattern Keywords | EmailSectionType |
|-----------------|------------------|
| `preheader`, `preview` | PREHEADER |
| `header`, `logo`, `masthead` | HEADER |
| `hero`, `banner`, `jumbotron` | HERO |
| `content`, `body`, `article`, `editorial`, `story` | CONTENT |
| `cta`, `button`, `action` | CTA |
| `footer`, `legal`, `unsubscribe` | FOOTER |
| `social`, `follow` | SOCIAL |
| `divider`, `separator`, `hr`, `line` | DIVIDER |
| `spacer`, `gap` | SPACER |
| `nav`, `menu`, `navigation` | NAV |

**Tier 4 — Content Heuristics:**

| Signal | Classification | Confidence |
|--------|---------------|------------|
| Large image at top position | HERO | 0.85 |
| `©` or `unsubscribe` in text | FOOTER | 0.85 |
| Social media URLs detected | SOCIAL | 0.80 |
| Single button, minimal text | CTA | 0.75 |
| Multiple images, no text | CONTENT | 0.65 |

**Tier 5 — Position Fallback:**

| Condition | Classification | Confidence |
|-----------|---------------|------------|
| Height < 30px | SPACER | 0.55 |
| Height 30-60px | DIVIDER | 0.50 |
| First section | HEADER | 0.45 |
| Last section | FOOTER | 0.45 |
| Otherwise | CONTENT | 0.40 |

### Column Detection

```python
def _detect_column_layout_with_groups(node, convention) -> tuple[ColumnLayout, int, list[ColumnGroup]]:
    # Returns: (layout_type, column_count, column_groups)
    
# ColumnGroup contains:
#   column_idx: int
#   texts: list[TextBlock]
#   images: list[ImagePlaceholder]
#   buttons: list[ButtonElement]
```

### Content Extraction

```python
# Text extraction — recursive, excludes button subtrees
def _extract_texts(node, *, exclude_node_ids=None) -> list[TextBlock]
    # TextBlock: content, font_size, family, weight, line_height,
    #            letter_spacing, color, align, hyperlink, style_runs

# Image extraction — handles nested frames with image fills
def _extract_images(node) -> list[ImagePlaceholder]
    # ImagePlaceholder: node_id, width, height, alt_text, image_ref

# Button extraction — small frames with single text child
def _extract_buttons(node, *, extra_hints=None) -> list[ButtonElement]
    # Criteria: ≤30 chars text, ≤80px height, button name OR non-white fill
    # ButtonElement: node_id, label, url, bg_color, text_color, border_radius
```

---

## 7. Stage 4 — Component Matching

**File:** `app/design_sync/component_matcher.py` (~900 lines)

### Entry Points

```python
def match_section(section, idx, container_width=600, image_urls=None) -> ComponentMatch
def match_all(sections, container_width=600, image_urls=None) -> list[ComponentMatch]

# With VLM fallback (async)
async def match_section_with_vlm_fallback(...) -> ComponentMatch
```

### Matching Algorithm Flow

```
EmailSection
  │
  ├── Column layout check
  │   2 columns → column-layout-2 (confidence 1.0)
  │   3 columns → column-layout-3 (confidence 1.0)
  │   4 columns → column-layout-4 (confidence 1.0)
  │
  ├── Section type dispatch (_match_by_type)
  │   │
  │   ├── PREHEADER → "preheader" (1.0)
  │   ├── HEADER → "logo-header" if images, else "email-header" (0.9-1.0)
  │   ├── HERO → "hero-block"/"hero-text"/"full-width-image" (0.8-1.0)
  │   ├── CTA → "cta-button" (1.0)
  │   ├── FOOTER → "email-footer" (1.0)
  │   ├── SOCIAL → "social-icons" (1.0)
  │   ├── DIVIDER → "divider" (1.0)
  │   ├── SPACER → "spacer" (1.0)
  │   ├── NAV → "navigation-bar"/"nav-hamburger" (0.95-1.0)
  │   ├── UNKNOWN → "article-card"/"image-block"/"text-block" (0.7)
  │   │
  │   └── CONTENT → candidate scoring pipeline ▼
  │
  ├── Base candidate scoring (_score_candidates) — 8 heuristics
  │   │
  │   │  Candidate               Condition                                   Score
  │   │  ─────────────           ──────────────────────────────              ─────
  │   ├─ product-grid            2+ column groups with mixed content         0.95
  │   ├─ editorial-2             1 column group with images + texts          0.92
  │   ├─ article-card            1 image + 1+ text + ≤1 column group        0.90
  │   ├─ navigation-bar          images + texts + all icons ≤30px           0.90
  │   ├─ image-gallery           3+ images + ≤1 text                        0.88
  │   ├─ image-grid              2 images + ≤1 text                         0.85
  │   ├─ category-nav            3+ short texts (<20 chars) + no headings   0.70
  │   └─ text-block (fallback)   None of above                              1.0/0.5
  │
  └── Extended candidate scoring (_score_extended_candidates) — 7 regex types
      Extended wins over base when match found (content signals beat heuristics)
      │
      │  Candidate               Key Signals                                 Score
      │  ─────────────           ──────────────────────────────              ─────
      ├─ pricing-table           Currency symbols + 2+ columns + buttons     0.93
      ├─ countdown-timer         3+ time patterns + headings                 0.92
      ├─ zigzag-alternating      3+ mixed column groups                      0.90
      ├─ testimonial             Quote chars + avatar ≤100px + short body    0.90
      ├─ video-placeholder       1 image (16:9 ratio) + button              0.88
      ├─ faq-accordion           3+ texts, alternating "?" patterns          0.88
      └─ event-card              Images + texts + date pattern               0.85
```

### Regex Patterns for Extended Scoring

```python
_TIME_PATTERN     = re.compile(r"\b\d{1,2}\s*[:.]\s*\d{2}\b")
_TIME_UNIT_PATTERN = re.compile(r"(hours?|mins?|minutes?|secs?|seconds?|days?)", re.I)
_CURRENCY_PATTERN  = re.compile(r"[$€£¥]")
_DATE_PATTERN      = re.compile(r"\d{1,2}[/\-\.]\d{1,2}(?:[/\-\.]\d{2,4})?")
_QUOTE_CHARS       = {"\u201c", "\u201d", "\u201e", "\u2014", "\u2018", "\u2019"}
```

---

## 8. Stage 5 — Slot Filling

### Slot Fill Data Model

```python
@dataclass(frozen=True)
class SlotFill:
    slot_id: str          # e.g., "heading", "image_url", "cta_text"
    value: str            # Content to inject
    slot_type: str        # "text" | "image" | "cta" | "attr"
    attr_overrides: dict  # For images: {width, height}

@dataclass(frozen=True)
class TokenOverride:
    css_property: str     # e.g., "background-color", "font-family"
    target_class: str     # "_outer", "_heading", "_body", "_cell"
    value: str            # CSS value to apply
```

### Builder Registry (key mappings)

| Component Slug | Builder Function | Slots Generated |
|----------------|-----------------|-----------------|
| `preheader` | `_fills_preheader` | `preheader_text` |
| `logo-header` | `_fills_logo_header` | `logo_url`, `logo_alt` |
| `hero-block`, `hero-text`, `hero-2cta` | `_fills_hero` | `hero_image`, `headline`, `subtext`, `cta_text`, `cta_url` |
| `full-width-image` | `_fills_full_width_image` | `image_url`, `image_alt` |
| `text-block` | `_fills_text_block` | `heading`, `body`, `cta_text`, `cta_url` |
| `article-card`, `editorial-*` | `_fills_article_card` | `image_url`, `image_alt`, `heading`, `body_text`, `cta_text`, `cta_url` |
| `product-grid` | `_fills_product_grid` | `product_{1-4}_image`, `product_{1-4}_title`, `product_{1-4}_desc`, `product_{1-4}_cta` |
| `category-nav` | `_fills_category_nav` | `nav_item_{1-6}` |
| `cta-button`, `button-*` | `_fills_cta` | `cta_text`, `cta_url` |
| `email-footer`, `footer-*` | `_fills_footer` | `footer_content` |
| `navigation-bar` | `_fills_nav` | `nav_links` |
| `social-icons` | `_fills_social` | (no slots) |
| `column-layout-{2,3,4}` | `_build_column_fills` | `col_{1-4}` (HTML content) |

### Text Content Assembly

```python
# Body text is wrapped in semantic <p> tags:
"<p style=\"margin:0 0 10px 0;\">{text}</p>"

# Headings pass through as-is (component template has <h1>-<h3>)

# Buttons in text-block (no dedicated CTA slot):
#   appended as HTML to body slot
```

### Token Override Extraction

```python
def _build_token_overrides(section) -> list[TokenOverride]:
    # Scans section properties:
    #
    # bg_color       → background-color on "_outer"
    # heading font   → font-family on "_heading"
    # body font      → font-family on "_body"
    # heading color  → color on "_heading" (must match #HEX regex)
    # body color     → color on "_body"
    # padding        → padding on "_cell" (format: "16px 24px 16px 24px")
```

### Safety Utilities

```python
_safe_text(text)   # html.escape(text, quote=False)
_safe_url(url)     # Validate schemes: http, https, mailto, tel, /; default "#"
_safe_color(color) # Validate #HEX; fallback "#333333"
_is_placeholder()  # Regex: "lorem ipsum|placeholder|add your text|..."
```

---

## 9. Stage 6 — Component Rendering

**File:** `app/design_sync/component_renderer.py` (~600 lines)

### Rendering Pipeline

```python
def render_section(match: ComponentMatch) -> RenderedSection
```

```
ComponentMatch
  │
  ├── 1. Load template HTML from COMPONENT_SEEDS[slug].html_source
  │
  ├── 2. Fill slots (_fill_slots)
  │     ├── _fill_text_slot()    → regex: <tag data-slot="id">...</tag>
  │     ├── _fill_image_slot()   → regex: <img data-slot="id" src="..."/>
  │     └── _fill_cta_slot()     → regex: <a data-slot="id" href="...">
  │
  ├── 3. Apply token overrides
  │     ├── background-color on first matching element
  │     ├── font-family on <h1>-<h3> or <p> elements
  │     ├── color on <h1>-<h3> or <p> (avoids background-color)
  │     └── padding on target class elements
  │
  ├── 4. Update MSO widths to container_width
  │     <!-- [if mso]> <table width="600"> → width="{container_width}"
  │
  ├── 5. Strip placeholder URLs
  │     via.placeholder.com, placehold.it → ""
  │
  ├── 6. Add section markers
  │     <!-- section:{node_id} --> ... <!-- /section:{node_id} -->
  │
  ├── 7. Extract dark mode classes
  │     Classes ending: -bg, -text, -link, -btn, -ghost, -line
  │
  └── 8. Extract image metadata
        All <img> tags → {src, alt}
```

### Component Template HTML Pattern

```html
<!-- Example: article-card.html -->
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
<![endif]-->
<table class="artcard-bg" width="100%" role="presentation" style="background-color:#ffffff;">
  <tr>
    <td style="font-size:0;">
      <!-- Image column (inline-block + MSO ghost table) -->
      <div class="column" style="display:inline-block;max-width:280px;">
        <table><tr><td>
          <img data-slot="image_url" src="placeholder.png" alt="Article image"
               width="280" style="display:block;border:0;"/>
        </td></tr></table>
      </div>
      <!-- Content column -->
      <div class="column" style="display:inline-block;max-width:320px;">
        <table>
          <tr><td data-slot="heading" class="artcard-heading">Heading</td></tr>
          <tr><td data-slot="body_text" class="artcard-body">Body text</td></tr>
          <tr><td>
            <a data-slot="cta_url" href="#">
              <span data-slot="cta_text">Read More</span>
            </a>
          </td></tr>
        </table>
      </div>
    </td>
  </tr>
</table>
<!--[if mso]>
  </td></tr></table>
<![endif]-->
```

**Key conventions:**
- `data-slot="..."` attributes mark content replacement points
- CSS classes enable dark mode targeting (e.g., `.artcard-bg`)
- `font-size:0` on parent TD prevents inline-block spacing artifacts
- MSO ghost tables provide Outlook column widths

### Component Library

**150+ pre-built components** loaded from `email-templates/components/*.html`

| Category | Count | Examples |
|----------|-------|---------|
| Structure | 1 | email-shell |
| Headers | 2 | logo-header, email-header |
| Hero | 5+ | hero-block, hero-text, hero-2cta, full-width-image, hero variants |
| Content | 15+ | text-block, article-card, editorial-1 through -5, editorial-reverse |
| Layout | 6+ | column-layout-2/3/4, zigzag, mosaic |
| Products | 5+ | product-grid, card grids |
| CTA | 5+ | cta-button, button-filled, button-ghost, cta-pair |
| Footer | 4+ | email-footer, footer-menu, footer-social |
| Navigation | 3+ | navigation-bar, nav-hamburger |
| Specialty | 30+ | countdown-timer ×4, testimonial ×3, pricing-table ×3, video-placeholder ×3, FAQ ×2, event-card ×3, social-proof ×4, announcement-bar ×3, app-download ×2, loyalty ×2, divider/spacer variants, interactive ×4 |

**Manifest:** `app/components/data/component_manifest.yaml` defines slug, name, description, category, compatibility, slot_definitions, default_tokens per component.

---

## 10. Stage 7 — Document Assembly

**File:** `app/design_sync/converter_service.py`

### Assembly Flow

```python
async def _convert_with_components(
    layout, tokens, image_urls, connection_id, section_hashes
) -> ConversionResult
```

```
list[RenderedSection]
  │
  ├── 1. Match all sections → list[ComponentMatch]
  │
  ├── 2. Check section cache (memory + Redis)
  │     Key: (connection_id, section_hash)
  │     Hit → use cached HTML
  │     Miss → render via ComponentRenderer
  │
  ├── 3. Custom component generation (for low-confidence matches)
  │     If confidence < threshold AND custom_component_enabled
  │     → generate_custom_component(section, tokens)
  │
  ├── 4. Join sections with inter-section spacers
  │     MSO:     <!--[if mso]><table><tr><td height="N">&nbsp;</td></tr></table><![endif]-->
  │     Non-MSO: <div style="height:Npx; line-height:Npx; font-size:1px;">&nbsp;</div>
  │
  ├── 5. Background color propagation (if enabled)
  │     image_sampler.py → sample edge colors from images
  │     bgcolor_propagator.py → inject bgcolor on adjacent sections
  │     → invert text colors for dark backgrounds (luminance < 0.4)
  │
  ├── 6. Build CSS style block
  │     _build_component_style_block(body_font, tokens)
  │     → :root, body reset, img reset, table reset
  │     → @media (max-width: 599px) responsive
  │     → @media (prefers-color-scheme: dark)
  │     → [data-ogsc]/[data-ogsb] Outlook.com dark mode
  │
  ├── 7. Wrap in COMPONENT_SHELL template
  │     Variables: meta_tags, style_block, mso_font, bg_color,
  │                body_font, base_size, container_width, sections
  │
  └── 8. Run quality contracts
        → contrast check (WCAG AA)
        → completeness check (section count, button count)
        → placeholder detection
        → image container bgcolor check
```

### COMPONENT_SHELL Template Structure

```html
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml"
                xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
  {meta_tags}
  <!--[if mso]>
    <noscript><xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml></noscript>
    <style>
      td,th,div,p,a,h1,h2,h3,h4,h5,h6 {
        font-family: {mso_font};
        mso-line-height-rule: exactly;
      }
    </style>
  <![endif]-->
  {style_block}
</head>
<body role="article" aria-roledescription="email" lang="en"
      style="margin:0;padding:0;width:100%;-webkit-text-size-adjust:100%;
             background-color:{bg_color};font-family:{body_font};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center" style="font-size:{base_size};font-family:{body_font};">
        <!--[if mso]>
          <table role="presentation" cellpadding="0" cellspacing="0"
                 width="{container_width}"><tr><td>
        <![endif]-->
        <table class="dark-bg" role="presentation" width="100%"
               style="max-width:{container_width}px;">
          <tr><td>
            {sections}
          </td></tr>
        </table>
        <!--[if mso]>
          </td></tr></table>
        <![endif]-->
      </td>
    </tr>
  </table>
</body>
</html>
```

---

## 11. Stage 8 — VLM Verification Loop

**Files:** `app/design_sync/visual_verify.py`, `app/design_sync/correction_applicator.py`, `app/rendering/screenshot_crop.py`

### Overview

The VLM verification loop iteratively compares rendered HTML against the original Figma design screenshots, extracts corrections via a vision-language model, and applies them until convergence.

### Flow Diagram

```
                    ┌─────────────────────────┐
                    │  Initial HTML            │
                    │  + Design Screenshots    │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
              ┌────▶│  Render HTML Screenshot  │
              │     │  (LocalRenderingProvider) │
              │     └───────────┬──────────────┘
              │                 │
              │     ┌───────────▼──────────────┐
              │     │  Crop Per-Section         │
              │     │  (screenshot_crop.py)     │
              │     └───────────┬──────────────┘
              │                 │
              │     ┌───────────▼──────────────┐
              │     │  Compare Sections         │
              │     │  ┌──────────────────┐    │
              │     │  │ ODiff Pre-filter  │    │
              │     │  │ diff < 2.0%?     │    │
              │     │  │ → Skip VLM       │    │
              │     │  └────────┬─────────┘    │
              │     │           │ diff ≥ 2.0%  │
              │     │  ┌────────▼─────────┐    │
              │     │  │ VLM Comparison   │    │
              │     │  │ (multimodal LLM) │    │
              │     │  │ → JSON corrects  │    │
              │     │  └──────────────────┘    │
              │     └───────────┬──────────────┘
              │                 │
              │     ┌───────────▼──────────────┐
              │     │  Convergence Check        │
              │     │                           │
              │     │  fidelity ≥ 0.97? → DONE │
              │     │  no corrections?  → DONE │
              │     │  regression?      → REVERT│
              │     │  max iterations?  → DONE │
              │     └───────────┬──────────────┘
              │                 │ not converged
              │     ┌───────────▼──────────────┐
              │     │  Apply Corrections        │
              │     │  (correction_applicator)  │
              │     │                           │
              │     │  For each correction:     │
              │     │  1. Confidence gate       │
              │     │  2. Extract section HTML  │
              │     │  3. Dispatch by type:     │
              │     │     color/font/spacing    │
              │     │       → _apply_style()    │
              │     │     content               │
              │     │       → _apply_content()  │
              │     │     image                 │
              │     │       → _apply_image()    │
              │     │  4. Splice back           │
              │     └───────────┬──────────────┘
              │                 │
              └─────────────────┘ (next iteration)
```

### Data Structures

```python
@dataclass(frozen=True)
class SectionCorrection:
    node_id: str                # Design node ID
    section_idx: int            # Index in sections list
    correction_type: CorrectionType  # "color"|"font"|"spacing"|"layout"|"content"|"image"
    css_selector: str           # CSS selector (e.g., ".hero h1")
    css_property: str           # CSS property (e.g., "color")
    current_value: str          # Rendered value
    correct_value: str          # Design value from VLM
    confidence: float           # 0.0-1.0
    reasoning: str              # VLM explanation

@dataclass(frozen=True)
class VerificationResult:
    iteration: int
    fidelity_score: float       # 1.0 - (avg_diff% / 100.0)
    section_scores: dict[str, float]  # node_id → ODiff diff%
    corrections: list[SectionCorrection]
    pixel_diff_pct: float
    converged: bool             # True when corrections list is empty

@dataclass(frozen=True)
class VerificationLoopResult:
    iterations: list[VerificationResult]
    final_html: str
    initial_fidelity: float
    final_fidelity: float
    total_corrections_applied: int
    total_vlm_cost_tokens: int
    converged: bool
    reverted: bool              # True if last iteration regressed
```

### Correction Application (correction_applicator.py)

```python
def apply_corrections(
    html: str,
    corrections: list[SectionCorrection], *,
    confidence_threshold: float = 0.0,
) -> CorrectionResult
```

**Section extraction:** Regex `<!--\s*section:(\S+)\s*-->` finds section boundaries. Supports prefix matching (`hero_1` matches `hero_1:content`).

**Style corrections (lxml + CSSSelector):**
1. Parse HTML fragment
2. CSS select target elements
3. Parse inline `style=""` attribute
4. Replace property value (if property exists)
5. Serialize back

**CSS sanitization:** Removes `expression()`, `url(javascript:)`, `url(data:text/html)`, `-moz-binding`, `@import`, injection characters (`;`, `<`, `>`, `{`, `}`, `'`, `"`, `\\`)

**Layout safety:** Complex layout corrections (anything except `width`, `max-width`, `min-width`, `text-align`, `vertical-align`) are skipped — deferred to LLM.

### VLM Cache

- Key: `SHA256(figma_png + html_png)[:16]`
- Max entries: 256
- Eviction: Clear all when full
- Scope: Session-only (not persisted)

---

## 12. Stage 9 — Post-Processing & Sanitization

**File:** `app/design_sync/converter.py`

### sanitize_web_tags_for_email()

```python
def sanitize_web_tags_for_email(html_str: str) -> str
```

```
Input HTML
  │
  ├── 1. Stash MSO conditionals
  │     <!--[if ...]>...<![endif]--> → placeholder tokens
  │
  ├── 2. Process <p> tags
  │     Inside <td>: preserve, add margin:0 0 10px 0
  │     Outside <td>: strip tags, insert <br><br> separator
  │     Last <p>: no trailing <br>
  │
  ├── 3. Process <div> tags (stack-based pairing)
  │     │
  │     ├── class="column" → preserve (multi-column layout)
  │     │
  │     ├── Layout CSS detected + inside <td> → preserve
  │     │   (width|max-width|float|display:inline-block|flex|grid)
  │     │
  │     ├── Layout CSS detected + outside <td> → convert to table:
  │     │   <table role="presentation" cellpadding="0" cellspacing="0">
  │     │     <tr><td style="[sanitized_style]">[content]</td></tr>
  │     │   </table>
  │     │
  │     └── No layout CSS + outside <td> → unwrap (remove tags, keep content)
  │
  ├── 4. Restore MSO blocks from placeholders
  │
  └── Output: email-safe HTML
```

---

## 13. Alternative Path — MJML Compilation

**Entry:** `converter_service.py:convert_document_mjml()`

```
EmailDesignDocument
  │
  ├── 1. Extract tokens: document.to_extracted_tokens()
  ├── 2. Validate: validate_and_transform(tokens, target_clients)
  ├── 3. Derive layout: document.to_layout_description()
  │
  ├── 4. Generate MJML template
  │     engine.render_email(body_sections, ctx, preheader=preheader)
  │     → Jinja2 MJML template rendering
  │
  ├── 5. Compile MJML → HTML
  │     POST {maizzle_builder_url}/compile-mjml
  │     Request:  { "mjml": str, "target_clients": list[str] }
  │     Response: { "html": str, "errors": [...], "build_time_ms": float }
  │     Timeout: 30 seconds
  │
  ├── 6. Inject section markers into compiled HTML
  │
  ├── 7. Run quality contracts
  │
  └── 8. Optional: VLM verification loop
```

**Fallback:** Legacy `convert_mjml()` shim catches `MjmlCompileError` and falls back to `_convert_recursive()`.

---

## 14. Alternative Path — Recursive Converter

**File:** `app/design_sync/converter.py`

The recursive converter traverses the full `DesignNode` tree and generates email-safe HTML directly, without component matching.

### Core Function

```python
def node_to_email_html(
    node: DesignNode, *,
    indent: int = 0,
    props_map: dict[str, _NodeProps] | None = None,
    parent_bg: str | None = None,
    parent_font: str | None = None,
    section_map: dict[str, EmailSection] | None = None,
    button_ids: set[str] | None = None,
    text_meta: dict[str, TextBlock] | None = None,
    current_section: EmailSection | None = None,
    body_font_size: float = 16.0,
    compat: ConverterCompatibility | None = None,
    gradients_map: dict[str, ExtractedGradient] | None = None,
    _depth: int = 0,
    container_width: int = 600,
    slot_counter: dict[str, int] | None = None,
) -> str
```

### Node Type Dispatch

```
DesignNode
  │
  ├── TEXT node
  │   ├── Determine heading level (size_ratio: ≥2.0→h1, ≥1.5→h2, ≥1.2→h3)
  │   ├── Render semantic HTML: <h1>-<h3> for headings, <p> for body
  │   ├── Apply style runs (bold→<strong>, italic→<em>, color→<span>, link→<a>)
  │   ├── Wrap in <td> with duplicate styles (Outlook compatibility)
  │   └── Add data-slot-name attributes
  │
  ├── IMAGE node
  │   ├── Generate <img> with src="", alt, dimensions
  │   ├── Set email-safe styles: display:block; border:0;
  │   └── Add data-node-id and data-slot-name
  │
  ├── BUTTON (node.id in button_ids)
  │   └── _render_button() → VML roundrect for Outlook + table fallback
  │       <!--[if mso]>
  │         <v:roundrect style="width:Npx;height:Npx;" arcsize="N%">
  │           <v:textbox><center>Button Text</center></v:textbox>
  │         </v:roundrect>
  │       <![endif]-->
  │       <!--[if !mso]><!-->
  │         <table><tr><td style="border-radius:...; background-color:...;">
  │           <a href="..." style="display:inline-block; padding:...;">Text</a>
  │         </td></tr></table>
  │       <!--<![endif]-->
  │
  └── FRAME / GROUP / COMPONENT / INSTANCE
      ├── Determine layout direction
      │   row → all children in one row
      │   column → each child in own row
      │   else → _group_into_rows() by Y-position (tolerance=20px)
      │
      ├── Calculate column widths
      │   Sparse detection: total_child_w < 60% container → keep natural
      │   Else: proportional distribution
      │
      ├── Render as nested tables
      │   Single-column rows: simple <tr><td>child</td></tr>
      │   Multi-column rows: _render_multi_column_row()
      │     → inline-block <div class="column"> + MSO ghost <table>
      │
      ├── Apply visual properties
      │   Background color, gradients (CSS + VML for Outlook)
      │   Border radius, padding, border
      │   Background images (CSS + VML <v:fill>)
      │
      └── Nesting depth guard (depth > 6)
          → Flatten to single-column, log warning
```

### Row Grouping Algorithm

```python
def _group_into_rows(nodes, tolerance=20.0, *, parent_width=None):
    # 1. Partition: y-known vs y-unknown nodes
    # 2. All y=None → [nodes] (single horizontal row)
    # 3. Y-known: sort by (y, x), group by y-proximity (±20px)
    # 4. Mixed: group y-known, append y-unknown to last row
    # 5. Hero image detection: IMAGE ≥80% parent width → own row
```

### Multi-Column Rendering

```html
<tr>
  <td style="font-size:0; text-align:center;">
    <!--[if mso]>
    <table width="{total}"><tr>
      <td width="{col1_w}">[child1]</td>
      <td width="{gap}"></td>
      <td width="{col2_w}">[child2]</td>
    </tr></table>
    <![endif]-->
    <!--[if !mso]><!-->
    <div class="column" style="display:inline-block;max-width:{col1_w}px;">
      <table><tr><td style="padding:...">[child1]</td></tr></table>
    </div>
    <div class="column" style="display:inline-block;max-width:{col2_w}px;">
      <table><tr><td style="padding:...">[child2]</td></tr></table>
    </div>
    <!--<![endif]-->
  </td>
</tr>
```

---

## 15. Custom Component Generation (AI Fallback)

**File:** `app/design_sync/custom_component_generator.py`

### When Triggered

- Component match confidence < `custom_component_confidence_threshold` (default 0.6)
- `custom_component_enabled = True`
- Custom component count < `custom_component_max_per_email` (default 3)

### Flow

```python
async def generate_custom_component(
    section: EmailSection,
    tokens: ExtractedTokens, *,
    design_screenshot: bytes | None = None,
) -> str
```

```
EmailSection (low-confidence match)
  │
  ├── 1. Build brief from section data
  │     "Generate a single email section of type '{section_type}'."
  │     "Column layout: {layout} ({count} columns)."
  │     "Text content ({count} blocks): {snippets[:5]};"
  │     "Image placeholders: {count};"
  │     "Buttons: {labels[:3]};"
  │     "Requirements: table-based layout, inline styles only."
  │
  ├── 2. Security scan (prompt injection guard)
  │     scan_for_injection(brief)
  │     → Sanitize if flagged
  │
  ├── 3. Build design context
  │     { design_tokens: {colors, typography, spacing},
  │       design_screenshot_b64: "..." }
  │
  ├── 4. Create ScaffolderRequest
  │     brief=brief, run_qa=False, output_mode="html"
  │
  ├── 5. Call Scaffolder agent service
  │     service.generate(request) → response.html
  │
  └── 6. Return generated HTML
        On failure: fall back to template renderer
```

---

## 16. Diagnostic Pipeline

**Files:** `app/design_sync/diagnose/runner.py`, `analyzers.py`, `models.py`

### Overview

The diagnostic pipeline traces data through every conversion stage, detecting data loss, mismatches, and structural issues.

### 6-Stage Pipeline

```python
def run_from_structure(
    self, structure, tokens, *,
    raw_figma_json=None, target_clients=None,
    verification_result=None, generation_methods=None, vlm_classifications=None,
) -> DiagnosticReport
```

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 0: Design Tree Analysis                                    │
│ analyze_design_tree(structure, raw_figma_json)                   │
│                                                                   │
│ → Walks entire tree, counts node types                           │
│ → Detects max depth, auto-layout frames                          │
│ → Checks naming compliance (section keywords)                    │
│ → Detects whitespace-only TEXT nodes                             │
│ → Detects IMAGE fills on FRAMEs (from raw JSON)                  │
│                                                                   │
│ Output: DesignSummary + list[DataLossEvent]                      │
├─────────────────────────────────────────────────────────────────┤
│ Stage 1: Layout Analysis                                         │
│ analyze_layout_stage(structure, layout)                           │
│                                                                   │
│ → Counts TEXT/IMAGE nodes in input vs layout output              │
│ → Flags UNKNOWN section types                                    │
│ → Detects nested images missed by analyzer                       │
│                                                                   │
│ Output: StageResult (data_loss events, warnings)                 │
├─────────────────────────────────────────────────────────────────┤
│ Stage 2: Component Matching                                      │
│ analyze_matching_stage(sections, matches)                        │
│                                                                   │
│ → Checks confidence scores (flags < 0.8)                         │
│ → Detects text count reduction (content collapsed)               │
│ → Flags empty slot fills despite source content                  │
│                                                                   │
│ Output: StageResult                                              │
├─────────────────────────────────────────────────────────────────┤
│ Stage 3: Rendering                                               │
│ analyze_rendering_stage(matches, rendered)                       │
│                                                                   │
│ → Detects fallback rendering (slug mismatch)                     │
│ → Counts unfilled data-slot attributes in HTML                   │
│                                                                   │
│ Output: StageResult                                              │
├─────────────────────────────────────────────────────────────────┤
│ Stage 4: Assembly                                                │
│ analyze_assembly_stage(rendered, final_html)                     │
│                                                                   │
│ → Checks <table> tag balance                                     │
│ → Validates MSO conditional balance                              │
│ → Validates CSS brace balance in <style>                         │
│                                                                   │
│ Output: StageResult                                              │
├─────────────────────────────────────────────────────────────────┤
│ Stage 5: Post-Processing                                         │
│ analyze_post_processing(before_html, after_html)                │
│                                                                   │
│ → Counts empty src="" remaining                                  │
│ → Measures div→table conversions                                 │
│ → Tracks HTML length delta                                       │
│                                                                   │
│ Output: StageResult                                              │
└─────────────────────────────────────────────────────────────────┘
```

### Section Trace

Per-section diagnostic trace with full pipeline visibility:

```python
@dataclass(frozen=True)
class SectionTrace:
    section_idx: int
    node_id: str
    node_name: str
    classified_type: str          # "HERO"|"CONTENT"|"FOOTER"|"UNKNOWN"
    matched_component: str        # "hero-block"|"article-card"|...
    match_confidence: float
    texts_found: int
    images_found: int
    buttons_found: int
    slot_fills: tuple[dict, ...]  # {slot_id, slot_type, value_preview}
    unfilled_slots: tuple[str, ...]
    html_preview: str             # First 3000 chars
    vlm_classification: str       # Phase 41.7 VLM result
    vlm_confidence: float
    verification_fidelity: float | None  # Phase 47 fidelity score
    corrections_applied: int      # Phase 47 correction count
    generation_method: str        # "template"|"custom"|"recursive"
```

### Diagnostic Report

```python
@dataclass(frozen=True)
class DiagnosticReport:
    id: str                       # UUID hex[:12]
    connection_id: int | None
    timestamp: str                # ISO format
    total_elapsed_ms: float
    stages_completed: int
    total_warnings: int
    total_data_loss_events: int
    design_summary: DesignSummary
    stages: tuple[StageResult, ...]
    section_traces: tuple[SectionTrace, ...]
    final_html_preview: str       # First 5000 chars
    final_html_length: int
    images: list[dict[str, str]]
    design_image_path: str | None
    design_image_width: int | None
    design_image_height: int | None
    verification_loop_iterations: int
    final_fidelity: float | None
```

### CLI Tool

```bash
python -m app.design_sync.diagnose.extract --connection-id 8 --node-id 2833-1623
```

Outputs to `data/debug/{connection_id}/`: `raw_figma.json`, `structure.json`, `tokens.json`, `report.json`, `design.png`

---

## 17. Webhook & Trigger Flow

**File:** `app/design_sync/webhook.py`

```
Figma                    Webhook Endpoint          Debouncer            DesignSyncService
  │                            │                      │                       │
  │──FILE_UPDATE event────────▶│                      │                       │
  │                            │                      │                       │
  │                            │──verify_signature()  │                       │
  │                            │  HMAC-SHA256         │                       │
  │                            │                      │                       │
  │                            │──enqueue_debounced──▶│                       │
  │                            │  sync()              │                       │
  │                            │                      │                       │
  │                            │                Redis │                       │
  │                            │         key: figma_webhook:{file_key}        │
  │                            │         TTL: webhook_debounce_seconds        │
  │                            │                      │                       │
  │                            │              [sleep debounce window + 0.5s]  │
  │                            │                      │                       │
  │                            │              check Redis key still exists    │
  │                            │                      │                       │
  │                            │                      │──handle_webhook_sync()│
  │                            │                      │                       │
  │                            │                      │  → sync_tokens_and_   │
  │                            │                      │    structure()        │
  │                            │                      │  → convert_document() │
  │                            │                      │                       │
  │                            │              broadcast via WebSocket         │
  │                            │              room: "project:{project_id}"    │
```

---

## 18. Data Model Reference

### Core Pipeline Models

```
ExtractedTokens
  ├── colors: list[ExtractedColor]
  │     └── name, hex, opacity, source
  ├── typography: list[ExtractedTypography]
  │     └── name, family, weight, size, line_height, letter_spacing, text_case, text_decoration
  ├── spacing: list[ExtractedSpacing]
  │     └── name, value
  ├── gradients: list[ExtractedGradient]
  │     └── angle, stops: list[{color, position}]
  ├── dark_colors: list[ExtractedColor]
  ├── variables: list[ExtractedVariable]
  └── variable_modes: dict[str, str]

DesignFileStructure
  ├── name: str
  ├── pages: list[DesignPage]
  │     └── name, children: list[DesignNode]
  └── version: str

DesignNode
  ├── id, name, type: DesignNodeType
  ├── x, y, width, height
  ├── children: list[DesignNode]
  ├── text_content, font_family, font_size, font_weight
  ├── fills, strokes, corner_radius
  ├── layout_mode, item_spacing, padding_*
  ├── image_ref
  └── style_runs: list[StyleRun]

DesignLayoutDescription
  ├── sections: list[EmailSection]
  ├── container_width: int
  ├── naming_convention: NamingConvention
  └── spacing_map: dict[str, dict[str, float]]

EmailSection
  ├── node_id, node_name
  ├── section_type: EmailSectionType
  ├── classification_confidence: float
  ├── y_position, height
  ├── column_layout: ColumnLayout
  ├── column_count: int
  ├── column_groups: list[ColumnGroup]
  ├── texts: list[TextBlock]
  ├── images: list[ImagePlaceholder]
  ├── buttons: list[ButtonElement]
  ├── bg_color: str | None
  ├── spacing_after: float | None
  └── padding_*: float

ComponentMatch
  ├── section_idx: int
  ├── section: EmailSection
  ├── component_slug: str
  ├── slot_fills: list[SlotFill]
  ├── token_overrides: list[TokenOverride]
  ├── spacing_after: float | None
  └── confidence: float

ConversionResult
  ├── html: str
  ├── sections_count: int
  ├── warnings: list[str]
  ├── layout: DesignLayoutDescription
  ├── compatibility_hints: list[str]
  ├── images: list[dict]
  ├── cache_hit_rate: float
  ├── quality_warnings: list[QualityWarning]
  ├── match_confidences: dict[int, float]
  ├── design_tokens_used: ExtractedTokens
  ├── verification_iterations: int
  ├── initial_fidelity: float
  └── final_fidelity: float
```

### EmailSectionType Enum

```
PREHEADER | HEADER | HERO | CONTENT | CTA | FOOTER | SOCIAL |
DIVIDER | SPACER | NAV | UNKNOWN
```

---

## 19. Configuration Reference

### Design Sync Settings (`settings.design_sync.*`)

| Setting | Default | Description |
|---------|---------|-------------|
| `figma_variables_enabled` | `True` | Fetch Figma Variables API |
| `opacity_composite_bg` | `"#FFFFFF"` | Background for opacity compositing |
| `section_cache_enabled` | `True` | Enable memory + Redis section cache |
| `bgcolor_propagation_enabled` | `True` | Propagate section background colors |
| `webhook_debounce_seconds` | — | Debounce window for Figma webhooks |

### VLM Classification (Phase 41)

| Setting | Default | Description |
|---------|---------|-------------|
| `vlm_classification_enabled` | `True` | Enable VLM section type classification |
| `vlm_fallback_enabled` | `True` | VLM fallback for low-confidence matches |
| `vlm_classification_confidence_threshold` | `0.5` | Minimum VLM confidence to use |
| `vlm_classification_timeout` | `30.0` | VLM call timeout (seconds) |
| `vlm_classification_model` | `""` | Model override (empty = auto-resolve) |
| `low_match_confidence_threshold` | — | Below this, trigger VLM fallback |

### VLM Verification Loop (Phase 47)

| Setting | Default | Description |
|---------|---------|-------------|
| `vlm_verify_enabled` | `False` | Enable verification loop |
| `vlm_verify_model` | `""` | Model override |
| `vlm_verify_timeout` | `30.0` | Per-section VLM timeout |
| `vlm_verify_diff_skip_threshold` | `2.0` | ODiff % below which skip VLM |
| `vlm_verify_max_sections` | `20` | Max sections to verify |
| `vlm_verify_max_iterations` | `3` | Max correction cycles |
| `vlm_verify_target_fidelity` | `0.97` | Target fidelity score |
| `vlm_verify_confidence_threshold` | `0.7` | Min correction confidence |
| `vlm_verify_correction_confidence` | `0.6` | Alternate threshold |
| `vlm_verify_client` | `"gmail_web"` | Rendering profile |

### Custom Component Generation (Phase 47.8)

| Setting | Default | Description |
|---------|---------|-------------|
| `custom_component_enabled` | `False` | Enable AI generation |
| `custom_component_confidence_threshold` | `0.6` | Trigger threshold |
| `custom_component_model` | `""` | Model override |
| `custom_component_max_per_email` | `3` | Max custom per email |

---

## 20. Caching Strategy

### Section-Level Cache

| Layer | Key | TTL | Max Size |
|-------|-----|-----|----------|
| Memory | `(connection_id, section_hash)` | Session | Unbounded |
| Redis | `(connection_id, section_hash)` | Configurable | Configurable |

**Section hash:** SHA256 of (section content + tokens + target_clients)

### VLM Result Cache

| Cache | Key | Max Size | Eviction |
|-------|-----|----------|----------|
| Section comparison | `SHA256(figma_png + html_png)[:16]` | 256 | Clear all |
| Batch classification | Incremental hash of all screenshots | 64 | LRU clear |
| Single classification | `SHA256(screenshot)[:16]` | 512 | — |

### Font Data Cache

- Source: `app/data/email_client_fonts.yaml`
- Loaded at import time, frozen dict

---

## 21. Error Handling & Fallbacks

| Error Scenario | Fallback Behavior |
|---|---|
| Component slug not in COMPONENT_SEEDS | `_fallback_render()` → plain text-block |
| MJML compilation fails | `_convert_recursive()` (legacy shim only) |
| Image URL resolution fails | `/api/v1/design-sync/assets/{node_id}.png` |
| Invalid hex color in token override | Fallback `#333333` |
| Invalid URL scheme in slot fill | Default `"#"` |
| VLM verification timeout (30s) | Log warning, return `[]` corrections |
| VLM API error | Log warning, return `[]` corrections |
| VLM parse error (bad JSON) | Log warning, skip item |
| ODiff comparison error | Return 100% diff (force VLM check) |
| Correction: section not found in HTML | Add to skipped list |
| Correction: invalid CSS selector | Log warning, skip |
| Correction: unsafe CSS value | Log warning, skip |
| Correction: complex layout change | Skip (defer to LLM) |
| Screenshot crop: height < 8px | Return full screenshot |
| Screenshot crop: out of bounds | Return full screenshot |
| Screenshot crop: Pillow error | Return full screenshot |
| Nesting depth > 6 in recursive path | Flatten to single-column, log warning |
| Custom component generation fails | Fall back to template renderer |
| Figma API rate limit (429) | Exponential backoff (credential pool) |
| lxml HTML parse failure | Return original HTML unchanged |

---

## 22. Quality Contracts

**Executed post-assembly via `run_quality_contracts(html, section_count, button_count)`**

| Contract | Check | Threshold |
|----------|-------|-----------|
| **Contrast** | WCAG AA ratio for all inline color pairs | Normal: 4.5:1, Large (≥18px / bold ≥14px): 3.0:1 |
| **Completeness** | Section marker count vs input | Warn if output < input |
| **Completeness** | Button count (`<a>` + VML `v:roundrect`) vs input | Warn if output < input |
| **Placeholders** | Scan text for `_PLACEHOLDER_PATTERNS` | Any match = warning |
| **Image Containers** | Background-color on elements wrapping `<img>` | Present = warning |

**Placeholder detection regex:**
```regex
image caption|describe\s+the\s+image|placeholder|lorem ipsum|
add\s+your\s+text|your\s+text\s+here|insert\s+text
```

---

## 23. Thresholds & Magic Numbers

### Classification & Matching

| Parameter | Value | Location |
|-----------|-------|----------|
| Heading detection | font_size ≥ median × 1.3 | `layout_analyzer.py` |
| Y-grouping tolerance | 20px | `converter.py:_group_into_rows` |
| Sparse layout detection | child_width < 60% container | `converter.py:_calculate_column_widths` |
| Icon size threshold | ≤30px width AND height | `component_matcher.py:_all_images_are_icons` |
| Button detection | ≤30 chars text, ≤80px height | `layout_analyzer.py:_extract_buttons` |
| Hero image detection | ≥80% parent width | `converter.py:_group_into_rows` |
| Nesting depth limit | 6 levels | `converter.py:node_to_email_html` |
| Parse depth limit | 30 levels | `figma/service.py:_parse_node` |
| Walk depth limit | 500 levels | `figma/service.py:_walk_for_*` |

### Extended Matcher Signals

| Component | Key Signal | Threshold |
|-----------|-----------|-----------|
| Countdown timer | Time pattern matches | ≥3 |
| Testimonial | Avatar image size | ≤100px |
| Testimonial | Body text length | ≤200 chars each |
| Video placeholder | Aspect ratio (16:9) | 1.6–1.9 |
| FAQ accordion | Alternating "?" texts | ≥2 questions |
| Zigzag | Mixed column groups | ≥3 |
| Category nav | Short text length | <20 chars |

### Slot Fill Limits

| Slot Type | Max Count |
|-----------|-----------|
| Product grid items | 4 |
| Category nav items | 6 |
| Image gallery images | 6 |
| Column layout groups | 4 |

### Quality & Rendering

| Parameter | Value |
|-----------|-------|
| WCAG AA normal text contrast | 4.5:1 |
| WCAG AA large text contrast | 3.0:1 |
| Slot fill rate warning | <50% |
| Outlook dark mode safety | `#000000` → `#010101`, `#FFFFFF` → `#FEFEFE` |
| Dark bg luminance threshold | <0.4 (invert text to white) |
| Container width default | 600px |
| Mobile breakpoint | 599px |

### VLM Verification

| Parameter | Default |
|-----------|---------|
| ODiff skip threshold | 2.0% |
| Target fidelity | 97% |
| Max iterations | 3 |
| Correction confidence | 0.7 |
| VLM timeout | 30s |
| VLM cache size | 256 entries |

---

*End of audit document.*
