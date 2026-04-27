# Converter Convergence Plan V2 — filler bugs + splitter

> **Date:** 2026-04-19
> **Status:** Investigation complete, awaiting approval before any code changes.
> **V1 predecessor:** `CONVERTER-CONVERGENCE-PLAN.md` (Fixes A–F shipped in commit `2fd5897`).
> **Trigger case:** LEGO Insiders Halloween email, Figma node `2833-1869`.

---

## 0. Context

Ran the converter on a new LEGO Insiders design. Output was nowhere near the reference:
- 6+ product/article card images dropped entirely
- 4 product cards collapsed into 1 giant `text-block` section
- 2 "Redeem reward" + 4 "Shop now" CTAs collapsed into 1 CTA per section
- Section 7 footer columns emit invalid `<td><tr><td>…</td></tr></td>` nesting
- Section 2 "Explore now" CTA is invisible (white text on white button)

V1's scope (event-card gate + social fills + tree-bridge compile + log upgrade + config default) didn't overlap with any of these.

---

## 1. Did V1 help?

| V1 fix | Helps LEGO? | Why |
|---|---|---|
| A. `{stem}_alt` fold in `tree_bridge` | No — LEGO ran on the legacy HTML path, not the tree path |
| B. `_fills_event_card` | No — LEGO has no event-card match |
| C. `_fills_social` populate | No — LEGO footer is `column-layout-4`, not `social-icons` |
| D. event-card false-positive gate | No — as above |
| E. Loud WARN→ERROR on tree compile fallback | No — no tree path exercised |
| F. `custom_component_confidence_threshold` 0.6→0.85 | No — `DESIGN_SYNC__CUSTOM_COMPONENT_ENABLED` is default `false`; threshold inert until enabled |

**Net:** V1 closed the 4 P0 issues it targeted (cases 5/6/10). It did not touch the code paths that LEGO exercises. Zero regression either.

---

## 2. Findings — 1 architecture gap + 4 code bugs

### 2.1 Top-level frame collapse *(§3 item 1 in V1 plan — the splitter)*

`layout_analyzer._get_section_candidates()` (L385-410) returns **top-level frames** as sections. Content extraction walks each frame recursively (`_extract_texts`, `_extract_images`, `_extract_buttons`) and flattens everything into one `EmailSection`. If Figma wraps 4 product cards inside a parent "Products" frame, that wrapper becomes ONE section with all 4 cards' content flattened. Matcher then scores as `text-block`.

`_extract_content_groups` (L1175) attempts to preserve parent-child hierarchy by keeping `child_content_groups` on the section, but it only helps fillers that read it (`_fills_article_card`, `_fills_hero`). `_fills_text_block` partially reads it but still renders into a single-heading/single-body template.

**Impact on LEGO:** 4 product cards + 2 article cards → ~2 text-block sections.

### 2.2 Bug A — `_fills_text_block` silently drops `section.images`

`app/design_sync/component_matcher.py:860-910`. The function consults `section.texts`, `section.buttons`, `section.child_content_groups`. It **never references `section.images`**. Any section that matches text-block loses every image it contained.

**Impact on LEGO:** 6 product/article images + hero Stranger Things composition — all dropped.

### 2.3 Bug B — `_fills_text_block` uses only `buttons[0]`

Same function, L899: `btn = section.buttons[0]`. Additional buttons are discarded.

**Impact on LEGO:** "Redeem reward" × 2, "Shop now" × 4 collapse to 1 CTA per section.

### 2.4 Bug C — `_build_column_fill_html` emits invalid `<tr>` inside `<td>`

`component_matcher.py:692-708`. The function wraps each text in `<tr><td style="…">{escaped}</td></tr>` and the caller injects the result INTO an existing `<td data-slot="col_N">`. Produces `<td data-slot="col_N"><tr><td>Andy</td></tr></td>` — invalid HTML.

Note: `_build_column_fill_html` also mixes raw `<img …>` tags (not wrapped in tr/td) with the `<tr><td>` text wrappers on the same level — structurally incoherent.

