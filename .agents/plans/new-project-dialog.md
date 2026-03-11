# Plan: New Project Creation Dialog

## Context

The "New Project" button exists on both the Dashboard (`/`) and Projects (`/projects`) pages but is completely non-functional — no `onClick` handler. We need a comprehensive project creation dialog that lets users configure everything upfront: naming, client org, category, creation method (blank, AI-assisted, from existing), and initial setup preferences. After creation, the user should land directly in the workspace ready to work.

## UX Flow Design

### Dialog Structure: Single-Page with Method Cards

A **single dialog** (not a multi-step wizard) with two logical sections:

**Section 1 — Project Details** (always visible)
- Project name (required, text input)
- Description (optional, textarea)
- Client organization (required, select from `useOrgs()`)
- Category (select: `promotional`, `transactional`, `newsletter`, `welcome_series`, `automated`, `other`)
- Target ESP (optional select: Braze, SFMC, Adobe Campaign, Taxi, Raw HTML — from `ConnectorPlatform`)

**Section 2 — Creation Method** (radio cards with conditional sub-options)
Four method cards as large radio-style selectors:

1. **Start from Scratch** — Blank Maizzle template, opens workspace editor immediately
2. **AI Scaffolder** — Provide a campaign brief, AI generates the initial template
   - Shows a textarea for the campaign brief when selected
3. **Pick from Components** — Start with pre-selected component blocks
   - Shows a scrollable checkbox grid of available components (from `useComponents()`)
4. **Clone Existing** — Duplicate a template from another project
   - Shows a select dropdown of existing projects/templates

### Post-Creation Landing Strategy

All paths lead to the **workspace** (`/projects/{id}/workspace`), but with different query params to trigger context-appropriate behavior:

| Method | Landing URL | Behavior |
|--------|------------|----------|
| Blank | `/projects/{id}/workspace` | Workspace creates default blank template, editor ready |
| AI Scaffolder | `/projects/{id}/workspace?agent=scaffolder` | Workspace opens with AI chat panel focused, scaffolder agent pre-selected |
| From Components | `/projects/{id}/workspace?components=1,3,7` | Workspace creates template with selected component boilerplate inserted |
| Clone Existing | `/projects/{id}/workspace` | Template already cloned during creation, workspace loads it |

The workspace already handles the "no templates" state by auto-creating a blank template with `DEFAULT_TEMPLATE`. For AI scaffolder, we just need to honor the `?agent=scaffolder` query param to auto-open the chat with scaffolder pre-selected.

## Files to Create/Modify

### New Files
1. `cms/apps/web/src/components/dashboard/create-project-dialog.tsx` — The dialog component
2. `cms/apps/web/src/types/projects.ts` — Project category type + creation method type

### Modified Files
3. `cms/apps/web/src/hooks/use-projects.ts` — Add `useCreateProject()` mutation hook
4. `cms/apps/web/src/lib/demo/mutation-resolver.ts` — Add `POST /api/v1/projects` demo handler
5. `cms/apps/web/src/app/[locale]/(dashboard)/page.tsx` — Wire dialog to "New Project" button
6. `cms/apps/web/src/app/[locale]/(dashboard)/projects/page.tsx` — Wire dialog to "New Project" button (same treatment)
7. `cms/apps/web/messages/en.json` — Add ~30 i18n keys under `dashboard` namespace
8. `cms/apps/web/src/app/[locale]/projects/[id]/workspace/page.tsx` — Honor `?agent=` query param to pre-select AI agent

## Implementation Steps

### Step 1: Create project types (`cms/apps/web/src/types/projects.ts`)

```typescript
export type ProjectCategory =
  | "promotional"
  | "transactional"
  | "newsletter"
  | "welcome_series"
  | "automated"
  | "other";

export type CreationMethod = "blank" | "ai_scaffolder" | "from_components" | "clone_existing";
```

### Step 2: Add `useCreateProject` hook to `use-projects.ts`

Add to the existing file, following the `useCreatePersona` pattern:

