# Frontend Validate — Run All Frontend Quality Checks

## Token Efficiency Note
If the project is indexed via jcodemunch, use `search_symbols` and `get_file_outline` to locate design system and i18n violations in Levels 3-4 instead of grepping entire file trees.

Run the frontend validation pyramid:

## Level 1: TypeScript
```bash
cd cms && pnpm --filter @merkle-email-hub/web exec tsc --noEmit
```

## Level 2: Build
```bash
cd cms && pnpm build
```
This runs turbo build across all packages (SDK + web). Catches TypeScript errors, import issues, and SSR problems.

## Level 3: Design System
Grep for primitive Tailwind colors in `cms/apps/web/src/**/*.tsx`. No matches = pass.
Pattern: `(text|bg|border|ring)-(gray|slate|zinc|red|blue|green|...)-\d`
Should use semantic tokens (`text-foreground`, `bg-card`, `border-border`, etc.)

## Level 4: i18n
Grep for hardcoded English strings in component JSX in `cms/apps/web/src/**/*.tsx`.
All user-visible text must use `useTranslations()` / `t("key")`.

## Notes
- No ESLint config exists yet — skip lint level until configured
- Fix any issues found automatically before reporting results
