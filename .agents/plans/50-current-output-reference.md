# Phase 50 — Current Converter Output Reference

## Purpose

Concrete "before vs after" markup excerpts from a single representative section of the LEGO Halloween email — used by Phase 50.4, 50.5, 50.6 plans as diff anchors for acceptance criteria.

**Sources — full LEGO artifact triplet** (`email-templates/training_HTML/for_converter_engine/Lego/`):

| Artifact | What it is | Used as |
|---|---|---|
| `viaual_design.png` | Source Figma design screenshot (Figma `2833:1869`) | Visual ground truth — what the converter sees |
| `hub_converter_phase49_baseline.html` (350 lines) | **Frozen Phase 49 baseline** — never regenerated | "Before" anchor; gaps visible (no inner-card pair, centred text, no per-corner radii, etc.). Diverging from this file is the *goal*, not a regression |
| `manual_component_build.html` (1309 lines) | **Target output** — Opus's manual conversion using hub components, `[Rule N]`-tagged | "After" — what Phase 50–53 must converge to |

This is the canonical before/after pair for Phase 50 acceptance. The excerpts below pull from `manual_component_build.html` (Expected / target) and `hub_converter_phase49_baseline.html` (Before / known-broken). For sections where the LEGO baseline doesn't surface a representative gap, fallback excerpts are pulled from `data/debug/{6,10,reframe}/expected.html` and noted inline.

**Note on file name:** `viaual_design.png` is a typo for `visual_design.png` — preserved as-is until a follow-up rename PR.

## Section 1 — Membership Card 1 ("Art prints"): nested-card bg + pill + per-corner image radii

**Figma source:** node `2833:1869 > Card 1 — Art prints` (FRAME `2833:1893`)

**Design intent:** white rounded inner card on lime-green wrapper, with image left + content right, pill above heading (left-aligned, square corners), image rounded only on left edge.

### Expected (LEGO worked example)

`email-templates/training_HTML/for_converter_engine/Lego/manual_component_build.html:326-411` (excerpt — outer wrapper + inner card + image col + pill row):

```html
<!-- Outer wrapper carries lime bg; inner table is the white card -->
<tr>
  <td class="lime-bg" bgcolor="#afca01"
      style="background-color: #afca01; padding: 8px 20px 8px 20px;">
    <!-- INNER white rounded card (Rule 1 + Gap 10) -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           bgcolor="#ffffff" class="artcard-bg"
           style="background-color: #ffffff; border-radius: 16px;
                  border-collapse: separate; overflow: hidden;">
      <tr>
        <td style="padding: 0;">
          <!-- 2-col layout: image left, content right -->
          <table ...><tr><td>
            <!-- IMAGE col with per-corner radii (Rule 10) -->
            <div class="column" style="display: inline-block; max-width: 250px; ...">
              <img src="..." width="222" class="bannerimg"
                   style="display: block; width: 100%; max-width: 222px; height: auto;
                          border-top-left-radius: 6px;
                          border-bottom-left-radius: 6px;" />
            </div>
            <!-- CONTENT col: pill (Rule 7+8) + heading + body + CTA -->
            <div class="column stack-pad" ...>
              <table>
                <!-- TAG PILL row — left-aligned, square corners (Gap 2) -->
                <tr>
                  <td align="left" style="padding: 0 0 10px 0;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="left"
                           bgcolor="#836eb2"
                           style="background-color: #836eb2;
                                  border-radius: 0;">
                      <tr>
                        <td style="padding: 4px 12px;
                                   font-family: 'Noto Sans', Arial, sans-serif; font-size: 10px;
                                   line-height: 14px; font-weight: 700; color: #ffffff;
                                   text-align: center; mso-line-height-rule: exactly;">
                          Art prints
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <!-- HEADING row — left-aligned (Gap 11) -->
                <tr>
                  <td class="artcard-heading"
                      style="font-family: ...; font-size: 22px; font-weight: 600;
                             color: #000000; padding: 0 0 10px 0;
                             text-align: left;">
                    Bundle of 6 Halloween posters
                  </td>
                </tr>
```

