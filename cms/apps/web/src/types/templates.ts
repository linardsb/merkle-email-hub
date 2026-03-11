/**
 * Template types — re-exported from SDK.
 * Frontend-only types kept locally.
 */
export type {
  TemplateResponse,
  TemplateCreate,
  TemplateUpdate,
  PaginatedResponseTemplateResponse,
} from "@email-hub/sdk";
export { type AppTemplatesSchemasVersionResponse as VersionResponse } from "@email-hub/sdk";
export { type AppTemplatesSchemasVersionCreate as VersionCreate } from "@email-hub/sdk";

/** @deprecated Use PaginatedResponseTemplateResponse from SDK */
export type PaginatedTemplates = {
  items: import("@email-hub/sdk").TemplateResponse[];
  total: number;
  page: number;
  page_size: number;
};
