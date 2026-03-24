# Fix div/p Tag Contamination in Email HTML Pipeline

**Problem:** `<div>` and `<p>` tags leak into email HTML output despite explicit scaffolder prompt rules against them. HTML email must use `<table>/<tr>/<td>` exclusively. The user has to repeatedly remind Claude about this.

**Root cause analysis (3 layers):**

## Layer 1: Known Bugs (fix immediately)

### 1.1 Assembler social links generates `<div>` AFTER sanitization
- **File:** `app/ai/agents/scaffolder/assembler.py:324`
- **Code:** `social_html = '<div style="text-align:center;padding:16px 0;">' + "".join(parts) + "</div>"`
- **Fix:** Replace with `<table role="presentation"><tr><td style="text-align:center;padding:16px 0;">` ... `</td></tr></table>`
- **Why this matters:** This div is injected AFTER `sanitize_web_tags_for_email()` runs, so it persists in final output.

### 1.2 Design converter maps VECTOR nodes to `<div>`
- **File:** `app/design_sync/converter.py:26`
- **Code:** `DesignNodeType.VECTOR: "div"`
- **Fix:** Map to `<td>` or a table wrapper instead. Vectors in email context should be image/spacer cells.
- **Risk:** Low — vectors are uncommon in email designs and are wrapped in `<td>` by parent node conversion.

## Layer 2: Missing Enforcement (add validation)

### 2.1 No QA check flags div/p tags in email HTML
- **Current state:** 14 QA checks exist, none validate table-only structure
- **Fix:** Add `table_structure` QA check in `app/qa_engine/checks/`
- **Rules:**
  - REJECT: `<p>` tags anywhere except preheader hidden text
  - REJECT: `<div>` tags except `role="article"` wrapper and MSO conditional blocks
  - REJECT: Semantic HTML (`<section>`, `<header>`, `<footer>`, `<main>`, `<nav>`, `<aside>`) outside MSO blocks
- **Severity:** Error-level (0.20 deduction) — these cause real rendering failures in Outlook/Gmail

### 2.2 No repair step converts div/p to table structure
- **Current state:** `repair/structure.py` only fixes skeleton (DOCTYPE, html, head, body)
- **Fix:** Add repair step that:
  - Converts `<p>content</p>` → content (already done by `sanitize_web_tags_for_email`)
  - Converts `<div style="...">content</div>` → `<table role="presentation"><tr><td style="...">content</td></tr></table>`
  - Unwraps nested divs
- **Placement:** After Stage 1 (Structure) in `RepairPipeline`

### 2.3 `sanitize_web_tags_for_email()` only called in design sync import pipeline
- **File:** `app/design_sync/import_service.py:213`
- **Gap:** The scaffolder pipeline (`app/ai/agents/scaffolder/pipeline.py`) and blueprint engine don't call this function
- **Fix:** Apply `sanitize_web_tags_for_email()` as a post-processing step in `TemplateAssembler` or `BlueprintEngine` output — NOT just in design sync

## Layer 3: Preventive Measures (reduce generation)

### 3.1 Strengthen scaffolder structured output schema
- **Current:** Prompt says "NEVER use div/p" but LLM output is free-form HTML
- **Fix:** In structured output mode, add a `validate_no_block_elements()` post-check on generated HTML sections
- **File:** `app/ai/agents/scaffolder/service.py` — add validation in `_post_process()`

### 3.2 Tighten nh3 sanitization profiles for email-output agents
- **Current:** `_BASE_ALLOWED_TAGS` in `app/ai/shared.py` includes `div` and `p` for all profiles
- **Consideration:** Can't simply remove div/p from allowlist because:
  - MSO hybrid columns legitimately use `<div>` inside conditional comments
  - Some content agents operate on non-email HTML (knowledge, code_reviewer)
- **Fix:** Create `_EMAIL_ALLOWED_TAGS` variant that excludes div/p, use for scaffolder/dark_mode/accessibility/personalisation/outlook_fixer profiles
- **Alternative:** Keep current allowlist but add post-sanitization stripping (Layer 2.3)

### 3.3 Add CLAUDE.md rule for session awareness
- Already in scaffolder prompt, but add to project CLAUDE.md so Claude sessions are aware:
  ```
  ## HTML Email Structure
  - HTML emails NEVER use <div> or <p> for layout. Use <table>/<tr>/<td> exclusively.
  - Only exceptions: role="article" wrapper div, MSO conditional <div> blocks, preheader hidden <p>.
  - The design sync pipeline's `sanitize_web_tags_for_email()` strips these, but it must run AFTER all HTML injection steps.
  ```

### 3.4 Save feedback memory for cross-session persistence
- Save memory: "Email HTML must never contain div/p tags. The design sync and scaffolder pipelines have a recurring issue where these leak through. Always verify final HTML output is table-based."

## Implementation Order

1. **Fix 1.1** — Assembler social links div (5 min, immediate win)
2. **Fix 2.3** — Apply `sanitize_web_tags_for_email()` after all HTML assembly, not just design sync (30 min)
3. **Fix 2.1** — Add `table_structure` QA check (1 session)
4. **Fix 3.1** — Post-validation in scaffolder service (15 min)
5. **Fix 3.3 + 3.4** — CLAUDE.md rule + feedback memory (5 min)
6. **Fix 2.2** — Repair step for div→table conversion (1 session, lower priority since 2.3 catches it)
7. **Fix 1.2** — Vector node mapping (5 min, low impact)
8. **Fix 3.2** — Email-specific sanitization profiles (30 min, optional if 2.3 is solid)

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `app/ai/agents/scaffolder/assembler.py` | Fix social links div → table | P0 |
| `app/design_sync/converter.py` | Export `sanitize_web_tags_for_email` for reuse | P0 |
| `app/ai/agents/scaffolder/pipeline.py` or `assembler.py` | Call `sanitize_web_tags_for_email()` on final output | P0 |
| `app/qa_engine/checks/table_structure.py` | New QA check | P1 |
| `app/qa_engine/rules/email_structure.yaml` | Add table-only rules | P1 |
| `app/ai/agents/scaffolder/service.py` | Post-validation for block elements | P1 |
| `CLAUDE.md` | Add HTML email structure rule | P1 |
| `app/qa_engine/repair/table_structure.py` | New repair step | P2 |
| `app/ai/shared.py` | Email-specific allowlist variant | P2 |
| `app/design_sync/converter.py:26` | Vector → td mapping | P2 |

## Test Strategy

- Unit test: `sanitize_web_tags_for_email` handles all injection patterns
- Unit test: QA check detects div/p in email HTML, allows MSO exceptions
- Integration test: Full scaffolder pipeline → verify no div/p in output
- Integration test: Design sync import → verify no div/p in output
- Regression: Existing golden templates still pass (they use MSO divs legitimately)
