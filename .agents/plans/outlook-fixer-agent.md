# Plan: Outlook Fixer Agent (Task 4.1 — Priority 1)

## Context

First agent built using the eval-first + skills workflow. The Outlook Fixer takes existing email HTML and fixes rendering issues for Outlook desktop (Word engine), Outlook.com, and Outlook mobile. Informed by:
- Phase 5.4-5.8 eval data: scaffolder `mso_conditional_correctness` at 0% — agents consistently produce malformed MSO/VML
- Existing skill asset: `app/ai/agents/html-email-innovation.skill` (668 lines, 15 Outlook bug patterns)
- Anthropic Agent Skills pattern: progressive disclosure, SKILL.md + reference files

## Skill Structure (Progressive Disclosure)

```
app/ai/agents/outlook_fixer/
├── __init__.py              # Module docstring
├── service.py               # OutlookFixerService — loads SKILL.md, calls provider
├── prompt.py                # System prompt (thin — core rules + references SKILL.md)
├── schemas.py               # OutlookFixerInput/Output schemas
├── SKILL.md                 # L1 metadata + L2 core instructions
├── skills/
│   ├── mso_bug_fixes.md     # L3: 15 Outlook bug patterns with copy-paste fixes
│   ├── vml_reference.md     # L3: VML shapes, fills, textbox patterns
│   ├── mso_conditionals.md  # L3: Version targeting, ghost tables, DPI
│   └── diagnostic.md        # L3: Symptom → cause → fix lookup table
└── CLAUDE.md                # Agent-specific dev notes
```

### SKILL.md Design (Anthropic Guidelines Applied)

**L1 — YAML Frontmatter (always loaded, enables skill discovery):**
```yaml
name: outlook-fixer
description: >
  Fix Outlook desktop rendering issues in email HTML. Handles MSO conditional
  comments, VML backgrounds/buttons, ghost tables, DPI scaling, dark mode
  data-ogsc/data-ogsb selectors, font stacks, image sizing, line-height,
  and 15 common Outlook bug patterns. Use when HTML renders incorrectly in
  Outlook 2007-2019, Microsoft 365, or Outlook.com.
```

**L2 — Core Instructions (loaded when skill is relevant):**
- Input/output contract (receive HTML, return fixed HTML)
- Preservation rules (never remove existing structure)
- Fix categorization (which bugs to check for)
- Confidence assessment rules

**L3 — Reference Files (loaded on-demand based on detected issues):**
- `mso_bug_fixes.md` — Decomposed from html-email-innovation.skill Parts 1-2 (sections 1-15)
- `vml_reference.md` — VML shapes, fills, roundrect buttons, background images
- `mso_conditionals.md` — Version targeting reference, ghost table patterns
- `diagnostic.md` — Symptom lookup table (from Part 5 of existing skill)

### Improvements Over Existing Skill (Anthropic Guidelines)

1. **Progressive disclosure** — Existing skill loads all 668 lines into context. New structure loads only relevant L3 files based on detected issues (e.g., if no VML in input, skip vml_reference.md)
2. **Executable validation** — SKILL.md includes deterministic checks the agent must run (MSO comment matching, VML namespace verification) rather than relying solely on LLM reasoning
3. **Eval-grounded** — Each L3 file maps to an eval criterion. `mso_bug_fixes.md` quality measured by `mso_conditional_correctness` judge criterion
4. **Confidence calibration** — Scoring rules tied to specific patterns: 0.9+ if only standard MSO fixes needed, 0.5-0.7 for VML nesting issues, below 0.5 for undocumented client quirks

## Implementation Steps

### ~~Step 1: Create SKILL.md + Reference Files~~ DONE
Decompose `html-email-innovation.skill` into the progressive disclosure structure above.
**Files:** `SKILL.md`, `skills/mso_bug_fixes.md`, `skills/vml_reference.md`, `skills/mso_conditionals.md`, `skills/diagnostic.md`
**No code changes yet** — skill files only.

### ~~Step 2: Agent Service Layer~~ DONE
Create `app/ai/agents/outlook_fixer/` following existing agent patterns (scaffolder, dark_mode).
**Files:** `__init__.py`, `prompt.py`, `schemas.py`, `service.py`
- `OutlookFixerService` with `fix(html: str, issues: list[str] | None) -> OutlookFixerOutput`
- System prompt references SKILL.md core instructions
- Progressive skill loading: detect VML/MSO/dark-mode patterns in input → load relevant L3 files as context
- Emit `AgentHandoff` with confidence score and fix decisions

### ~~Step 3: Blueprint Node~~ DONE
Add `OutlookFixerNode` to `app/ai/blueprints/nodes/`.
- Receives HTML + QA failure details from recovery router
- Loads relevant skills based on QA failure types (e.g., dark_mode failures → load dark mode section)
- Emits `AgentHandoff` with fix list for downstream agents

