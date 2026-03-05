// ── Backend-aligned types (matches app/rendering/schemas.py) ──

export interface ScreenshotResult {
  client_name: string;
  screenshot_url: string | null;
  os: string;
  category: string; // "desktop" | "mobile" | "web" | "dark_mode"
  status: "pending" | "complete" | "failed";
}

export interface RenderingTest {
  id: number;
  external_test_id: string;
  provider: string;
  status: "pending" | "processing" | "complete" | "failed";
  build_id: number | null;
  template_version_id: number | null;
  clients_requested: number;
  clients_completed: number;
  screenshots: ScreenshotResult[];
  created_at: string;
}

export interface RenderingTestRequest {
  html: string;
  subject?: string;
  clients?: string[];
  build_id?: number | null;
  template_version_id?: number | null;
}

export interface RenderingComparisonRequest {
  baseline_test_id: number;
  current_test_id: number;
}

export interface RenderingDiff {
  client_name: string;
  diff_percentage: number;
  has_regression: boolean;
  baseline_url: string | null;
  current_url: string | null;
}

export interface RenderingComparisonResponse {
  baseline_test_id: number;
  current_test_id: number;
  total_clients: number;
  regressions_found: number;
  diffs: RenderingDiff[];
}

export interface PaginatedRenderingTests {
  items: RenderingTest[];
  total: number;
  page: number;
  page_size: number;
}
