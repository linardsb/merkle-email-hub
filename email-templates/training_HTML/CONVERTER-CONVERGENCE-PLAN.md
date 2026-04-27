# Converter Convergence Plan — Revised after Step 1–2 executed

> **Date:** 2026-04-19
> **Status:** Step 1 (run with flags) and Step 2 (diff + probe) **done**. Awaiting approval before any code changes.
> **Companion doc:** `data/debug/converter-gap-analysis-v2.md` — detailed evidence.

---

## 0. What I executed (no code changed, only probing)

1. Ran `uv run python scripts/snapshot-capture.py {5,6,10}` — baseline. Case counts match current `expected.html`.
2. Re-ran with all Phase 47–49 flags enabled via environment variables. **Output bit-identical** (same MD5).
3. Wrote `scripts/_probe_tree_bridge.py` (one-off diagnostic, not wired into the pipeline) to:
   - Force `output_format="tree"` to exercise Phase 49.8
   - Print per-section matcher confidences + fill counts
   - Call `TreeCompiler.compile()` directly with surfaced errors
4. Saved flags-on outputs to `data/debug/{5,6,10}/actual-with-flags.html`.
5. Wrote detailed findings to `data/debug/converter-gap-analysis-v2.md`.

---

## 1. Headline findings (the short version)

### 1.1 Phase 47–49 flags are currently no-ops on the snapshot pipeline

All five flags either:
- require an async path or design screenshots not present in the sync flow (`VLM_VERIFY_ENABLED`)
- require an argument the CLI doesn't pass (`TREE_BRIDGE_ENABLED` needs `output_format="tree"`)
- require a confidence threshold lower than any real match (`CUSTOM_COMPONENT_ENABLED` at 0.6 threshold, matches all score ≥0.85)
- are already on by default but don't address the dominant failure mode (`SIBLING_DETECTION_ENABLED`)

### 1.2 Phase 49.8 TreeCompiler is dead on arrival

Forcing the tree path reveals:
```
CompilationError: Tree validation failed:
  sections[0]: slot 'image_alt' not defined for component 'full-width-image'
  sections[2]: slot 'image_alt' not defined for component 'full-width-image'
  sections[4]: slot 'image_alt' not defined for component 'article-card'
  sections[7]: slot 'image_alt' not defined for component 'full-width-image'
```

`tree_bridge.build_email_tree()` emits an `image_alt` slot; `component_manifest.yaml` doesn't define it. Validator rejects → fallback to legacy. Silent in WARN logs only.

### 1.3 The matchers pick things the fillers can't populate

| Match | Case | Confidence | Fills produced | Template defaults leak |
|-------|------|------------|----------------|-------------------------|
| `event-card` (false positive on Mammut) | 10 | 0.85 | 0 / 6 | "April 15, 2026", "London Convention Centre", "Register Now", `example.com/event` |
| `social-icons` | 6, 10 | 1.00 | 0 / ?  | `example.com/link` on every icon |
| `divider` | 5 | 1.00 | 0 / 1 | bg/line colors not overridden |

`_fills_event_card` **does not exist** in `component_matcher.py`. The event-card match is registered by the scorer but never by the fill dispatcher.

`_fills_social` returns `[]` with a misleading comment ("no data-slot — uses fixed template HTML"). The template DOES have data-slot; the extracted Figma button URLs are discarded.

### 1.4 Section under-counts are a vocabulary gap, not a pipeline bug

| Case | Ref | Actual | Missing components (all exist in the library, never selected) |
|------|-----|--------|----------------------------------------------------------------|
| MAAP (5) | 13 | 9 | standalone heading × 2, standalone paragraph, button-ghost |
| Starbucks (6) | 9 | 5 | standalone heading, standalone paragraph, button-filled, footer (legal) + Rewards logo |
| Mammut (10) | 18 | 12 | standalone heading × 4, text-link × 2, button-ghost × 2, navigation-bar (MEN/WOMEN/EQUIPMENT) |

The matcher collapses `1 heading + 1 paragraph + 1 CTA` into a single `text-block` section. The references split these. Until the layout analyzer splits at text-size boundaries, matcher changes alone cannot recover the missing sections.

---

## 2. Ordered fix proposals (all surgical, scoped)

Each item includes **what changes, where, and why**. Nothing below is executed yet.

### Fix A — TreeCompiler schema compatibility `[~15 min]`

