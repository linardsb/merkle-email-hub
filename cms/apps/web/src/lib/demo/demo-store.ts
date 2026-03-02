/**
 * Runtime in-memory store for demo mode.
 * Bridges mutations (POST) and reads (GET) so that dynamically
 * created entities are visible to subsequent fetches.
 * Data lives only for the current browser session (page reload clears it).
 */

import type { ProjectResponse } from "@merkle-email-hub/sdk";
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
  findVersion(
    templateId: number,
    versionNumber: number,
  ): VersionResponse | undefined {
    return versions.find(
      (v) =>
        v.template_id === templateId && v.version_number === versionNumber,
    );
  },
};