**Key markers** (50.4/50.5/50.6 acceptance criteria check for these):
- Outer `<td class="lime-bg" bgcolor="#afca01">` carries wrapper bg → 50.3 + 50.4
- Inner `<table bgcolor="#ffffff" class="artcard-bg" style="...border-radius: 16px; border-collapse: separate; overflow: hidden;">` → 50.4 (`inner_bg`, `inner_radius`)
- `<img style="border-top-left-radius: 6px; border-bottom-left-radius: 6px;">` → 50.5 Rule 10 (per-corner from `rectangleCornerRadii: [6, 0, 0, 6]`)
- Pill `<table align="left" bgcolor="#836eb2" style="border-radius: 0;">` → 50.5 Rule 7 (`align="left"` from bbox.x match) + Rule 8 (`border-radius: 0` from absent `cornerRadius`)
- Heading `<td style="text-align: left;">` → 50.6 (from `text.text_align="LEFT"`)

### Current (representative converter output — debug case 6 or analogous)

What the converter produces today for a card-shaped section on a coloured wrapper, based on real snapshots in `data/debug/`:

```html
<!-- Single flat table — no outer/inner distinction (Gap 1, Gap 10) -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       data-component-name="mj-wrapper"
       style="border-collapse: collapse; max-width: 600px; margin: 0 auto;">
  <tr>
    <td style="padding: 32px 16px; text-align: left;">
      <!-- Image renders without per-corner radii (Rule 10 unimplemented) -->
      <img data-slot="image_url" src="..." class="bannerimg"
           style="display: block; width: 100%; max-width: 250px; height: auto; border: 0;" />
      <!-- "Art prints" tag swallowed into body_text or dropped (Gap 2) -->
      <td class="artcard-heading" data-slot="heading"
          style="font-family: Inter, ...; font-size: 24px; font-weight: 600;
                 color: #000000; text-align: center;">  <!-- centred-by-default (Gap 11) -->
        Bundle of 6 Halloween posters
      </td>
      <td class="artcard-body" data-slot="body_text"
          style="font-family: Inter, ...; font-size: 14px;
                 color: #000000; text-align: center;">  <!-- centred-by-default -->
        Art prints
        As a member, you can make things even more mysterious...
      </td>
```

**Specific gaps this section surfaces:**

| Gap / Rule | Symptom | Plan |
|---|---|---|
| Gap 10 | No outer/inner table pair; lime wrapper bleeds through where white card should sit | 50.4 |
| Gap 1 | Wrapper not unwrapped — card section's own `bg_color` is lime (or empty), no `container_bg` distinct from `inner_bg` | 50.3 → 50.4 |
| Rule 10 | `<img>` has no `border-top-left-radius` / `border-bottom-left-radius` — Figma `rectangleCornerRadii: [6, 0, 0, 6]` ignored | 50.5 |
| Gap 2 | "Art prints" text either swallowed into `body_text` (above) or dropped — no `tag` slot exists on `article-card.html` | 51.3 (Phase 51 — references this section) |
| Rule 7 | If pill is rendered, it gets centred by default (matcher emits no `align`) — should be `align="left"` from bbox.x | 50.5 |
| Rule 8 | If pill is rendered, gets a default `border-radius: 12px` from chip-component template — should be `0` from absent `cornerRadius` | 50.5 |
| Gap 11 | Heading + body get `text-align: center` from `text-block-centered.html` default — should be `left` from `textAlignHorizontal=LEFT` | 50.6 |

## Section 2 — "Expect lots of treats" heading: text-align override

**Figma source:** `2833:1869 > Section 9 heading` (TEXT node with `textAlignHorizontal=LEFT`)

### Expected (LEGO worked example)

```html
<tr>
  <td class="lime-bg" bgcolor="#afca01"
      style="background-color: #afca01; padding: 32px 24px 16px 24px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="textblock-heading"
            style="font-family: 'Noto Sans', Arial, sans-serif; font-size: 28px;
                   font-weight: 700; color: #000000;
                   text-align: left;     /* ← from text.text_align="LEFT" */
                   mso-line-height-rule: exactly;">
          Expect lots of treats this Halloween!
        </td>
      </tr>
    </table>
  </td>
</tr>
```

### Current (analogous converter output)

The converter routes heading-only sections to `text-block-centered.html` when the parent wrapper has `align=CENTER`. Result:

