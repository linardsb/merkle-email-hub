/**
 * Outlook Dependency Analyzer types.
 * Local interfaces matching backend schemas (app/qa_engine/schemas.py).
 * TODO: Replace with SDK re-exports after `make sdk` regeneration.
 */

export interface OutlookAnalysisRequest {
  html: string;
}

export interface OutlookDependencySchema {
  type: string;
  location: string;
  line_number: number;
  code_snippet: string;
  severity: string;
  removable: boolean;
  modern_replacement: string | null;
}

export interface ModernizationStep {
  description: string;
  dependency_type: string;
  removals: number;
  byte_savings: number;
}

export interface OutlookAnalysisResponse {
  dependencies: OutlookDependencySchema[];
  total_count: number;
  removable_count: number;
  byte_savings: number;
  modernization_plan: ModernizationStep[];
  vml_count: number;
  ghost_table_count: number;
  mso_conditional_count: number;
  mso_css_count: number;
  dpi_image_count: number;
  external_class_count: number;
  word_wrap_count: number;
}

export interface OutlookModernizeRequest {
  html: string;
  target?: "new_outlook" | "dual_support" | "audit_only";
}

export interface OutlookModernizeResponse {
  html: string;
  changes_applied: number;
  bytes_before: number;
  bytes_after: number;
  bytes_saved: number;
  target: string;
  analysis: OutlookAnalysisResponse;
}
