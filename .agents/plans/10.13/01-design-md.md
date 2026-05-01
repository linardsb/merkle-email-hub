# 10.13 / Phase 1 — DESIGN.md as a portable window

> Read the existing 3-tier token system at runtime, project it as a Google `DESIGN.md` document, and surface it via a chip + drawer in the top bar. **Tokens stay canonical in `tokens.css`. DESIGN.md becomes a *view* of them**, not a source-of-truth swap.

**Spine:** `.agents/plans/10.13-agentic-ui-frontend-adoption.md` §4 Phase 1 + §13 References + §12 UX principles.

| | |
|---|---|
| Calendar | 3–5 working days |
| LOC budget | ~700 (the 700-line cap) |
| Dependencies | Phase 0 verification gates V1–V8 green; especially V2 (token fixtures captured) |
| Outputs consumed by | Phase 2 (A2UI cards reference `colors.tertiary` etc. via tokens map), Phase 5 (canvas section overlay shows DESIGN.md token usage), Phase 6 (intelligence page reuses inspector chrome) |
| Locked by spine | tokens NOT renamed (§1); chip lives **right of breadcrumb** (D4); fonts/colors/icons unchanged (§1) |

---

## 1 · Inputs

### Local code (read first)

| What | File / Path | Why |
|---|---|---|
| 3-tier token CSS | `cms/packages/ui/src/tokens.css` | Authoritative token set; we *project* this, never edit it |
| Tailwind 4 `@theme` block | `cms/packages/ui/src/globals.css` | Confirms tokens emit on `:root` |
| Brand config hook | `cms/apps/web/src/hooks/use-brand.ts` | Per-org/per-project brand overrides — name, logo, color overrides |
| Brand config types | `cms/apps/web/src/types/brand.ts` | Shape of `BrandConfig` |
| Theme provider | `cms/apps/web/src/components/theme-provider.tsx` (uses `next-themes`) | Tells us the active theme; we re-project on theme change |
| Existing dashboard layout | `cms/apps/web/src/app/(dashboard)/layout.tsx` | Where we mount the chip (right of breadcrumb, before user menu — D4) |
| Existing Sheet primitive | `cms/packages/ui/src/components/ui/sheet.tsx` | Drawer container for the inspector (S4: no modals over canvas) |
| Existing Tooltip primitive | `cms/packages/ui/src/components/ui/tooltip.tsx` | All hover-revealed labels per N2 |
| Token fixtures | `cms/apps/web/src/lib/design-md/__fixtures__/tokens-{light,dark}.json` | Captured in Phase 0.2 — input to mapping tests |
| Skeleton | `cms/apps/web/src/lib/design-md/{index.ts, types.ts}` | Created in Phase 0.4 — fill these in |

### External primary sources

| Ref | Source | Time |
|---|---|---|
| R4 | DESIGN.md spec — `https://github.com/google-labs-code/design.md/blob/main/docs/spec.md` | 20 min — section ordering, token types, lint rules |
| R4b | DESIGN.md README — `https://github.com/google-labs-code/design.md` | 10 min — example doc, CLI commands |
| R4c | npm package — `npm view @google/design.md` (run locally) | 5 min — confirm it's installable, current version, peer deps |

---

## 2 · Tasks

### 1.1 — Type definitions (~2 h)

**Goal:** define TypeScript types that exactly mirror the DESIGN.md schema. The lint package (if installed in 1.4) will validate against the same shape.

**File:** `cms/apps/web/src/lib/design-md/types.ts`

**Required exports (sketch):**

```typescript
// Mirrors https://github.com/google-labs-code/design.md spec
export type DesignMdVersion = "alpha";

export type ColorValue = `#${string}`;                     // sRGB hex
export type Dimension = `${number}${"px" | "em" | "rem"}` | number;
export type TokenRef<P extends string = string> = `{${P}}`; // e.g. "{colors.primary}"

export type Typography = {
  fontFamily: string;
  fontSize: Dimension;
  fontWeight?: number;
  lineHeight?: Dimension | number;
  letterSpacing?: Dimension;
  fontFeature?: string;
  fontVariation?: string;
};

export type ComponentTokens = {
  backgroundColor?: ColorValue | TokenRef;
  textColor?: ColorValue | TokenRef;
  typography?: TokenRef<`typography.${string}`>;
  rounded?: Dimension | TokenRef<`rounded.${string}`>;
  padding?: Dimension;
  size?: Dimension;
  height?: Dimension;
  width?: Dimension;
};