```html
<tr>
  <td style="padding: 32px 16px; text-align: center;">  <!-- ← centred by default -->
    <table>
      <tr>
        <td data-slot="heading"
            style="font-family: Inter, ...; font-size: 28px; font-weight: 700;
                   color: #000000; text-align: center;">  <!-- ← wrong -->
          Expect lots of treats this Halloween!
        </td>
      </tr>
    </table>
  </td>
</tr>
```

**Gap surfaced:** Gap 11 — `_build_token_overrides` doesn't emit a `text-align` override even when the text node carries `textAlignHorizontal`. Fix: 50.6 (one-line emit per role).

## Section 3 — Membership Card Footer: card width matches dominant image

**Figma source:** `2833:1869 > Footer Insiders white card` (FRAME `2833:2057` — 4 children, all 440px native width on 600px viewport)

### Expected (LEGO worked example)

`email-templates/training_HTML/for_converter_engine/Lego/manual_component_build.html:1209+`:

```html
<!-- Outer cell padding decoupled from card width -->
<td bgcolor="#afca01" class="lime-bg" align="center"
    style="background-color: #afca01; padding: 6px 16px;">
  <!-- INNER card width matches dominant image (440px) — NOT 100% (Rule 11) -->
  <table role="presentation" width="440" align="center"
         cellpadding="0" cellspacing="0" border="0"
         bgcolor="#ffffff" class="wf"
         style="background-color: #ffffff; border-radius: 24px;
                border-collapse: separate; overflow: hidden;">
    <!-- 4 image rows, all max-width 440 — NO horizontal gap -->
    ...
  </table>
</td>
```

**Key markers:**
- `<table width="440" align="center" ... class="wf">` — fixed pixel width, centred, mobile-stretches via `.wf`
- Outer cell padding (`6px 16px`) is purely aesthetic — does NOT determine card width

### Current (analogous converter output)

```html
<!-- Card stretches to whatever parent allows; images leave 40px gap on right -->
<td style="padding: 32px 16px;">
  <table role="presentation" width="100%" ...
         bgcolor="#ffffff"
         style="background-color: #ffffff; border-radius: 24px;">  <!-- ← width:100%, no class="wf" -->
    <!-- images at max-width:440 inside 480px-wide card → visible white gap -->
    ...
  </table>
</td>
```

**Gap surfaced:** Rule 11 — when card's children all share the same `max-width`, card itself must be `width="<NATIVE_PX>"` not `width="100%"`. Fix: 50.5.

## Quick Reference for Plans

| Plan | Sections to cite | What to check post-implementation |
|---|---|---|
| 50.3 | §1 (outer wrapper carries `class="lime-bg" bgcolor="#afca01"`) | Outer `<td>` has wrapper bg; inner section has its own `bg_color` distinct |
| 50.4 | §1 (outer/inner table pair) | `<table class="_inner" bgcolor="#ffffff" style="...border-radius:16px; border-collapse:separate; overflow:hidden;">` present in card components |
| 50.5 Rule 7 | §1 pill `align="left"` from bbox.x | Pill `<table align="left">` when `pill.bbox.x = parent.bbox.x` |
| 50.5 Rule 8 | §1 pill `border-radius: 0` from absent `cornerRadius` | No "looks like pill therefore round it" — square corners when Figma says square |
| 50.5 Rule 10 | §1 `border-top-left-radius:6px + border-bottom-left-radius:6px` | Per-corner longhand on `<img>` from `rectangleCornerRadii` |
| 50.5 Rule 11 | §3 `<table width="440" align="center" class="wf">` | Inner card fixed-width when all children share `max-width` |
| 50.6 | §1 heading `text-align: left` + §2 entire section | `text-align: left` (or right) emitted from `TextBlock.text_align` |

## Notes

- **Excerpts are illustrative**, not full markup. For the complete worked examples, see the LEGO artifact triplet (Sources table at top of file).
- **Before-state anchor:** `hub_converter_phase49_baseline.html` is **frozen at Phase 49 completion** and must not be regenerated. Diverging from it is the goal of Phase 50; overwriting it would erase the historical baseline that every subtask diffs against. `data/debug/{6,reframe}/expected.html` are supplementary anchors for patterns the LEGO baseline doesn't surface (e.g. reframe-specific table widths).
- **Update cadence:** this `.md` file (the planning notes) is the only thing that gets revised — when a phase lands and renders a section differently, append a "Phase X delta" note next to the affected excerpt rather than rewriting the original "Before" markup.
