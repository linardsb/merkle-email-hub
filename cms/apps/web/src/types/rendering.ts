export type RenderingProvider = "litmus" | "email_on_acid";
export type RenderingClientCategory = "desktop" | "webmail" | "mobile";
export type RenderingClientPlatform = "windows" | "macos" | "linux" | "web" | "ios" | "android";

export interface RenderingClient {
  id: string;
  name: string;
  category: RenderingClientCategory;
  platform: RenderingClientPlatform;
  market_share: number;
}

export type RenderingTestStatus = "queued" | "processing" | "completed" | "failed";
export type RenderingResultStatus = "pass" | "warning" | "fail" | "pending";

export type RenderingIssueType =
  | "missing_background"
  | "clipped_content"
  | "dark_mode_inversion"
  | "font_fallback"
  | "layout_shift"
  | "image_blocking"
  | "spacing_mismatch"
  | "alignment_error";

export type RenderingIssueSeverity = "critical" | "major" | "minor";

export interface RenderingIssue {
  type: RenderingIssueType;
  severity: RenderingIssueSeverity;
  description: string;
  affected_area: string;
}

export interface RenderingResult {
  client_id: string;
  status: RenderingResultStatus;
  screenshot_url: string;
  load_time_ms: number;
  issues: RenderingIssue[];
}

export interface RenderingTest {
  id: number;
  build_id: number | null;
  template_name: string;
  provider: RenderingProvider;
  status: RenderingTestStatus;
  clients_requested: string[];
  results: RenderingResult[];
  compatibility_score: number;
  created_at: string;
  completed_at: string | null;
}

export interface RenderingComparison {
  test_id_baseline: number;
  test_id_current: number;
  client_id: string;
  baseline_url: string;
  current_url: string;
  diff_percentage: number;
  status: "identical" | "minor_diff" | "major_diff";
}

export interface RenderingTestRequest {
  build_id?: number | null;
  provider: RenderingProvider;
  client_ids: string[];
  html?: string;
}

export interface PaginatedRenderingTests {
  items: RenderingTest[];
  total: number;
  page: number;
  page_size: number;
}

export interface RenderingDashboardSummary {
  latest_score: number;
  total_tests: number;
  problematic_clients: { client_id: string; client_name: string; fail_rate: number }[];
  last_test_date: string;
}
