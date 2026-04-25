// ── Approval types (28.3) ────────────────────────────────

import type { GateResult } from "./rendering-gate";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "revision_requested";

export interface ApprovalGateResult {
  required: boolean;
  passed: boolean;
  reason: string | null;
  approval_id: number | null;
  approved_by: string | null;
  approved_at: string | null;
}

export interface QACheckSummary {
  check_name: string;
  passed: boolean;
  score: number;
  severity: string;
  details: string | null;
}

export interface QAGateResult {
  passed: boolean;
  verdict: string;
  mode: string;
  blocking_failures: QACheckSummary[];
  warnings: QACheckSummary[];
  checks_run: number;
  evaluated_at: string;
}

export interface ExportPreCheckRequest {
  html: string;
  project_id: number;
  target_clients?: string[];
  build_id?: number;
}

export interface ExportPreCheckResponse {
  qa: QAGateResult;
  rendering: GateResult | null;
  approval: ApprovalGateResult | null;
  can_export: boolean;
}
