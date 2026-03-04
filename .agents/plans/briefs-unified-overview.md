# Plan: Briefs Unified Overview with Campaign Thumbnails & Resources

## Context

The current `/briefs` page is connection-centric: you pick a platform connection, then see its items. The user wants a **unified campaign brief hub** where all briefs from all connected platforms appear in one rich overview with:
- **Campaign design thumbnails** — visual preview of each campaign
- **Resource links** — Excel files, translations, design mockups, documents
- **Platform indicator** — which platform each brief comes from
- **More platform support** — beyond Jira/Asana/Monday (ClickUp, Trello, Notion, Wrike, Basecamp)

## Architecture Decision

**Tab-based page with two views:**
1. **"All Briefs"** tab (new default) — unified grid of campaign cards with thumbnails, resources, platform badges
2. **"Connections"** tab — existing connection management (mostly untouched)

This preserves the existing connection management while adding the unified overview as the primary view.

## Files to Create

### 1. `cms/apps/web/src/components/briefs/brief-campaign-card.tsx`
Rich campaign card for the unified overview grid. Shows:
- Thumbnail image (top section, 16:9 aspect ratio, placeholder gradient if no image)
- Platform badge (top-right overlay on thumbnail)
- Title, external ID, status badge
- Assignees + due date row
- Resource link chips (Excel, Translation, Design, PDF icons)
- Connection name as subtle label

### 2. `cms/apps/web/src/components/briefs/brief-resource-links.tsx`
Inline resource link chips. Maps file type → icon:
- `.xlsx` / `.csv` → `FileSpreadsheet`
- `.pdf` → `FileText`
- `.png` / `.jpg` / `.fig` / `.sketch` → `Image`
- `.json` / translation files → `Languages`
- Other → `Paperclip`

Each chip is clickable (opens URL) and shows filename truncated.

### 3. `cms/apps/web/src/components/briefs/brief-platform-badge.tsx`
Small badge with platform name + colored dot. Platform color map:
- jira: blue, asana: coral/orange, monday: purple
- clickup: violet, trello: sky, notion: neutral
- wrike: green, basecamp: gold

### 4. `cms/apps/web/src/components/briefs/briefs-overview.tsx`
The "All Briefs" tab content. Contains:
- Search input (debounced 300ms)
- Filter pills row: "All" + each connected platform + status filters
- Grid of `BriefCampaignCard` (responsive: 1 col → sm:2 → lg:3)
- Loading skeleton state, empty state, error state
- Uses `useAllBriefItems()` hook

## Files to Modify

### 5. `cms/apps/web/src/types/briefs.ts`
**Changes:**
- Extend `BriefPlatform` union: add `"clickup" | "trello" | "notion" | "wrike" | "basecamp"`
- Add `BriefResource` interface:
  ```ts
  interface BriefResource {
    id: number;
    type: "excel" | "translation" | "design" | "document" | "image" | "other";
    filename: string;
    url: string;
    size_bytes: number | null;
  }
  ```
- Extend `BriefItem` with optional fields:
  ```ts
  thumbnail_url: string | null;
  resources: BriefResource[];
  platform?: BriefPlatform;       // denormalized for unified view
  connection_name?: string;        // denormalized for unified view
  ```
- Extend `BriefDetail` — inherits new fields from BriefItem, keep attachments for backward compat

### 6. `cms/apps/web/src/hooks/use-briefs.ts`
**Add new hook:**
```ts
export function useAllBriefItems(options?: { platform?: BriefPlatform; status?: BriefItemStatus; search?: string }) {
  // Build query params from options
  return useSWR<BriefItem[]>(buildKey("/api/v1/briefs/items", options), fetcher);
}
```

### 7. `cms/apps/web/src/app/(dashboard)/briefs/page.tsx`
**Redesign to tab-based layout:**
- Add tab bar: "All Briefs" | "Connections" (use established tab pattern from ComponentDetailDialog)
- Default to "All Briefs" tab → renders `<BriefsOverview />`
- "Connections" tab → renders existing connection cards + items panel (extract current content)
- Move "Connect Platform" button to Connections tab; add "Sync All" to All Briefs tab header