**Impact on LEGO:** Section 7 footer column layout is broken in any standards-mode renderer. Also explains why "Andy" / "0" render but other column text gets misparsed.

### 2.5 Bug D — `_fills_text_block` hardcodes `color:#ffffff` on CTA anchor

Same function, L905: `f"padding:10px 24px;background-color:{bg};color:#ffffff;"`. When `btn.fill_color` is `#FFFFFF` (white button as Figma intended), text and background are both white → invisible button.

Note: `_build_column_fill_html` (L714) correctly uses `txt_color = _safe_color(btn.text_color, "#ffffff")`. The pattern already exists in the file; `_fills_text_block` simply doesn't use it.

**Impact on LEGO:** Section 2 "Explore now" CTA vanishes. Any white/light-CTA design triggers this.

---

## 3. Fix proposals — all surgical, scoped

Each fix is a few-line change in `component_matcher.py`. None touch `layout_analyzer.py` or split sections.

### Fix A — passthrough `section.images` from text-block `[~20 min]`

In `_fills_text_block`, after body parts are built, emit one `<img>` tag per `section.image` into an appended HTML fragment that merges into the body slot (same pattern as the existing CTA append). Prefer `child_content_groups`'s per-group images when present, flat `section.images` when not.

**Alternatives considered:**
- A new `image_grid` slot — requires template edit; out of scope.
- Route text-block with images to `article-card` — would change existing cases 5/6/10; out of scope.
- Append images into body slot as inline `<img>` fragments — minimal, compatible with existing template. ✓

**Verify:** LEGO section 4/5 regain 6+ product images. Cases 5/6/10 unchanged (they hit text-block without images today; fresh run proves parity).

### Fix B — emit all buttons, not just `buttons[0]` `[~15 min]`

Loop `section.buttons`, append each button's `<a>` HTML to the body slot. Keep the `_is_placeholder(btn.text)` filter. Cap at 6 (arbitrary safety limit) to avoid runaway output on broken extraction.

**Verify:** LEGO section 5 gains 3+ "Shop now" CTAs. Cases 5/6/10 unchanged (text-block sections have ≤1 button each today).

### Fix C — stop emitting `<tr><td>` as column cell content `[~15 min]`

In `_build_column_fill_html`, replace `<tr><td style="…">{escaped}</td></tr>` with either:
- **Option C1:** `<div style="…">{escaped}</div>` — valid inside `<td>`. Simple.
- **Option C2:** Open an inner `<table>` once, emit `<tr><td>…</td></tr>` rows inside it, close the table. More faithful to email structure rules but more churn.
- **Option C3 (recommended):** Plain `<br>`-separated text inside styled `<span>`s. Least churn, valid HTML, same visual outcome because each text was its own visual line anyway.

`div` inside `<td>` is allowed per CLAUDE.md ("Simple wrappers: `<div style="text-align:center;">` inside `<td>` is fine"). Use C1 or C3.