export type DesignMdDoc = {
  version?: DesignMdVersion;
  name: string;
  description?: string;
  colors?: Record<string, ColorValue>;
  typography?: Record<string, Typography>;
  rounded?: Record<string, Dimension>;
  spacing?: Record<string, Dimension>;
  components?: Record<string, ComponentTokens>;
  // prose, captured separately for round-trip
  prose?: {
    overview?: string;
    colors?: string;
    typography?: string;
    layout?: string;
    elevation?: string;
    shapes?: string;
    components?: string;
    dosAndDonts?: string;
  };
};

export type DesignMdLintFinding = {
  severity: "error" | "warning" | "info";
  rule: string;          // e.g. "broken-ref", "contrast-ratio"
  path: string;          // e.g. "components.button-primary"
  message: string;
};

export type DesignMdLintReport = {
  findings: readonly DesignMdLintFinding[];
  summary: { errors: number; warnings: number; info: number };
};
```

**Acceptance:** `pnpm tsc --noEmit` clean; types match the README example verbatim.

---

### 1.2 — `tokensToDesignMd()` mapper (~4 h)

**Goal:** read computed CSS variables off `:root` and produce a `DesignMdDoc`. Pure function (takes element + brand config, returns doc) — no side effects.

**File:** `cms/apps/web/src/lib/design-md/tokens-to-design-md.ts`

**Sketch:**

```typescript
import type { BrandConfig } from "@/types/brand";
import type { ColorValue, DesignMdDoc, Dimension } from "./types";

// Source-of-truth token map — semantic Tier 2 names → DESIGN.md section
const COLOR_TOKEN_MAP = {
  // semantic --color-* → DESIGN.md colors.*
  "--color-foreground":   "primary",
  "--color-muted-foreground": "secondary",
  "--color-interactive":  "tertiary",
  "--color-background":   "neutral",
  "--color-surface":      "surface",
  "--color-success":      "success",
  "--color-warning":      "warning",
  "--color-danger":       "danger",
  "--color-info":         "info",
  // … extend per actual semantic set in tokens.css
} as const;

const TYPOGRAPHY_TOKEN_MAP = {
  "--font-sans": ["body-md", "h1", "h2", "h3", "label"],
  "--font-mono": ["mono"],
} as const;

const SPACING_TOKEN_MAP = {
  "--spacing-xs": "xs",
  "--spacing-sm": "sm",
  "--spacing-md": "md",
  "--spacing-lg": "lg",
  "--spacing-xl": "xl",
} as const;

export function tokensToDesignMd(
  rootEl: HTMLElement = document.documentElement,
  brand?: BrandConfig | null,
): DesignMdDoc {
  const cs = getComputedStyle(rootEl);
  const read = (k: string): string => cs.getPropertyValue(k).trim();

  // Convert OKLCH → hex (Tailwind 4 emits oklch). Use `culori` if dep allowed,
  // else implement a small oklch→hex via a temp <canvas> trick.
  const toHex = (raw: string): ColorValue => oklchOrHexToHex(raw);

  const colors: Record<string, ColorValue> = {};
  for (const [cssVar, key] of Object.entries(COLOR_TOKEN_MAP)) {
    const v = read(cssVar);
    if (v) colors[key] = toHex(v);
  }

  // Apply brand overrides (project-level > org-level > defaults)
  if (brand?.color_overrides) {
    Object.assign(colors, brand.color_overrides);
  }

  return {
    version: "alpha",
    name: brand?.name ?? "Email Hub Default",
    description: brand?.description,
    colors,
    typography: buildTypography(cs),
    rounded: buildRounded(cs),
    spacing: buildSpacing(cs),
    components: buildComponentMap(cs),
    prose: {
      overview: brand?.brand_voice ?? undefined,
    },
  };
}
```

**Test fixtures:** unit-test against `__fixtures__/tokens-light.json` and `tokens-dark.json` from Phase 0.

**Edge cases:**

- OKLCH → hex conversion. Tailwind 4 emits `oklch(0.55 0.220 27)` strings. Convert via `culori` (small dep, MIT) or via a `<canvas>` round-trip. Pick `culori` — already in deps via shadcn color-utils per existing `lib/color-utils.ts`. **Verify** before installing anything new.
- Empty CSS var. Return `null` from the mapping; do not silently default to `#000000`.
- Brand overrides may use named tokens (`{colors.primary}`) — preserve those without resolving to hex (the lint will flag broken refs).