**Problem:** Phase 49.8 path dead because manifest validator rejects the `image_alt` slot that tree_bridge emits.

**Option A1 (recommended):** Add `image_alt` as an optional "attr" slot to `full-width-image` and `article-card` in `app/components/data/component_manifest.yaml`. Type: "text". Required: false. Selector: `[data-slot='image_url']` (attr `alt`).

**Option A2:** Change `tree_bridge.py:build_email_tree()` to not emit `image_alt` as a separate slot — fold it into the `image_url` slot's `attr_overrides`.

**Why A1 is better:** tree compiler cross-validation is working correctly; the manifest is just incomplete. A1 makes the feature work without rewiring tree_bridge.

**Blast radius:** manifest YAML only. No Python change.

**Verify:** Re-run probe. TreeCompiler.compile() no longer raises. Output HTML generated through tree path.

### Fix B — Add `_fills_event_card` + register it `[~30 min]`

**Problem:** `event-card` matcher fires, fill dispatcher has no entry for it, all 6 template defaults leak.

**What changes:** In `app/design_sync/component_matcher.py`:
1. Add function `_fills_event_card(section, container_width, **kw) -> list[SlotFill]`
   - `event_name`: first `TextBlock` with `role_hint == "heading"` or largest font
   - `date`: first text matching `_DATE_PATTERN`
   - `time`: first text matching `_TIME_PATTERN`
   - `location`: text starting with "Location:" or similar, OR text after date+time
   - `description`: any remaining non-heading body text
   - `cta_text` / `cta_url`: from `section.buttons[0]` if present
2. Register `"event-card": _fills_event_card` in the dispatcher (line 512-552 in `_build_slot_fills`)
3. When a slot can't be populated (e.g., no matching date pattern), return an **empty** `SlotFill(slot_id, "")` — forces renderer to visibly strip the default rather than leak it

**Blast radius:** one new function + one dispatcher entry. No other call sites affected.