### 8. `cms/apps/web/src/components/briefs/connect-brief-dialog.tsx`
**Add new platform options:**
- Add ClickUp, Trello, Notion, Wrike, Basecamp to the platform dropdown
- Add credential field configurations for each:
  - ClickUp: `{ api_token: credential }`
  - Trello: `{ api_key: credential, api_token: trelloToken }` (two fields)
  - Notion: `{ integration_token: credential }`
  - Wrike: `{ access_token: credential }`
  - Basecamp: `{ access_token: credential }`
- Add URL placeholders per platform

### 9. `cms/apps/web/src/components/briefs/brief-detail-dialog.tsx`
**Enhance with thumbnail + resources:**
- Add thumbnail preview at top of dialog (if `thumbnail_url` exists) — full-width image with rounded corners
- Add "Resources" section below description (before attachments) using `BriefResourceLinks`
- Widen dialog to `max-w-[32rem]` to accommodate thumbnail
- Add "Open in {platform}" external link button in header

### 10. `cms/apps/web/src/components/briefs/brief-connection-card.tsx`
**Minor update:**
- Support new platform types in the initial letter badge
- Add platform color to the badge background

### 11. `cms/apps/web/src/lib/demo/data/briefs.ts`
**Extend demo data:**
- Add `thumbnail_url` to existing items (use placeholder gradient data URIs or `/demo/` paths)
- Add `resources` arrays to existing items (mix of Excel, translation JSON, design files)
- Add `platform` and `connection_name` fields to items
- Add a ClickUp demo connection (id: 4) with 2 items
- Add demo details for items 103, 104, 202, 203

### 12. `cms/apps/web/src/lib/demo/resolver.ts`
**Add route:**
- `GET /api/v1/briefs/items` → return all items across all connections (aggregate), support query params for platform/status/search filtering

### 13. `cms/apps/web/messages/en.json`
**Add i18n keys under `"briefs"` namespace:**
```json
"tabAllBriefs": "All Briefs",
"tabConnections": "Connections",
"searchBriefs": "Search briefs...",
"filterAll": "All",
"filterPlatform": "Platform",
"filterStatus": "Status",
"allBriefsEmpty": "No briefs yet",
"allBriefsEmptyDescription": "Connect a platform to start syncing campaign briefs",
"resources": "Resources",
"openInPlatform": "Open in {platform}",
"noThumbnail": "No preview available",
"syncAll": "Sync All",
"syncAllSuccess": "All connections synced",
"platformClickup": "ClickUp",
"platformTrello": "Trello",
"platformNotion": "Notion",
"platformWrike": "Wrike",
"platformBasecamp": "Basecamp",
"resourceExcel": "Spreadsheet",
"resourceTranslation": "Translation",
"resourceDesign": "Design",
"resourceDocument": "Document",
"resourceImage": "Image",
"briefCount": "Showing {count} briefs",
"campaignPreview": "Campaign Preview"
```

## Implementation Steps

### Step 1: Extend types (types/briefs.ts)
Add new platform types, `BriefResource` interface, extend `BriefItem` and `BriefDetail` with `thumbnail_url`, `resources`, `platform`, `connection_name`.

### Step 2: Add i18n keys (messages/en.json)
Add all new translation keys under the `"briefs"` namespace.

### Step 3: Create BriefPlatformBadge component
Small badge showing platform name with colored dot. Uses semantic tokens for background with platform-specific accent via inline style or CSS variable for the dot color only (acceptable exception since platform colors are dynamic data, not theme colors).

### Step 4: Create BriefResourceLinks component
Row of clickable file-type chips. Each chip: icon + truncated filename. Uses `FileSpreadsheet`, `FileText`, `Image`, `Languages`, `Paperclip` from lucide-react. Chips styled as: `rounded border border-card-border bg-surface-muted px-2 py-1 text-xs text-foreground-muted hover:bg-surface-hover`.

