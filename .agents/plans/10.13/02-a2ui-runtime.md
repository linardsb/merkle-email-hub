# 10.13 / Phase 2 — A2UI runtime + 12-card vocabulary

> Build a frontend renderer that consumes A2UI v0.8 JSONL, resolves the adjacency-list components, binds data, and dispatches actions — using a custom catalog of 12 Email-Hub-specific cards. **Per Phase 0 decision D1 = Option B: roll-our-own A2UI v0.8-compliant.**

**Spine:** §4 Phase 2, §13 References (R1, R3, R5), §12 N10 (card anatomy), §10 D1.

| | |
|---|---|
| Calendar | 2–2.5 weeks (was 1.5–2; expanded post-spec discovery) |
| LOC budget | ~2200 (~700 cap means split across files; this plan is one orchestration doc) |
| Dependencies | Phase 0 V1–V8 green; Phase 1 chip shipped (so we reuse the chrome pattern) |
| Outputs consumed by | Phase 3 (AG-UI events deliver A2UI specs as TOOL_CALL_RESULT payloads), Phase 4 (Crew rail clicks render an `AgentProposalCard`), Phase 5 (chat panel renders A2UI cards inline), Phase 6 (Intelligence/Approvals adopt the same vocabulary) |
| Locked by spine | A2UI v0.8 spec compliance (§13 R1); 12-card v1 vocabulary cap (D5); no email-canvas A2UI (§9 non-goal) |

---

## 1 · Inputs

### Local code

| What | File / Path | Why |
|---|---|---|
| A2UI skeleton | `cms/apps/web/src/lib/a2ui/{spec.ts, index.ts}` | Stub from Phase 0.4; fill in here |
| Real fixtures | `cms/apps/web/src/lib/a2ui/__fixtures__/*.json` | Captured Phase 0.1 — adapter inputs |
| Existing chat shape | `cms/apps/web/src/types/chat.ts` | Defines `ChatMessage`; we extend with optional `a2ui` field |
| Existing message bubble | `cms/apps/web/src/components/workspace/chat/message-bubble.tsx` | Render integration point |
| Existing decisions schemas (BE) | `app/ai/agents/schemas/*_decisions.py` (read-only) | Adapter source of truth |
| QA result type | `cms/apps/web/src/types/qa.ts` | For `qaResultToA2UI` adapter |
| Failure pattern type | `cms/apps/web/src/types/failure-patterns.ts` | For `KnowledgeHitsList` adapter |
| Brand config hook | `cms/apps/web/src/hooks/use-brand.ts` | Cards consume via Phase 1's `useDesignMdDoc()` |
| Existing UI primitives | `cms/packages/ui/src/components/ui/{card, button, badge, sheet, tooltip}.tsx` | Cards wrap these — never replace |
| Selection bus | `cms/apps/web/src/lib/selection/SelectionContext.tsx` | Cards subscribe + emit (S1) |

### External primary sources (mandatory before coding)

