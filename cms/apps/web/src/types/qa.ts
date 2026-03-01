/** Result of a single QA check. */
export interface QACheckResult {
  check_name: string;
  passed: boolean;
  score: number;
  details?: string | null;
  severity?: string;
}

/** Override attached to a QA result. */
export interface QAOverrideResponse {
  id: number;
  qa_result_id: number;
  overridden_by_id: number;
  justification: string;
  checks_overridden: string[];
  created_at: string;
}

/** Full QA result with checks and optional override. */
export interface QAResultResponse {
  id: number;
  build_id?: number | null;
  template_version_id?: number | null;
  overall_score: number;
  passed: boolean;
  checks_passed: number;
  checks_total: number;
  checks: QACheckResult[];
  override?: QAOverrideResponse | null;
  created_at: string;
}

/** Request to run QA checks. */
export interface QARunRequest {
  build_id?: number | null;
  template_version_id?: number | null;
  html: string;
}

/** Request to override failing checks. */
export interface QAOverrideRequest {
  justification: string;
  checks_overridden: string[];
}

/** Paginated response shape matching backend PaginatedResponse. */
export interface PaginatedQAResults {
  items: QAResultResponse[];
  total: number;
  page: number;
  page_size: number;
}

/** Aggregated metrics for the intelligence dashboard. */
export interface QADashboardMetrics {
  totalRuns: number;
  avgScore: number;
  passRate: number;
  overrideCount: number;
  checkAverages: { checkName: string; avgScore: number; passRate: number }[];
  scoreTrend: { score: number; passed: boolean; date: string }[];
}