### Step 5: Create BriefCampaignCard component
Card structure (top to bottom):
```
┌─────────────────────────────┐
│  [Thumbnail 16:9]  [Badge]  │  ← aspect-[16/9] overflow-hidden rounded-t-lg
│                              │    bg-surface-muted placeholder if no image
├─────────────────────────────┤
│  External ID  •  Platform    │  ← text-xs font-mono text-foreground-muted
│  Title (line-clamp-2)        │  ← text-sm font-medium text-foreground
│  👤 Assignees   📅 Due       │  ← text-xs text-foreground-muted
│  [Excel] [Translation] ...   │  ← BriefResourceLinks
│                  [Status] ↗  │  ← status badge + external link icon
└─────────────────────────────┘
```
Card is a `<button>` that opens `BriefDetailDialog`. Uses established card pattern: `rounded-lg border border-card-border bg-card-bg transition-colors hover:bg-surface-hover`.

### Step 6: Create BriefsOverview component
Layout:
```
[Search input                          ]
[All] [Jira] [Asana] [Monday] [ClickUp] ...  [Open] [In Progress] [Done]
─────────────────────────────────────────
[CampaignCard] [CampaignCard] [CampaignCard]
[CampaignCard] [CampaignCard] [CampaignCard]
─────────────────────────────────────────
Showing 12 briefs
```
- Search with debounce → filters by title
- Platform pills → filter by platform
- Status pills → filter by status (separate row or same row with divider)
- Grid: `grid gap-4 sm:grid-cols-2 lg:grid-cols-3`
- Triptych: loading skeletons → error → empty → grid

### Step 7: Add useAllBriefItems hook
New SWR hook that fetches `GET /api/v1/briefs/items` with optional `platform`, `status`, `search` query params.

### Step 8: Extend demo data
- Add `thumbnail_url` and `resources` to existing items
- Add ClickUp connection + items
- Add demo details for all items
- Wire up `GET /api/v1/briefs/items` in resolver.ts with filtering

### Step 9: Redesign briefs page with tabs
- Add tab bar at top (below header)
- "All Briefs" renders `<BriefsOverview />`
- "Connections" renders existing connection cards + items panel
- Default active tab: "All Briefs"

### Step 10: Enhance BriefDetailDialog
- Add thumbnail preview section
- Add resources section with `BriefResourceLinks`
- Add "Open in {platform}" link
- Widen to `max-w-[32rem]`

### Step 11: Update ConnectBriefDialog for new platforms
- Add ClickUp, Trello, Notion, Wrike, Basecamp to platform select
- Add per-platform credential fields and URL placeholders

### Step 12: Update BriefConnectionCard for new platforms
- Support new platform types in badge colors/labels

### Step 13: Build verification
- Run `pnpm build` from `cms/`
- Fix any TypeScript errors
- Visual check: demo data renders thumbnails, resource links, platform badges correctly

## Token Mapping Reference

| Element | Token |
|---------|-------|
| Card background | `bg-card-bg` |
| Card border | `border-card-border` |
| Card hover | `hover:bg-surface-hover` |
| Thumbnail placeholder | `bg-surface-muted` |
| Primary text | `text-foreground` |
| Secondary text | `text-foreground-muted` |
| Active tab | `border-b-2 border-interactive text-foreground` |
| Inactive tab | `text-foreground-muted hover:text-foreground` |
| Active filter pill | `bg-interactive text-foreground-inverse` |
| Inactive filter pill | `bg-surface-muted text-foreground-muted hover:bg-surface-hover` |
| Resource chip | `border-card-border bg-surface-muted text-foreground-muted` |
| Status badges | `bg-badge-{variant}-bg text-badge-{variant}-text` |
| Search input | `border-input-border bg-input-bg focus:border-input-focus focus:ring-input-focus` |

## Verification
- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] All user-visible text uses `useTranslations()`
- [ ] Semantic Tailwind tokens only (no primitive colors except platform dot colors)
- [ ] Tab switching works: All Briefs ↔ Connections
- [ ] Search filters briefs by title
- [ ] Platform filter pills work
- [ ] Status filter pills work
- [ ] Campaign cards show thumbnails (or placeholder gradient)
- [ ] Resource links render with correct file type icons
- [ ] Brief detail dialog shows thumbnail + resources
- [ ] New platforms appear in Connect dialog with correct credential fields
- [ ] Demo data renders all new fields correctly
