/**
 * Chaos & Property Testing types.
 * Local interfaces matching backend schemas (app/qa_engine/schemas.py).
 * TODO: Replace with SDK re-exports after `make sdk` regeneration.
 */

// ── Chaos Testing (18.1) ────────────────────────────────────

export interface ChaosTestRequest {
  html: string;
  profiles?: string[];
  project_id?: number;
}

export interface ChaosFailure {
  profile: string;
  check_name: string;
  severity: string;
  description: string;
}

export interface ChaosProfileResult {
  profile: string;
  description: string;
  score: number;
  passed: boolean;
  checks_passed: number;
  checks_total: number;
  failures: ChaosFailure[];
}

export interface ChaosTestResponse {
  original_score: number;
  resilience_score: number;
  profiles_tested: number;
  profile_results: ChaosProfileResult[];
  critical_failures: ChaosFailure[];
}

// ── Property-Based Testing (18.2) ───────────────────────────

export interface PropertyTestRequest {
  invariants?: string[];
  num_cases?: number;
  seed?: number;
}

export interface PropertyFailureSchema {
  invariant_name: string;
  violations: string[];
  config: Record<string, unknown>;
}

export interface PropertyTestResponse {
  total_cases: number;
  passed: number;
  failed: number;
  failures: PropertyFailureSchema[];
  seed: number;
  invariants_tested: string[];
}
