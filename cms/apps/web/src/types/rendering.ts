/**
 * Rendering types — re-exported from SDK.
 * Frontend-only types kept locally.
 */
export type {
  ScreenshotResult,
  RenderingTestResponse as RenderingTest,
  RenderingTestRequest,
  RenderingComparisonRequest,
  RenderingDiff,
  RenderingComparisonResponse,
  PaginatedResponseRenderingTestResponse,
} from "@email-hub/sdk";

/** @deprecated Use PaginatedResponseRenderingTestResponse from SDK */
export type PaginatedRenderingTests = {
  items: import("@email-hub/sdk").RenderingTestResponse[];
  total: number;
  page: number;
  page_size: number;
};

// ── Screenshot types (17.1) ────────────────────────────────
export interface ScreenshotRequest {
  html: string;
  clients?: string[];
}

export interface ClientScreenshot {
  client_name: string;
  image_base64: string;
  viewport: string;
  browser: string;
}

export interface ScreenshotResponse {
  screenshots: ClientScreenshot[];
  clients_rendered: number;
  clients_failed: number;
}

// ── Visual Diff types (17.2) ───────────────────────────────
export interface VisualDiffRequest {
  baseline_image: string;
  current_image: string;
  threshold?: number;
}

export interface ChangedRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VisualDiffResponse {
  identical: boolean;
  diff_percentage: number;
  diff_image: string | null;
  pixel_count: number;
  changed_regions: ChangedRegion[];
  threshold_used: number;
}

// ── Baseline types (17.2) ──────────────────────────────────
export interface BaselineResponse {
  id: number;
  entity_type: string;
  entity_id: number;
  client_name: string;
  image_hash: string;
  created_at: string;
  updated_at: string;
}

export interface BaselineListResponse {
  entity_type: string;
  entity_id: number;
  baselines: BaselineResponse[];
}

export interface BaselineUpdateRequest {
  client_name: string;
  image_base64: string;
}

// ── VLM Defect types (17.3 — stub, not wired yet) ─────────
export interface DefectAnnotationData {
  region: ChangedRegion;
  severity: "critical" | "major" | "minor" | "info";
  description: string;
  suggested_fix?: string;
}

export type ClientProfile =
  | "gmail_web"
  | "outlook_2019"
  | "apple_mail"
  | "outlook_dark"
  | "mobile_ios";

export const CLIENT_DISPLAY_NAMES: Record<ClientProfile, string> = {
  gmail_web: "Gmail Web",
  outlook_2019: "Outlook 2019",
  apple_mail: "Apple Mail",
  outlook_dark: "Outlook Dark",
  mobile_ios: "Mobile iOS",
};

export type VisualQAEntityType = "component_version" | "golden_template";
