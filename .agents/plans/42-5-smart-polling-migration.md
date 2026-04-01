# Plan: 42.5 Migrate High-Traffic Hooks to Smart Polling + Constants

## Context

Replace hardcoded `refreshInterval`/`dedupingInterval` values in SWR hooks with `useSmartPolling` (42.3) and centralized constants from `swr-constants.ts` (42.4). Reduces server load from background/unfocused tabs.

## Research Summary

**useSmartPolling signature:** `(baseInterval: number) => number` — returns `baseInterval` when visible, `baseInterval * 1.5` when blurred, `0` when hidden. Returns `0` if input is `0`.

**Constants available** (`cms/apps/web/src/lib/swr-constants.ts`):
- `POLL`: `realtime=3000`, `frequent=5000`, `moderate=15000`, `status=30000`, `background=60000`, `off=0`
- `DEDUP`: `standard=5000`, `reference=300000`, `static=600000`
- `SWR_PRESETS`: `polling` (`dedupingInterval: 5000, revalidateOnFocus: false`), `static`, `reference`, `interactive`

**Actual hooks with hardcoded polling intervals (8 hooks in 6 files):**

| # | File | Hook | Current | Target | Conditional? |
|---|------|------|---------|--------|-------------|
| 1 | use-renderings.ts:40 | `useRenderingTestPolling` | `3000` | `POLL.realtime` | Yes (pending/processing) |
| 2 | use-design-sync.ts:176 | `useDesignImport` | `2000` | `POLL.realtime` | Yes (polling flag) |
| 3 | use-mcp.ts:36 | `useMCPStatus` | `30_000` | `POLL.status` | No |
| 4 | use-mcp.ts:43 | `useMCPConnections` | `15_000` | `POLL.moderate` | No |
| 5 | use-ontology.ts:16 | `useOntologySyncStatus` | `60_000` | `POLL.background` | No |
| 6 | use-penpot.ts:10 | `usePenpotConnections` | `60_000` | `POLL.background` | No |
| 7 | use-plugins.ts:12 | `usePlugins` | `60_000` | `POLL.background` | No |
| 8 | use-plugins.ts:16 | `usePluginHealthSummary` | `60_000` | `POLL.background` | No |

**NOT migrated (no active polling):** `use-blueprint-runs.ts` (no refreshInterval), `use-qa.ts` (no refreshInterval), `use-approvals.ts` (no refreshInterval), `use-email-clients.ts` (dedup only, no polling — already uses `dedupingInterval: 300_000` = `DEDUP.reference`).

**Design note:** `useDesignImport` currently polls at 2000ms. Bumping to `POLL.realtime` (3000ms) is acceptable — design imports are not latency-sensitive at the 1s granularity.

## Test Landscape

**Existing test files:**
- `hooks/__tests__/use-smart-polling.test.ts` — 8 test cases, full visibility state coverage
- `hooks/__tests__/use-data-hooks-2.test.ts` — covers renderings (`refreshInterval` presence), design-sync (`refreshInterval: 2000`), email-clients
- `hooks/__tests__/use-data-hooks-3.test.ts` — covers blueprint-runs
- `hooks/__tests__/use-data-hooks.test.ts` — covers QA, approvals

**No dedicated tests for:** use-mcp, use-plugins, use-ontology, use-penpot

**Test pattern:** All hook tests mock `swr` and `@/lib/swr-fetcher` with `vi.mock()`, use `renderHook()`, assert on `mockUseSWR.mock.calls[0][2]` for SWR options. Dynamic imports in `beforeEach`.

**Key test issue:** Existing tests assert `options.refreshInterval` presence or exact hardcoded values. After migration, `refreshInterval` will be a number from `useSmartPolling` — need to mock `useSmartPolling` in existing tests OR update assertions.

## Type Check Baseline

| Check | Count |
|-------|-------|
| TypeScript errors | 1 (pre-existing: `Blocks` not found in components/page.tsx) |
| ESLint | N/A (broken — `next lint` removed in Next.js 16) |

## Files to Modify

### Hook migrations (6 files)
- `cms/apps/web/src/hooks/use-renderings.ts` — add `useSmartPolling(POLL.realtime)` with conditional
- `cms/apps/web/src/hooks/use-design-sync.ts` — add `useSmartPolling` with polling flag conditional
- `cms/apps/web/src/hooks/use-mcp.ts` — replace 2 hardcoded intervals
- `cms/apps/web/src/hooks/use-ontology.ts` — replace 1 hardcoded interval
- `cms/apps/web/src/hooks/use-penpot.ts` — replace 1 hardcoded interval
- `cms/apps/web/src/hooks/use-plugins.ts` — replace 2 hardcoded intervals

### Dedup-only migration (1 file)
- `cms/apps/web/src/hooks/use-email-clients.ts` — replace `dedupingInterval: 300_000` with `...SWR_PRESETS.reference`

### Test updates (1 file) + new tests (1 file)
- `cms/apps/web/src/hooks/__tests__/use-data-hooks-2.test.ts` — update renderings/design-sync assertions
- `cms/apps/web/src/hooks/__tests__/use-smart-polling-migration.test.ts` — new: 8 integration tests (one per migrated hook)

## Implementation Steps

### Step 1: Unconditional hooks (4 files, 6 hooks)