| Ref | Source | Time |
|---|---|---|
| R1 | A2UI v0.8 spec — `https://a2ui.org/specification/v0.8-a2ui/` | 30 min — re-read; this is binding |
| R5 | CopilotKit generative-ui examples — `https://github.com/CopilotKit/generative-ui` | 30 min — skim the renderer + custom-catalog pattern |
| R5b | `@copilotkitnext/a2ui-renderer` source — clone or unpkg | 30 min — crib structural patterns (we don't depend on it) |
| R1b | Standard catalog definition JSON — `https://a2ui.org/v0_8/standard_catalog_definition.json` | 10 min — see actual catalog file format |

---

## 2 · Tasks

### 2.1 — Spec types (~3 h)

**Goal:** TypeScript types for the four message kinds and the standard catalog. **Match v0.8 verbatim.**

**File:** `cms/apps/web/src/lib/a2ui/spec.ts`

**Required exports (sketch):**

```typescript
// === Message envelope (4 kinds, JSONL-streamed) ===
export type A2UIMessage =
  | { surfaceUpdate: SurfaceUpdate }
  | { dataModelUpdate: DataModelUpdate }
  | { beginRendering: BeginRendering }
  | { deleteSurface: DeleteSurface };

export type SurfaceUpdate = {
  surfaceId: string;
  components: ComponentEntry[];
};

export type DataModelUpdate = {
  surfaceId: string;
  path?: string;                        // JSON Pointer-ish, e.g. "/form"
  contents: DataEntry[];
};

export type BeginRendering = {
  surfaceId: string;
  root: string;                         // component id
  catalogId?: string;                   // omit = standard catalog
};

export type DeleteSurface = { surfaceId: string };

// === Components (adjacency list) ===
export type ComponentEntry = {
  id: string;
  component: ComponentBody;
};

// Discriminated union over standard + custom catalog names
export type ComponentBody =
  | { Text: TextProps }
  | { Row: RowProps }
  | { Column: ColumnProps }
  | { Button: ButtonProps }
  | { Card: CardProps }
  | { Image: ImageProps }
  | { List: ListProps }
  // === custom catalog v1 (12 cards) ===
  | { BuildSummaryCard: BuildSummaryCardProps }
  | { ColorPairPreview: ColorPairPreviewProps }
  | { QaCheckResultCard: QaCheckResultCardProps }
  | { AgentProposalCard: AgentProposalCardProps }
  | { RenderingMatrixCard: RenderingMatrixCardProps }
  | { KnowledgeHitsList: KnowledgeHitsListProps }
  | { InsightCard: InsightCardProps }
  | { TokenDriftCard: TokenDriftCardProps }
  | { EvalVerdictCard: EvalVerdictCardProps }
  | { HitlPauseCard: HitlPauseCardProps }
  | { CalibrationDeltaCard: CalibrationDeltaCardProps }
  | { ContractFailureCard: ContractFailureCardProps };

// === BoundValue (the data binding union) ===
export type BoundValue =
  | { literalString: string }
  | { literalBoolean: boolean }
  | { literalNumber: number }
  | { path: string };                  // points into the data model

// === DataEntry ===
export type DataEntry =
  | { key: string; valueString: string }
  | { key: string; valueBoolean: boolean }
  | { key: string; valueNumber: number }
  | { key: string; valueMap: DataEntry[] };

// === Children ===
export type Children =
  | { explicitList: string[] }                              // child ids
  | { template: { dataBinding: string; componentId: string } };

// === Action ===
export type A2UIAction = {
  name: string;
  context: Array<{ key: string; value: BoundValue }>;
};
```

**Standard catalog props** (Text/Row/Column/Button/Card/Image/List): mirror the spec's example shapes. Each prop value is `BoundValue`.

**Custom catalog props** (12 cards): typed shapes per card. Defined in dedicated files in `lib/a2ui/components/types/`, re-exported from `spec.ts`.

**Acceptance:** `pnpm tsc --noEmit` clean; types parse the v0.8 example JSON from R1 without `as any`.

---

### 2.2 — JSONL parser (~3 h)

**Goal:** parse a stream of newline-delimited JSON into `A2UIMessage[]`, skipping malformed lines with a warning.

**File:** `cms/apps/web/src/lib/a2ui/parser.ts`

**Sketch:**

```typescript
import type { A2UIMessage } from "./spec";

export function parseA2UIJsonl(raw: string): {
  messages: A2UIMessage[];
  errors: { line: number; reason: string }[];
} {
  const messages: A2UIMessage[] = [];
  const errors: { line: number; reason: string }[] = [];
  raw.split("\n").forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const parsed = JSON.parse(trimmed);
      if (isA2UIMessage(parsed)) messages.push(parsed);
      else errors.push({ line: idx + 1, reason: "unknown message kind" });
    } catch (e) {
      errors.push({ line: idx + 1, reason: (e as Error).message });
    }
  });
  return { messages, errors };
}

// Streaming variant for AG-UI integration (Phase 3)
export class A2UIStreamParser {
  private buf = "";
  feed(chunk: string): A2UIMessage[] { /* split on \n, return parsed */ }
}
```

**Acceptance:** unit-tested against fixtures with intentionally malformed lines; partial-line streaming preserves remainder.

---

### 2.3 — `<A2UIRenderer />` component (~6 h)

**Goal:** the core component. Maintains a `surfaces` registry, applies messages, resolves components by id, renders the tree starting from `beginRendering.root`.

**File:** `cms/apps/web/src/lib/a2ui/A2UIRenderer.tsx`

**Anatomy:**

```typescript
type Props = {
  messages: A2UIMessage[];                        // append-only stream
  catalog: ComponentCatalog;                      // {[name]: React.FC}
  onAction?: (action: A2UIAction) => void;        // dispatch user actions
};

type SurfaceState = {
  components: Map<string, ComponentEntry>;        // by id
  data: DataModel;
  ready: boolean;
  rootId: string | null;
  catalogId?: string;
};

export function A2UIRenderer({ messages, catalog, onAction }: Props) {
  const surfaces = useMemo(() => buildSurfaces(messages), [messages]);
  // pick the most recent ready surface (or specific surfaceId if prop added)
  const surface = pickActiveSurface(surfaces);
  if (!surface || !surface.ready || !surface.rootId) return null;

  return (
    <ActionContext.Provider value={onAction}>
      <DataContext.Provider value={surface.data}>
        <ComponentContext.Provider value={surface.components}>
          <RenderNode id={surface.rootId} catalog={catalog} />
        </ComponentContext.Provider>
      </DataContext.Provider>
    </ActionContext.Provider>
  );
}

function RenderNode({ id, catalog }: { id: string; catalog: ComponentCatalog }) {
  const components = useContext(ComponentContext);
  const entry = components.get(id);
  if (!entry) return <UnknownNode id={id} />;
  const [name, props] = entryToNameAndProps(entry);
  const Cmp = catalog[name];
  if (!Cmp) return <UnknownNode name={name} id={id} />;
  return <Cmp {...resolveProps(props)} />;
}
```

**Helpers:**

- `buildSurfaces(messages)` — fold the message list into a `Map<surfaceId, SurfaceState>`. Apply `surfaceUpdate` (replace components), `dataModelUpdate` (merge into data at `path`), `beginRendering` (set rootId + ready), `deleteSurface` (remove).
- `resolveProps(rawProps)` — recursively resolve `BoundValue`s against the current data model.
- `useDataPath(path)` — hook for components to subscribe to a data path; triggers re-render on path-scoped updates.

**Performance:** memoize `buildSurfaces` keyed on message length + last message id. Avoid re-rendering all components on data update — use path-scoped subscriptions.

**Acceptance:** renderer correctly handles a 50-message JSONL fixture; data model updates propagate without unmounting unaffected components; unknown component → graceful `<UnknownNode />` placeholder.

---

### 2.4 — Data binding model (~3 h)

**Goal:** resolve `BoundValue` against a hierarchical data model with JSON-Pointer-style paths.

**File:** `cms/apps/web/src/lib/a2ui/data-model.ts`

**API:**

```typescript
export class DataModel {
  private root: Record<string, unknown> = {};

  applyUpdate(update: DataModelUpdate): void;
  get(path: string): unknown;
  set(path: string, value: unknown): void;
  subscribe(path: string, listener: () => void): () => void;
  resolve(value: BoundValue): unknown;
}
```

**Path semantics:** mirror v0.8 — `/foo/bar/0/baz`. Empty path = root. Trailing `/` ignored.

**Subscription:** path-scoped. Updating `/form/email` notifies subscribers to `/form/email`, `/form`, and `/`. Not subscribers to `/form/name`.

**Acceptance:** unit tests; binding resolution tested with both literals and paths; subscription pruning verified.

---

### 2.5 — Action dispatch (~2 h)

**Goal:** when the user interacts with a `Button` (or any actionable card), invoke `onAction(action)` with the resolved context.

**File:** `cms/apps/web/src/lib/a2ui/actions.ts`

**Sketch:**

```typescript
export function dispatchAction(action: A2UIAction, dataModel: DataModel) {
  const resolved: Record<string, unknown> = {};
  for (const { key, value } of action.context) {
    resolved[key] = dataModel.resolve(value);
  }
  return { name: action.name, context: resolved };
}
```

**Wiring:** every catalog component that has an `action` prop calls `useAction()` (a small hook reading `ActionContext`).

**Acceptance:** clicking a `Button` in a fixture triggers `onAction` with resolved context; literal values pass through, paths get current values.

---

### 2.6 — Catalog setup (~2 h)

**Goal:** registry mapping component name → React component.

**File:** `cms/apps/web/src/lib/a2ui/catalog.ts`

```typescript
import * as Standard from "./components/standard";
import * as Custom from "./components/custom";

export type ComponentCatalog = Record<string, React.ComponentType<any>>;

export const STANDARD_CATALOG: ComponentCatalog = {
  Text: Standard.Text,
  Row: Standard.Row,
  Column: Standard.Column,
  Button: Standard.Button,
  Card: Standard.Card,
  Image: Standard.Image,
  List: Standard.List,
};

export const EMAIL_HUB_CATALOG: ComponentCatalog = {
  ...STANDARD_CATALOG,
  BuildSummaryCard: Custom.BuildSummaryCard,
  ColorPairPreview: Custom.ColorPairPreview,
  QaCheckResultCard: Custom.QaCheckResultCard,
  AgentProposalCard: Custom.AgentProposalCard,
  RenderingMatrixCard: Custom.RenderingMatrixCard,
  KnowledgeHitsList: Custom.KnowledgeHitsList,
  InsightCard: Custom.InsightCard,
  TokenDriftCard: Custom.TokenDriftCard,
  EvalVerdictCard: Custom.EvalVerdictCard,
  HitlPauseCard: Custom.HitlPauseCard,
  CalibrationDeltaCard: Custom.CalibrationDeltaCard,
  ContractFailureCard: Custom.ContractFailureCard,
};
```

**Acceptance:** importing the catalog tree-shakes correctly; bundle analyzer shows only used components in a per-page chunk.

---

### 2.7 — 12-card vocabulary (~6 days, the bulk of phase)

**Goal:** ship 12 production-quality custom catalog components. **Each must conform to §12 N10 anatomy** (title row + body + action footer) via a shared `<_BaseCard>` primitive.

**Files:** one per card under `cms/apps/web/src/lib/a2ui/components/custom/`, plus the shared base:

```
cms/apps/web/src/lib/a2ui/components/
├── _BaseCard.tsx                 # the anatomy enforcer
├── standard/
│   ├── Text.tsx
│   ├── Row.tsx
│   ├── Column.tsx
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Image.tsx
│   └── List.tsx
└── custom/
    ├── BuildSummaryCard.tsx
    ├── ColorPairPreview.tsx
    ├── QaCheckResultCard.tsx
    ├── AgentProposalCard.tsx
    ├── RenderingMatrixCard.tsx
    ├── KnowledgeHitsList.tsx
    ├── InsightCard.tsx
    ├── TokenDriftCard.tsx
    ├── EvalVerdictCard.tsx
    ├── HitlPauseCard.tsx
    ├── CalibrationDeltaCard.tsx
    └── ContractFailureCard.tsx
```

**`_BaseCard` shape:**

```tsx
type BaseCardProps = {
  name: string;                       // e.g. "BuildSummaryCard" — drives "view contract" pill
  title: string;
  subtitle?: string;
  contractJson: unknown;              // raw spec node, for the inspector
  body: React.ReactNode;
  actions?: React.ReactNode;          // action footer
  agentColor?: string;                // semantic token name, not hex
};

export function _BaseCard(props: BaseCardProps) { /* fixed anatomy */ }
```

**Per-card spec (one row per card, full props in `types/`):**

| Card | Purpose | Required props (BoundValue) | Action surface |
|---|---|---|---|
| `BuildSummaryCard` | Scaffolder build output | `title`, `subtitle`, `componentsCount`, `confidence`, `slotFills`, `brandViolations` | "Apply", "Show alternatives" |
| `ColorPairPreview` | Light/dark color pair check | `section`, `lightBg`, `lightText`, `darkBg`, `darkText`, `contrastRatio` | "Accept pair", "Try alt", "Reject" |
| `QaCheckResultCard` | Single QA check verdict | `checkName`, `status (pass\|warn\|fail)`, `score`, `reason`, `agentId` | "Re-run", "Override" |
| `AgentProposalCard` | Agent's diff proposal | `agentId`, `summary`, `diff`, `confidence` | "Apply", "Reject", "Ask why" |
| `RenderingMatrixCard` | 14-client render matrix | `gates: {clientId, status}[]` | "Open client", "Re-render" |
| `KnowledgeHitsList` | Retrieved knowledge hits | `hits: {title, source, snippet, severity}[]` | "Open hit" |
| `InsightCard` | Generic stat card | `headline`, `value`, `trend?`, `caption?` | optional |
| `TokenDriftCard` | Off-token color found | `value`, `nearestToken`, `deltaE`, `section` | "Replace with token", "Keep override" |
| `EvalVerdictCard` | Adversarial evaluator output | `verdict (accept\|revise\|reject)`, `score`, `issues: string[]` | "Accept revision" |
| `HitlPauseCard` | Pipeline paused for human | `agentId`, `reason`, `proposal`, `resumeOptions: string[]` | "Resume", "Override", "Ask agent" |
| `CalibrationDeltaCard` | TPR/TNR shift report | `criterion`, `tprDelta`, `tnrDelta`, `verdict` | "View baseline" |
| `ContractFailureCard` | Pipeline contract fail | `contractName`, `expected`, `got`, `nodeId` | "Re-run agent", "Override" |

**Per-card deliverable:**

1. Type definition in `lib/a2ui/components/types/<Name>.ts`
2. Component file `<Name>.tsx` using `_BaseCard`
3. Storybook story with 3 fixture variants (default, error, edge)
4. Unit test snapshot

**Brand handling:** each card uses the existing token system (semantic tokens only, never hex per §12 N3). Status colors map: pass=`text-success`, warn=`text-warning`, fail=`text-danger`, info=`text-info`. Never inline hex.

**Dark/light parity:** every card story rendered in both themes (Storybook chromatic).

**Acceptance:** all 12 cards render; storybook coverage 100%; bundle delta per card ≤ 4 KB gz; structural snapshot test confirms anatomy invariant.

---

### 2.8 — "Inspect" (admin-only) inspector (~3 h)

**Goal:** ⌘. (period) toggles a side sheet showing the raw card payload for the currently focused/hovered card. Per §12 S4 (no modal) and N10 (anatomy invariant).

**Per spine §1.6 user-facing naming policy:**
- **Pill label:** "Inspect" (never "view contract")
- **Pill visibility:** ADMIN ONLY by default. Hidden for `developer`/`viewer` roles unless URL contains `?inspector=1`. Code-internal name stays `ContractInspector`.
- **Tooltip:** "View structured data (admin)"

**File:** `cms/apps/web/src/lib/a2ui/ContractInspector.tsx` (internal name unchanged)

- Side sheet, ~480 px (matches Phase 1 brand drawer width)
- Syntax-highlighted JSON via Shiki
- Two tabs: "Source" | "Resolved" (was "Component spec" | "Resolved props" — neutralize)
- Pin button — keep open across cards
- Copy + download

**Trigger:** keyboard shortcut `⌘.` opens for the most-recently-focused card *for admins only*; non-admin users get a no-op.

**Acceptance:** ⌘. opens for admins; non-admins see no pill and ⌘. is a no-op; cycles cards via Tab+⌘.; ESC closes; ESLint rule blocks "view contract" string anywhere in JSX.

---

### 2.9 — Adapters from existing decisions (~3 days)

**Goal:** synthesize A2UI specs on the client from existing chat / blueprint / QA responses. **No backend changes.**

**Files** in `cms/apps/web/src/lib/a2ui/adapters/`:

| Adapter | Input | Output A2UI shape |
|---|---|---|
| `decisionsToA2UI.ts` | `EmailBuildPlan` (existing) | `BuildSummaryCard` + nested standard catalog |
| `qaResultToA2UI.ts` | `QAResultResponse` | `RenderingMatrixCard`-like list of `QaCheckResultCard`s |
| `chatMessageToA2UI.ts` | `ChatMessage` with structured payload | per-agent card (Scaffolder→`BuildSummaryCard`, Dark Mode→`ColorPairPreview`, etc.) |
| `failurePatternsToA2UI.ts` | `FailurePattern[]` | `KnowledgeHitsList` |
| `hitlPauseToA2UI.ts` | blueprint paused state | `HitlPauseCard` |
| `evalVerdictToA2UI.ts` | evaluator response | `EvalVerdictCard` |
| `tokenDriftToA2UI.ts` | code reviewer decision | `TokenDriftCard` |

**Pattern:**

```typescript
export function decisionsToA2UI(plan: EmailBuildPlan): A2UIMessage[] {
  const surfaceId = `build-${plan.runId}`;
  return [
    { surfaceUpdate: { surfaceId, components: [
      { id: "root", component: { BuildSummaryCard: {
        name: "BuildSummaryCard",
        title: { literalString: `${plan.components.length} components selected` },
        subtitle: { literalString: `${plan.layoutFamily} · ${plan.confidence.toFixed(2)} conf` },
        componentsCount: { literalNumber: plan.components.length },
        confidence: { literalNumber: plan.confidence },
        slotFills: { literalNumber: plan.slotFills.filled },
        brandViolations: { literalNumber: plan.brandViolations.length },
      } }},
    ] }},
    { beginRendering: { surfaceId, root: "root" }},
  ];
}
```

**Acceptance:** every adapter has a fixture-driven test; adapted output renders without errors via `<A2UIRenderer />`.

---

### 2.10 — Chat panel integration (~1 day)

**Goal:** existing `<MessageBubble>` renders an A2UI card when the chat message has a `a2ui` payload; otherwise falls through to current rendering.

**File:** `cms/apps/web/src/components/workspace/chat/message-bubble.tsx` (modify, additive)

**Change:** add optional `a2ui?: A2UIMessage[]` field on `ChatMessage`. When present, render via `<A2UIRenderer messages={msg.a2ui} catalog={EMAIL_HUB_CATALOG} onAction={handleA2UIAction} />`. **Preserve all existing rendering paths.**

**Action handler:** routes A2UI actions to existing chat handlers — `applyHtml` → existing `onApplyToEditor`, `acceptVerdict` → existing approval flow, etc.

**Wire-up at send time:** `useChat` hook's response handler tries adapter chain (`decisionsToA2UI`, `chatMessageToA2UI`, etc.) and attaches `a2ui` field if any adapter returns non-empty.

**Acceptance:** existing chat (no a2ui) renders unchanged; new chat messages with structured payloads render as cards; "view contract" pill works; backward-compatible.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | Spec types parse a real A2UI v0.8 example without `as any` | unit test against R1 example |
| V2 | JSONL parser handles partial chunks, empty lines, malformed JSON | unit |
| V3 | Renderer applies all 4 message kinds correctly | integration test with multi-message fixture |
| V4 | Data binding: literal vs path resolves correctly | unit |
| V5 | Subscription scoping: updating `/foo/bar` doesn't re-render `/foo/baz` subscribers | render-count assertion |
| V6 | All 12 cards render in both themes | Storybook + chromatic |
| V7 | Card anatomy invariant (§12 N10) | structural snapshot test on `_BaseCard` usage |
| V8 | "View contract" pill works on every card | manual + e2e |
| V9 | Adapters produce valid A2UI specs from real fixtures | fixture-driven tests |
| V10 | Existing chat (no a2ui) renders identically | snapshot diff |
| V11 | Bundle size impact ≤ 35 KB gz on workspace route (renderer + 12 cards combined) | `pnpm analyze` |
| V12 | Renderer + standard catalog tree-shake correctly | bundle analyzer per route |
| V13 | A11y: every card has proper roles, focus order, keyboard support | axe |
| V14 | Backend untouched | `git diff main..HEAD -- app/` empty |
| V15 | `pnpm tsc && pnpm test && pnpm storybook:build` clean | CI |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D2.1 | Standard catalog implementation: full v0.8 fidelity vs subset? | **Full v0.8** for forward compat |
| D2.2 | Streaming-first vs batch-first renderer? | **Both** — `messages` prop accepts arrays; streaming via `A2UIStreamParser` |
| D2.3 | Action dispatch: callback prop vs event bus? | **Callback prop** (simpler, no global state) |
| D2.4 | Inline catalog support (`acceptsInlineCatalogs`)? | **No for v1** — security risk; hardcoded catalog only |
| D2.5 | Path syntax: support array indexing (`/foo/0`)? | **Yes** per v0.8 |
| D2.6 | Custom catalog id | `email-hub-v1` (registered locally; not published) |
| D2.7 | "View contract" trigger | **⌘.** (period) per Phase 0 D7 alignment |
| D2.8 | Render perf budget | re-render count under 1.5× minimum on data update |

Record in `docs/decisions/D-005-a2ui-runtime-locks.md`.

---

## 5 · Pitfalls

- **Don't auto-render every surface.** When multiple `surfaceUpdate`s arrive, `beginRendering` is the explicit signal. Until it arrives, surface is "buffered" and not rendered. Test this — agents may push updates before the begin-rendering message.
- **Don't re-resolve all bindings on every render.** Use path-scoped subscriptions; profile re-render counts during a streaming run.
- **Don't fight v0.8 shape.** If a card needs nested data, model it as `dataModelUpdate` with `valueMap`. Don't invent your own envelope.
- **Don't bypass the catalog.** Direct `<BuildSummaryCard />` calls are tempting in app code — disallow via lint. Always go through the renderer so contract inspection works.
- **Don't ship cards that break N10.** Reviewer rejects PRs that don't use `_BaseCard`.
- **Don't expose backend internals via context.** `BoundValue` paths point to data the *agent* deemed safe to share — never reach into Redux/store from a card. Pure props in, callback out.
- **Don't use hex colors in cards.** §12 N3. Lint rule: ban `#[0-9a-f]{3,6}` in `lib/a2ui/components/`.
- **Don't lazy-load 12 cards individually.** Bundle them as one chunk per route — shipping 12 separate chunks blows the budget.
- **Don't assume single surface.** Spec allows multiple surfaces. v1 renders the most recent ready surface; future phases may render multiple.

---

## 6 · Hand-off to Phase 3

Phase 3 (AG-UI envelope) consumes from Phase 2:

- `parseA2UIJsonl` and `A2UIStreamParser` — AG-UI `TOOL_CALL_RESULT` events may carry A2UI JSONL as `content`; the AG-UI hook splits + feeds the parser
- The custom catalog id `email-hub-v1` — Phase 3 fixtures encode this in `beginRendering.catalogId`
- The `EMAIL_HUB_CATALOG` — Phase 5's chat panel imports this directly when rendering streamed messages

When Phase 2 closes, the next agent reads:

1. Spine §13 (AG-UI events table)
2. Phase 2 V1–V15 verification table
3. `10.13/03-ag-ui-envelope.md`
4. Phase 0 fixtures: `progress-mid.json`, `blueprint-stream-chunks.jsonl`

**End-state of Phase 2:** workspace renders A2UI cards inline in chat; ⌘. shows the contract; brand stays consistent; backend untouched; bundle delta ≤ 35 KB gz.
