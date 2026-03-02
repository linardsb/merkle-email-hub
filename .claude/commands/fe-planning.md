# Frontend Planning — Create Implementation Plan

Research the codebase and create a self-contained frontend implementation plan.

## Process

1. **Understand the task** — Read the user's requirements carefully
2. **Research existing code** — Find related pages, components, hooks, and patterns
3. **Identify files to create/modify** — List every file that needs changes
4. **Write the plan** — Step-by-step instructions that another agent can follow

## Plan Format

Save the plan to `.agents/plans/{feature-name}.md` with this structure:

```markdown
# Plan: {Feature Name}

## Context
{Why this change is needed}

## Files to Create/Modify
- `cms/apps/web/src/app/(dashboard)/{route}/page.tsx` — {what changes}
- `cms/apps/web/src/hooks/use-{domain}.ts` — {what changes}
- `cms/apps/web/messages/en.json` — {what i18n keys to add}
- ...

## Implementation Steps
1. {Step with exact code or clear instructions}
2. ...

## Verification
- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] All user-visible text uses `useTranslations()`
- [ ] Semantic Tailwind tokens only (no primitive colors)
- [ ] Auth/RBAC works correctly
```

## Rules
- Use semantic Tailwind tokens — NEVER primitive colors (`text-gray-500`, `bg-blue-600`)
- Use `useTranslations()` hook for ALL user-visible text
- Use `authFetch` for API calls, SWR hooks for data fetching
- React 19: No setState in useEffect, no component defs inside components
- Dialog for detail views (not Sheet). Widths: detail=28rem, forms=32rem
- Named container sizes collapse in Tailwind v4 — use explicit rem values
- Route protection via middleware.ts ROLE_PERMISSIONS map
- Preview iframes must use sandbox attribute (no allow-scripts)

@_shared/tailwind-token-map.md
@_shared/frontend-security.md
