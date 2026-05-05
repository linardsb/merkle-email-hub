# Preflight Check — Scan & Fix Known Friction Patterns

Run this **before** `/be-execute` to catch and auto-fix patterns that historically cause fix cycles.

## Step 1: Parse the Plan

Read the implementation plan file (user specifies path, or find the most recent `.agents/plans/*.md`).
Extract:
- All file paths listed under "Files to Create/Modify" or "Implementation Steps"
- All function/class names being added or modified
- What changes each function/file is getting (new parameters, new return fields, new items)

## Step 2: Deferred-Items Cross-Reference

Grep `.agents/deferred-items.json` for entries that overlap the plan. The convention (`.claude/rules/deferred-items.md`) requires this before any new plan or execution touching an existing phase or file — entries cataloged here often point to real bugs that haven't surfaced yet.

### 2a: Match by phase

If the plan name or content references a phase id (e.g. `tech-debt-03`, `phase-50.7`):

```bash
jq -r --arg phase "<plan-phase-or-prefix>" '.items[] | select(.status == "deferred" and (.phase | startswith($phase))) | "\(.id) — \(.title)"' .agents/deferred-items.json
```

### 2b: Match by code_refs overlap

For each file in the plan's "Files to Create/Modify" list:

```bash
jq -r --arg file "<file-path>" '.items[] | select(.status == "deferred" and (.code_refs[]? | contains($file))) | "\(.id) — \(.title) [refs: \(.code_refs | join(", "))]"' .agents/deferred-items.json
```

Run once per target file; dedupe matches by `id`.

### 2c: Surface in the report

Every match goes into the "Deferred Items Touching This Plan" table in Step 6 — including `id`, `severity`, `summary` (one-line), and `closes_when`. Empty section when no matches — never silent. The agent (or user) must decide per match whether the new work should:
- **close** the entry (do the fix as part of this plan; flip `status` to `closed` after `/be-execute`),
- **avoid** it (leave alone but note the constraint), or
- **carry forward** (add a note linking the new plan to the existing entry).

This step is informational — it does NOT auto-fix. Surfacing is the deliverable.

## Step 3: Scan & Fix Hardcoded Assertions in Related Tests

For each target file `app/{feature}/{file}.py`, find its test files:

```bash
find app/{feature}/tests/ -name "test_*.py" -type f 2>/dev/null
find tests/ -name "test_{file}*.py" -type f 2>/dev/null
```

### 3a: Hardcoded Count Assertions
```
Grep pattern: "== \d+|len\(.+\) == \d+|assert.*count.*== \d+|assert.*\.count\("
```
**Assess:** Cross-reference with the plan — will this count change? (e.g., plan adds a new token → `== 14` becomes wrong). If the count is unaffected by the plan's changes, mark as "safe" and skip.

**Auto-fix if affected:** Replace exact count with `>=` to tolerate additions:
- `assert len(results) == 14` → `assert len(results) >= 14`
- `assert result.count("<td") == 5` → `assert result.count("<td") >= 5`

### 3b: Tuple Unpacking
```
Grep pattern: "^\s+\w+,\s*\w+.*=\s*\w+\("
```
**Assess:** Does the plan change the return signature of the unpacked function?

**Auto-fix if affected:** Add the new variable to the unpacking:
- `a, b, c, d = _parse_variables(...)` → `a, b, c, d, e = _parse_variables(...)` (matching the new return signature from the plan)

### 3c: Hardcoded String Assertions
```
Grep pattern: 'assert.*==.*"[^"]{20,}"'
```
**Assess:** Will the plan change the output string?

**Auto-fix if affected:** Replace with `in` check on the critical substring:
- `assert result == "long exact string..."` → `assert "critical_part" in result`

## Step 4: Scan & Fix Target Files for Fragile Patterns

For each file being **modified** (not created):

### 4a: New Parameter Propagation
For any function whose signature is changing (new parameter added by the plan), `Grep` for all callsites across the codebase.

**Auto-fix:** If the new parameter has a default value (e.g., `slot_counter: dict | None = None`), no callsite changes needed — just verify. If it does NOT have a default, add the parameter with a sensible default to each callsite, or add a default to the function signature itself.

### 4b: Return Tuple Expansion
```
Grep pattern: "-> tuple\[|return \w+, \w+"
```
If the plan adds fields to a return tuple, find all callers.

**Auto-fix:** Update the unpacking at each callsite to include the new field with an appropriate variable name. Add `_ =` for unused fields if the caller doesn't need the new value.

### 4c: Pydantic Field Defaults Without Type Annotations
```
Grep pattern: "Field\(default_factory="
```
**Auto-fix:** If the plan adds new `Field(default_factory=...)`, ensure explicit type annotation is present (required for pyright strict). Add the annotation if missing.

## Step 5: Pyright Baseline

Run pyright on only the target files to capture the **before** error count:

```bash
uv run pyright {space-separated target files} 2>&1 | tail -5
```

Save the error count. After `/be-execute`, compare against this baseline to distinguish pre-existing errors from newly introduced ones.

## Step 6: Report

Output a preflight report as a markdown table:

```
## Preflight Report for {plan name}

### Deferred Items Touching This Plan

| ID | Severity | Title | Closes-When | Action |
|----|----------|-------|-------------|--------|
| tech-debt-03-tenant-isolation-regression-harness | soft | Cross-entity tenant-isolation regression test self-skips | A db: AsyncSession fixture lands and the test runs without TEST_DATABASE__URL gating | Carry forward — outside this plan's scope |

(Empty table if no matches — print "No deferred items touch the files in this plan." Never silent.)

### Fixes Applied

| File | Line | Pattern | What Changed |
|------|------|---------|--------------|
| test_service.py | 42 | `assert len(results) == 14` | Changed to `>= 14` — plan adds new tokens |
| test_dark_mode.py | 87 | `a, b, c, d = _parse_variables(...)` | Added 5th variable `e` — plan adds gradients field |
| converter.py | 655 | `node_to_email_html(...)` recursive call | Will need `slot_counter` threaded — plan adds it with default |

### Patterns Found (Safe — No Fix Needed)

| File | Line | Pattern | Why Safe |
|------|------|---------|----------|
| test_penpot_converter.py | 736 | `assert result.count("<p") == 2` | Plan adds data-* attrs, <p tag count unchanged |
| test_token_transforms.py | 20 | `result, warnings = validate_and_transform(...)` | Signature not changing |

### Pyright Baseline
- Target files: {N} errors before implementation (all pre-existing)
- Run `uv run pyright {files}` after /be-execute — new errors above {N} are regressions

### Status
{If fixes applied}: {N} patterns auto-fixed. Proceed with /be-execute.
{If clean}: No friction patterns found. Proceed with /be-execute.
```

## Rules

- **Auto-fix** any pattern that WILL break based on the plan's changes
- **Skip** patterns that are unaffected by the plan (mark as "safe" in report)
- Use judgement: read the plan to understand what's changing before deciding fix vs safe
- Run `uv run ruff format {changed_files}` after any fixes to maintain formatting
- Do NOT run the full test suite — only scan and fix test file contents
- Focus on the specific files in the plan, not the entire codebase
- Report everything (fixes applied + safe patterns) for full visibility
