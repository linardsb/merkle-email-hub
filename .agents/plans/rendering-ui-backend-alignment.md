# Plan: Rendering UI — Backend Alignment & Enhancement

## Context

The `/renderings` page and 5 components were built with demo-mode mock data. Now that backend task 4.4 (Litmus/EoA integration) is complete, the frontend needs to:

1. **Align types and API paths** with actual backend schemas
2. **Wire up visual regression comparison** (backend supports `POST /compare`, no frontend UI yet)
3. **Add async test polling** (backend tests are async: queued → processing → complete)
4. **Fix submit dialog** to match backend API (requires `html` input, not just `provider` + `client_ids`)
5. **Add pagination controls** (backend supports pagination, frontend is hardcoded to 10)

### Key Backend vs Frontend Mismatches

| Aspect | Backend (actual) | Frontend (current) |
|--------|------------------|--------------------|
| Route prefix | `/api/v1/rendering/` | `/api/v1/renderings/` (extra 's') |
| Submit requires | `html` (string, required), `subject`, `clients` (string[]) | `provider`, `client_ids` |
| Test response | `external_test_id`, `clients_requested` (int), `clients_completed` (int), `screenshots` (ScreenshotResult[]) | `template_name`, `clients_requested` (string[]), `results` (RenderingResult[]), `compatibility_score` |
| Screenshot model | `client_name`, `screenshot_url`, `os`, `category`, `status` | `client_id`, `status`, `screenshot_url`, `load_time_ms`, `issues` |
| Compare request | `baseline_test_id`, `current_test_id` | `test_id_baseline`, `test_id_current` |
| Missing endpoints | — | `/clients`, `/tests/latest`, `/summary` (frontend hooks exist, no backend) |

## Files to Create/Modify

1. `cms/apps/web/src/types/rendering.ts` — Align all types with backend schemas
2. `cms/apps/web/src/hooks/use-renderings.ts` — Fix API paths, remove non-existent endpoints, add polling
3. `cms/apps/web/src/app/(dashboard)/renderings/page.tsx` — Adapt to new types, add pagination, remove client endpoint dependency
4. `cms/apps/web/src/components/renderings/rendering-test-dialog.tsx` — Add HTML input field, align request schema
5. `cms/apps/web/src/components/renderings/rendering-test-list.tsx` — Adapt to `screenshots` instead of `results`, handle async status
6. `cms/apps/web/src/components/renderings/rendering-stats-cards.tsx` — Compute stats from aligned types
7. `cms/apps/web/src/components/renderings/rendering-screenshot-dialog.tsx` — Adapt to `ScreenshotResult` shape
8. `cms/apps/web/src/components/renderings/client-compatibility-matrix.tsx` — Remove dependency on `/clients` endpoint, derive from test data
9. `cms/apps/web/src/components/renderings/visual-regression-dialog.tsx` — **NEW**: Compare two tests side-by-side
10. `cms/apps/web/messages/en.json` — Add new i18n keys for comparison UI, polling states, HTML input

## Implementation Steps

### Step 1: Align Types (`types/rendering.ts`)

Replace frontend types to match backend schemas exactly. Keep demo-compatible fallback types where the frontend adds computed fields.

```typescript
// Match backend ScreenshotResult
export interface ScreenshotResult {
  client_name: string;
  screenshot_url: string | null;
  os: string;
  category: string; // "desktop" | "mobile" | "web" | "dark_mode"
  status: "pending" | "complete" | "failed";
}

// Match backend RenderingTestResponse
export interface RenderingTest {
  id: number;
  external_test_id: string;
  provider: string;
  status: "pending" | "processing" | "complete" | "failed";
  build_id: number | null;
  template_version_id: number | null;
  clients_requested: number;
  clients_completed: number;
  screenshots: ScreenshotResult[];
  created_at: string;
}

// Match backend RenderingTestRequest
export interface RenderingTestRequest {
  html: string;
  subject?: string;
  clients?: string[];
  build_id?: number | null;
  template_version_id?: number | null;
}

// Match backend RenderingComparisonRequest
export interface RenderingComparisonRequest {
  baseline_test_id: number;
  current_test_id: number;
}

// Match backend RenderingDiff
export interface RenderingDiff {
  client_name: string;
  diff_percentage: number;
  has_regression: boolean;
  baseline_url: string | null;
  current_url: string | null;
}

// Match backend RenderingComparisonResponse
export interface RenderingComparisonResponse {
  baseline_test_id: number;
  current_test_id: number;
  total_clients: number;
  regressions_found: number;
  diffs: RenderingDiff[];
}

export interface PaginatedRenderingTests {
  items: RenderingTest[];
  total: number;
  page: number;
  page_size: number;
}
```

