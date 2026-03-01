/**
 * Local TypeScript types for template API.
 * Mirrors app/templates/schemas.py.
 * TODO: Replace with SDK types after next openapi-ts regeneration.
 */

export interface TemplateResponse {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
  subject_line: string | null;
  preheader_text: string | null;
  status: "draft" | "active" | "archived";
  created_by_id: number;
  latest_version: number | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateCreate {
  name: string;
  description?: string | null;
  subject_line?: string | null;
  preheader_text?: string | null;
  html_source: string;
  css_source?: string | null;
}

export interface TemplateUpdate {
  name?: string;
  description?: string | null;
  subject_line?: string | null;
  preheader_text?: string | null;
  status?: "draft" | "active" | "archived";
}

export interface VersionResponse {
  id: number;
  template_id: number;
  version_number: number;
  html_source: string;
  css_source: string | null;
  changelog: string | null;
  created_by_id: number;
  created_at: string;
}

export interface VersionCreate {
  html_source: string;
  css_source?: string | null;
  changelog?: string | null;
}

export interface PaginatedTemplates {
  items: TemplateResponse[];
  total: number;
  page: number;
  page_size: number;
}
