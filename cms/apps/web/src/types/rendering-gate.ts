// ── Gate types (27.3) ────────────────────────────────────

export type GateMode = "enforce" | "warn" | "skip";

export type GateVerdict = "pass" | "warn" | "block";

export interface ClientGateResult {
  client_name: string;
  confidence_score: number; // 0-100
  threshold: number; // 0-100
  passed: boolean;
  tier: string; // "tier_1" | "tier_2" | "tier_3"
  blocking_reasons: string[];
  remediation: string[];
}

export interface GateResult {
  passed: boolean;
  verdict: GateVerdict;
  mode: GateMode;
  client_results: ClientGateResult[];
  blocking_clients: string[];
  recommendations: string[];
  evaluated_at: string; // ISO datetime
}

export interface GateEvaluateRequest {
  html: string;
  target_clients?: string[];
  project_id?: number;
}

export interface RenderingGateConfig {
  mode: GateMode;
  tier_thresholds: Record<string, number>; // { tier_1: 85, tier_2: 70, tier_3: 60 }
  target_clients: string[];
  require_external_validation: string[];
}

export interface GateConfigUpdateRequest {
  mode?: GateMode;
  tier_thresholds?: Record<string, number>;
  target_clients?: string[];
  require_external_validation?: string[];
}