**Acceptance:** unit tests with light + dark fixtures both produce valid DESIGN.md docs; round-trip through 1.3 serializer produces parseable YAML.

---

### 1.3 — `designMdToYaml()` serializer (~1.5 h)

**Goal:** deterministic YAML output. Pure function. Section order matches spec table.

**File:** `cms/apps/web/src/lib/design-md/serialize.ts`

**Pseudo-code:**

```typescript
import yaml from "js-yaml";          // already in deps
import type { DesignMdDoc } from "./types";

const SECTION_ORDER = [
  "version", "name", "description",
  "colors", "typography", "rounded", "spacing", "components",
] as const;

export function designMdToYaml(doc: DesignMdDoc): string {
  // Preserve key order (js-yaml respects insertion order)
  const out: Record<string, unknown> = {};
  for (const key of SECTION_ORDER) {
    if (doc[key as keyof DesignMdDoc] !== undefined) {
      out[key] = doc[key as keyof DesignMdDoc];
    }
  }
  return yaml.dump(out, {
    quotingType: '"',
    forceQuotes: true,
    lineWidth: 100,
    sortKeys: false,            // critical — we set order ourselves
  });
}

export function designMdDocToFullMarkdown(doc: DesignMdDoc): string {
  const front = `---\n${designMdToYaml(doc)}---\n\n`;
  const prose = doc.prose ?? {};
  const sections = [
    prose.overview && `## Overview\n\n${prose.overview}`,
    prose.colors && `## Colors\n\n${prose.colors}`,
    // …
  ].filter(Boolean).join("\n\n");
  return front + sections;
}
```

**Acceptance:** snapshot test produces stable output across Node versions; section order matches spec.

---

### 1.4 — Lint adapter (~2 h, optional)

**Goal:** wire `@google/design.md` lint package as an opt-in capability. If install fails or the package is unavailable, fall back gracefully (return empty findings).

**File:** `cms/apps/web/src/lib/design-md/lint.ts`

**Decision gate:** in this task, run `npm view @google/design.md` to confirm the package is published. If yes, install (`pnpm add @google/design.md`) and wire the lint API. If no/alpha-broken, ship a stub that returns `{ findings: [], summary: {…} }` and revisit later.

**Sketch (with package):**

```typescript
import type { DesignMdLintReport } from "./types";

let lintImpl: ((md: string) => DesignMdLintReport) | null = null;

async function loadLinter(): Promise<typeof lintImpl> {
  if (lintImpl !== null) return lintImpl;
  try {
    const pkg = await import("@google/design.md/linter");
    lintImpl = (md: string) => {
      const r = pkg.lint(md);
      return {
        findings: r.findings,
        summary: r.summary,
      };
    };
  } catch {
    lintImpl = () => ({
      findings: [],
      summary: { errors: 0, warnings: 0, info: 0 },
    });
  }
  return lintImpl;
}