### ~~Step 4: Eval Data (Synthetic Test Cases)~~ DONE
Create `app/ai/agents/evals/synthetic_data_outlook_fixer.py` — 10-12 test cases:
- MSO conditional comment mismatches
- Missing VML namespaces
- Broken ghost tables (3-column layouts)
- DPI scaling issues (high-DPI displays)
- Font stack falling to Times New Roman
- Background image not rendering (CSS only, no VML)
- Bulletproof button without VML roundrect
- 1px white lines between sections
- Body background bleeding through table gaps
- Image sizing without HTML attributes
- Line height issues
- Animated GIF fallback missing

### ~~Step 5: Judge Prompts~~ DONE
Create `app/ai/agents/evals/judges/outlook_fixer.py` — `OutlookFixerJudge` with 5 criteria:
1. `mso_conditional_correctness` — Are MSO conditionals properly opened/closed with correct version targeting?
2. `vml_wellformedness` — Are VML elements properly structured with namespaces, correct attributes?
3. `html_preservation` — Is the original HTML structure, content, and non-Outlook styles preserved?
4. `fix_completeness` — Are all identified rendering issues addressed (not just some)?
5. `outlook_version_targeting` — Are fixes correctly scoped to affected Outlook versions?

### Step 6: Eval Run + Iterate
```bash
make eval-run --agent outlook_fixer    # Generate traces
make eval-judge --agent outlook_fixer  # Judge verdicts
make eval-analysis                     # Identify skill gaps
# Iterate: refine SKILL.md/skills/*.md → re-eval → measure improvement
make eval-baseline                     # Lock in when stable
```

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `app/ai/agents/outlook_fixer/__init__.py` | Create | Module docstring |
| `app/ai/agents/outlook_fixer/service.py` | Create | OutlookFixerService |
| `app/ai/agents/outlook_fixer/prompt.py` | Create | System prompt |
| `app/ai/agents/outlook_fixer/schemas.py` | Create | Input/Output schemas |
| `app/ai/agents/outlook_fixer/SKILL.md` | Create | L1+L2 skill definition |
| `app/ai/agents/outlook_fixer/skills/mso_bug_fixes.md` | Create | L3: 15 bug patterns |
| `app/ai/agents/outlook_fixer/skills/vml_reference.md` | Create | L3: VML patterns |
| `app/ai/agents/outlook_fixer/skills/mso_conditionals.md` | Create | L3: Version targeting |
| `app/ai/agents/outlook_fixer/skills/diagnostic.md` | Create | L3: Symptom lookup |
| `app/ai/agents/outlook_fixer/CLAUDE.md` | Create | Dev notes |
| `app/ai/agents/evals/synthetic_data_outlook_fixer.py` | Create | 10-12 test cases |
| `app/ai/agents/evals/judges/outlook_fixer.py` | Create | 5-criteria judge |
| `app/ai/agents/evals/dimensions.py` | Modify | Add outlook_fixer dimensions |
| `app/ai/agents/evals/runner.py` | Modify | Register outlook_fixer agent |
| `app/ai/agents/evals/judges/__init__.py` | Modify | Register OutlookFixerJudge |
| `app/ai/blueprints/nodes/outlook_fixer.py` | Create | Blueprint node |
| `app/ai/blueprints/definitions.py` | Modify | Add node to campaign graph |
| `app/ai/agents/CLAUDE.md` | Modify | Update agent status table |

## Security Checklist

- [x] No new endpoints added (agent invoked via blueprint engine, not direct API)
- [x] Agent output sanitized via `sanitize_html_xss()` from `app/ai/shared.py`
- [x] No user input passed directly to `sa.text()`, `subprocess`, `eval`
- [x] Synthetic test data uses only `placehold.co` / `example.com` URLs
- [x] SKILL.md files contain no real client data or API keys
- [x] VML patterns in skill files sanitized (no script injection via VML)

## Verification

- [x] `make lint` passes
- [x] `make types` passes (MyPy 0 errors, Pyright pre-existing only)
- [x] `make test` passes (535 tests, 0 failures)
- [x] `make eval-verify` passes
- [x] `make eval-run --agent outlook_fixer` generates 12 traces (dry-run verified)
- [ ] `make eval-judge --agent outlook_fixer` produces verdicts
- [ ] `mso_conditional_correctness` pass rate > 50% (target: >70%)
- [ ] Blueprint pipeline with Outlook Fixer in recovery path works
- [ ] `make eval-check` passes (no regressions on existing agents)

## Estimated Effort

- Step 1 (SKILL.md + skills): ~1 hour (decompose existing skill)
- Step 2 (service layer): ~2 hours (follows existing patterns)
- Step 3 (blueprint node): ~1 hour
- Step 4-5 (eval data + judge): ~2 hours
- Step 6 (eval iteration): ~1-2 hours (depends on initial pass rates)
- **Total: ~7-8 hours**

## Dependencies

- [x] Phase 7.1 — AgentHandoff schemas (DONE)
- [x] Phase 7.3 — Confidence scoring (DONE)
- [x] Phase 7.4 — Component context (DONE)
- [x] Phase 5.4-5.8 — Eval baseline (DONE — 2026-03-09)
- [x] Existing skill: `html-email-innovation.skill` (668 lines)