```typescript
import useSWRMutation from "swr/mutation";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ProjectCreate, ProjectResponse } from "@email-hub/sdk";

export function useCreateProject() {
  return useSWRMutation<ProjectResponse, Error, string, ProjectCreate>(
    "/api/v1/projects",
    mutationFetcher
  );
}
```

### Step 3: Add demo mutation handler in `mutation-resolver.ts`

Add before the `return null` at the bottom:

```typescript
// Create project
if (p === "/api/v1/projects") {
  const body = _body as Record<string, unknown> | null;
  return {
    id: Math.floor(Math.random() * 10000) + 100,
    name: body?.name ?? "New Project",
    description: body?.description ?? null,
    client_org_id: body?.client_org_id ?? 1,
    status: "draft",
    created_by_id: 1,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}
```

### Step 4: Add i18n keys to `en.json`

Add under the `"dashboard"` namespace:

```json
"newProjectTitle": "Create New Project",
"newProjectDescription": "Set up a new email project with your preferred starting point.",
"newProjectName": "Project Name",
"newProjectNamePlaceholder": "e.g., Q2 Summer Campaign",
"newProjectDescriptionField": "Description",
"newProjectDescriptionPlaceholder": "Brief overview of this email project...",
"newProjectOrg": "Client Organization",
"newProjectOrgPlaceholder": "Select organization",
"newProjectCategory": "Category",
"newProjectCategoryPromotional": "Promotional",
"newProjectCategoryTransactional": "Transactional",
"newProjectCategoryNewsletter": "Newsletter",
"newProjectCategoryWelcomeSeries": "Welcome Series",
"newProjectCategoryAutomated": "Automated",
"newProjectCategoryOther": "Other",
"newProjectTargetEsp": "Target ESP",
"newProjectTargetEspNone": "Decide later",
"newProjectMethod": "How do you want to start?",
"newProjectMethodBlank": "Start from Scratch",
"newProjectMethodBlankDescription": "Empty Maizzle template — full creative control",
"newProjectMethodAI": "AI Scaffolder",
"newProjectMethodAIDescription": "Describe your campaign and let AI generate the initial template",
"newProjectMethodAIBrief": "Campaign Brief",
"newProjectMethodAIBriefPlaceholder": "Describe the campaign: audience, goal, tone, key content sections...",
"newProjectMethodComponents": "From Components",
"newProjectMethodComponentsDescription": "Pick from the component library to assemble your starting blocks",
"newProjectMethodComponentsSelect": "Select components to include:",
"newProjectMethodClone": "Clone Existing",
"newProjectMethodCloneDescription": "Duplicate a template from another project as your starting point",
"newProjectMethodCloneSelect": "Select project to clone from:",
"newProjectCancel": "Cancel",
"newProjectSubmit": "Create Project",
"newProjectSubmitting": "Creating...",
"newProjectSuccess": "Project created successfully",
"newProjectError": "Failed to create project"
```

### Step 5: Build the dialog component (`create-project-dialog.tsx`)

**File:** `cms/apps/web/src/components/dashboard/create-project-dialog.tsx`

```
"use client";

imports:
  - useState from react
  - useTranslations from next-intl
  - useRouter, useLocale from next/navigation (for navigation after create)
  - Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription from ui
  - Loader2, FileText, Wand2, Blocks, Copy from lucide-react
  - toast from sonner
  - useSWRConfig from swr
  - useCreateProject from hooks/use-projects
  - useOrgs from hooks/use-orgs
  - useComponents from hooks/use-components
  - useProjects from hooks/use-projects
  - type ConnectorPlatform from types/connectors
  - type ProjectCategory, CreationMethod from types/projects
```

**Component structure:**

