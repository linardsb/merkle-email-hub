# Plan: Brief Cards → Design Sync & Component Extraction

## Context

The Briefs page was showing "No briefs yet" (fixed: `NEXT_PUBLIC_DEMO_MODE=true`). The previous implementation added "Open in Figma/Sketch" external links on brief cards — **wrong approach**. The user wants briefs to trigger the existing in-hub design-sync pipeline: sync design → extract components → match with HTML email components. The entire design-sync infrastructure already exists (`DesignImportDialog`, `ConnectDesignDialog`, hooks, demo resolvers). We just need to wire it into the briefs UI.

## Key Design Decision: Link via `project_id`

Brief connections and design connections are linked through shared `project_id`:
- Brief conn 1 (`project_id: 1`) ↔ Design conn 1 (`project_id: 1`) — Spring Campaign (Figma)
- Brief conn 3 (`project_id: 3`) ↔ Design conn 3 (`project_id: 3`) — Welcome Series (Sketch)
- Brief conns 2, 4 have `project_id: null` → no linked design connection

No new fields needed on `BriefItem`. Resolve the link at runtime.

## Changes (6 files)

### 1. Revert `design_file_url` from type — `cms/apps/web/src/types/briefs.ts`
- Remove `design_file_url?: string | null;` (line 49, added in previous session)

### 2. Revert `design_file_url` from demo data — `cms/apps/web/src/lib/demo/data/briefs.ts`
- Remove all `design_file_url` properties from `DEMO_BRIEF_ITEMS` and `DEMO_BRIEF_DETAILS`
- Revert resource URLs for items with IDs **101, 102, 104, 301, 401** (the 5 items that had Figma/Sketch URLs added) — set their design-type resource URLs back to `"#"`
- Keep everything else (the demo data itself is correct and needed)

### 3. Replace external link with sync button on card — `cms/apps/web/src/components/briefs/brief-campaign-card.tsx`

**New props:**
```tsx
interface BriefCampaignCardProps {
  item: BriefItem;
  onClick: () => void;
  designConnection?: DesignConnection | null;  // NEW
  onSyncDesign?: (connectionId: number) => void;  // NEW
  onConnectDesign?: () => void;  // NEW
}
```

**Replace** the "Open in Figma" `<a>` block (currently between meta row and resources) with:
```tsx
{designConnection ? (
  <button
    type="button"
    onClick={(e) => { e.stopPropagation(); onSyncDesign?.(designConnection.id); }}
    className="flex items-center gap-2 rounded-md border border-interactive/20 bg-interactive/5 px-3 py-2 text-xs font-medium text-interactive transition-colors hover:bg-interactive/10"
  >
    <Puzzle className="h-3.5 w-3.5" />
    Sync & Extract Components
    <ArrowRight className="ml-auto h-3 w-3" />
  </button>
) : onConnectDesign ? (
  <button
    type="button"
    onClick={(e) => { e.stopPropagation(); onConnectDesign(); }}
    className="flex items-center gap-2 rounded-md border border-dashed border-foreground-muted/30 px-3 py-2 text-xs text-foreground-muted transition-colors hover:border-interactive/40 hover:text-interactive"
  >
    <LinkIcon className="h-3.5 w-3.5" />
    Connect Design File
  </button>
) : null}
```

**Imports:** Replace `PenTool, ExternalLink` with `Puzzle, ArrowRight, Link as LinkIcon` from lucide-react. Import `DesignConnection` from `@/types/design-sync`.

### 4. Replace external link with sync action in detail dialog — `cms/apps/web/src/components/briefs/brief-detail-dialog.tsx`

**New props:**
```tsx
interface BriefDetailDialogProps {
  itemId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  designConnection?: DesignConnection | null;  // NEW
  onSyncDesign?: (connectionId: number) => void;  // NEW
  onConnectDesign?: () => void;  // NEW
}
```

**Replace** the "Open Design in Figma" `<a>` block (between description and resources) with:
```tsx
{designConnection ? (
  <button
    type="button"
    onClick={() => onSyncDesign?.(designConnection.id)}
    className="flex items-center gap-2 rounded-md border border-interactive/20 bg-interactive/5 px-4 py-3 text-sm font-medium text-interactive transition-colors hover:bg-interactive/10"
  >
    <Puzzle className="h-4 w-4" />
    Sync & Extract Components
    <span className="ml-auto text-xs text-foreground-muted">
      {designConnection.provider === "figma" ? "from Figma" :
       designConnection.provider === "sketch" ? "from Sketch" :
       `from ${designConnection.provider}`}
    </span>
  </button>
) : onConnectDesign ? (
  <button
    type="button"
    onClick={onConnectDesign}
    className="flex items-center gap-2 rounded-md border border-dashed border-foreground-muted/30 px-4 py-3 text-sm text-foreground-muted transition-colors hover:border-interactive/40 hover:text-interactive"
  >
    <LinkIcon className="h-4 w-4" />
    Connect Design File
  </button>
) : null}
```

**Imports:** Replace `PenTool` with `Puzzle, Link as LinkIcon`. Import `DesignConnection` from `@/types/design-sync`.

### 5. Wire design connection lookup into overview — `cms/apps/web/src/components/briefs/briefs-overview.tsx`

This is the main orchestration point. Changes:

1. **Import** `useDesignConnections` from `@/hooks/use-design-sync`
2. **Import** `DesignImportDialog` from `@/components/design-sync/design-import-dialog`
3. **Import** `ConnectDesignDialog` from `@/components/design-sync/connect-design-dialog`
4. **Import** `DesignConnection` from `@/types/design-sync`
5. **Import** `BriefItem` from `@/types/briefs` (add to existing import)

