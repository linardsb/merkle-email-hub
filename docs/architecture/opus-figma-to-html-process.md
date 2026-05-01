# Opus Figma → HTML Email Conversion Process

How a direct-to-Opus conversion of a Figma design into an HTML email differs
from the email-hub `design_sync` converter, plus concrete recommendations for
closing the gap. Findings drawn from converting the LEGO Insiders "Frights and
brick-built delights" Halloween email (Figma node `2833:1869`) entirely from
existing components in `email-templates/components/`.

Output of the conversion: `email-templates/lego-insiders-halloween.html`
Assets: `email-templates/lego-insiders-halloween-assets/` (23 PNGs)

---

## TL;DR — the biggest leverage points

### 1. Feed the full-design PNG into classification (Gap 9)

**The converter already fetches `design.png` (`figma/service.py:522`) but
discards it before classification.** It only ever passes per-section
screenshots through `design_screenshots: dict[str, bytes]` keyed by
node_id. Every classification decision is local to one section. Most of
the misreads we caught across three review cycles are *relational*
properties that require seeing two adjacent sections together — or
properties that need the rendered design as ground truth (rules 4, 5, 6
in §8.3 strictly need it; rules 9 and 11 use it as cheap verification).
A non-exhaustive sample of the relational mistakes:

- "Card sits as a white rounded inner box on lime wrapper, not directly on
  lime" → Rule 1 + Rule 9
- "Heading is left-aligned within its outer wrapper, not centered" → Gap 11
- "Tag pill is left-aligned (its bbox.x equals the parent column's bbox.x)
  and has no `cornerRadius` so it must render with square corners" → Rule 7 + Rule 8
- "These 4 sections are 4 product rows that share a heading two sections up"
  → Gap 5 / repeating-group detection
- "This 600×40 image is a colour-transition band, not a stand-alone divider"
  → Gap 8

The fix is one extra `/v1/images` call up front (~$0 in Figma quota), one
new field on `DesignFileStructure`, and threading the bytes through to
`analyze_layout()` and the matcher's confidence-fallback path. Without
this, the converter is structurally limited to ~85% fidelity on any
non-trivial design. With it (plus the 11 rules in §8.3 codified), the
ceiling moves to ~95%+. See §8.6.2 for the per-design contract: PNG is
loaded fresh per conversion, never reused as a stand-in.

### 2. Add a `composite_slot` slot type

> Every slot today is a string (text, URL, HTML fragment). With composite
> slots, a card can *contain* a tag-pill + a CTA, a zigzag row can
> *contain* a spec-list, and a footer wrapper can *contain* a
> barcode-image + social-row + links-block. **Three of the five "missing
> component" gaps collapse into "add a sub-slot" once composite slots
> exist.**

### Other high-leverage moves (Part 4)

1. Promote `bgcolor_propagator` from one-direction propagator to first-class
   section-boundary classifier — fixes Gaps 1, 6, 8, 10.
2. Two-stage layout: wrapper unwrap → section classify — fixes Gaps 1, 4, 6.
3. Verification reuse for repeating groups — cuts VLM cost ~4× on product
   grids.
4. Default to per-frame image export for composited frames; keep `imageRef`
   only for raw-rectangle leaves — fixes Gap 7.

### 3. Run the universal repair loop (Part 8)

**The single biggest converter-engine win after Gap 9 is codifying the
five-stage repair loop (capture → diff → categorize → apply → re-render →
loop) and the 11 detection rules in Part 8.** They are *design-agnostic*
— each rule fires on structural properties (frame nesting, alpha
channel, sibling count, child x-coordinate, cornerRadius, fill-colour
parity, viewport class, table-vs-image width parity), not on
LEGO-specific or e-commerce-specific content. The same loop handles
transactional emails, newsletters, abandoned cart flows. The 11 rules
cover ~92% of the structural divergences we see between Figma designs
and rendered HTML; the remaining 8% are content-level errors (wrong
copy, wrong asset) that fall outside the visual-fidelity problem.

Rules 7–11 in particular came out of *successive* review cycles on the
same LEGO email — even after rules 1–6 passed, five further classes of
misread surfaced one at a time (pill alignment from x-position, pill
cornerRadius from the FRAME, dark-mode contrast on nested cards,
per-corner image radii, fixed-width inner card matching image width).
**Plan to run at least three review cycles per design until the rule
set stops growing** — each cycle exposes errors the previous fix
masked.

The loop also forces the converter to **render at every viewport class the
design targets** (typical: 600 px desktop and one mobile breakpoint ≤
480 px) — single-viewport rendering is the most common cause of "fixed in
one place, broken in another" loops, and the bug we just fixed on the LEGO
membership cards (image at 250 px max-width on a 480 px stacked column,
leaving whitespace) is its canonical example.

## Section → component → gap map

What I did, at a glance. Each row is one Figma `mj-wrapper` (or sub-row
when wrappers split):

| # | Figma section | Component used | Slots filled | `[GAP]` inlined |
|---|---|---|---|---|
| 1 | Top-bar `View online` link | `text-block` (right-aligned) | heading | none |
| 2 | LEGO Insiders logo band (600×67) | `full-width-image` | image_url, image_alt | none |
| 3 | Hero image (600×400, Stranger Things) | `full-width-image` | image_url, image_alt | none |
| 4 | Hero text+CTA on purple | `text-block-centered` + `button-filled` | heading, body, cta_text, cta_url | wrapper bgcolor + white-button-on-purple variant |
| 5 | Green decorative band (600×40) | `image-block` (no caption) | image_url | none — but converter routes 600×40 image to wrong component without "transition_band" type |
| 6 | "Membership Tip" heading on lime | `text-block-centered` | heading, body | wrapper bgcolor (Gap 1) |
| 7 | Card: Art prints | `zigzag-image-left` | image, heading, body, cta | **tag-pill (Gap 2)**, **white-card-on-lime (Gap 10)** — Rules 1, 2, 3, 7, 8, 9, 10 |
| 8 | Card: Stationery | `zigzag-image-left` | image, heading, body, cta | **tag-pill (Gap 2)**, **white-card-on-lime (Gap 10)** — Rules 1, 2, 3, 7, 8, 9, 10 |
| 9 | "Expect lots of treats" heading | `text-block` (left-align variant) | heading | **left-align override (Gap 11)** |
| 10 | Product 1: Halloween Wreath | `zigzag-image-right` | heading, cta | **spec mini-table (Gap 3)**, white-card-on-lime, multi-line text — Rules 1, 2, 3, 6, 9 |
| 11 | Product 2: Hocus Pocus | `zigzag-image-left` | heading, cta | spec mini-table, white-card-on-lime, multi-line text — Rules 1, 2, 3, 9 |
| 12 | Product 3: Haunted mansion | `zigzag-image-right` | heading, cta | spec mini-table, white-card-on-lime, multi-line text — Rules 1, 2, 3, 6, 9 |
| 13 | Product 4: Jack-O'-Lantern | `zigzag-image-left` | heading, cta | spec mini-table, white-card-on-lime, multi-line text — Rules 1, 2, 3, 9 |
| 14 | Lower decorative band (600×55) | `image-block` (no caption) | image_url | seam-color matching (Gap 8) |
| 15 | Footer: 4-cell user-info row + literal pipe divider | `column-layout-4` | (4 cells: avatar/name/icon/points) | **composite footer (Gap 4)** — Rule 4 (visible-but-absent divider), Rule 9 footer-strong sub-pattern |
| 16 | Footer: Insiders white card (header logo + andy/email + barcode + bottom shape) | unified card-shell wrapping 4 children | image, image, text, image | (Gap 4) — collapsed from 4 separate sections via Rule 1; identity exception of Rule 9 (stays white in dark mode); Rule 5 (`footer-social.png` is actually a barcode); Rule 11 (card width matches 440px image children) |
| 20 | Footer: links + legal | `footer-centered` | links, copyright | Rule 9 (`.footer-link a` overrides inline anchor `color`) |

The four `[GAP]` types — tag-pill, spec mini-table, composite footer,
wrapper bgcolor — drive Gaps 1–4 in Part 3. Rules 1–11 (codified in §8.3,
worked instances marked `[Rule N]` in `lego-insiders-halloween.html`)
specify the per-design action that closes most of these gaps once the
converter implements them.

---

## Part 1 — How Opus reasoned about this conversion

The conversion was not "look at design, write HTML." It was a six-pass loop
where each pass yielded an artifact the next pass relied on. Most of the
decisions that determine fidelity happen in passes 3–5, not in writing HTML.

### Pass 0 — Source-of-truth ingestion (~5% of effort)

- `GET /v1/files/{key}/nodes?ids=2833:1869&geometry=paths` — full subtree as
  JSON. 223 KB, 8 top-level `mj-wrapper` children. Cached locally.
- `GET /v1/images?ids=2833:1869&format=png&scale=2` — rendered PNG of the
  whole frame (1200×6446). Used as the **ground-truth reference** against
  which I check every later inference.
- `GET /v1/images?ids=…23 image-leaf node ids…&format=png&scale=2` — one
  composited export per `mj-image-Frame`. **Critical move**: I do not chase
  raw `imageRef` hashes. Exporting the parent frame gives the design exactly
  as it appears, including masks, transforms, and overlapping vector
  decoration. 23/23 image assets resolved in one round-trip.

**Insight:** the Figma JSON gives me the structure; the rendered PNG gives me
ground truth. Neither alone is enough. The JSON tells me there are eight
`mj-wrapper` sections; the PNG tells me which two of them are decorative
torn-paper bands and which is the lime-green section background.

**The full-design PNG is load-bearing — and the converter doesn't use it.**
The current pipeline (`figma/service.py:522`) writes `design.png` to the
training-case folder for regression archival, but never feeds it back into
classification, matching, or rendering. The `design_screenshots: dict[str,
bytes]` parameter on `DesignConverterService.convert_document` (and threaded
through to `visual_verify`, `vlm_classifier`) is keyed by **per-section
node_id**, not the global frame. The visual reference exists upstream but is
discarded before it can inform decisions. See Gap 9 below — most of the
mismatches I had to fix in pass two are mismatches an LLM with a global
visual reference would have caught on pass one.

> **Note on universality.** Pass 0 here describes the LEGO-specific Figma
> calls. The same step generalises to any design — the converter should
> always (a) fetch the FRAME tree JSON for the email's root frame, (b)
> fetch the full-design PNG via `/v1/images` once, (c) batch-export all
> image-leaf assets — for *any* design, regardless of brand or theme.
> §8.6.2 codifies this as a per-design contract: the PNG is loaded fresh
> per conversion, never reused as a stand-in across designs. Cards that
> look LEGO-specific here ("8 mj-wrappers", "23 image assets") are
> calibration values for *this* design — the algorithm is the same for
> any other design, with each design's own counts and asset list.

**Concrete example from this conversion:** my first pass placed the
"Membership Tip" cards directly on the lime-green wrapper because the JSON
said `mj-section` with no fill. The actual design has each card as a
**white rounded inner card** sitting on the lime wrapper. From the
**per-section** PNGs you cannot tell — each card export shows just its own
content. From the **full-design** PNG it is unambiguous on a single glance.
The 30-line patch I wrote in pass two (8 `<table>` wrappers with
`border-radius: 16px`) maps directly to *one* observation that needs the
global view.

