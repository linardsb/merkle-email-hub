# Plan: Fix New Project → Workspace Landing (Demo Mode)

## Context

When a user creates a new project via the Create Project dialog, they get navigated to `/projects/{id}/workspace`. In demo mode, the mutation resolver returns a project with a **random ID** (e.g., 7678). The workspace page then calls `useProject(7678)` → the GET demo resolver looks up `DEMO_PROJECTS.find(p => p.id === 7678)` → **not found** → shows "Project not found".

The root cause: demo mode mutations create entities with random IDs that the GET resolver can't find because they're not in the static demo data arrays.

## Strategy

Add a lightweight **runtime demo store** that bridges mutations and reads. When the mutation resolver creates a project (or template/version), it writes the response to the store. When the GET resolver can't find an entity in static data, it checks the store.

This is the minimal fix — the workspace page already handles empty template lists gracefully (shows default template boilerplate), so we only need to make the project lookup succeed.

## Files to Create/Modify

1. **Create** `cms/apps/web/src/lib/demo/demo-store.ts` — In-memory runtime store for dynamically created demo entities
2. **Modify** `cms/apps/web/src/lib/demo/mutation-resolver.ts` — Write created projects, templates, and versions to the store
3. **Modify** `cms/apps/web/src/lib/demo/resolver.ts` — Fall back to the store when static data doesn't match

## Implementation Steps

### Step 1: Create `demo-store.ts`

Create `cms/apps/web/src/lib/demo/demo-store.ts`:

```ts
/**
 * Runtime in-memory store for demo mode.
 * Bridges mutations (POST) and reads (GET) so that dynamically
 * created entities are visible to subsequent fetches.
 * Data lives only for the current browser session (page reload clears it).
 */

import type { ProjectResponse } from "@email-hub/sdk";
import type { TemplateResponse, VersionResponse } from "@/types/templates";

const projects: ProjectResponse[] = [];
const templates: TemplateResponse[] = [];
const versions: VersionResponse[] = [];

export const demoStore = {
  // ── Projects ──
  addProject(p: ProjectResponse) {
    projects.push(p);
  },
  findProject(id: number): ProjectResponse | undefined {
    return projects.find((p) => p.id === id);
  },
  allProjects(): ProjectResponse[] {
    return projects;
  },

  // ── Templates ──
  addTemplate(t: TemplateResponse) {
    templates.push(t);
  },
  findTemplate(id: number): TemplateResponse | undefined {
    return templates.find((t) => t.id === id);
  },
  templatesForProject(projectId: number): TemplateResponse[] {
    return templates.filter((t) => t.project_id === projectId);
  },

  // ── Versions ──
  addVersion(v: VersionResponse) {
    versions.push(v);
  },
  versionsForTemplate(templateId: number): VersionResponse[] {
    return versions.filter((v) => v.template_id === templateId);
  },
  findVersion(templateId: number, versionNumber: number): VersionResponse | undefined {
    return versions.find(
      (v) => v.template_id === templateId && v.version_number === versionNumber,
    );
  },
};
```

### Step 2: Update `mutation-resolver.ts`

Import the store and write to it on project/template/version creation:

**2a.** Add import at top:
```ts
import { demoStore } from "./demo-store";
```

**2b.** In the "Create project" handler (line ~223), after building the response object, add it to the store:
```ts
// Create project
if (p === "/api/v1/projects") {
  const body = _body as Record<string, unknown> | null;
  const project = {
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
  demoStore.addProject(project as any);
  return project;
}
```

**2c.** In the "Create template" handler (line ~89), extract the project_id from the URL and store:
```ts
// Create template
if (p.match(/^\/api\/v1\/projects\/\d+\/templates$/)) {
  const projectId = parseInt(p.match(/\/projects\/(\d+)\//)![1]!, 10);
  const body = _body as Record<string, unknown> | null;
  const template = {
    id: Math.floor(Math.random() * 10000) + 100,
    project_id: projectId,
    name: body?.name ?? "New Template",
    description: null,
    subject_line: null,
    preheader_text: null,
    status: "draft",
    created_by_id: 1,
    latest_version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  demoStore.addTemplate(template as any);
  return template;
}
```

