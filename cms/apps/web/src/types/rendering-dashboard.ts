// ── Dashboard types (27.6) ──────────────────────────────────

export interface ConfidenceBreakdown {
  emulator_coverage: number; // 0-1
  css_compatibility: number; // 0-1
  calibration_accuracy: number; // 0-1
  layout_complexity: number; // 0-1
  known_blind_spots: string[];
}

export interface ClientConfidence {
  client_id: string;
  accuracy: number;
  sample_count: number;
  last_calibrated: string;
  known_blind_spots: string[];
  emulator_rule_count: number;
  profiles: string[];
}

export interface CalibrationSummaryItem {
  client_id: string;
  current_accuracy: number; // 0-100
  sample_count: number;
  last_calibrated: string;
  accuracy_trend: number[]; // last 10 values
  regression_alert: boolean; // accuracy dropped >10%
}

export interface CalibrationSummaryResponse {
  items: CalibrationSummaryItem[];
}

export interface CalibrationHistoryEntry {
  id: number;
  measured_accuracy: number;
  smoothed_accuracy: number;
  diff_percentage: number;
  created_at: string;
}

export interface CalibrationHistoryResponse {
  client_id: string;
  entries: CalibrationHistoryEntry[];
}
