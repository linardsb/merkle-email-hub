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

/** Frontend-only: aggregated metrics for the intelligence dashboard. */
export interface QADashboardMetrics {
  totalRuns: number;
  avgScore: number;
  passRate: number;
  overrideCount: number;
  checkAverages: { checkName: string; avgScore: number; passRate: number }[];
  scoreTrend: { score: number; passed: boolean; date: string }[];
}