Remove: `RenderingClient`, `RenderingResult`, `RenderingIssue`, `RenderingDashboardSummary`, `RenderingComparison` (old shapes).

### Step 2: Fix Hooks (`hooks/use-renderings.ts`)

1. Change all paths from `/api/v1/renderings/` to `/api/v1/rendering/`
2. Remove `useRenderingClients()` — no backend endpoint
3. Remove `useRenderingSummary()` — no backend endpoint
4. Remove `useRenderingLatest()` — no backend endpoint
5. Keep `useRenderingTests()` — add `status` filter param
6. Keep `useRenderingTest()` — single test by ID
7. Keep `useRequestRendering()` — align with new `RenderingTestRequest`
8. Update `useRenderingComparison()` — use `POST /api/v1/rendering/compare` (it's POST, not GET)
9. Add `useRenderingTestPolling(testId)` — SWR with `refreshInterval` when test status is `pending` or `processing`

```typescript
export function useRenderingTests(params: {
  page?: number;
  pageSize?: number;
  status?: string | null;
}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.pageSize) searchParams.set("page_size", String(params.pageSize));
  if (params.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return useSWR<PaginatedRenderingTests, ApiError>(
    `/api/v1/rendering/tests${qs ? `?${qs}` : ""}`,
    fetcher,
  );
}

export function useRenderingTest(testId: number | null) {
  return useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/rendering/tests/${testId}` : null,
    fetcher,
  );
}

