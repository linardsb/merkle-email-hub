# Frontend Ship — Full Quality Pipeline

Run the complete validate → review → fix → validate pipeline in one pass.

Use after completing a feature implementation (`/fe-execute`) to catch and fix all issues before commit.

## Phase 1: Initial Validation

Run `/fe-validate` (all 4 levels). If everything passes cleanly, proceed. If there are failures, fix them before moving on.

## Phase 2: Code Review

Run `/review` against the changed files. Check applicable quality standards:
1. Type Safety
2. Security
3. Architecture
4. Performance
5. API Design (if touching API hooks/fetchers)

Report all findings with severity (critical, warning, suggestion).

## Phase 3: Fix Review Findings

Run `/fe-code-review-fix` for **critical** findings from Phase 2 that violate codified project rules (CLAUDE.md, tsconfig.json, .claude/rules/). Warnings are optional — fix only if they match a documented convention and are trivial (<3 lines). Do NOT fix subjective opinions that don't reference a specific project rule.

Skip this phase if Phase 2 found zero critical issues.

@_shared/tailwind-token-map.md
@_shared/frontend-security.md

## Phase 4: Final Validation

Run `/fe-validate` again to confirm all fixes are clean. This is the gate — nothing ships if this fails.

## Output

End with a single summary table:

```
| Phase | Result | Details |
|-------|--------|---------|
| 1. Validate | PASS/FAIL | errors found / clean |
| 2. Review | N critical, N warning, N suggestion | key findings |
| 3. Fix | N fixes applied | or "skipped — no issues" |
| 4. Validate | PASS/FAIL | final gate |
```

## Rules

- Do NOT skip phases — run all 4 in order
- Do NOT commit — this pipeline validates only. User runs `/commit` separately
- If Phase 4 fails after fixes, iterate (fix → validate) until clean, max 3 rounds
- If a fix requires architectural changes, stop and recommend `/fe-planning` instead
