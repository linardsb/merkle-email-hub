# Frontend Preflight Check — Scan & Fix Known Friction Patterns

Run this **before** `/fe-execute` to catch and auto-fix patterns that historically cause fix cycles.

## Step 1: Parse the Plan

Read the implementation plan file (user specifies path, or find the most recent `.agents/plans/*.md`).
Extract:
- All file paths listed under "Files to Create/Modify" or "Implementation Steps"
- All components/hooks/functions being added or modified
- What changes each file is getting (new props, new API fields, new hook return values)

## Step 2: Scan & Fix Fragile Patterns in Related Tests

For each target file `cms/apps/web/src/{path}/{file}.tsx`, find test files:

```bash
find cms/apps/web/src/ -path "*__tests__*" -name "*.test.tsx" -o -name "*.test.ts" 2>/dev/null
```

### 2a: Hardcoded Count Assertions
```
Grep pattern: "toHaveLength\(\d+\)|\.length\)\.toBe\(\d+\)|expect.*==.*\d+"
```
**Assess:** Cross-reference with the plan — will this count change?

**Auto-fix if affected:** Replace with flexible assertion:
- `expect(items).toHaveLength(5)` → `expect(items.length).toBeGreaterThanOrEqual(5)`

### 2b: Snapshot Tests
```
Grep pattern: "toMatchInlineSnapshot|toMatchSnapshot"
```
**Assess:** Does the plan modify the component's render output?

**Auto-fix if affected:** Delete the stale snapshot so it regenerates on next test run:
- For `toMatchInlineSnapshot`: remove the inline snapshot string argument
- For `toMatchSnapshot`: delete the corresponding `.snap` file entry (or flag for manual `pnpm test -- -u`)

### 2c: Mock Return Values with Fixed Shape
```
Grep pattern: "mockReturnValue\(|mockResolvedValue\("
```
**Assess:** Does the plan change the API response shape or hook return type?

**Auto-fix if affected:** Add the new fields to the mock return value with sensible defaults matching the plan's new schema.

## Step 3: Scan & Fix Target Files for Fragile Patterns

For each file being **modified** (not created):

### 3a: `as any` Casts
```
Grep pattern: "as any"
```
**Assess:** Will the plan change the type that `as any` is hiding?

**Auto-fix if affected:** Replace `as any` with the correct type from the plan. If the correct type isn't clear, replace with `as unknown as CorrectType` and add a `// TODO: remove cast after types stabilize` comment.

### 3b: Destructured Props/Hook Returns
```
Grep pattern: "^\s*const \{.*\} = (props|use\w+)"
```
**Assess:** Does the plan add new props or change hook return shape?

**Auto-fix if affected:** Add the new destructured fields at each callsite where they're needed by the plan.

### 3c: API Response Types
```
Grep pattern: "interface.*Response|type.*Response"
```
**Assess:** Does the plan change backend API responses?

**Auto-fix if affected:** Add the new fields to the TypeScript interface/type to match the backend changes described in the plan.

### 3d: Type Assertions
```
Grep pattern: "as [A-Z]\w+[>\]]"
```
**Assess:** Will the underlying type change?

**Auto-fix if affected:** Update the assertion to the new type, or remove it if TypeScript can now infer correctly.

## Step 4: TypeScript Baseline

Run tsc on the frontend to capture the **before** error count:

```bash
cd cms && pnpm --filter web tsc --noEmit 2>&1 | tail -10
```

Save the error count. After `/fe-execute`, compare against this baseline.

## Step 5: Report

Output a preflight report as a markdown table:

```
## Frontend Preflight Report for {plan name}

### Fixes Applied

| File | Line | Pattern | What Changed |
|------|------|---------|--------------|
| use-builder.test.ts | 42 | `toHaveLength(12)` | Changed to `toBeGreaterThanOrEqual(12)` — plan adds components |
| types/api.ts | 15 | `interface QAResponse` | Added `newField: string` — matches backend change in plan |
| BuilderCanvas.test.tsx | 87 | `mockReturnValue({...})` | Added `newProp` to mock — plan changes hook return |

### Patterns Found (Safe — No Fix Needed)

| File | Line | Pattern | Why Safe |
|------|------|---------|----------|
| use-presence.test.ts | 20 | `toHaveLength(3)` | Plan doesn't affect presence data |

### TypeScript Baseline
- Frontend: {N} errors before implementation (all pre-existing)
- Run `pnpm --filter web tsc --noEmit` after /fe-execute — new errors above {N} are regressions

### Status
{If fixes applied}: {N} patterns auto-fixed. Proceed with /fe-execute.
{If clean}: No friction patterns found. Proceed with /fe-execute.
```

## Rules

- **Auto-fix** any pattern that WILL break based on the plan's changes
- **Skip** patterns that are unaffected by the plan (mark as "safe" in report)
- Use judgement: read the plan to understand what's changing before deciding fix vs safe
- Run `cd cms && pnpm --filter web lint:fix && pnpm --filter web format` after any fixes
- Do NOT run the full test suite — only scan and fix test file contents
- Focus on the specific files in the plan, not the entire codebase
- Report everything (fixes applied + safe patterns) for full visibility