**2d.** In the "Save version" handler (line ~106), store the version with the HTML source:
```ts
// Save version
if (p.match(/^\/api\/v1\/templates\/\d+\/versions$/)) {
  const templateId = parseInt(p.match(/\/templates\/(\d+)\//)![1]!, 10);
  const body = _body as Record<string, unknown> | null;
  const existingVersions = demoStore.versionsForTemplate(templateId);
  const nextVersion = existingVersions.length + 1;
  const version = {
    id: Math.floor(Math.random() * 10000) + 100,
    template_id: templateId,
    version_number: nextVersion,
    html_source: body?.html_source ?? "",
    css_source: null,
    changelog: `v${nextVersion} save`,
    created_by_id: 1,
    created_at: new Date().toISOString(),
  };
  demoStore.addVersion(version as any);
  return version;
}
```

### Step 3: Update `resolver.ts`

Import the store and check it as fallback:

**3a.** Add import at top:
```ts
import { demoStore } from "./demo-store";
```

**3b.** In the projects list handler, merge runtime projects:
```ts
// Projects list
if (p === "/api/v1/projects") {
  const search = url.searchParams.get("search");
  const allProjects = [...DEMO_PROJECTS, ...demoStore.allProjects()];
  return paginate(filterBySearch(allProjects, search), url);
}
```

**3c.** In the single project handler, add store fallback:
```ts
m = p.match(/^\/api\/v1\/projects\/(\d+)$/);
if (m) {
  const id = matchId(m, 1);
  return DEMO_PROJECTS.find((proj) => proj.id === id) ?? demoStore.findProject(id) ?? null;
}
```

**3d.** In the templates list handler, merge runtime templates:
```ts
m = p.match(/^\/api\/v1\/projects\/(\d+)\/templates$/);
if (m) {
  const projectId = matchId(m, 1);
  const search = url.searchParams.get("search");
  const status = url.searchParams.get("status");
  let templates = [
    ...DEMO_TEMPLATES.filter((t) => t.project_id === projectId),
    ...demoStore.templatesForProject(projectId),
  ];
  if (search) templates = filterBySearch(templates, search);
  if (status) templates = templates.filter((t) => t.status === status);
  return paginate(templates, url);
}
```

**3e.** In the single template handler, add store fallback:
```ts
m = p.match(/^\/api\/v1\/templates\/(\d+)$/);
if (m) {
  const id = matchId(m!, 1);
  return DEMO_TEMPLATES.find((t) => t.id === id) ?? demoStore.findTemplate(id) ?? null;
}
```

**3f.** In the template versions list handler, merge runtime versions:
```ts
m = p.match(/^\/api\/v1\/templates\/(\d+)\/versions$/);
if (m) {
  const templateId = matchId(m, 1);
  return [
    ...DEMO_VERSIONS.filter((v) => v.template_id === templateId),
    ...demoStore.versionsForTemplate(templateId),
  ];
}
```

**3g.** In the single version handler, add store fallback:
```ts
m = p.match(/^\/api\/v1\/templates\/(\d+)\/versions\/(\d+)$/);
if (m) {
  const templateId = matchId(m, 1);
  const versionNum = matchId(m, 2);
  return (
    DEMO_VERSIONS.find(
      (v) => v.template_id === templateId && v.version_number === versionNum,
    ) ??
    demoStore.findVersion(templateId, versionNum) ??
    null
  );
}
```

## Verification

- [ ] Create a new project via the dashboard dialog → lands on workspace with project name visible in toolbar
- [ ] Workspace shows empty editor with default template boilerplate (no "Project not found")
- [ ] Creating a template in the workspace works (save + reload doesn't break)
- [ ] Existing demo projects (IDs 1-4) continue working as before
- [ ] Projects page shows both static + dynamically created projects
- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
