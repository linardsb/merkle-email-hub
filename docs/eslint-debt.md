# ESLint Debt

Rules currently demoted in `cms/apps/web/eslint.config.mjs` under the
**Tracked debt** config block. Each entry below records the violation count at
the time of demotion (Phase 1b — frontend tooling spike) and the ratchet target.
Re-promote one rule at a time as backlog is paid down.

## Why these are demoted

Phase 1b's goal was to **remove `|| true` wrappers** from CI/pre-commit hooks
and run real ESLint/Prettier gates. The frontend lint had been silently
broken for some time (Next.js 16 dropped `next lint --max-warnings`, Prettier
was not installed). When it started running, 165 findings surfaced. Real bug-
class violations (eqeqeq false positives via `null:"ignore"`,
`react-hooks/rules-of-hooks` actual crash bug, duplicate imports, no-alert,
prefer-const) were fixed in the same PR. The remaining items are tech debt
that does not need to block CI today; demoting them lets the gate flip from
advisory (`|| true`) to enforced.

## Rules demoted to off

| Rule | Sites | Notes / Ratchet target |
|---|---:|---|
| `@typescript-eslint/no-unused-vars` | 19 | Many are dead imports/vars; some are intentional. Triage: underscore-prefix (`_unused`) or delete. Re-enable as `error` once 0 remain. |
| `@next/next/no-img-element` | 15 | Migrate `<img>` → `next/image` where the use case is layout/optimization. Some sites are inside `dangerouslySetInnerHTML` previews and unavoidable. |
| `react-hooks/exhaustive-deps` | 12 | Often false positives where the omitted dep is intentionally stale. Audit each site, add a one-line `// eslint-disable-next-line react-hooks/exhaustive-deps -- <reason>` comment, then re-enable rule. |
| `@typescript-eslint/ban-ts-comment` | 12 | `@ts-ignore` / `@ts-expect-error` without justification. Add `--<reason>` to each, then re-enable as `error` with `ts-expect-error: { descriptionFormat }`. |
| `jsx-a11y/label-has-associated-control` | 9 | A11y audit follow-up — labels missing `htmlFor` or wrapped input. |
| `jsx-a11y/click-events-have-key-events` | 7 | Replace clickable `<div>` with `<button>` or add `onKeyDown`. |
| `jsx-a11y/no-static-element-interactions` | 6 | Same root cause — non-interactive elements with click handlers. |
| `security/detect-non-literal-regexp` | 7 | Audit each `RegExp` constructor for taint; prefer literal regex. |
| `security/detect-unsafe-regex` | 3 | ReDoS-prone patterns; rewrite or document boundaries. |
| `jsx-a11y/no-autofocus` | 2 | Modal focus UX — replace with imperative ref-based focus on dialog open. |
| `react/no-danger` | 2 | Both sites already wrapped in DOMPurify — audit the input path then re-enable with site-by-site disable comments. |
| `jsx-a11y/role-supports-aria-props` | 1 | Spot fix. |
| `jsx-a11y/no-noninteractive-tabindex` | 1 | Spot fix. |
| `jsx-a11y/no-noninteractive-element-interactions` | 1 | Spot fix. |
| `jsx-a11y/media-has-caption` | 1 | Add `<track kind="captions">` or document the audio-only context. |

**Total demoted findings:** 106 (57 errors + 49 warnings, ESLint 9.39.4 + typescript-eslint 8.x baseline)

## Already-fixed bug-class items (Phase 1b)

These were fixed mechanically in the same PR rather than tracked as debt:

| Rule | Original count | Resolution |
|---|---:|---|
| `react-hooks/rules-of-hooks` | 4 | Real crash bug — `useMemo` calls after early return in `rendering-dashboard.tsx:101-130`. Hooks moved above the early return. |
| `eqeqeq` | 18 | All `!= null` / `== null` (intentional null+undefined check). Rule reconfigured with `{ null: "ignore" }`. |
| `no-duplicate-imports` | 25 | 20 were `import type` + `import` from same module (TS pattern). Rule reconfigured with `{ allowSeparateTypeImports: true }`. 5 real duplicates merged. |
| `no-alert` | 3 | `confirm()` calls — UX pattern for delete confirms. Inline `// eslint-disable-next-line no-alert -- replace with modal confirm` comments added. |
| `prefer-const` | 1 | `let data` → `const data` after assignment in `use-chat.ts:230`. |
| `no-implicit-coercion` | 6 | Auto-fixed by `eslint --fix`. |

## Inline `// eslint-disable-next-line` directives

11 pre-existing inline disables for now-demoted rules surface as
"Unused eslint-disable directive" warnings. Leave them in place — when the
rule is re-promoted, the directive becomes load-bearing again. They are
non-blocking advisory warnings under the current `eslint .` (no
`--max-warnings 0`) gate.

## Re-enabling a rule

1. Pick a rule from the table above.
2. Run `pnpm --filter @email-hub/web exec eslint . --rule '<rule>:error'`
   to surface the current violation list.
3. Fix mechanically where possible; add inline `// eslint-disable-next-line <rule> -- <reason>` for site-specific exemptions.
4. Remove the rule's `"off"` line from the **Tracked debt** block in
   `cms/apps/web/eslint.config.mjs`.
5. Confirm `pnpm --filter @email-hub/web lint` exits 0.
6. Update this file: move the rule from "demoted" to a "resolved" section.
