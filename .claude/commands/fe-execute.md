# Frontend Execute — Execute Frontend Implementation Plan

Execute a frontend implementation plan step by step.

## Security Verification (scoped to files changed in this step)
- No `(x as any)` casts — use proper TypeScript types or module augmentation
- No `dangerouslySetInnerHTML` without DOMPurify
- API calls use `authFetch` (not raw `fetch`)
- Data from storage (sessionStorage/localStorage) validated with runtime type guards
- Token expiry derived from JWT `exp` claim, not hardcoded
- Only check the files you're changing — full sweep is `/fe-validate`

## Rules
- Run `cd cms && pnpm --filter web lint:fix && pnpm --filter web format` after creating/modifying frontend files (ESLint: security, a11y, React hooks + Prettier with Tailwind class sorting)
- Use semantic Tailwind tokens (not primitive colors like `text-gray-500`)
- Follow React 19 patterns (no setState in useEffect, no component defs inside components)
- Use `authFetch` for API calls, SWR for data fetching
- All detail views use Dialog (not Sheet)
- Never use `as any` — if types are wrong, fix the type declarations

@_shared/tailwind-token-map.md
@_shared/frontend-security.md
