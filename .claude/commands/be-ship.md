# Backend Ship — Full Quality Pipeline

Run the complete validate → review → fix → validate pipeline in one pass.

Use after completing a feature implementation (`/be-execute`) to catch and fix all issues before commit.

## Phase 1: Initial Validation

Run `/be-validate` (all 6 levels). If everything passes cleanly, proceed. If there are failures, fix them before moving on.

## Phase 2: Code Review

Run `/review` against the changed files. Check all 8 quality standards:
1. Type Safety
2. Error Handling
3. Security
4. Logging
5. Testing
6. Architecture
7. Performance
8. API Design

Report all findings with severity (critical, warning, suggestion).

## Phase 3: Fix Review Findings

Run `/be-code-review-fix` for any critical or warning findings from Phase 2. Suggestions are optional — fix only if trivial (<3 lines).

Skip this phase if Phase 2 found zero critical/warning issues.

@_shared/python-anti-patterns.md

## Phase 4: Final Validation

Run `/be-validate` again to confirm all fixes are clean. This is the gate — nothing ships if this fails.

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
- If a fix requires architectural changes, stop and recommend `/be-planning` instead
