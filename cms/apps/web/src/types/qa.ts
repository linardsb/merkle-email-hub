/**
 * QA types — re-exported from SDK with stable local aliases.
 * Frontend-only types kept locally.
 */
export type { QaCheckResult as QACheckResult } from "@email-hub/sdk";
export type { QaOverrideResponse as QAOverrideResponse } from "@email-hub/sdk";
export type { QaResultResponse as QAResultResponse } from "@email-hub/sdk";
export type { QaRunRequest as QARunRequest } from "@email-hub/sdk";
export type { QaOverrideRequest as QAOverrideRequest } from "@email-hub/sdk";
export type { PaginatedResponseQaResultResponse as PaginatedQAResults } from "@email-hub/sdk";

/** Structured details from the css_audit QA check. */
export interface CSSAuditConversion {
  original_property: string;
  original_value: string;
  replacement_property: string;
  replacement_value: string;
  reason: string;
  affected_clients: string[];
}

export interface CSSAuditDetails {
  compatibility_matrix: Record<
    string,
    Record<string, "supported" | "converted" | "removed" | "partial">
  >;
  conversions: CSSAuditConversion[];
  removed_properties: string[];
  client_coverage_score: Record<string, number>;
  overall_coverage_score: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  issues: string[];
}

/** Frontend-only: aggregated metrics for the intelligence dashboard. */
export interface QADashboardMetrics {
  totalRuns: number;
  avgScore: number;
  passRate: number;
  overrideCount: number;
  checkAverages: { checkName: string; avgScore: number; passRate: number }[];
  scoreTrend: { score: number; passed: boolean; date: string }[];
}