6. **Fetch design connections:**
```tsx
const { data: designConnections } = useDesignConnections();
```

7. **Build project→designConnection lookup (useMemo):**
```tsx
const designConnectionByProject = useMemo(() => {
  const map = new Map<number, DesignConnection>();
  for (const dc of designConnections ?? []) {
    if (dc.project_id != null) map.set(dc.project_id, dc);
  }
  return map;
}, [designConnections]);
```

8. **Helper to resolve design connection for a brief item:**
```tsx
const getDesignConnection = (item: BriefItem): DesignConnection | null => {
  const briefConn = connections?.find(c => c.id === item.connection_id);
  if (!briefConn?.project_id) return null;
  return designConnectionByProject.get(briefConn.project_id) ?? null;
};
```

9. **Add state for dialogs:**
```tsx
const [syncConnection, setSyncConnection] = useState<DesignConnection | null>(null);
const [showConnectDialog, setShowConnectDialog] = useState(false);
```

10. **Pass props to `BriefCampaignCard`:**
```tsx
<BriefCampaignCard
  key={item.id}
  item={item}
  onClick={() => setSelectedItemId(item.id)}
  designConnection={getDesignConnection(item)}
  onSyncDesign={(connId) => {
    const dc = designConnections?.find(c => c.id === connId) ?? null;
    setSyncConnection(dc);
  }}
  onConnectDesign={() => setShowConnectDialog(true)}
/>
```

11. **Pass same props to `BriefDetailDialog`** (use unfiltered `items` to avoid filter-out bugs):
```tsx
<BriefDetailDialog
  itemId={selectedItemId}
  open={selectedItemId !== null}
  onOpenChange={(open) => { if (!open) setSelectedItemId(null); }}
  designConnection={selectedItemId ? getDesignConnection(items?.find(i => i.id === selectedItemId) ?? null as unknown as BriefItem) : null}
  onSyncDesign={(connId) => {
    setSelectedItemId(null);
    const dc = designConnections?.find(c => c.id === connId) ?? null;
    setSyncConnection(dc);
  }}
  onConnectDesign={() => { setSelectedItemId(null); setShowConnectDialog(true); }}
/>
```

**NOTE:** The `designConnection` prop lookup should use the unfiltered `items` array (not `filteredItems`) to avoid null reference when a selected item gets filtered out by client filter. Cleaner approach — extract to a variable before JSX:
```tsx
const selectedItem = items?.find(i => i.id === selectedItemId) ?? null;
// then in JSX:
designConnection={selectedItem ? getDesignConnection(selectedItem) : null}
```

12. **Render dialogs at bottom:**
```tsx
{syncConnection && (
  <DesignImportDialog
    open
    onOpenChange={(open) => { if (!open) setSyncConnection(null); }}
    connectionId={syncConnection.id}
    connectionName={syncConnection.name}
    initialTab="components"
  />
)}
<ConnectDesignDialog
  open={showConnectDialog}
  onOpenChange={setShowConnectDialog}
/>
```

### 6. Wire design connection into items panel — `cms/apps/web/src/components/briefs/brief-items-panel.tsx`

Add similar design connection resolution for the detail dialog rendered inside this panel. The panel already has the `BriefConnection`, so it can look up design connection by `connection.project_id`.

**Add props:**
```tsx
interface BriefItemsPanelProps {
  connection: BriefConnection;
  designConnection?: DesignConnection | null;  // NEW — passed from parent
}
```

Pass `designConnection` through to the `BriefDetailDialog` inside this panel. Add `onSyncDesign` / `onConnectDesign` handlers + `DesignImportDialog` / `ConnectDesignDialog` state management (same pattern as overview).

### Keep `brief-resource-links.tsx` as-is
The `PenTool` icon for design resources is correct — no changes needed.

## Known Limitations

1. **`ConnectDesignDialog` creates orphan connections** — When a user clicks "Connect Design File" on a brief with `project_id: null`, the dialog creates a new design connection but has no context about which project to associate it with. The new connection won't automatically link back to the brief. Future improvement: pass `project_id` to `ConnectDesignDialog` so it auto-associates.

2. **Design conn 3 (Sketch) is `status: "disconnected"`** — Brief items under conn 3 will show "Sync & Extract Components", but clicking it opens `DesignImportDialog` for a disconnected connection. Verify the dialog handles this gracefully (shows reconnect prompt).

## Files NOT Changed
- `.env.local` — already fixed to `true` (keep)
- Demo resolvers — already handle all design-sync endpoints
- Hooks — `useDesignConnections` already exists
- `design-import-dialog.tsx` — already supports `initialTab="components"`

## Security Checklist
N/A — no new API endpoints, backend changes, or auth modifications. This is a frontend-only UI wiring change.

## Verification

1. `make check-fe` — type-check + unit tests pass
2. `make dev` → navigate to Briefs
3. Brief items under conn 1 (O2, project 1) show **"Sync & Extract Components"** button
4. Brief items under conn 3 (Virgin Media, project 3) show **"Sync & Extract Components"** button
5. Brief items under conns 2, 4 (HSBC, Lloyds — no project link) show **"Connect Design File"** dashed button
6. Click "Sync & Extract" → `DesignImportDialog` opens on "Extract Components" tab with component grid
7. Select components → click "Extract Selected" → success → "View in Component Library"
8. Click "Connect Design File" → `ConnectDesignDialog` opens with provider/URL/token form