```
Props: { open, onOpenChange }

State:
  - name: string (required)
  - description: string
  - clientOrgId: number | null
  - category: ProjectCategory ("promotional" default)
  - targetEsp: ConnectorPlatform | "" (optional)
  - method: CreationMethod ("blank" default)
  - aiBrief: string (for scaffolder method)
  - selectedComponents: number[] (for components method)
  - cloneProjectId: number | null (for clone method)

Form reset: prevOpen pattern (no useEffect)

Validation: name.trim().length >= 1 && clientOrgId !== null

Submit handler:
  1. trigger({ name, description, client_org_id: clientOrgId })
  2. mutate projects SWR cache
  3. toast.success
  4. Build query string based on method:
     - blank: no params
     - ai_scaffolder: ?agent=scaffolder
     - from_components: ?components=1,3,7
     - clone_existing: no params (clone handled separately)
  5. router.push(`/${locale}/projects/${newProject.id}/workspace${queryString}`)
  6. onOpenChange(false)
```

**Layout (inside DialogContent, max-w-[36rem]):**

```
DialogHeader (title + description)

Section 1: Project Details
  - Name input (full width)
  - Description textarea (full width, 3 rows)
  - Org select + Category select (2-col grid)
  - Target ESP select (full width, optional)

Separator/spacing

Section 2: Creation Method
  - "How do you want to start?" label
  - 2x2 grid of method cards (radio-style), each with:
    - Icon (top-left)
    - Title (bold)
    - Description (muted text)
    - Selected state: border-interactive ring
    - Unselected state: border-card-border

  Conditional sub-options (below cards, only when relevant method selected):
  - AI Scaffolder → textarea for brief
  - From Components → scrollable checkbox list of components (max-h-[10rem])
  - Clone Existing → select from existing projects

Footer: Cancel + Create Project buttons
```

**Styling rules:**
- All inputs use the `inputClass` / `selectClass` pattern from CreatePersonaDialog
- Method cards: `rounded-lg border-2 p-4 cursor-pointer transition-colors`
  - Selected: `border-interactive bg-interactive/5`
  - Unselected: `border-card-border bg-card-bg hover:bg-surface-hover`
- Semantic tokens only (no primitive colors)
- All text via `useTranslations("dashboard")`

### Step 6: Wire the dialog to Dashboard page (`page.tsx`)

In `cms/apps/web/src/app/[locale]/(dashboard)/page.tsx`:

1. Add import: `import { CreateProjectDialog } from "@/components/dashboard/create-project-dialog";`
2. Add state: `const [createOpen, setCreateOpen] = useState(false);`
3. Add `onClick={() => setCreateOpen(true)}` to the existing button
4. Add `<CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />` before closing `</div>`

### Step 7: Wire the dialog to Projects page (`projects/page.tsx`)

Same treatment as Step 6 for `cms/apps/web/src/app/[locale]/(dashboard)/projects/page.tsx`.

### Step 8: Honor `?agent=` query param in workspace page

In `cms/apps/web/src/app/[locale]/projects/[id]/workspace/page.tsx`:

The workspace already reads `useSearchParams()`. Add logic to check for `agent` param and use it to pre-select the agent mode and auto-expand the chat panel:

```typescript
const agentParam = searchParams.get("agent");

// In the existing agent/chat state initialization:
// If agentParam is a valid AgentMode, set it as initial agent
// Also set chat panel to visible/expanded
```

This is a lightweight change — just read the param and set initial state.

### Step 9: Honor `?components=` query param (stretch)

If `components` param is present, the workspace could pre-populate the template with those component HTML blocks. This can be deferred to a follow-up since it requires component HTML lookup and template assembly. For now, just navigate to workspace and let the user insert components manually.

## Verification

- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] All user-visible text uses `useTranslations("dashboard")`
- [ ] Semantic Tailwind tokens only (no primitive colors)
- [ ] Dialog opens from both Dashboard and Projects page buttons
- [ ] Form validation prevents submit without name + org
- [ ] Method cards toggle correctly with visual feedback
- [ ] AI Scaffolder brief textarea appears only when AI method selected
- [ ] Component picker appears only when Components method selected
- [ ] Clone project selector appears only when Clone method selected
- [ ] Project creates successfully in demo mode (toast confirmation)
- [ ] User navigates to workspace after creation
- [ ] `?agent=scaffolder` query param pre-selects scaffolder in workspace chat
- [ ] Form resets when dialog reopens
- [ ] Cancel button closes dialog without side effects
- [ ] Loading state shows spinner during mutation