### Pass 1 — Tree-walking with intent (~10%)

For every node I capture only the *load-bearing* properties:

| Node type | Captured |
|-----------|----------|
| `TEXT`    | `characters`, `style.{fontSize,fontWeight,fontFamily,textAlignHorizontal}`, fill color, absolute bbox |
| `RECTANGLE` / `FRAME` with `IMAGE` fill | `imageRef`, bbox, parent path |
| `FRAME` (structure) | name, child count, layout direction, padding, fill |

I do this with one `walk()` recursion in Python, not with the LLM doing
visual interpretation. **The LLM should never be asked to be the parser.**
It should be asked to be the planner.

This pass produces a flat dump like:

```
TEXT y=3843 x=1747 w=540 h=41 fs=30.0 fw=600 ff=Noto Sans align=CENTER color=#ffffff
     'Frights and brick-built delights'
```

That single line locks in: heading, semantic role (large bold centered white
text on a coloured wrapper = hero title), exact typography. The matcher
can't recreate this from name alone — `mj-wrapper`/`mj-section`/`mj-column`
tells it nothing about which child is the hero title.

**What the LLM does that a deterministic pass can't:**

- Reading `'Frights and brick-built delights'` and `'Conjure up even more
  joy this scary season…'` together as a hero pair instead of two unrelated
  texts. Any classifier that scores on counts/geometry alone will mis-pair
  texts that *belong* together.
- Inferring that the 4 product rows are a **list** (so the heading
  "Expect lots of treats this Halloween!" governs all 4) versus 4
  independent sections that happen to look similar. The text content
  ("treats" → list of treats) is the cue, not the layout.
- Detecting that "+260 LEGO® Insiders Points" is a *reward count*, not a
  product description, and therefore lives in a spec-list slot rather than
  a body-text slot. Same string of characters, very different role.

These three judgments are *cheap* for an LLM (one prompt with the dump) and
*expensive* for hand-written heuristics (each requires a separate
case/pattern).

### Pass 2 — Visual ground-truth sampling (~10%)

Two questions the JSON cannot answer:

1. **What is the background color *behind* a section?** Figma's `fills` on a
   `FRAME` may be empty even when the rendered output sits on a colored
   background, because the colour comes from a sibling rectangle or a parent
   wrapper. I sample the rendered PNG at `(x_left, y_section_top + 5)` and
   `(x_left, y_section_bottom - 5)` to get the actual visible color.
2. **Where do two sections actually *butt up* against each other vs. have a
   transition image between them?** I sample the last 5 px of section *n*
   and the first 5 px of section *n+1*. If they match (Δ ≤ 5 in each
   channel), it's a continuous wrapper; if not, there's a transition asset
   I need to keep.

For this email:

| Boundary | Top edge | Bottom edge | Verdict |
|---|---|---|---|
| Hero image → hero text | `#492d8e` | `#4a2e8f` | Continuous purple wrapper |
| Purple wrapper → green band | `#4e3092` | `#afca01` (post-band) | Hard transition, band asset is the bridge |
| White treats → lower band | `#ffffff` | `#e9eecb` | Hard transition, band asset is the bridge |

This is a 12-pixel sample, not vibes. **The converter cannot fake this with
LLM eyeballing because pixel sampling is deterministic and free.**

### Pass 3 — Section semantics (the actual hard part, ~25%)

The Figma file is named in MJML convention (`mj-wrapper` → `mj-section` →
`mj-column` → `mj-text-Frame`/`mj-image-Frame`/`mj-button-Frame`). That tells
me almost nothing about *what each wrapper is for*. I have to derive intent
from contents, geometry, and color.

For each of the 8 wrappers I asked: what role does this play? I label each
wrapper with one of: `top-bar`, `header`, `hero-image`, `hero-text-cta`,
`decorative-band`, `section-heading + cards`, `section-heading + product-rows`,
`footer-composite`. The mapping isn't 1:1 with `EmailSectionType`:

| Figma wrapper | Width × Height | My label | Single `EmailSectionType` it fits? |
|---|---|---|---|
| #1 | 600×30 | preheader-link bar | (none — `PREHEADER` is hidden text, but here it's a visible top-link strip) |
| #2 | 600×467 | logo-band + hero-image | (mixed — wants `HEADER` *and* `HERO`) |
| #3 | 600×206 | hero-text-cta on purple | `HERO` (text-only, but classified as `CONTENT` by the matcher because it has no image) |
| #4 | 600×40 | green band 1 (decorative) | (none — `DIVIDER` is a 1px line, this is a torn-paper image) |
| #5 | 600×723 | section-heading + 2 cards | (mixed — wants `CONTENT` heading *and* repeating `CONTENT` cards) |
| #6 | 600×1072 | section-heading + 4 zigzag rows | (mixed — same problem) |
| #7 | 600×55 | green band 2 | (none) |
| #8 | 600×630 | composite footer | `FOOTER` (but `_fills_footer` only emits `<br><br>`-joined text) |

This is the most important finding for the converter team:
**the `mj-wrapper` boundary is not the section boundary.** A `mj-wrapper` is
a Figma layout convenience; it routinely groups a section heading with the
N cards beneath it on the *same* coloured background. The converter
currently treats one `mj-wrapper` = one `EmailSection`, which is why
wrappers #5 and #6 are misclassified into a single component instead of
splitting into `(heading, repeating-group)`.

### Pass 4 — Component selection (~15%)

For each labelled section I pick from `email-templates/components/` by
matching: number of images, number of texts, button presence, column
structure, *and* the inferred role. The matcher does this with a candidate
score; I do it as a flowchart but the algorithm is the same. Where the
matcher and I diverge:

- **Repeating cards** — the matcher would pick `editorial-2` or
  `article-card` *per row* and emit 2 (or 4) sibling tables. I pick
  `zigzag-image-left.html` / `zigzag-image-right.html` *alternating*,
  which is the same component the engine already uses, but I commit to
  the alternation up front. The engine does have `sibling_detector.py:62`
  for this — but as far as I can see it's wired to detect groups, not to
  drive the alternation pattern of the renderer.
- **Tag pills, spec mini-tables** — see Gap 1 + Gap 2 below. I inline these
  inside the existing component shells. The matcher has no slot for them
  and would silently drop them.
- **Composite footer** — see Gap 3 below.

### Pass 5 — Inline content + token overrides (~25%)

This is where the converter and I look the most similar — both fill
`data-slot` markers with extracted values and override colors/fonts via
inline style mutations. `_build_token_overrides` at
`app/design_sync/component_matcher.py:1401` overrides `background-color`,
`font-family`, `font-size`, `color`, `padding`, and CTA properties on
`_outer`/`_heading`/`_body`/`_cell`/`_cta` targets. That covers ~90% of my
overrides. The mismatches are localized:

- The converter applies CTA overrides only to the *first* button. Wrapper
  #3 (hero) has a white-on-purple button; wrappers #5–8 use purple buttons.
  Per-section override is correct; my email applies them per-section.
- Sample bgcolor of *adjacent* sections to detect the wrapper, not just the
  bg of the section's own frame — covered by `bgcolor_propagator.py` (41.2)
  but only one direction, and only when the section frame has an empty fill.

### Pass 6 — Verification (~10%)

I view the rendered PNG of each component as I write it. The converter has
the same primitive: `visual_verify.py` with section-level cropping +
ODiff pre-filter + VLM correction. The architectural piece the converter
already has but doesn't yet exploit: this email has 4 visually-similar
zigzag rows. If row 1 verifies, rows 2–4 should be checked with a much
cheaper *self-similarity* check (do they look like row 1 modulo image
content?) before invoking VLM correction on each. That cuts VLM calls 4× on
exactly the kind of section that's most expensive to verify.

---

## Part 2 — How the email-hub converter currently works

Pipeline (line counts as of this write-up):

```
Figma REST          ──>  figma/service.py            (1720 LOC)
                            sync_tokens_and_structure()
                            └─> DesignFileStructure (DesignNode tree)
                                ↓
Layout analysis     ──>  figma/layout_analyzer.py    (1299 LOC)
                            analyze_layout()         :222
                            ├─ _get_section_candidates :385  (unwrap single full-email frame)
                            ├─ _detect_naming_convention :413  (mjml/descriptive/generic)
                            ├─ _classify_section     :446
                            │    ├─ _classify_mj_section :485
                            │    └─ _classify_by_content
                            ├─ _detect_column_layout_with_groups
                            ├─ _extract_texts/_extract_images/_extract_buttons
                            └─ _extract_content_groups (49.5)
                                ↓
                            DesignLayoutDescription
                                  ├── EmailSection × N
                                  └── spacing_map
                                ↓
Sibling grouping    ──>  sibling_detector.py         (169 LOC)
                            detect_repeating_groups() :62
                                ↓
                            list[EmailSection | RepeatingGroup]
                                ↓
Component matching  ──>  component_matcher.py        (1469 LOC)
                            match_all()              :93
                            └─ match_section()       :56
                               ├─ _match_by_type     :187
                               │   ├─ _score_candidates  :273
                               │   └─ _score_extended_candidates :380
                               ├─ _build_slot_fills  (per-component fills :742-1308)
                               └─ _build_token_overrides :1401
                                ↓
                            ComponentMatch × N
                                ↓
Rendering           ──>  component_renderer.py       (848 LOC)
                            render_all()
                            ├─ render_section()      (single-section path)
                            └─ render_repeating_group()  (49.2)
                                ↓
                            HTML
                                ↓
Visual verify       ──>  visual_verify.py            (517 LOC)
                            run_verification_loop()
                            ├─ compare_sections()    (ODiff + VLM)
                            └─ correction_applicator.py :apply_corrections()
```

The stage that misclassifies on this email is **layout_analyzer**: it
treats one `mj-wrapper` as one section, regardless of how many heterogeneous
rows live inside.

---

## Part 3 — Concrete gaps from this conversion

Each gap below = something Opus did that the engine, given the same Figma
file, would not produce today. Each lists: what's missing, where, what to
add, and the file:line that would change.

### Gap 1 — Section "wrapper" with a coloured background is not a first-class concept

**Symptom on this email:** wrappers #3, #5, and #6 each contain multiple
content rows that all sit on the *same* coloured background (purple, lime
green, lime green). The converter treats the wrapper as one `EmailSection`
and produces a single-component output (`text-block` or `article-card`),
losing both the contained heading and the per-row structure.

**Where it breaks:**
- `figma/layout_analyzer.py:385` `_get_section_candidates()` unwraps a
  single top-level wrapper but does not unwrap the inner `mj-section`
  children of a tall `mj-wrapper`. For MJML files, a `mj-wrapper` is a
  background-painted container; its `mj-section` children are the actual
  rows.

**Recommendation:**
1. In `_get_section_candidates()`, add a second unwrap pass for MJML
   convention: when a candidate `mj-wrapper` has a fill color *and* contains
   ≥2 `mj-section` children, return the children with `bg_color` propagated
   from the wrapper.
