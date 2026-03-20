# Plan: Fix Design Sync Remove Not Working

## Context
In demo mode, clicking "Remove" on a design sync connection returns `{ success: true }` but never removes the connection from the demo store or filters it from the static demo data. The connection persists on refresh.

## Files to Modify
- `cms/apps/web/src/lib/demo/demo-store.ts` — add `removeDesignConnection()` and `isDesignConnectionDeleted()` with a deleted-IDs set
- `cms/apps/web/src/lib/demo/mutation-resolver.ts` — extract ID from body and call `demoStore.removeDesignConnection()`
- `cms/apps/web/src/lib/demo/resolver.ts` — filter out deleted connections from GET response

## Implementation Steps

1. **demo-store.ts**: Add a `deletedDesignConnectionIds` Set and methods:
   - `removeDesignConnection(id)` — splice from runtime array + add to deleted set
   - `isDesignConnectionDeleted(id)` — check deleted set (for filtering static data)

2. **mutation-resolver.ts**: In the `/api/v1/design-sync/connections/delete` handler, extract `id` from `_body` and call `demoStore.removeDesignConnection(id)`

3. **resolver.ts**: Filter the GET response to exclude deleted IDs using `demoStore.isDesignConnectionDeleted()`

## Verification
- [ ] Click Remove → connection disappears from list
- [ ] `make check-fe` passes