// Poll every 3s while test is in progress
export function useRenderingTestPolling(testId: number | null) {
  const swr = useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/rendering/tests/${testId}` : null,
    fetcher,
    {
      refreshInterval: (data) =>
        data && (data.status === "pending" || data.status === "processing") ? 3000 : 0,
    },
  );
  return swr;
}

export function useRequestRendering() {
  return useSWRMutation<RenderingTest, ApiError, string, RenderingTestRequest>(
    "/api/v1/rendering/tests",
    longMutationFetcher,
  );
}

// POST-based comparison (use mutation, not SWR read)
export function useRenderingComparison() {
  return useSWRMutation<RenderingComparisonResponse, ApiError, string, RenderingComparisonRequest>(
    "/api/v1/rendering/compare",
    longMutationFetcher,
  );
}
```

### Step 3: Update Renderings Page (`renderings/page.tsx`)

1. Remove `useRenderingClients()` import and usage
2. Remove `clients` prop from `ClientCompatibilityMatrix`
3. Pass `screenshots` data shape instead of `results`
4. Add pagination state (`page`, `setPage`) and wire to `useRenderingTests({ page, pageSize: 10 })`
5. Add simple prev/next pagination buttons below the test list
6. Add "Compare" button that opens visual regression dialog (select two tests to compare)
7. Remove `RenderingResult` type references, use `ScreenshotResult`

### Step 4: Fix Submit Dialog (`rendering-test-dialog.tsx`)

The backend **requires** `html` as input. The dialog currently only picks provider + clients.

1. Add a `<textarea>` for pasting HTML (or a note that HTML comes from the current workspace build)
2. Accept optional `html` prop — if provided (from workspace context), skip the textarea
3. Remove the provider toggle (backend determines provider from config)
4. Remove the client category checkboxes (backend uses `DEFAULT_CLIENTS` if none specified)
5. Simplify to: HTML input + optional subject line + "Run Test" button
6. After submit, return the `test.id` and switch to polling mode showing progress (`clients_completed / clients_requested`)

```tsx
interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTestSubmitted?: (test: RenderingTest) => void;
  html?: string; // Pre-filled from workspace
}
```

Dialog states: `idle` → `testing` (show polling progress bar) → `completed` (show summary) | `error`

In `testing` state, use `useRenderingTestPolling(submittedTestId)` to show live progress:
```
Testing... 12/20 clients complete
[=========>          ] 60%
```

### Step 5: Update Test List (`rendering-test-list.tsx`)

1. Change `test.results` → `test.screenshots`
2. Change `test.compatibility_score` → compute from screenshots: `Math.round((complete / total) * 100)` where `complete` = screenshots with status `"complete"`
3. Change `result.client_id` → `screenshot.client_name`
4. Change `result.screenshot_url` → `screenshot.screenshot_url` (handle null — show placeholder)
5. Change `result.status` (pass/warning/fail) → `screenshot.status` (pending/complete/failed) — update badge colors
6. Remove `test.template_name` → show `test.external_test_id` (truncated) or `#${test.id}`
7. Change `test.results.length` → `test.clients_requested` (number, not array)
8. Add visual indicator for in-progress tests (animated pulse on "processing" status)
9. Add "Compare" checkbox per test row for selecting two tests to compare

### Step 6: Update Stats Cards (`rendering-stats-cards.tsx`)

Adapt computed stats to new schema:
- Total tests: `tests.length` (unchanged)
- Avg completion rate: `avg(test.clients_completed / test.clients_requested * 100)`
- Most problematic: find client_name with most `"failed"` screenshots across tests
- Last test: `tests[0]?.created_at` (unchanged)

### Step 7: Update Screenshot Dialog (`rendering-screenshot-dialog.tsx`)

1. Accept `ScreenshotResult` instead of `RenderingResult`
2. Remove `issues` list (backend doesn't have per-screenshot issues)
3. Remove `load_time_ms` display
4. Show `os` and `category` metadata
5. Handle null `screenshot_url` — show "Screenshot pending" placeholder

### Step 8: Update Compatibility Matrix (`client-compatibility-matrix.tsx`)

Remove dependency on `clients` prop (no `/clients` endpoint). Instead:
1. Derive unique clients from `test.screenshots` across all tests
2. Group by `screenshot.category` instead of `client.category`
3. Remove `market_share` column (not available without `/clients` endpoint)
4. Keep the pass/fail dot matrix — map `screenshot.status`: `"complete"` → green, `"failed"` → red, `"pending"` → gray

### Step 9: Create Visual Regression Dialog (`visual-regression-dialog.tsx`) — NEW

New component for comparing two test runs side-by-side using `POST /api/v1/rendering/compare`.

```tsx
interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  baselineTestId: number | null;
  currentTestId: number | null;
}
```

Layout:
- Header: "Visual Regression: Test #{baselineId} vs #{currentId}"
- Summary bar: "{regressions_found} regressions out of {total_clients} clients"
- Grid of diffs, each card shows:
  - Client name
  - Side-by-side: baseline screenshot | current screenshot
  - Diff percentage badge (green if <2%, yellow 2-5%, red >5%)
  - "Regression" badge if `has_regression === true`
- Loading state while comparison runs
- Width: `max-w-[56rem]` (wide dialog for side-by-side)

### Step 10: Add i18n Keys (`messages/en.json`)

Add under `"renderings"`:

```json
"htmlInput": "Email HTML",
"htmlInputPlaceholder": "Paste compiled email HTML here...",
"htmlFromWorkspace": "HTML from current workspace build",
"subjectLine": "Subject Line",
"subjectLinePlaceholder": "e.g., Your Weekly Newsletter",
"testProgress": "{completed}/{total} clients complete",
"compareTests": "Compare",
"selectTestsToCompare": "Select two tests to compare",
"visualRegressionTitle": "Visual Regression",
"visualRegressionSummary": "{count} regressions found across {total} clients",
"noRegressions": "No regressions detected",
"regressionDetected": "Regression",
"diffBelow": "< 2% diff",
"diffMinor": "2-5% diff",
"diffMajor": "> 5% diff",
"baseline": "Baseline",
"current": "Current",
"pending": "Pending",
"screenshotPending": "Screenshot not yet available",
"completionRate": "Completion Rate",
"prevPage": "Previous",
"nextPage": "Next",
"pageOf": "Page {page} of {total}"
```

## Verification

- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors (`pnpm typecheck`)
- [ ] All user-visible text uses `useTranslations()`
- [ ] Semantic Tailwind tokens only (no primitive colors)
- [ ] Auth/RBAC works correctly (submit requires developer role)
- [ ] API paths match backend routes (`/api/v1/rendering/` not `/renderings/`)
- [ ] Types match backend Pydantic schemas exactly
- [ ] Polling stops when test reaches terminal state (complete/failed)
- [ ] Null screenshot URLs handled gracefully (placeholder shown)
- [ ] Visual regression dialog works with POST mutation (not GET)
- [ ] Demo mode still works (mock data shape may need updating in demo store)
