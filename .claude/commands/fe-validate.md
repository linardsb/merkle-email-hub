# Frontend Validate — Run All Frontend Quality Checks

Run the frontend validation pyramid:

## Level 1: TypeScript
```bash
cd cms && pnpm --filter web tsc --noEmit
```

## Level 2: Lint
```bash
cd cms && pnpm --filter web lint
```

## Level 3: Build
```bash
cd cms && pnpm --filter web build
```

## Level 4: Design System
Check that no primitive Tailwind colors are used (should use semantic tokens).

## Level 5: i18n
Check that all user-visible text uses translation keys.

Report results for each level. Fix any issues found automatically.