**Verify:** LEGO section 7 footer renders cleanly (no stray `<tr>`). Cases 5/6/10 column sections unchanged (they don't hit the text-as-row path).

### Fix D — CTA text color from `btn.text_color` `[~10 min]`

In `_fills_text_block` CTA append, mirror the existing pattern from `_build_column_fill_html:714`:
```
txt_color = _safe_color(btn.text_color, "#ffffff")
```
If `btn.text_color` is absent AND `btn.fill_color` is light, fall back to a contrast-safe dark. Simplest heuristic: if `_safe_color(bg)` normalized starts with `#fff` / `#eee` / has luminance ≥ 0.7, use `#000000`.

**Verify:** LEGO section 2 "Explore now" renders visible text. Cases 5/6/10 unchanged (their CTAs either have text_color set or have dark backgrounds).

### Fix E — section splitter in `layout_analyzer.py` *(separate PR, 1-2 days)*

Out of this plan's scope. Keep the sibling_detector pattern (49.1) as reference — it merges top-level siblings; the splitter does the opposite. New helper `_split_card_grid(frame)` that:
1. Detects a frame with 2+ child frames of similar shape (sibling signature).
2. Returns each child as its own `EmailSection` candidate instead of flattening.
3. Gated behind `DESIGN_SYNC__SECTION_SPLITTER_ENABLED` (default false) until tested on all 4 reference cases.

The splitter is the real unlock for LEGO (and MAAP/Starbucks card-heavy designs). Do it AFTER A-D land so surgical bug fixes aren't bundled with architecture risk.

---

## 4. Execution order

1. **Fix A + B + D** in `_fills_text_block` (single function, shared context) — ~45 min.
2. **Fix C** in `_build_column_fill_html` — ~15 min.
3. Re-run LEGO probe + existing probes for cases 5/6/10 — ~15 min. Save to `data/debug/{case}/actual-with-v2-fixes.html` + a new `data/debug/lego/actual-with-v2-fixes.html` if a debug fixture for LEGO is produced.
4. **Stop and review.** Show placeholder/image/CTA counts delta vs both V0 (pre-V1) and V1.
5. Approval gate → Fix E (splitter) as separate scoped PR.

**Total before checkpoint:** ~90 min of focused work + review.

---

## 5. What NOT to do

(Same spirit as V1 §5. Specific to this plan:)

- Don't touch `_get_section_candidates` or `_extract_texts/images/buttons` in `layout_analyzer.py`. That's Fix E territory. Changing flatten behaviour without the matcher vocabulary to consume it breaks cases 5/6/10.
- Don't route text-block with images to `article-card` as a shortcut. The scoring gate decisions (§3 matcher logic) assume text-block = no structural image component. Silent routing breaks the intent.
- Don't edit email-templates/components/*.html for Fix A. The existing text-block template is fine; inject images into the body slot fragment.
- Don't auto-overwrite `data/debug/{5,6,10}/expected.html` — V1's §4.6 pause still applies. Even pure-win changes need human approval on the baselines.
- Don't add a "product-card" matcher slug before Fix E lands. It would only fire if LEGO's 4 cards are split into 4 sections, which requires the splitter.

---

## 6. Approval checkpoints

Reply one of:

- **"proceed"** → I ship Fix A+B+C+D bundled, re-run probes, show delta, stop.
- **"proceed with A+D only"** → smallest-reversible pair (images + visible CTA text). Same verify step.
- **"skip to splitter"** → if you want Fix E first (riskier but biggest impact).
- **"change the plan"** → tell me what to adjust.
- **"hold"** → no code changes.

I will not write production code without one of the above.

---

## 7. Lessons carried forward from V1

Saved here so the next planning session reaches these without re-deriving them.

### L1 — Verify the actual code path before writing a fix

V1 Fix A1 as originally written targeted `component_manifest.yaml`. The tree compiler builds `slot_definitions` from HTML `data-slot` regex matches at runtime — YAML is **not consulted**. Advisor caught this during orientation; saved roughly an hour. For V2: before committing to any fix, load the function, trace slot_fills → renderer consumption, confirm where the gap actually lives.

### L2 — 2-pass, order-independent transformations

V1 Fix A folds `{stem}_alt` into paired image fills. The first draft assumed `image_url` always appears before `image_alt` in the fill list. Advisor flagged: don't rely on emit order; pre-scan to build a lookup, then apply. V2 Fix A (image passthrough) should similarly build an image-by-slot map first, then merge.

### L3 — Snapshot baseline divergence is expected and surfaceable

V1 intentionally changed outputs for cases 6 and 10. `test_snapshot_matches[6]/[10]` and `test_background_continuity[6]/[10]` failed as expected. Saving `actual-with-fixes.html` for review + explicitly calling out the 4 RED tests is the right pattern. Don't silently `--overwrite` baselines; that pattern bit the V1 plan author's predecessor.

### L4 — Probe script pattern

V1's `scripts/_probe_tree_bridge.py` force-exercised a gated code path with exceptions surfaced. Huge diagnostic ROI. V2 should write `scripts/_probe_text_block_fills.py` that, for each existing debug case, prints per-section `(slug, n_images_extracted, n_images_rendered, n_buttons_extracted, n_buttons_rendered)`. Makes Fix A/B/C/D regressions visible at a glance.

### L5 — Preserve the §6 approval gate

V1 required explicit "proceed" before any code. Kept scope tight. V2 preserves this.

### L6 — Keep surgical bugs and architecture gaps in separate PRs

V1 bundled 6 surgical fixes (A-F) and deliberately left the splitter for a separate scope. V2 mirrors this: A+B+C+D together, E (splitter) standalone. Avoids "one PR that touches 5 modules with different risk profiles."

### L7 — HTML structure rules apply to the **insertion context**, not just the generator

V1 review caught `alt` attribute quoting (W1): the generator itself was valid, but `_safe_text(quote=False)` became invalid once inserted into `alt="..."`. V2's Bug C is the same shape: `_build_column_fill_html` emits standalone valid `<tr><td>…</td></tr>` fragments that become invalid once inserted into `<td data-slot="col_N">`. Rule: when writing a slot filler, ask "where does this string end up?" before picking the wrapping tags.

### L8 — Advisor at orientation + before-done, not mid-execution

V1 got highest ROI from advisor calls at (a) after orientation, before coding (caught YAML-vs-HTML mismatch); (b) at "I think I'm done" (caught unaddressed user messages, unsurfaced red tests, and data-availability vs code-limit framing for the `href="#"` social fallback). Mid-execution calls weren't as useful. V2 plan: one advisor call after reading the target functions and before Fix A; one before declaring done.

### L9 — The plan's §5 "what NOT to do" list is load-bearing

V1 §5 explicitly said "Don't touch `layout_analyzer.py` until Fix A-D + splitter are scoped together." That single constraint kept the V1 PR scope small and shippable. V2 preserves a similar §5.

### L10 — Evidence artifacts (`actual-with-flags.html`, `actual-with-fixes.html`) as durable before/after record

Survives past the session. Makes diff visible to humans. Cheap to produce, high-value. V2 continues the pattern: `actual-with-v2-fixes.html` per case.

---

## 8. Out-of-scope but noted for next plan

- **Preheader detection for top-row text.** LEGO's "View online | My Account" matched as text-block section 0. `layout_analyzer._classify_section` has no rule for "short text frame in the top 100px of the page that contains nav keywords". Add a pre-classification hook.
- **Full-width hero composition.** LEGO hero (Stranger Things + brick kids) is not appearing in output. Likely in a frame matched as CONTENT → text-block → dropped via Bug A. Fix A probably fixes this incidentally.
- **Button color fidelity.** Beyond Fix D, button border-radius, padding, font family are also hardcoded in `_fills_text_block`'s CTA append. `_build_column_fill_html` already uses real Figma values (L713-724). Should port that pattern to text-block. ~30 min follow-up.
- **Article-card vs product-card vocabulary.** Once splitter lands, need matcher rules to distinguish "image + heading + body + CTA" (article-card) from "image + heading + metadata list + CTA" (product-card). LEGO needs both. ~1 day.
- **Dark mode CSS pollution.** The output email-shell dark-mode CSS always ships even when the design has no dark palette. Not a bug per se, but payload bloat.

---

## 9. Artifacts

To be produced on approval:

| Path | Purpose |
|------|---------|
| `data/debug/lego/actual-pre-v2.html` | Baseline of today's broken LEGO output |
| `data/debug/lego/actual-with-v2-fixes.html` | LEGO with A+B+C+D applied |
| `data/debug/{5,6,10}/actual-with-v2-fixes.html` | Regression check on prior cases |
| `scripts/_probe_text_block_fills.py` | Per-section image/button extract-vs-render counter (L4) |

V1 artifacts (`actual-with-fixes.html`, `actual-with-flags.html`, `converter-gap-analysis-v2.md`) remain in place as historical record.
