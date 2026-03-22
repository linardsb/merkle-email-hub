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
  | "gmail_web_dark"
  | "outlook_web"
  | "outlook_web_dark"
  | "apple_mail"
  | "apple_mail_dark"
  | "mobile_ios"
  | "mobile_ios_dark"
  | "yahoo_web"
  | "yahoo_mobile"
  | "samsung_mail"
  | "samsung_mail_dark"
  | "outlook_desktop"
  | "thunderbird";

export const CLIENT_DISPLAY_NAMES: Record<ClientProfile, string> = {
  gmail_web: "Gmail Web",
  gmail_web_dark: "Gmail Web (Dark)",
  outlook_web: "Outlook.com",
  outlook_web_dark: "Outlook.com (Dark)",
  apple_mail: "Apple Mail",
  apple_mail_dark: "Apple Mail (Dark)",
  mobile_ios: "Mobile iOS",
  mobile_ios_dark: "Mobile iOS (Dark)",
  yahoo_web: "Yahoo Web",
  yahoo_mobile: "Yahoo Mobile",
  samsung_mail: "Samsung Mail",
  samsung_mail_dark: "Samsung Mail (Dark)",
  outlook_desktop: "Outlook Desktop",
  thunderbird: "Thunderbird",
};

/** Approximate market share per client for summary bar segment widths. */
export const CLIENT_MARKET_SHARE: Partial<Record<ClientProfile, number>> = {
  gmail_web: 0.15,
  gmail_web_dark: 0.15,
  outlook_web: 0.05,
  outlook_web_dark: 0.05,
  apple_mail: 0.14,
  apple_mail_dark: 0.14,
  mobile_ios: 0.07,
  mobile_ios_dark: 0.03,
  yahoo_web: 0.04,
  yahoo_mobile: 0.02,
  samsung_mail: 0.03,
  samsung_mail_dark: 0.02,
  outlook_desktop: 0.07,
  thunderbird: 0.04,
};

export type VisualQAEntityType = "component_version" | "golden_template";