**Verify:** Case 10 section 1 — either (a) event-card fills populate from Mammut content (unlikely — it's not an event), producing empty string slots; or (b) fix D tightens matcher so event-card doesn't fire for Mammut at all.

### Fix C — `_fills_social` populated from Figma buttons `[~30 min]`

**Problem:** `_fills_social` returns `[]`; social-icons.html template defaults (`example.com/link` × 4) leak.

**What changes:** In `app/design_sync/component_matcher.py:1105`:
1. Replace `return []` with a builder that reads `section.buttons: list[ButtonElement]`
2. For each button, emit `SlotFill("social_{i}_url", button.url)` and `SlotFill("social_{i}_icon", button.image_url)`
3. Requires verifying the slot IDs in `email-templates/components/social-icons.html` — if the template doesn't have per-icon slots, a template edit is needed first

**Pre-check:** Read `social-icons.html` to confirm slot IDs exist. If not, add template edit to this fix.

**Blast radius:** one function rewrite + possibly one HTML template edit.

**Verify:** Cases 6, 10 section 11 — no `example.com` URLs in output for social icons.

### Fix D — event-card false-positive gate `[~15 min]`

**Problem:** event-card matches Mammut section 1 (large hero image + heading + body + 2 CTAs) because "duvet day" contains a date-like pattern. Should match `hero` variant or content+2-button instead.

**What changes:** In `app/design_sync/component_matcher.py:441-456` (event-card scoring in `_score_extended_candidates`):
- Add gate: **reject event-card if section has an image ≥ 200px** (event-cards are text-dense, no hero image)
- OR **require BOTH date pattern AND time pattern** (current is either date OR keywords; Mammut has date-like but no time)
- OR **require ≤1 button** (Mammut has 2)

**Blast radius:** 3–5 lines in one scoring block. No downstream effects.

**Verify:** Case 10 section 1 no longer matches event-card. Probably falls back to `article-card` or `hero-2cta`.

### Fix E — make TreeCompiler failures loud `[~5 min]`

**Problem:** `tree_bridge.compile_fallback` warning goes unnoticed. Phase 49.8 silent dead-code for an unknown time.

**What changes:** In `app/design_sync/converter_service.py:717-720`:
- Upgrade log level from WARN to ERROR when `output_format == "tree"` explicitly requested (silent fallback is acceptable for default "html" path)
- Include exception details in log payload

**Blast radius:** one log statement.

### Fix F — custom_component threshold more useful `[~2 min]`

**Problem:** `custom_component_confidence_threshold=0.6` is too low; every match scores ≥0.85 so AI fallback never triggers.

**What changes:** `app/core/config.py:415` default from `0.6` to `0.85`.

**Blast radius:** config default only. Must be paired with `CUSTOM_COMPONENT_ENABLED=true` to have effect.

---

## 3. Not fixable without larger work (for later PRs)

| Gap | Scope | Effort |
|-----|-------|--------|
| Standalone heading / paragraph / text-link splitter in `layout_analyzer.py` | Split a `CONTENT` section with multiple text blocks at font-size boundaries; new matcher paths for `heading`, `paragraph`, `text-link` | 1–2 days |
| `button-filled` / `button-ghost` distinct matching with VML + brand colors | New matcher paths, token extraction from buttons, template routing | 1 day |
| `col-icon` repeating-group matcher for REFRAME 5-reasons | New pattern: 3+ child frames with icon≤64px + text, inside one container frame | 1 day |
| `navigation-bar` variants: MAAP vertical, Mammut with red arrows, Starbucks APP/ORDER/OFFERS/REWARDS | Three distinct nav styles, currently all fall into generic navigation-bar | 1 day |
| Footer-with-legal-text preservation (vs collapsing to social-icons) | Classification precedence fix in `layout_analyzer.py` — FOOTER tier-4 rule should win over SOCIAL when both signals present | 4 hours |
| REFRAME fixture completion (Step 7 of original plan) | Sync Figma node 2833-1491, produce structure/tokens/vlm_classifications | 1 hour once Figma API available |
| `2833-1292` fixture (new case) | Needs user input on what this campaign is | unknown |

---

## 4. Proposed execution order (if approved)

1. **Fix A, E, F** (manifest + log + config) — low risk, clears the deck for Phase 49.8 and custom-gen to actually fire later. No behavior change for current sync path. `[25 min total]`
2. **Fix D** (event-card gate) — stops the Mammut false positive before fixing its filler. `[15 min]`
3. **Fix B** (event-card filler) — catches real event-card matches when they do occur (REFRAME has a real one). `[30 min]`
4. **Fix C** (social fills) — removes `example.com` leaks from cases 6, 10. `[30 min]`
5. **Re-run probe on all 3 cases.** Capture `actual-with-fixes.html`. Compare section counts + placeholder counts to baseline. `[10 min]`
6. **Stop and review with user.** Show delta. If encouraging, proceed with the standalone-heading splitter (§3 item 1) as its own scoped PR.

**Total before checkpoint:** ~2 hours of focused work + review.

---

## 5. What NOT to do

- Don't flip config defaults to `true` for `TREE_BRIDGE_ENABLED` or `CUSTOM_COMPONENT_ENABLED` until Fix A and Fix F respectively are in. Otherwise every run would hit the silent fallback or miss the threshold.
- Don't touch `layout_analyzer.py` until Fix A–D + standalone-heading splitter are scoped together. Changing section boundaries without matcher updates breaks the current passing cases.
- Don't modify `email-templates/components/*.html` component files unless Fix C specifically requires a template edit for social-icons slot IDs.
- Don't re-sync Figma for cases 5, 6, 10 — the cached `structure.json` + `tokens.json` are sufficient.

---

## 6. Approval checkpoints

Please reply one of:

- **"proceed"** → I execute Fix A–D + E + F, re-run probe, show delta, stop for review.
- **"proceed with A and E only"** → Smallest reversible change first (manifest + log). Same verify step.
- **"change the plan"** → Tell me what to adjust.
- **"hold"** → No code changes. Plan stays as-is for later.

I will not write any production code or modify settings without one of the above.

---

## 7. Artifacts produced so far

| Path | Purpose |
|------|---------|
| `email-templates/training_HTML/CONVERTER-CONVERGENCE-PLAN.md` | This doc |
| `data/debug/converter-gap-analysis-v2.md` | Detailed evidence for each finding |
| `data/debug/5/actual-with-flags.html` | Case 5 output with flags ON (identical to current `expected.html`) |
| `data/debug/6/actual-with-flags.html` | Case 6 output with flags ON |
| `data/debug/10/actual-with-flags.html` | Case 10 output with flags ON |
| `scripts/_probe_tree_bridge.py` | One-off probe used for the investigation; underscore prefix marks it as non-production |