**use-mcp.ts** — add imports, replace both intervals:
```typescript
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

export function useMCPStatus() {
  const interval = useSmartPolling(POLL.status);
  return useSWR<MCPServerStatus>("/api/v1/mcp/status", fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
}

export function useMCPConnections() {
  const interval = useSmartPolling(POLL.moderate);
  return useSWR<MCPConnection[]>("/api/v1/mcp/connections", fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
}
```

**use-ontology.ts** — same pattern with `POLL.background`.

**use-penpot.ts** — same pattern with `POLL.background`.

**use-plugins.ts** — both `usePlugins` and `usePluginHealthSummary` with `POLL.background`. Note: two hooks in one file means two `useSmartPolling` calls — each hook gets its own.

### Step 2: Conditional hooks (2 files)

**use-renderings.ts** — `useRenderingTestPolling`:
```typescript
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

export function useRenderingTestPolling(testId: number | null) {
  const interval = useSmartPolling(POLL.realtime);
  return useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/rendering/tests/${testId}` : null,
    fetcher,
    {
      refreshInterval: (data: RenderingTest | undefined) =>
        data && (data.status === "pending" || data.status === "processing")
          ? interval
          : POLL.off,
      ...SWR_PRESETS.polling,
    },
  );
}
```

**use-design-sync.ts** — `useDesignImport`:
```typescript
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

export function useDesignImport(importId: number | null, polling?: boolean) {
  const interval = useSmartPolling(polling ? POLL.realtime : POLL.off);
  return useSWR<DesignImport>(
    importId ? `/api/v1/design-sync/imports/${importId}` : null,
    fetcher,
    { refreshInterval: interval, ...SWR_PRESETS.polling },
  );
}
```

### Step 3: Dedup-only migration

**use-email-clients.ts**:
```typescript
import { SWR_PRESETS } from "@/lib/swr-constants";

export function useEmailClients() {
  return useSWR<EmailClientResponse[]>(
    "/api/v1/ontology/clients",
    fetcher,
    { ...SWR_PRESETS.reference },
  );
}
```

### Step 4: Update existing tests

**use-data-hooks-2.test.ts** — renderings test currently asserts `options.refreshInterval` is defined. After migration, `refreshInterval` is still a function (callback form) — assertion still passes. But if it asserts exact value `2000` for design-sync, update to check it's a number (from `useSmartPolling`).

Need to mock `useSmartPolling` in data-hooks-2 tests:
```typescript
vi.mock("@/hooks/use-smart-polling", () => ({
  useSmartPolling: vi.fn((base: number) => base), // passthrough in tests
}));
```

### Step 5: New migration integration tests

Create `cms/apps/web/src/hooks/__tests__/use-smart-polling-migration.test.ts`:

Test each migrated hook verifies:
1. Correct `POLL.*` constant passed to `useSmartPolling`
2. SWR options include `revalidateOnFocus: false` (from preset)
3. Conditional hooks: verify polling activates/deactivates correctly

```typescript
// Pattern for each unconditional hook:
it("useMCPStatus uses POLL.status via useSmartPolling", async () => {
  const { useMCPStatus } = await import("../use-mcp");
  renderHook(() => useMCPStatus());
  expect(mockUseSmartPolling).toHaveBeenCalledWith(30_000); // POLL.status
  const options = mockUseSWR.mock.calls[0][2];
  expect(options.refreshInterval).toBe(30_000);
  expect(options.revalidateOnFocus).toBe(false);
});

// Pattern for conditional hooks:
it("useRenderingTestPolling uses POLL.realtime conditionally", async () => {
  const { useRenderingTestPolling } = await import("../use-renderings");
  renderHook(() => useRenderingTestPolling(1));
  expect(mockUseSmartPolling).toHaveBeenCalledWith(3_000); // POLL.realtime
  const options = mockUseSWR.mock.calls[0][2];
  // refreshInterval is a callback — test with pending data
  expect(options.refreshInterval({ status: "pending" })).toBe(3_000);
  expect(options.refreshInterval({ status: "completed" })).toBe(0);
});
```

8 tests total: 1 per hook (renderings, design-sync, mcp-status, mcp-connections, ontology, penpot, plugins, plugin-health).

## Preflight Warnings

1. **use-data-hooks-2.test.ts:~line 400** — asserts `options.refreshInterval` for design-sync import is exactly `2000`. Must update to `3000` (POLL.realtime) or mock useSmartPolling as passthrough.
2. **use-renderings.ts** — uses callback form of `refreshInterval`. The hook value from `useSmartPolling` is captured in closure — React will re-render when visibility changes, providing updated interval. This is correct behavior.
3. **use-plugins.ts** — two hooks with polling means two `useSmartPolling` calls in the same file but different functions — no hook rules violation since each is in its own function component/hook.

## Security Checklist

- [x] No `(x as any)` casts
- [x] API calls use `authFetch` (via fetcher)
- [x] No `dangerouslySetInnerHTML`
- [x] No new attack surface — client-side polling config only
- [x] Server sees fewer requests from background tabs

## Verification

- [ ] `pnpm --filter web tsc --noEmit` — errors <= 1 (baseline)
- [ ] All existing hook tests pass (use-data-hooks-*.test.ts)
- [ ] New migration tests pass (use-smart-polling-migration.test.ts)
- [ ] Grep confirms no hardcoded `refreshInterval: \d` in migrated files
- [ ] Grep confirms no hardcoded `dedupingInterval` in use-email-clients.ts
- [ ] All 7 migrated files import from `@/hooks/use-smart-polling` and `@/lib/swr-constants`