export async function lintDesignMd(md: string): Promise<DesignMdLintReport> {
  const fn = await loadLinter();
  return fn!(md);
}
```

**Tests:**
- Pass a known-broken DESIGN.md (broken token ref) → expect a finding
- Pass a known-good DESIGN.md → expect zero errors
- Mock the package as unavailable → expect empty findings (no throw)

**Acceptance:** lint runs in either mode; UI never throws on bad input.

---

### 1.5 — `<DesignMdInspector />` (~5 h)

**Goal:** the chip + the drawer. Chip lives in the top bar (D4); click opens a side sheet (S4 — no modals over canvas) showing live YAML, lint findings, and theme switcher preview.

**Files:**

- `cms/apps/web/src/components/design-md/DesignMdInspector.tsx` (chip + sheet)
- `cms/apps/web/src/components/design-md/DesignMdYamlView.tsx` (syntax-highlighted code block — reuse Monaco read-only or Shiki)
- `cms/apps/web/src/components/design-md/DesignMdLintList.tsx` (findings list)
- `cms/apps/web/src/components/design-md/__tests__/DesignMdInspector.test.tsx`

**Anatomy (chip — user-visible text per spine §1.6):**

```
┌──────────────────────────────────────────┐
│ [paint-icon] Brand · Heritage      [▾]   │  ← clickable, opens drawer
└──────────────────────────────────────────┘
```

- Compact: ~140 px wide, height matches existing top-bar buttons (~32 px)
- Tooltip on hover: "Project brand · click to inspect"
- Keyboard: focusable, Enter/Space opens drawer
- **No "DESIGN.md" string visible to users.** The internal module name stays — only the chip text is rebranded.

**Anatomy (drawer, opens from right, ~480 px wide — user-visible per spine §1.6):**

```
┌─────────────────────────────────────────┐
│ Brand                              [×]  │
│ Heritage · light theme                  │
├─────────────────────────────────────────┤
│ [ Tokens ] [ Components ] [ Checks (2) ]│  ← tabs (was "YAML / Components / Lint")
├─────────────────────────────────────────┤
│ ---                                     │
│ name: Heritage                          │  ← syntax-highlighted YAML
│ colors:                                 │     read-only — internal format
│   primary: "#1A1C1E"                    │     visible only inside drawer
│   …                                     │
├─────────────────────────────────────────┤
│ [ Copy ] [ Download brand file ]        │
└─────────────────────────────────────────┘
```

The YAML *content* is still DESIGN.md format (canonical) — users see the YAML inside the drawer, but the chrome (chip label, drawer title, tab labels, button labels) is Email-Hub-branded.

**Implementation notes:**

- Use `<Sheet>` primitive (existing) — `side="right"`, `widthClass="w-[480px]"`
- Re-project DESIGN.md on every open (cheap; runs `tokensToDesignMd` once)
- Subscribe to `useTheme()` from `next-themes` and re-render on change (live update)
- Subscribe to `useBrandConfig(orgId)` so brand overrides reflect immediately
- Memoize the YAML string with `useMemo` keyed on `(doc, theme)`
- Provide a "Copy YAML" action that hits `navigator.clipboard.writeText`
- Provide a "Download .md" action via `Blob` + `URL.createObjectURL`

**Acceptance:** chip + sheet render in both light and dark; YAML updates live when theme toggles; copy + download actions work.

---

### 1.6 — Wire chip into top bar (~1 h)

**Goal:** mount the chip in the existing dashboard layout per D4 (right of breadcrumb, before user menu).

**File:** `cms/apps/web/src/app/(dashboard)/layout.tsx`

**Steps:**

1. Locate the existing top-bar JSX in `layout.tsx`
2. Identify the breadcrumb element and the user-menu element
3. Insert `<DesignMdInspector />` between them with proper spacing (e.g. `mx-3`)
4. Verify nothing else moved; existing avatars, save status, etc. positions unchanged

**Acceptance:** visual diff against pre-change baseline shows only the new chip; no other layout shift; works on all 14 routes.

---

### 1.7 — Brand config integration (~1.5 h)

**Goal:** chip name reflects the active project's brand. Falls back to "Default" when no project context.

**Files:**

- `cms/apps/web/src/components/design-md/DesignMdInspector.tsx` (extend)
- `cms/apps/web/src/lib/design-md/use-design-md-doc.ts` (new hook)

**Hook sketch:**

```typescript
import { useTheme } from "next-themes";
import { useEffect, useMemo, useState } from "react";
import { useBrandConfig } from "@/hooks/use-brand";
import { tokensToDesignMd } from "./tokens-to-design-md";
import type { DesignMdDoc } from "./types";