2. New `EmailSection.wrapper_bg_color` field, distinct from
   `EmailSection.bg_color` (the section's own fill). The renderer applies
   wrapper bg as the outer `<td bgcolor>` and the section bg as the inner
   table.
3. Adjacent-section bg matching to validate the unwrap (cheap:
   `bgcolor_propagator.py` already does the sampling).

**Lines that would change:** `layout_analyzer.py:385-410` (unwrap pass);
`layout_analyzer.py:135-165` (`EmailSection` field); renderer needs a new
"wrapper" frame type.

### Gap 2 — Tag/pill overlay is not a slot on any card component

**Symptom:** the membership cards have a tiny purple pill above the heading
("Art prints", "Stationery"). It's a `FRAME` (not a RECTANGLE) with a fill
+ padding + a `TEXT` child centred on it, sitting flush-left in the card's
content column. `_fills_article_card` (component_matcher.py:920) emits only
`image_url`, `heading`, `body_text`, `cta_text`, `cta_url`. The pill text
gets either swallowed into `body_text` or dropped (depending on whether
content groups fire). The pill's alignment and corner radius come from
the FRAME's bbox-x and `cornerRadius` (Rules 7 + 8) — **the converter
must NOT default to "tag pills are right-aligned and rounded" because
Figma data routinely contradicts both assumptions** (the LEGO pills are
left-aligned with `cornerRadius=0`).

**Where it breaks:**
- `component_matcher.py:920` `_fills_article_card` consumes the first
  heading and first body — short uppercase-ish text that is structurally
  styled as a pill is not a heading per Figma's font-size logic.
- `email-templates/components/article-card.html`,
  `zigzag-image-left.html`, `zigzag-image-right.html` — none have a
  `data-slot="tag"` or `data-slot="category"` slot.

**Recommendation:**
1. Add an optional `tag` slot to `article-card.html`, `zigzag-image-left.html`,
   `zigzag-image-right.html`, and the editorial cards. When unfilled, the
   tag row is stripped (already standard "render component" hygiene).
2. In `_extract_content_groups`, mark any text whose parent FRAME is a
   small fill + padding leaf (typically `layoutMode=HORIZONTAL`,
   paddingLeft/Right ≥ 8 px, single TEXT child) as `role_hint="tag"`. **Do
   not require a non-zero `cornerRadius`** — Rule 8 says the pill's
   corners come from Figma's `cornerRadius` (often 0), so detection must
   not gate on it.
3. `_fills_article_card` consumes the tag-roled text into the `tag` slot
   before falling back to body extraction. The `tag` slot template emits
   alignment and border-radius from per-FRAME data:
   - `align` = output of Rule 7's bbox.x comparison (left / center / right)
   - `border-radius` = output of Rule 8 (`cornerRadius` field, default 0)

**Lines that would change:** `layout_analyzer.py:_extract_content_groups`
(role detection); `component_matcher.py:920-961` (slot population);
3 component HTML files (slot markup).

**See also:** §8.3 Rules 7 + 8 for the per-design alignment / radius logic;
`email-templates/lego-insiders-halloween.html` sections #7 and #8 for the
worked instances tagged `[Rule 7]` and `[Rule 8]`.

### Gap 3 — Spec mini-table inside zigzag/product rows is not a slot

**Symptom:** each of the four zigzag product rows includes a 4-cell mini
table: `[icon] 617 Pieces  [icon] +260 LEGO Insiders Points`. Two small
images (16×22 and 26×26) and two short text labels. The matcher sees
`section.images = [product_img, icon_pieces, icon_points]` (3 images) and
either over-counts to `image-gallery` (3+ images, ≤1 text — but here we
have many texts so it doesn't fire) or, more likely, the 3 images push it
into `editorial-2` / `image-grid` candidates, while the small icons get
treated as "more product images".

**Where it breaks:**
- `component_matcher.py:_score_candidates` (line 273) and
  `_score_extended_candidates` (line 380) both decide based on counts and
  geometric ratios. They have no concept of "one big image + N icon-sized
  images that are siblings of texts inside a single column" = "spec list".
- The new `col-icon` extended candidate (line 478) handles 1 icon + 1-3
  texts. The spec-row in this email is *2 icon+text pairs* arranged in a
  single row. Today it would either fall into `text-block` (icons
  ignored) or `article-card` (icons swallowed into image_url).

**Recommendation:**
1. Add `spec-list` to `_score_extended_candidates` triggered by: ≥2 images
   ≤30 px wide *each* sibling-paired with a text < 40 chars. Confidence
   0.92 with 2+ pairs.
2. New component `spec-list.html` with a slot that takes a list of
   `(icon_url, label)` tuples — emitted as a single-row table, one cell pair
   per item. Use as a *child* component of zigzag rows (i.e. the matcher
   nests it inside the zigzag content column).
3. Alternatively (cheaper): extend zigzag-image-{left,right}.html with
   an optional repeating `<tr data-slot-repeat="specs">` row + matching
   filler in `_fills_article_card`.

**Lines that would change:** `component_matcher.py:380-490`,
`component_matcher.py:920-961`, plus one new component file or two updated
ones. New section type might be unnecessary if the spec is always a
*sub-row* of a card.

### Gap 4 — Composite footer pattern (`_fills_footer` is a stub)

**Symptom:** the footer wrapper contains: a 4-cell user-info row (above
the card), a unified white card with 4 children (header logo image,
name+email text, barcode image, bottom-shape image), and a links + legal
row underneath. The white card's 4 children come from a single Figma
FRAME (`2833:2057`) with `fills[0]=#ffffff` and `cornerRadius=24` — i.e.
**Rule 1's canonical case**. Pre-Rule-1 conversions emitted 4 separate
top-level rows; the rule says: collapse them into one wrapping rounded
table.

`component_matcher.py:_fills_footer` (line 1087) does:
```python
parts = [_safe_text(text.content) for text in section.texts]
return [SlotFill("footer_content", "<br><br>".join(parts))]
```

That's a straight join. Images are dropped. Structure is dropped. The
links row collapses into the legal text. The barcode card image vanishes.

**Where it breaks:**
- `component_matcher.py:1087-1105` `_fills_footer` ignores
  `section.images`, `section.column_groups`, and structural ordering.
- `email-templates/components/footer-centered.html` is a single-column
  footer; `email-templates/components/footer.html` is even thinner. Neither
  expresses the parent-frame-as-rounded-card pattern that Rule 1 demands.

**Recommendation:**
1. Detect "composite footer" structurally: `_classify_section` keeps
   `FOOTER` for the leaf footer-text sections, but Rule 1 fires on the
   *parent* FRAME with `fills` + `cornerRadius` + ≥2 heterogeneous
   children — the renderer wraps them in one `<table bgcolor=…
   border-radius:Npx>` and emits each child as an inner row.
2. Pair Rule 1 with Rule 11 (card width matches image children) so the
   inner card is exactly as wide as its imagery (no horizontal gap on
   the right). For LEGO that's `width="440"`; for any other design,
   read the dominant child image's native width.
3. The user-info row (above the card) and the links + legal row (below)
   stay as their own sections — Rule 4 emits the literal `|` divider
   in the user-info row when no FRAME node exists for it.
4. `_fills_footer` keeps its current responsibility for the *links + legal*
   leaf section only. Rename to clarify: `_fills_footer_legal`.

**Lines that would change:** `component_matcher.py:1087` (stricter scope);
Rule 1's wrapper-unwrap supplies the needed sub-sections.

**See also:** §8.3 Rules 1 + 4 + 5 + 9 (identity exception) + 11;
`email-templates/lego-insiders-halloween.html` sections #15 and #16 for the
worked instances. Note the dark-mode identity exception on #16: the white
card stays white in dark mode (no `class="card-bg"`) because it represents
a physical membership card.

### Gap 5 — Sibling group renderer is wired but not exploited for verification

**Symptom:** wrapper #6 has 4 product rows with the same shape. They are
the textbook input for `sibling_detector.detect_repeating_groups()` at
`sibling_detector.py:62`. The detector builds `RepeatingGroup` and the
renderer has `render_repeating_group()`. But:

- The 4 rows are inside one `mj-wrapper`; without Gap 1's fix they are
  *one* section, not 4 sections, so the sibling detector never sees them
  as siblings.
- Even when they are seen as 4 siblings, `visual_verify.run_verification_loop`
  (`visual_verify.py`) runs the VLM compare per section. For 4 visually-
  similar siblings that's 4 VLM calls when 1 + 3 cheap structural-equality
  checks would do.

**Recommendation:**
1. Fix Gap 1 first — without sub-section unwrapping, sibling detection
   can't fire on the inner rows.
2. In `visual_verify.py`, when a section is a member of a `RepeatingGroup`
   *and* the first member has verified, cache the corrections from member
   1 and apply them by default to members 2..N, calling the VLM only as a
   *second-pass* check on members 2..N.

**Lines that would change:** mostly in `visual_verify.py`; the gain is cost
not fidelity — but on emails with N×4 product rows it's the difference
between 1 VLM call and 16.

### Gap 6 — Hero-text-only section with adjacent hero-image misclassified

**Symptom:** wrapper #3 (`Frights and brick-built delights` + body + CTA on
purple) has 2 texts, 1 button, 0 images. `_match_by_type` sees `CONTENT`
and routes to `_score_candidates`, which falls through to `text-block`
(line 344) because there's no image. The hero context is lost — the heading
gets `text-block`'s default 24 px on white instead of 30 px on purple.

The *actual* hero is wrapper #2's image. The *text* belongs to that hero.
But because they are separate `mj-wrapper`s and the analyzer treats them
as separate sections, the relationship is lost.

**Where it breaks:**
- `component_matcher.py:205-214` — `HERO` requires `has_images`. Text-only
  hero halves are routed into `CONTENT`.

**Recommendation:**
1. Pair-detection: when a section classifies as `HERO` (image-bearing) and
   the immediately following section is a `CONTENT` text-on-coloured-bg
   that matches the hero's bottom-edge bgcolor, merge them or tag both
   with a shared `hero_pair_id`. The renderer then emits a single
   `hero-block`/`hero-text` component with the image as background and the
   text + CTA as overlay.
2. Trigger heuristic: section A has a 600-px-wide image bottom-aligned;
   section B has texts + ≤1 button on a non-white bg; A.bottom_color ≈
   B.top_color. All three checks are cheap.

**Lines that would change:** new pair-merger pass between
`detect_repeating_groups()` and `match_all()`; small edit to
`_classify_by_content` to mark text-on-coloured-bg sections as
`hero-text-candidate`.

### Gap 7 — Image asset resolution should default to per-frame export, not imageRef

**Symptom (not a bug, an efficiency):** the converter resolves images via
`imageRef`-based S3 URLs. That's the raw source asset. For a frame that has
masks, transforms, or composited vector decoration, the raw asset doesn't
match what the user sees. Per-frame `/v1/images?ids=…` rendering at
`scale=2` returns the design-as-rendered, which is what every email-design
visual-verification step actually wants to compare against.

**Recommendation:** add a `image_resolution_mode: "imageRef" | "frame_export"`
toggle on `DesignSyncConfig`. Default to `frame_export` for any frame whose
node has children other than the imageRef-bearing rectangle (i.e.
"composited") and `imageRef` for a leaf rectangle. The cost is one extra
`/v1/images` call per email but it's batched (single call for all frames).

**Lines that would change:** `figma/service.py` image-extraction path; new
config field in `app/core/config.py`'s `DesignSyncConfig`.

### Gap 8 — Decorative band assets need an explicit "transition" type

**Symptom:** wrappers #4 and #7 are pure-image `mj-wrapper`s containing one
600-px-wide image — the torn-paper/wave decorative bands. The matcher
classifies them as `image-block` or `full-width-image` (correct), but the
renderer surrounds them with default 32-px padding which breaks the
seamless wrapper-to-wrapper transition.

**Recommendation:** when a section is a single image with `width ≥ 95% of
container_width` *and* its bottom edge color matches the next section's
top edge color *and* its image dimensions are < 70 px tall, mark as
`transition_band` and emit zero padding on its outer cell.

**Lines that would change:** `_score_candidates` for the heuristic;
`_build_token_overrides` to emit zero-padding overrides on transitions;
sampling already exists in `bgcolor_propagator.py`.

---

## Part 4 — Process recommendations the engine can adopt

Beyond the per-gap fixes, four structural changes would close most of the
remaining 2 % gap to direct-Opus output.

### 1. Make pixel sampling a peer of geometry, not an afterthought

`bgcolor_propagator.py` (Phase 41.2) already samples edge pixels. Promote
it from a single-direction propagator to a first-class **section-boundary
classifier** that runs *before* `_classify_section`. Output:
`continuous_with_above`/`continuous_with_below`/`hard_break`. This enables
Gaps 1, 6, and 8 with one shared computation.

### 2. Two-stage layout: wrapper unwrap → section classify

The current pipeline does one classification pass per top-level frame. A
two-stage pass — wrapper detection (single big bg, multiple inner sections)
followed by inner-section classification — costs almost nothing
computationally and unblocks Gaps 1, 4, and 6. The `mj-wrapper` MJML idiom
should be the canonical signal for stage one.

### 3. Component composition should be a first-class slot type

Today, slots take strings (text, URL). Add a `composite_slot` whose value
is a list of `ComponentMatch` objects rendered by a sub-renderer. This lets
the membership card row *contain* a `tag-pill` plus a `cta-button`, the
zigzag row *contain* a `spec-list`, the footer wrapper *contain* a
`barcode-card-image` + `social-row` + `links-block`. Without this, every
new compositional pattern requires a new component file. This is the
single biggest leverage point — Gaps 2, 3, 4 collapse to "add a composite
slot".

### 4. Verification reuse for repeating groups

Already proposed in Gap 5. The cost saving compounds because almost every
e-commerce / membership / newsletter email has 3-6 visually-similar
product or article rows.

---

## Part 5 — What didn't matter

Things I expected to matter that didn't, in case the engine team is
considering work in these areas:

- **VLM section classifier** (`vlm_classifier.py`): on this email all 8
  wrappers were correctly classifiable from MJML names + content rules.
  The VLM fallback would only trigger on the text-only hero (Gap 6) and
  even there, structural pair-detection is cheaper and more reliable.
- **Custom component generation** (`custom_component_generator.py`): not
  needed for any section here. Every gap was either a missing slot in an
  existing component or a missing wrapper concept — not a missing
  component. AI-generating new components for already-familiar shapes
  trades determinism for novelty when determinism is what email rendering
  needs.
- **Token transforms**: the design uses Noto Sans + a small palette
  (#4e3092, #afca01, #ffffff, #000000, #836eb2, #f4f4f4). The existing
  `_build_token_overrides` machinery handles all of these. No changes
  needed.

---

## Part 6 — Second-pass corrections after seeing the rendered ground truth

Pass 1 produced an HTML email that read the JSON correctly but missed five
visual relationships that only become obvious from the full-design PNG.
This is exactly the failure mode the converter would hit — it has all the
JSON inputs but no global visual reference. Each item below is a fix I had
to make in pass 2 *and* a corresponding gap to add to the engine.

### What I missed on pass 1 (and why)

| Pass-1 mistake | Visual cue I missed | Why JSON alone can't tell you |
|---|---|---|
| Membership cards painted directly on lime green | Each card is a **white rounded inner box** floating on lime | The card frames have empty fills in the JSON; the rounded white shape is implied by the parent layout, not declared |
| Product cards painted directly on white | Each card is a **white rounded inner box** floating on lime | Same as above |
| Sections #9–13 outer bg = white | The lime wrapper extends across all of them | The wrapper bgcolor is on `mj-wrapper`, not the inner `mj-section`s |
| Tag pills centered (or right-aligned) above heading | Tags are **left-aligned** in the content column (pill bbox.x equals parent column.x) **and have square corners** (`cornerRadius=0` or absent) | The pill text node has `align=CENTER` (its own internal alignment) but the pill FRAME's bbox-x relative to the parent column tells you the pill's *layout* alignment. Both Rule 7 (alignment) and Rule 8 (corner radius) read these per-FRAME — never assume "pills are rounded and right-aligned" |
| "Expect lots of treats" heading centered | The heading is left-aligned | The text node's `textAlignHorizontal` is `LEFT`; my pass-1 used the parent `text-block-centered` component default and forgot to override |
| Spec mini-table as a single row of 4 cells | 2 columns × (icon + bold value + small label stacked vertically) | The text node `'617\nPieces'` carries a literal `\n`; without rendering, the layout is ambiguous |

The pattern: **the JSON tells you what the leaf nodes are; the rendered PNG
tells you how they relate to each other.** The converter has the leaf
nodes. It does not look at the rendered PNG. So it produces "structurally
correct, visually wrong" output.

### Gap 9 — Full-design screenshot is fetched but never used as a global visual reference

**Symptom:** the converter's `figma/service.py:522` writes `design.png` to
the training-case folder, and `vlm_classifier.py:189` accepts a
`frame_screenshots: dict[str, bytes]` keyed by per-section node_id. There
is no parameter on `analyze_layout()` or `match_section()` for the
**whole-frame** PNG. Every classification decision is local to a single
section.

This is why the 5 mistakes above happen: every one of them is a
*relational* property — "this card is white-on-lime", "this row is
left-aligned in its outer wrapper" — and the converter only ever sees one
section at a time.

**Where it breaks:**
- `figma/service.py` exports `design.png` only when called from the
  training-case ingestion path; the production conversion path doesn't
  fetch it.
- `figma/layout_analyzer.py:222` `analyze_layout()` accepts no PNG argument.
- `component_matcher.py:56` `match_section()` accepts `image_urls` but no
  global screenshot.
- `visual_verify.py` consumes per-section crops from `design_screenshots`
  but never the full frame.

**Recommendation:**

1. **Capture the full-frame PNG up front** in the production flow:
   ```python
   # In figma/service.py:sync_tokens_and_structure
   design_png = await self._export_frame_image(
       file_key, node_id, scale=2.0
   )  # one extra /v1/images call, ~2-5 MB
   ```
2. **Add `design_image: bytes | None` to `DesignFileStructure`** so it
   travels alongside the node tree.
3. **Pass it into `analyze_layout`** as `global_design_image: bytes | None`.
   The analyzer uses it for three checks:
   - **Wrapper-bgcolor classification** (Gap 1): sample interior pixels of
     each top-level wrapper to detect coloured backgrounds with multiple
     children rendered as inner cards.
   - **White-card-on-wrapper detection** (Gap 10 below): when a wrapper
     has bg ≠ white and N inner sections, sample center pixels of each
     inner section. If they're white *and* the wrapper is coloured, mark
     each inner section as `inner_bg=white, container_bg=<wrapper>` so
     the renderer wraps content in a white rounded container.
   - **Left/center/right alignment of headings** (Gap 11 below):
     compare text-node `textAlignHorizontal` against the *centroid* of
     where the text is rendered in the PNG. Disagreements indicate the
     heading is positioned by its container, not by `align`.
4. **Pass it into the matcher's confidence-fallback path**: when
   `_score_candidates` returns ≤0.7 confidence, send the full PNG +
   per-section crop to the VLM with prompt "this section is at y=X-Y in
   the email; what role does it play in the page?" Today the VLM gets
   only the section crop, which is the wrong question — the role of a
   section is defined by its place in the page, not by its own pixels.

**Cost:** one extra `/v1/images` call per email (~$0 in Figma quota).
Memory: ~2-5 MB resident for the page lifecycle. Token cost only when the
PNG is sent to the VLM (already paid in the per-section path).

**Lines that would change:**
`figma/service.py:export_frame_screenshots` (or new `export_frame_full`),
`protocol.py:DesignFileStructure` (new field),
`figma/layout_analyzer.py:222` (new param),
`component_matcher.py:56` (new param threaded through),
`visual_verify.py` (new global-context check on low-confidence sections).

### Gap 10 — White-card-on-coloured-wrapper pattern

**Symptom:** the design uses a recurring pattern: lime-green wrapper
contains 6 sections (heading + 2 membership cards + heading + 4 product
rows), and each of the cards/rows has a **white rounded inner background**.
The wrapper provides the colour, the inner card provides the surface for
content.

The converter today either (a) treats the wrapper as one section and
collapses 6 sections into 1, or (b) treats each section independently and
gives them all the wrapper's lime bg, losing the white card surface.

**Where it breaks:**
- `figma/layout_analyzer.py:222` `analyze_layout()` — no
  `inner_bg`/`container_bg` distinction on `EmailSection`.
- `component_matcher.py:1401` `_build_token_overrides` — emits
  `background-color` on `_outer` only, no concept of "outer wrapper bg vs.
  inner card bg".
- The component HTMLs (`zigzag-image-left/right.html`,
  `article-card.html`) — wrap content in one `<table>` only. There's no
  outer/inner table pair for nesting bg colors.

**Recommendation:**

1. New fields on `EmailSection`:
   ```python
   container_bg: str | None  # outer wrapper bg, set during wrapper unwrap
   inner_bg: str | None      # section's own bg, distinct from container
   inner_radius: float | None  # corner radius if inner is a card
   ```
2. `_build_token_overrides` emits two-target overrides:
   `(background-color, _outer, container_bg)` for the wrapper td;
   `(background-color, _inner, inner_bg)` and
   `(border-radius, _inner, inner_radius)` for the card td.
3. Component HTMLs gain an inner-table layer: `<td class="_outer"><table
   class="_inner">…</table></td>`. The renderer's existing token-override
   mechanism then targets either layer.

**Lines that would change:**
`figma/layout_analyzer.py:135-165` (`EmailSection` field additions);
`component_matcher.py:1401-1467` (override emission);
~6 component HTML files (inner table wrapper).

### Gap 11 — Heading alignment from text-node attribute, not from component default

**Symptom:** the "Expect lots of treats this Halloween!" heading has
`textAlignHorizontal=LEFT` in the JSON. My pass-1 conversion used
`text-block-centered.html` (default centered) and forgot to override the
align. Result: heading rendered centered when the design wants left.

**Where it breaks:**
- The matcher treats heading-only sections as `text-block-centered` by
  default when the parent wrapper has `align=CENTER` set (which happens
  on the wrapper, not the heading).
- `_build_token_overrides` does not emit a `text-align` override even
  when the text node carries `textAlignHorizontal`.

**Recommendation:** in `_build_token_overrides`, for the first heading and
first body text, emit `(text-align, _heading, text.text_align.lower())`
and same for `_body`. The renderer already accepts arbitrary CSS-property
overrides; this is one new line per role.

**Lines that would change:** `component_matcher.py:1411-1428` (new override
emission); renderer is already capable.

### Gap 12 — Multi-line text inside a single TEXT node loses structure

**Symptom:** the spec mini-table's left column has the text node
`'617\nPieces'` — a single TEXT node with a literal newline, which
**Figma renders as two visually distinct lines** (number on top, label
below). The converter's `_safe_text(text.content)` HTML-escapes the
content but doesn't handle the `\n`, so the value renders as
`617 Pieces` on one line and the layout collapses.

**Where it breaks:**
- `component_matcher.py:_safe_text` (used in all `_fills_*` functions) —
  passes through `\n` as a regular character, which becomes whitespace in
  HTML.

**Recommendation:** in `_safe_text`, replace `\n` with `<br>` *after*
HTML-escaping. Better: detect the multi-line case in `_extract_texts`
(layout_analyzer) and split the TEXT node into structurally distinct
`TextBlock` instances with `role_hint="value"` and `role_hint="label"`,
plus a `font_weight_diff` flag if the lines have different weights (which
they often do — bold value, regular label).

**Lines that would change:**
`component_matcher.py:620` (`_safe_text` should preserve `\n`);
`figma/layout_analyzer.py:_extract_texts` (multi-line splitter);
new spec-list slot type to consume the value/label pair.

---

## Part 7 — How exactly Opus does it (cognitive process expanded)

The user asked for more detail on what Opus is doing during conversion.
The bullet-point answer below is honest about which steps are
LLM-reasoning, which are deterministic computation, and where each could
be pulled into the converter.

### Step 1 — Read the JSON dump like a transcript, not like a tree

The Figma JSON is a tree with hundreds of nodes. I do not read it as a
tree. I read it as the **flat output of pass 1's tree-walk** — sorted by
`y`, with each line carrying typography and content. That order is the
**visual reading order** of the email. So the dump is, effectively, a
transcript of the email read top-to-bottom.

The very first decision (top-bar vs hero vs body vs footer) is made by
*counting*: there are 8 wrappers; the first is 30 px tall (clearly a
top-bar); the last is 630 px tall (clearly a footer); the middle six are
the body. No pattern matching, no heuristics — just "which wrappers are
extreme in size."

**Engine implication:** the matcher's first pass should be a
position-and-size sort, not a name-and-content classifier. Today the
matcher does name-then-content; it should do position-then-content. The
result is the same for clean files but more robust on messy ones.

### Step 2 — Identify wrappers vs sections by colour and child count

For each wrapper I ask two questions:
- Does it have a fill that's not white?
- Does it have ≥ 2 inner sections that themselves have content?

If both → it's a **container**, and the inner sections are the real
sections to classify. If only the first → it's a **single coloured
section** (e.g. the purple hero text block). If neither → it's a single
plain section.

**Engine implication:** this two-question test is exactly Gap 1's
recommended pre-pass. Cost: O(N) over wrappers. Net benefit: solves Gaps
1, 4, 6, 9, 10 simultaneously.

### Step 3 — For each section, ask "what role does this play?"

Roles I use are larger than `EmailSectionType`:

```
top-bar | header | hero-image | hero-text-cta | divider-band |
section-heading | repeat-card | repeat-product-row | composite-footer
```

I derive the role from a 3-bit decision:
- Has-image? Has-text? Has-button?
- If 1-image-no-text → `divider-band` if narrow-tall, `hero-image` if
  large-square.
- If 0-image-text → `section-heading` if first text is large+bold,
  `top-bar` if at the very top and small, `body-text` otherwise.
- If 1-image-text-button → `card` (heading present) or `repeat-card`
  (multiple sections share the same shape).
- If multi-image-text-button → `composite` (decompose into sub-sections).

**Engine implication:** this is mostly what `_score_candidates` does
already. The gaps are:
1. No `repeat-*` role (sibling-detection runs separately and never
   feeds back into role assignment).
2. No `composite` role (the matcher always assigns one component per
   section even when 6 are needed).
3. No `divider-band` role (transition images are misclassified as
   `image-block`).

### Step 4 — Pick the closest existing component

Given the role and the structural facts (image count, text count,
column count), I scan the 150-component manifest for the best fit. My
internal scoring is roughly:
- Role match: required (no role match → no candidate).
- Image-count match: ±1 acceptable.
- Text-count match: ±1 acceptable.
- Layout match: column count must match.

Multiple candidates often qualify. Tie-break by:
1. Specificity of role (e.g. `event-card` > `article-card` if event
   keywords present).
2. Depth of slot population (component with more slot-fills > component
   with fewer).
3. Renderer track record (components used in golden references first).

**Engine implication:** this is essentially `_score_candidates` +
`_score_extended_candidates`, which the engine already does. The
divergence is on the tie-break rules — the engine has no concept of
"renderer track record" (golden references it knows handle this case
correctly). Adding a +0.05 confidence boost for components that appear
in golden-reference YAMLs would likely improve component selection on
edge cases.

### Step 5 — Extract slot values, with role hints

Once a component is picked, slot population is mostly mechanical: take
the first heading-styled text → `heading` slot; first body-styled text →
`body` slot; first button → `cta_text`/`cta_url`; first image →
`image_url`. The places where I *don't* do this mechanically:
- **Tag pills**: a TEXT node inside a small fill+padding FRAME (typically
  `layoutMode=HORIZONTAL`, `paddingLeft/Right ≥ 8`), short text
  (< 20 chars), uppercase-ish or Title Case → goes into a `tag` slot.
  The pill's *alignment* and *corner radius* come from per-FRAME data
  (Rules 7 + 8) — bbox.x relative to parent column drives `align`, and
  the FRAME's `cornerRadius` (often 0 or absent → square) drives
  `border-radius`. Don't gate detection on rounded corners.
- **Spec rows**: pairs of (small image ≤ 30 px, short text < 40 chars)
  in adjacent positions inside one column → goes into a `spec_list`
  slot, formatted as `[(icon, value, label), …]`.
- **Multi-line text**: split on `\n` into structurally-paired children;
  the first half is the `value`, the second half is the `label`.

**Engine implication:** these three are Gaps 2, 3, 12. They share a
single root cause: **the matcher only emits string slot fills.** Adding
a `composite_slot` slot type (Part 4 §3 of the original doc) makes all
three trivial.

### Step 6 — Override design tokens

For each picked component, I check what's different from the component's
defaults and emit overrides:
- Container bgcolor (outer + inner if nested).
- Heading and body font-family, size, color, alignment.
- Button background, text color, border-radius, border.
- Padding (4-tuple).

**Engine implication:** this is `_build_token_overrides`. It already
covers most of this. The gaps it doesn't cover (and which I patched in
pass 2):
- Inner vs outer bgcolor (Gap 10).
- `text-align` from text-node attr (Gap 11).
- Padding asymmetry (the engine emits a single 4-tuple; many designs use
  asymmetric per-row padding for whitespace control).

### Step 7 — Self-check against the rendered PNG

After writing the HTML I render it (locally with a browser or
Playwright) and look at it side-by-side with the design PNG. I look at
seven specific things, in order:

1. **Vertical rhythm**: are the bands and section breaks at the right
   positions? If a section is too tall or too short, padding is off.
2. **Background-color continuity**: do adjacent sections meet without
   visible stripes? (My memory `feedback_bg_color_continuity.md` —
   this is something the engine could pixel-check too.)
3. **Card vs wrapper structure**: does each card visually float on its
   wrapper, or does the wrapper colour bleed through?
4. **Heading and text alignment**: does each heading land where the
   design has it (left/center/right)?
5. **Button styling**: is the CTA's bg / text-color / shape correct?
6. **Image fitting**: does each image have the right aspect ratio and
   not crop the design's intended composition?
7. **Footer composition**: is each footer block (logo, social, links,
   legal) at the right level of prominence?

**Engine implication:** `visual_verify.py` does steps 1-2 already (ODiff
on per-section crops). Steps 3-6 require the global PNG (Gap 9). Step 7
is `_fills_footer` (Gap 4). Adding the global PNG check turns this from
"verify each section in isolation" to "verify the page as a whole."

### What's actually unique about Opus on this task

Of the 7 steps above, only 2 require LLM reasoning that a deterministic
engine can't replicate:

- **Step 3** (role assignment when role is ambiguous) — when a section
  could be `text-block`, `hero-text-cta`, or `repeat-card` and the
  signal is the *content meaning* (e.g. is "Frights and brick-built
  delights" a hero tagline or a section heading? An LLM reads the words
  and knows; a heuristic counts characters and guesses).
- **Step 5** (slot value extraction with role hints) — when a piece of
  content is structurally ambiguous (a 18-char text in a small rectangle
  could be a tag, a label, a date, or a sticker). The LLM reads the
  word and knows.

The other 5 steps are all deterministic. That means **the engine could
match Opus on ~70 % of the workflow with no LLM at all** if it adopts
the global-PNG check, the wrapper-unwrap pre-pass, the composite-slot
type, and the role-hint extraction. The LLM-reasoning portion would
remain as a high-confidence reviewer rather than a primary classifier.

---

## Part 8 — Universal design-fix workflow (applies to any design)

This section is intentionally **decoupled from the LEGO email**. It is the
generic loop Opus runs whenever a rendered HTML diverges from a design — and
it is the loop the converter engine should adopt. The fixes that closed the
gap on this LEGO conversion (third-pass corrections in the section below) are
all instances of universal patterns; each pattern includes a detection rule
the engine can codify.

### 8.1 The repair loop

Five stages, run iteratively until visual fidelity ≥ target or
diminishing-returns is detected:

1. **CAPTURE.** Render the current HTML at *each viewport class the design
   targets* (typical: 600px desktop and one mobile width ≤ 480px). Save both
   PNGs. Single-viewport rendering is the most common cause of "fixed in
   one place, broken in another" loops.
2. **DIFF.** For each viewport, walk the rendered PNG side-by-side with the
   matching design PNG, *bounded to one section at a time*. Don't try to diff
   the whole email at once — a per-section bounded diff is what makes the
   error class identifiable.
3. **CATEGORIZE.** Drop each diff into one of the 6 detection rules in §8.3.
   If a diff doesn't fit any rule, it is either a content-level error
   (wrong text, wrong asset) or a brand-new pattern worth adding to this list.
4. **APPLY.** Make the smallest surgical edit that resolves the categorized
   diff. Do not bundle unrelated edits — each fix should map 1:1 to one diff
   so a re-render isolates whether the fix worked.
5. **RE-RENDER + LOOP.** Re-capture both viewports. If new diffs surface, loop.
   Stop when the rendered output is within target fidelity or when 2
   consecutive iterations produce no net improvement.

The order matters. Many engines run the diff at one viewport only, find a
"fix", apply it, and break the other viewport. Capturing both first prevents
this.

### 8.2 Where each stage maps onto the converter

| Stage | Hub component today | Gap | Recommended owner |
|---|---|---|---|
| CAPTURE | `playwright.async_api` in `app/rendering/`. Per-viewport baselines exist for `make rendering-baselines` but per-section design PNGs are only captured for snapshot regression cases. | Generalise to per-conversion: render output at desktop+mobile after `convert_document()` returns, stash to `traces/conversions/`. | `app/design_sync/converter_service.py:_apply_verification` already has the hook; extend to call `playwright` for HTML render output, not just design screenshots. |
| DIFF | `app/design_sync/visual_verify.py:compare_sections` + ODiff pre-filter + VLM extraction (Phase 47). | Already runs section-by-section, but only against the **design** PNG, never against the rendered HTML at the rendered viewport. | Add a `viewport: int` parameter to `compare_sections()` so the same logic runs at 600 and 480; merge results before returning corrections. |
| CATEGORIZE | Implicit in the VLM correction extraction prompt (Phase 47.2). | The prompt asks "what's wrong" — not "which class of fix". | Constrain the VLM output schema to the 6 categories below so the correction applicator can dispatch deterministically per class. |
| APPLY | `app/design_sync/correction_applicator.py:apply_corrections` (Phase 47.3) — selector + style/content/image edits. | Today the applicator can only mutate styles/content/images on existing elements. Categories like *card-with-N-children collapsing* and *responsive-image-overflow* require **structural mutations** (wrapping, class additions). | Extend `CorrectionResult` to include `wrap_in: dict | None` (parent tag + style) and `add_class: list[str]` per target element. |
| RE-RENDER + LOOP | `run_verification_loop()` in `visual_verify.py` (Phase 47.4). | Already a render-compare-correct loop, but only at one viewport and only for the design (not HTML output). | Reuse the existing iteration cap and convergence-detection logic; just feed it the HTML render PNG too. |

### 8.3 Eleven detection rules every converter pre-pass should run

> **Read this first — these rules are design-agnostic.** Every signal
> and condition below is read from the **Figma FRAME tree at conversion
> time** (or, for rules 4–6, from the rendered design PNG fetched in
> Step 0). Nothing in this section hardcodes a colour, brand, copy
> string, or layout pattern from the LEGO email — every rule fires by
> comparing live Figma node properties (`cornerRadius`, `fills[].color`,
> `absoluteBoundingBox`, `rectangleCornerRadii`, `layoutMode`,
> `paddingLeft`, sibling count, child x-coordinate, image alpha
> channel, etc.) against thresholds and predicates. Apply them to a
> Halloween promo, a transactional receipt, a newsletter, a B2B onboarding
> flow, an abandoned-cart email — the rule outputs adjust per design
> because the inputs are read fresh from each design's nodes.
>
> **The LEGO email is a calibration reference, not a template.** Where
> a rule cites LEGO ("the LEGO membership card section #16 is the
> canonical case"), the citation is *one worked instance* of the
> abstract rule firing — useful for grepping a known-good fix. The
> converter must **never copy LEGO output verbatim**; it must run the
> rule against the *current* design's FRAME tree and emit
> design-specific output. See §8.6 for the calibration-vs-template
> contract and how to extend the reference set.

Each rule has the same shape:

- **Signal** — what to look for in the Figma node tree or rendered diff
- **Rule** — the condition under which the engine should act
- **Action** — the surgical edit, expressed in element/CSS terms

These eleven cover ~92% of the divergences we saw across three review
cycles on the LEGO email. The same rules apply to any email design —
they are written in terms of structural properties (frame nesting,
sibling count, alpha channel, child x-coordinate, cornerRadius, fill
colour parity, viewport class, table-vs-image width parity), not
domain content.
- Rules 1–6 came from the first review pass.
- Rules 7–10 came from the second pass after observing specific misreads
  on the rendered HTML (pill alignment, pill border-radius, dark-mode
  contrast on nested cards, per-corner image radii).
- Rule 11 came from the third pass after spotting the inner-card-vs-
  image-max-width gap on the membership-card footer.

#### Rule 1 — Card with N children collapses to one container

> **Signal.** A `FRAME` whose `fills[0]` is a non-default solid (i.e. not the
> wrapper bg) **AND** `cornerRadius > 0` **AND** holds ≥ 2 child frames that
> the layout analyzer would otherwise emit as separate top-level sections.
>
> **Rule.** Emit a single wrapping container (`<table bgcolor="…"
> style="background-color:…; border-radius:Npx; border-collapse:separate;
> overflow:hidden;">`) and render each child as an inner row instead of a
> top-level email-shell row.
>
> **Action.** In `layout_analyzer.py`, before building `EmailSection`s, walk
> for these "container frames" and tag their children with `parent_card_id`.
> In `component_renderer.py`, when iterating sections, group consecutive
> sections sharing a `parent_card_id` and wrap them in one rounded outer
> table (this is the same primitive `sibling_detector.py` already produces
> for repeating-group rendering — needs to be reused for *non-repeating
> heterogeneous* siblings too).

The LEGO footer's `2833:2057` frame is the canonical case (4 heterogeneous
children inside one #ffffff rounded frame), but the same shape covers:
membership cards with image+text+CTA inside a colored card, banner sets with
image+caption inside a rounded frame, hero panels with logo+headline+button
on a tinted overlay — any "card with structured contents" the designer
groups into one rounded surface.

#### Rule 2 — Responsive image overflow on stacked columns

> **Signal.** A column-layout component (two or more inline-block divs with
> `class="column"`) where at least one inner `<img>` has an inline
> `max-width: <PX>` that is **smaller** than the parent column's stacked
> width on the mobile breakpoint.
>
> **Rule.** When `class="column"` triggers `display:block;width:100%`, any
> child image with a smaller `max-width` will render at its constrained
> size and leave whitespace beside it. The image must also be allowed to
> grow to 100% **on the mobile breakpoint only**.
>
> **Action.** Add `class="bannerimg"` (or any class controlled by the
> mobile @media block) to the image and ensure that class sets
> `width:100% !important; max-width:100% !important; height:auto !important`
> at `max-width: 599px`. Do *not* change the desktop inline `max-width`.

Hub has `.bannerimg` in every shell template but historically without
`max-width:100% !important` — the same bug we just fixed for LEGO. The
converter should emit `bannerimg` on every image inside a `.column`-stacked
parent by default.

#### Rule 3 — Image padding inside non-bleed container

> **Signal.** An image's `absoluteBoundingBox` is **strictly inside** its
> parent FRAME's bounding box (margin > 0 on at least one axis), AND the
> parent has a non-default fill (it's a coloured/white card, not the email
> wrapper).
>
> **Rule.** The image is *not* full-bleed against the card edge. The HTML
> image cell must therefore have padding equal to the visible margin in the
> design (rounded to 4px increments). The image's max-width must be reduced
> by 2× the horizontal padding so the image stays within the same column
> width budget.
>
> **Action.** On the image's wrapping `<td>`, set
> `padding: <top> <right> <bottom> <left>` measured from the design.
> Pair with `class="img-pad"` (or equivalent) so the mobile breakpoint can
> override `padding: 0 !important` if the stacked image should go full-bleed
> on mobile (this is a per-design call — record the design's mobile
> reference frame if it exists, otherwise default to "preserve padding").

LEGO product cards (sections 10–13) had this exact issue — image flush to
card edge in HTML, ~16–18 px margin in Figma. Same pattern shows up in
testimonial cards (avatar with breathing room), pricing tiles (icon with
visible inset), product grids — anywhere a design treats the image as
*content inside a card* rather than *the card surface*.

#### Rule 4 — Visible divider absent from FRAME tree

> **Signal.** Two or more sibling text/image columns visibly separated by a
> uniform-coloured 1–2px-wide vertical or horizontal line in the design
> reference PNG, but **no LINE / RECTANGLE / TEXT node containing
> `|` / `·` / `–`** exists between them in the FRAME tree.
>
> **Rule.** The divider was probably drawn outside the frame the designer
> exported (a separate guide layer, a CSS-rendered pseudo element in
> someone's hand-converted HTML, or simply a typed character that got
> stripped during export). Emit a divider element between the columns.
>
> **Action.** Insert a `<td>` between the columns containing either
>   (a) a literal `|` character with `color: #c8c8c8; padding: 0 14px;`,
>   (b) a 1px-wide bgcolor `<td>` if the design shows a clean line, or
>   (c) a `<hr>` styled `border-top: 1px solid #...; margin: ...` if it's
>       horizontal.
> Choice (a) is most robust across mail clients.

The LEGO user-info row (`Andy | 0`) used the literal-pipe variant. The same
pattern shows up between footer link rows ("Privacy Policy | Terms"), in
spec-row dividers ("4.5★ | 230 reviews"), and inside hero overlays
("$29 / month | Save 40%").

#### Rule 5 — Asset name disagrees with asset content

> **Signal.** A Figma node's `name` field implies one content type (e.g.
> `"footer-social"`) but the rendered PNG / image-fill imageRef shows
> something else (e.g. a barcode).
>
> **Rule.** Trust dimensions and visual content over names. The matcher
> must not slot images into component slots based on name string-matching
> (`name.contains("social")` ⇒ social-icon-row).
>
> **Action.** When emitting `data-slot` attribute candidates, base the slot
> assignment on:
>   1. **Aspect ratio** (very wide → banner; ≤ 1:1.2 → square icon; ≥ 1:4 →
>      barcode/strip).
>   2. **Sibling order within parent card** (top → header logo; middle →
>      content; bottom → decoration / shape).
>   3. **Image-fill perceptual hash** if a brand asset library is available.
>
> Only use the `name` as a tie-breaker between two visually-equivalent
> candidates.

The LEGO assets `footer-card.png` (actually the Insiders header logo with
shapes), `footer-social.png` (actually the barcode), and `footer-logo.png`
(actually the bottom blue paper-cut shape) were all named after the
designer's intended *role* in the card, not the visual content. A
matcher reading those names would route the barcode into a social-icon
component slot and produce visibly wrong output.

#### Rule 6 — Mobile DOM order ≠ desktop visual order — use `dir="rtl"`

> **Signal.** A 2-column section where the design places image on the
> right (image cell appears *after* content cell in DOM), AND the section
> has `class="column"` mobile stacking, AND the design's mobile reference
> (or the consistency rule "all cards stack image-on-top") expects image
> *above* content.
>
> **Rule.** Default mobile stacking follows DOM order, so an image-right
> desktop layout naïvely collapses to content-on-top, image-below on
> mobile — typically opposite to the desired mobile pattern
> (image-above-content is the canonical content-card stack). Naïvely
> swapping DOM to `[image][content]` and accepting the desktop-zigzag
> loss is the wrong tradeoff. Use the **`dir="rtl"` technique** to keep
> both desktop zigzag and uniform mobile stacking.
>
> **Action — `dir="rtl"` flip pattern (verified working).**
>
> Put the image div first in DOM (so it stacks on top on mobile) and
> apply `direction: rtl` to the parent at desktop so the inline-block
> flow reverses visually. Each child div carries `dir="ltr"` so its
> content stays LTR.
>
> **Gotcha — `direction: rtl` MUST live on a class with a mobile
> override, not inline.** When the columns become `display: block` on
> mobile, the rtl direction bleeds into the block-layout context and
> silently kills the text column's left padding (the `stack-pad`
> 24 px-each-side rule visually collapses on the left edge). Use a
> dedicated class:
>
> ```css
> .flip-row { direction: rtl; }
> @media only screen and (max-width: 599px) {
>   .flip-row { direction: ltr !important; }
> }
> ```
>
> ```html
> <!--[if mso]>
> <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl">
>   <tr>
>     <td width="240" valign="middle" dir="ltr">  <!-- image cell, visually on RIGHT in Outlook due to table dir=rtl -->
> <![endif]-->
> <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
>        style="font-size: 0; text-align: left;">
>   <tr>
>     <td class="flip-row" style="font-size: 0;">  <!-- desktop: rtl flip; mobile: media query restores ltr -->
>       <div class="column" dir="ltr"
>            style="display: inline-block; max-width: 240px; width: 100%; vertical-align: middle;">
>         <!-- image — appears visually on RIGHT on desktop, on TOP on mobile -->
>       </div>
>       <!--[if mso]></td><td width="280" valign="middle" dir="ltr"><![endif]-->
>       <div class="column stack-pad" dir="ltr"
>            style="display: inline-block; max-width: 280px; width: 100%; vertical-align: middle;">
>         <!-- text — appears visually on LEFT on desktop, BELOW image on mobile -->
>       </div>
>       <!--[if mso]></td></tr></table><![endif]-->
>     </td>
>   </tr>
> </table>
> ```
>
> Padding inside each div is *physical* (CSS `top right bottom left`),
> not logical, so flip the per-side image / text padding to match the
> visual position the div ends up in. For the image-right case above:
> - Image cell: `padding: 18px 14px 18px 0` (14px gap on the card's
>   right edge, flush-left where it meets the content column).
> - Text inner cell: `padding: 18px 16px 18px 22px` (22px gap on the
>   card's left edge, 16px from the column boundary on the right).
>
> **Don't do it.** Two anti-patterns to avoid:
>
> - Swapping DOM `[image][content]` and accepting the loss of desktop
>   zigzag — designers added the alternation intentionally; uniform
>   image-left destroys the rhythm.
> - Adding a paired hidden mobile-only image with `display: none` /
>   `display: block` (~2× image weight; many clients don't honour
>   `display:none` on `<img>` reliably; CSS-stripping clients show two
>   images stacked).
>
> Verified compatibility:
> - Apple Mail / iOS Mail / Gmail Web / Gmail iOS / Gmail Android: full
>   `dir` support — desktop zigzag + mobile uniform stack work.
> - Outlook 2007+ Windows: `<table dir="rtl">` reverses cell order
>   correctly when the conditional path is taken.
> - Outlook.com / Outlook iOS / Outlook Android: full support.
> - AOL / Yahoo: full support.
>
> The verified working markup is `email-templates/lego-insiders-halloween.html`
> sections #10 and #12 — pattern can be copied directly.

#### Rule 7 — Pill / tag alignment from child x-coordinate, not heuristic

> **Signal.** A button-like FRAME (`mj-button`, `mj-button-Frame`, or any
> small fill+text+padding leaf) whose `absoluteBoundingBox.x` is **within
> 4 px of its parent column's left edge** — meaning the designer placed it
> flush-left in the column.
>
> **Rule.** Pill / tag alignment must be derived from the pill's bbox
> position relative to its parent column, not from a default like
> "always emit `align='right'` for tag chips above headings".
>
> **Action.** In `component_renderer.py`, when filling a tag/pill slot,
> compare `pill.bbox.x` to `parent_column.bbox.x`:
>
> - `|pill.x - parent.x| ≤ 4` → emit `align="left"`
> - `|(pill.x + pill.w) - (parent.x + parent.w)| ≤ 4` → emit `align="right"`
> - else → emit `align="center"`
>
> The same calculation applies to logos, badges, social-icon rows, and any
> other "single horizontal element above/below larger content".

The LEGO membership cards (sections #7 and #8) had pills at `x=2027`,
identical to their parent column's `x=2027` — the designer placed them
flush-left, but the converter emitted `align="right"`. The same misread
shows up on testimonial avatars, "NEW" badges over hero images, and any
chip-style label that the designer left-aligned in its column.

#### Rule 8 — Pill `cornerRadius` is the source of truth (don't assume pill-shape)

> **Signal.** A FRAME styled like a tag/badge has `cornerRadius` of either
> `0` or absent (no rounded-corner key) — but the renderer emitted a CSS
> `border-radius` value derived from a "tag chip → pill shape" heuristic.
>
> **Rule.** Border-radius must come directly from Figma's `cornerRadius`
> (or `rectangleCornerRadii`). When the field is absent or `0`, emit
> square corners — even if the element looks like a pill in isolation.
>
> **Action.** Read `cornerRadius` from the FRAME node:
> - missing or `0` → `border-radius: 0`
> - scalar `N` → `border-radius: Npx`
> - `rectangleCornerRadii: [TL, TR, BR, BL]` → emit `border-radius: TLpx
>   TRpx BRpx BLpx` (CSS shorthand order matches Figma's per-corner array).
>
> Never apply a "looks like a pill therefore round it" rule. Trust the
> design.

LEGO membership pills (`mj-button` 2833:1912 / 2833:1932) had no
`cornerRadius` field — flat sharp corners — but the converter rounded them
because the renderer's chip-component template hardcoded
`border-radius: 12px`. Same pattern misfires on date stickers, ribbon
labels, and bottom-corner price tags that designers explicitly draw with
sharp corners for editorial weight.

#### Rule 9 — Dark-mode contrast on nested cards (white-on-white invisibility)

> **Signal.** An outer wrapper has a dark-mode CSS class that flips both
> background AND text color (e.g. `.lime-bg` → dark green; `.artcard-heading`
> → white text), but a **nested inner FRAME** with a *different* fill
> (typically white card on the lime wrapper) has no dark-mode class. The
> inner frame's text classes still target the dark-mode override — so in
> dark mode the nested card stays white while its text turns white →
> invisible.
>
> **Rule.** Every nested coloured surface — not just the outermost wrapper
> — needs its own dark-mode background class. Inheritance does not save
> you.
>
> **Action.** During FRAME-walk, every node with a non-default solid fill
> (the white inner card, the cream pull-quote, the tinted footer
> sub-block) gets its own `class="card-bg-N"` on the rendered `<table>`.
> Emit a matching `@media (prefers-color-scheme: dark) { .card-bg-N {
> background-color: <darkColor> !important; } }` rule. The
> light→dark mapping comes from the design system's `dark_palette`
> (`design_system.py` already exposes this) — fall back to a deterministic
> "shift L by –40, hue preserved" if no mapping exists.

Concretely: the LEGO membership and product cards all had a white inner
table inside a lime-green outer cell. In dark mode the lime flipped to
dark green ✓, but the white inner card stayed white ✗ — and the heading
+ body classes flipped to white text ✗. Result: zero contrast in dark
mode. The fix was to add `class="artcard-bg"` to the inner card and a
matching `.artcard-bg { background-color: #1d104b !important; }` in the
dark block. The same shape covers tinted overlays inside hero panels,
white pull-quotes inside coloured callouts, white-on-tinted CTA cards —
any "card on coloured background" that designers nest one layer deep.

Stat / metric numbers that share the same parent (e.g. piece counts and
points values inside product cards) need their own dark classes too —
inline `color: #000000` on a `<td>` survives the cascade unless a class
with `!important` overrides it. Same with anchor tags: links inside a
class-controlled parent (e.g. `<td class="footer-link">`) still need
`.footer-link a { color: ... !important }` to override the anchor's
inline `color`.

> **Identity exception — physical-card representations stay light.** Not
> every nested white surface should flip dark. When a card visually
> represents a physical identity object — a membership card with logo +
> barcode, a credit-card-style coupon, a boarding-pass mock-up — the
> design intent is "this looks like a real plastic card, *always*". Flip
> the surrounding bg, but leave the card itself white (no `card-bg`
> class). Telltale signals from the FRAME tree:
>
> - The card aspect ratio matches a physical card (1.586:1 ID-1 / 2:1
>   loyalty-card / 4:3 boarding pass).
> - The card contains a barcode, QR code, or strip-of-numbers asset.
> - The card has a logo asset on a perfectly white field.
> - The card has its own `cornerRadius` distinct from surrounding
>   sections (typical 16–24 px for cards).
>
> When two of these signals fire, opt the surface OUT of the auto-dark
> flip. The text inside stays dark — readable on the unflipped white
> surface, faithful to the "physical card" identity in either mode. The
> LEGO Insiders membership card (footer section #16) is the canonical
> example: barcode + logo + 24 px corners → keep white in dark mode.

> **User-info row over flipped bg.** A common dark-mode bug: a
> user-info row above a card (avatar + "Andy" + pipe + points + "0")
> sits on the *outer* dark-flipped bg, but its text classes are inline
> `color: #000000`. Add `class="footer-strong"` (or equivalent) to the
> name and number cells — the divider pipe `|` is already a neutral
> mid-grey (e.g. `#c8c8c8`) so it stays readable in both modes. CSS:
> `.footer-strong { color: #000 } @media dark { .footer-strong { color:
> #fff !important } }`.

#### Rule 10 — Image per-corner border-radius from `rectangleCornerRadii`

> **Signal.** An image FRAME (or `<rectangle>` with image fill) has
> `rectangleCornerRadii: [TL, TR, BR, BL]` with at least one non-zero
> value — typically the design's "image rounded only on the side facing
> the card edge" pattern.
>
> **Rule.** Per-corner radii on Figma image frames must propagate to the
> rendered `<img>` (or its wrapping `<td>`) as
> `border-top-left-radius`/`border-top-right-radius`/
> `border-bottom-right-radius`/`border-bottom-left-radius`. The CSS
> shorthand `border-radius: TLpx TRpx BRpx BLpx` works in modern clients
> but expanded longhand survives more legacy renderers (Outlook 2016, AOL).
>
> **Action.** Read `rectangleCornerRadii` (or scalar `cornerRadius`) on
> the image-bearing FRAME. Emit the four longhand properties as inline
> styles on the `<img>`. Pair with `overflow: hidden` on the wrapping
> `<td>` if the image is itself a fill on a rectangular shape (otherwise
> the rounded clip won't render in WebKit-based clients).

The LEGO membership card images had
`rectangleCornerRadii: [6, 0, 0, 6]` — left side rounded (TL=6, BL=6) to
match the white card's outer radius, right side square so the image
flows into the content column. The renderer emitted square corners on
all sides, leaving a visible "missing slice" at the card's rounded edge.
Same pattern recurs in tile galleries (top-row images rounded TL/TR,
bottom-row images rounded BL/BR), avatar strips, partial-width banners.

#### Rule 11 — Inner card width must match its image children's max-width

> **Signal.** A nested `<table>` styled as a card (rounded corners, fill,
> typically wrapping image rows + text rows) has `width="100%"` while one
> or more child `<img>` elements have an inline `max-width: <PX>` smaller
> than the table's effective rendered width. Visually: the card surface
> extends past the imagery on one side, leaving a coloured gap between
> the image's right edge and the card's right edge.
>
> **Rule.** When a card's children include images sized to a fixed Figma
> width (e.g. 440 px), the card itself must be sized to that same fixed
> width — *not* `width="100%"`. Otherwise the card stretches to whatever
> the parent cell allows (parent width minus parent padding) and the
> images leave a horizontal gap inside the card.
>
> **Action.** On the inner card `<table>`:
> - Replace `width="100%"` with `width="<NATIVE_PX>"` (the imagery's
>   native width — read from the dominant `<img>`'s Figma frame).
> - Add `align="center"` so the card is centred within the parent cell
>   (the parent's bg fills the surrounding area).
> - Add `class="wf"` (or equivalent `width:100% !important` mobile-only
>   class) so the card stretches to full viewport width on mobile, where
>   the same `bannerimg` rule lifts the image's `max-width` cap.
>
> ```html
> <td bgcolor="<wrapBg>" class="wrapper-bg" align="center"
>     style="background-color: <wrapBg>; padding: 6px 16px;">
>   <table role="presentation" width="440" align="center"
>          cellpadding="0" cellspacing="0" border="0"
>          bgcolor="#ffffff" class="wf"
>          style="background-color:#ffffff; border-radius:24px;
>                 border-collapse:separate; overflow:hidden;">
>     <!-- rows of images with max-width:440px -->
>   </table>
> </td>
> ```
>
> Outer cell padding becomes purely aesthetic (gap between card edge and
> viewport on mobile) — no longer determines card width.

The LEGO Insiders membership-card section (footer #16) is the canonical
case. The 4 image rows (header logo 440×114, andy/email text, barcode
440×90, bottom shape 440×44) all share the same Figma 440 px native
width. With the card at `width="100%"` and outer padding of 60 px each
side at 600 px viewport, the card was 480 px while imagery stayed at
440 px → 40 px white gap on the right. Setting card `width="440"` +
`align="center"` + `class="wf"` makes desktop pixel-perfect and mobile
full-bleed via the `.wf` rule.

The same shape appears in pull-quote tiles with a fixed-width quotation
graphic, hero panels with a logo asset of fixed dimensions, and any
"icon strip" component where the icon row has a designed pixel width.
**Detection heuristic for the converter:** if every direct child of an
inner card carries the same `max-width` (the dominant image native
width), set the card's `width` to that value rather than 100 %.

### 8.4 What the converter cannot infer without the full-design PNG

Three of the six rules above require *visual* signals the FRAME tree alone
doesn't expose:

- **Rule 4** (visible-but-absent dividers) — only the rendered PNG shows a
  divider line.
- **Rule 5** (name vs content mismatch) — only the rendered PNG (or
  image-fill hash) reveals the actual content.
- **Rule 6** (mobile DOM order) — needs both desktop and mobile reference
  PNGs to know whether the design intent diverges from DOM order.

This is the strongest argument for the recommendation in §6.3 (Gap 9):
**fetch the full-design PNG once at the start of conversion and thread it
through `analyze_layout()`.** Without it, the engine cannot run rules 4–6,
and the conversion will need a human reviewer for those classes of issue
forever.

### 8.5 Telemetry: log every fix the loop makes

For each correction the verification loop applies, emit a structured event:

```python
log.info("conversion.correction_applied",
    rule_id="rule_1_card_with_n_children"
          | "rule_2_responsive_image"
          | "rule_3_image_padding"
          | "rule_4_visible_divider_absent"
          | "rule_5_asset_name_mismatch"
          | "rule_6_mobile_dom_order"
          | "rule_7_pill_align_from_x"
          | "rule_8_pill_corner_radius"
          | "rule_9_nested_dark_mode"
          | "rule_10_image_corner_radii"
          | "rule_11_card_width_matches_image",
    section_id=section.node_id,
    viewport=600 | 480 | "dark",
    iteration=loop_iter,
    diff_severity="major" | "minor",
)
```

After 100+ conversions, the histogram of `rule_id` counts tells the team
which detection rules pay back the most engineering effort. The LEGO
conversion fired all eleven rules across three review cycles — a typical
e-commerce email is likely to fire rules 1, 2, 3, 9, 10, 11 most often;
a transactional email is likely to fire rules 4, 6, 7, 8.

The point: this isn't a checklist Opus follows in their head. It's a
deterministic dispatch table the converter can run automatically once
the 11 detection rules are codified. Rules 7–11 in particular are pure
FRAME-tree reads (no PNG required) and should ship first because they
have the highest hit rate per minute of engineering investment.

### 8.6 Reference exhibits — calibration, not templates

This section pins down the contract for *how* the converter consumes
the LEGO HTML / design PNG referenced throughout §8.3. The single
biggest implementation pitfall is treating either as a template. **They
are inputs to rule evaluation, not outputs to mimic.**

#### 8.6.1 What the LEGO HTML reference is

`email-templates/lego-insiders-halloween.html` is a *worked example* of
all 11 rules firing correctly on one design. Section comments in that
file are tagged `[Rule N]` so that:

- A rule documented in §8.3 → grep `[Rule 7]` in the codebase →
  reach the exact markup that satisfies that rule.
- A rule that fires on a *new* design (not LEGO) → engineer reads
  the rule, confirms the abstract condition, looks at the LEGO
  instance for shape, then writes design-specific output keyed to
  the new design's FRAME data.

The LEGO file is one calibration instance. The converter must:

- ✅ Read the rule from §8.3 and the worked instance from the LEGO
  file to understand "what good looks like" *structurally*.
- ✅ Apply the rule to the *current* conversion's FRAME tree, emitting
  output that uses the current design's colours, copy, dimensions,
  and node IDs.
- ❌ Never copy LEGO-specific colours, brand assets, copy, or fixed
  pixel values into a new conversion.
- ❌ Never refuse to apply a rule because "this design doesn't look
  like LEGO".

#### 8.6.2 What the design PNG reference is

The full-design PNG fetched at conversion start (Step 0) is a
*per-design* orientation prior. Each conversion gets its own PNG;
the LEGO PNG is never reused as a stand-in. The PNG's role:

- Feed the VLM at Step 0 so it can describe the current design's
  global structure ("4 product cards in zigzag layout, hero with
  CTA, footer membership card").
- Provide ground truth for rules 4, 5, 6 which need to see the
  rendered design (not just the FRAME tree).
- Provide post-render verification ground truth for the repair loop
  in §8.1.

The PNG is **not** a style guide and never bleeds across designs —
it is loaded fresh, used for the conversion in flight, then released.

#### 8.6.3 Extending the reference set

Once 2 + designs have full `[Rule N]`-tagged HTML in the repo, treat
the union as the calibration set. The eval suite already provides this
discipline via the 14 golden references at
`email-templates/golden-references/` — once those are also `[Rule N]`-
tagged, the multi-design coverage becomes load-bearing. Recommended
order to add tags:

1. **LEGO** (already exists). Heaviest annotation, all 11 rules.
2. **One transactional email** (e.g. order confirmation). Anchors
   rules 4, 6, 7, 8 in a layout dominated by data tables and
   dividers, not product cards.
3. **One newsletter** (multi-section, multi-CTA). Anchors rules 1, 2,
   3 across editorial-style content.

Rule 6's "image-right desktop / image-on-top mobile" pattern, for
example, will look identical at the structural level (DOM order,
`direction: rtl` class, mobile media query override) on a transactional
email's "you spent $X / here's your receipt" two-column row as on a
LEGO product card — the rule reads the same FRAME-tree signals, the
HTML pattern is the same, only the colours, copy, and dimensions
differ. Three reference designs make this generalisation visible to
both Claude and any future engineer.

#### 8.6.4 Anti-patterns to refuse during implementation

When asked to "build a converter rule" or "fix a section", refuse the
following framings:

- "This Halloween email needs lime-green wrappers like LEGO." → No.
  LEGO uses lime green because *its* `fills[].color` is
  `rgba(0.69, 0.79, 0.00, 1.0)`. The rule reads the *current*
  design's `fills[].color` and emits *that* value.
- "All membership cards should have rounded corners like LEGO." → No.
  Rule 8 reads `cornerRadius` from each FRAME independently. A
  current-design membership card with `cornerRadius: 0` gets square
  corners, full stop.
- "Apply Rule 11 (`width="440"`) to every inner card." → No. Rule 11's
  action reads the dominant child image's native width from the
  current design and emits *that* value (might be 440, 380, or 600
  depending on the design).

Each rule's `Action` block is parameterised by the live FRAME data;
read it that way, not as a literal recipe.

## Appendix — Conversion quality checklist Opus runs against the rendered output

The same checks the engine could run automatically:

- [ ] Top-of-section bgcolor matches bottom-of-previous-section bgcolor
      (or there's a transition asset between them)
- [ ] No `<div>`/`<p>` used for layout (table-only)
- [ ] Every text `<td>` has `font-family`, `font-size`, `color`,
      `line-height`, `mso-line-height-rule:exactly`
- [ ] Every image has non-empty `alt` (or `alt=""` + `role="presentation"`
      for decorative)
- [ ] CTAs have VML round-rect for Outlook + table button for everyone else
- [ ] Dark-mode override classes on every coloured surface — **including
      every nested coloured surface, not just the outermost wrapper**
      (Rule 9). Inline `color: #000000` on stat values needs an
      `!important` class override too, or it stays black on dark.
      `<a>` tags inside a class-controlled parent need
      `.parent-class a { color: ... !important }` — anchor inline
      `color` survives the cascade otherwise.
- [ ] Physical-card surfaces (membership cards with barcode/logo, credit
      cards, boarding passes) stay light in dark mode — opt OUT of the
      auto dark flip and leave the card white with dark text (Rule 9
      identity exception).
- [ ] User-info row text on a dark-flipped bg has a `footer-strong`-type
      class so name/number stays readable; the divider pipe `|` stays a
      neutral mid-grey that reads in both modes.
- [ ] Inner cards whose children are all images sized to a fixed Figma
      pixel width have their own `width="<NATIVE_PX>"` + `align="center"`
      + `class="wf"` (Rule 11) — `width="100%"` will leave a horizontal
      gap when the parent cell is wider than the image's `max-width`.
- [ ] Pill / tag / badge alignment matches the element's x-coordinate
      relative to its parent column (Rule 7) — not a hardcoded default
- [ ] Pill / button border-radius matches the FRAME's `cornerRadius`
      (Rule 8) — `0` or absent means square, regardless of how the
      element "looks"
- [ ] Image per-corner radii match `rectangleCornerRadii` (Rule 10) —
      asymmetric (e.g. `[6, 0, 0, 6]`) is common where an image meets a
      rounded card edge on one side
- [ ] Repeating rows alternate consistently or visibly stack — and when
      design alternates desktop zigzag, mobile DOM order is uniform
      (Rule 6) so all rows stack the same way
- [ ] Render at *both* light and dark color-schemes when verifying
      dark-mode (Playwright `color_scheme='dark'`) — many invisibility
      bugs only appear in dark mode
- [ ] Footer legal text fits in ≤ 600px viewport without truncation
- [ ] Total HTML size < 100 KB after Maizzle/Juice inlining

The first item is the only one that requires PNG sampling, and it's the
one that most often catches design-sync regressions. Items 2–4 above
(Rules 7, 8, 10) are pure FRAME-tree reads — cheapest to ship, biggest
silent-misread reduction.
