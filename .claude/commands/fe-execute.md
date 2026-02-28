# Frontend Execute — Execute Frontend Implementation Plan

Execute a frontend implementation plan step by step.

## Rules
- Use semantic Tailwind tokens (not primitive colors like `text-gray-500`)
- Use `useTranslations()` for all user-visible text
- Follow React 19 patterns (no setState in useEffect, no component defs inside components)
- Use `authFetch` for API calls, SWR for data fetching
- All detail views use Dialog (not Sheet)

@_shared/tailwind-token-map.md