export function useDesignMdDoc(): DesignMdDoc {
  const { resolvedTheme } = useTheme();
  const { data: brand } = useBrandConfig();           // existing hook
  const [doc, setDoc] = useState<DesignMdDoc | null>(null);

  useEffect(() => {
    if (typeof document === "undefined") return;     // SSR safety
    setDoc(tokensToDesignMd(document.documentElement, brand ?? null));
  }, [resolvedTheme, brand]);

  return useMemo(
    () => doc ?? { version: "alpha", name: "Default" },
    [doc],
  );
}
```

**Acceptance:** without a project context, chip shows "Default"; on project route, shows the project's brand name; theme toggle updates underlying YAML in real time.

---

### 1.8 — Tests + Storybook (~3 h)

**Coverage goals:**

- Unit: `tokensToDesignMd` against light + dark fixtures
- Unit: `designMdToYaml` snapshot stability
- Unit: `lintDesignMd` with known-good and known-bad inputs
- Component: `DesignMdInspector` renders chip + opens sheet
- Storybook stories:
  - `DesignMdInspector/Default` — light theme, default brand
  - `DesignMdInspector/DarkMode` — dark variant
  - `DesignMdInspector/HeritageBrand` — branded variant
  - `DesignMdInspector/WithLintFindings` — show 2 warnings
  - `DesignMdInspector/Empty` — no project context

**Files:**

- `cms/apps/web/src/lib/design-md/__tests__/tokens-to-design-md.test.ts`
- `cms/apps/web/src/lib/design-md/__tests__/serialize.test.ts`
- `cms/apps/web/src/lib/design-md/__tests__/lint.test.ts`
- `cms/apps/web/src/components/design-md/DesignMdInspector.stories.tsx`

**Acceptance:** `pnpm test cms/apps/web/src/lib/design-md` clean; `pnpm storybook:build` clean; chromatic visual diffs reviewed.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | Chip visible on every dashboard route | manual + Playwright on top 5 routes |
| V2 | Chip name reflects active project brand | navigate to two projects with different brands |
| V3 | Sheet opens on click; closes on ESC + outside-click + ✕ | Playwright |
| V4 | YAML updates live when toggling theme | manual + visual diff |
| V5 | Lint findings appear when DESIGN.md has broken refs | inject a broken ref via dev override; confirm warning surfaces |
| V6 | Sheet does not cover the canvas (S4 — uses `<Sheet>`, not `<Dialog>`) | code grep |
| V7 | Copy + download actions work | manual |
| V8 | All existing pages unchanged visually except for the new chip | visual regression |
| V9 | `pnpm tsc --noEmit && pnpm test && pnpm storybook:build` clean | CI |
| V10 | Bundle size impact ≤ 12 KB gz on dashboard route | `pnpm analyze` |
| V11 | Backend untouched | `git diff main..HEAD -- app/` empty |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D1.1 | Install `@google/design.md` as runtime dep? | **Yes** if alpha is stable; else stub-only path |
| D1.2 | Color conversion: `culori` vs hand-rolled OKLCH→hex | **culori** if existing color-utils uses it; else hand-rolled (~30 LOC) |
| D1.3 | Chip width responsive vs fixed | **Fixed 140 px**; collapses to icon-only on viewport < 1024 px |
| D1.4 | Yaml view: Monaco read-only vs Shiki | **Shiki** — lighter, no editor weight, no input handling |
| D1.5 | Drawer width | **480 px** desktop; full-width sheet on mobile |
| D1.6 | Show prose sections in inspector | **Yes** but collapsed by default |

Record in `cms/apps/web/docs/decisions/D-004-design-md-phase1.md`.

---

## 5 · Pitfalls

- **Don't touch `tokens.css`.** Spine §1 locks the token system. If a token is missing for the mapping, *add a semantic token* via a separate PR — do not co-mingle.
- **Don't break SSR.** `document` is undefined server-side. Use `useEffect` to read tokens; render an empty/loading chip during SSR.
- **Don't trigger layout thrash.** `getComputedStyle` is synchronous and forces style flush. Read tokens once per theme change, memoize the doc.
- **Don't expose secrets.** Brand config may include non-public fields (org id, customer notes). Inspector shows only `name`, `colors`, `typography`, etc. — explicitly whitelist fields.
- **Don't skip dark-mode parity.** Every visual deliverable must be tested in `.dark` class. Storybook stories should exist in both themes.
- **Don't fight Tailwind 4 precedence.** `@theme` at root can be overridden by `:root { … }` blocks elsewhere. Confirm the *resolved* value from `getComputedStyle`, not the source.
- **Don't add a modal.** §12 S4: Sheet, not Dialog. Reviewers will reject any `<Dialog>` PR for this surface.
- **Don't add new fonts.** Spine §1 locks the font stack.

---

## 6 · Hand-off to Phase 2

Phase 2 (A2UI runtime) consumes from Phase 1:

- The `DesignMdDoc` shape via `useDesignMdDoc()` — A2UI cards reference tokens by name (e.g. `colors.tertiary`), and Phase 5's section-overlay shows token usage tied to this hook.
- The chip-and-drawer pattern (Sheet, no modal, syntax-highlighted code) — Phase 2's "view contract" pill follows the same chrome.

When Phase 1 closes, the next agent reads:

1. Spine
2. Phase 1 verification table (V1–V11) — to know what's built
3. `10.13/02-a2ui-runtime.md`
4. The captured fixtures from Phase 0.1

**End-state of Phase 1:** every dashboard route shows a `DESIGN.md ▸ <name>` chip top-right; clicking opens a sheet with live YAML; theme toggle updates the YAML in real time; bundle delta ≤ 12 KB gz; existing pages otherwise pixel-identical.
