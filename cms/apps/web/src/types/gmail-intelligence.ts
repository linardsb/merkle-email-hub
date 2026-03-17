// Gmail AI Summary Predictor (Phase 20.1)
export interface GmailPredictRequest {
  html: string;
  subject: string;
  from_name: string;
}

export interface GmailPredictResponse {
  summary_text: string;
  predicted_category: string;
  key_actions: string[];
  promotion_signals: string[];
  improvement_suggestions: string[];
  confidence: number;
}

// Gmail Preview Optimizer
export interface GmailOptimizeRequest {
  html: string;
  subject: string;
  from_name: string;
  target_summary?: string;
}

export interface GmailOptimizeResponse {
  original_subject: string;
  suggested_subjects: string[];
  original_preview: string;
  suggested_previews: string[];
  reasoning: string;
}

// Deliverability Score (Phase 20.3)
export interface DeliverabilityIssue {
  dimension: string;
  severity: "error" | "warning" | "info";
  description: string;
  fix: string;
}

export interface DeliverabilityDimension {
  name: string;
  score: number;
  max_score: number;
  issues: DeliverabilityIssue[];
}

export interface DeliverabilityScoreRequest {
  html: string;
}

export interface DeliverabilityScoreResponse {
  score: number;
  passed: boolean;
  threshold: number;
  dimensions: DeliverabilityDimension[];
  issues: DeliverabilityIssue[];
  summary: string;
}

// Schema.org Auto-Markup (Phase 20.2)
export interface DetectedIntent {
  intent_type: string;
  confidence: number;
  entity_count: number;
}

export interface ExtractedEntity {
  entity_type: string;
  value: string;
}

export interface SchemaInjectRequest {
  html: string;
  subject?: string;
}

export interface SchemaInjectResponse {
  html: string;
  injected: boolean;
  intent: DetectedIntent;
  entities: ExtractedEntity[];
  schema_types: string[];
  validation_errors: string[];
  inject_time_ms: number;
}

// BIMI Readiness (Phase 20.4)
export interface DMARCInfo {
  policy: string;
  subdomain_policy: string | null;
  pct: number;
}

export interface SVGValidation {
  valid: boolean;
  issues: string[];
}

export interface BIMICheckRequest {
  domain: string;
}

export interface BIMICheckResponse {
  domain: string;
  ready: boolean;
  dmarc_ready: boolean;
  dmarc_policy: string;
  dmarc_record: string | null;
  dmarc_info: DMARCInfo | null;
  bimi_record_exists: boolean;
  bimi_record: string | null;
  bimi_svg_url: string | null;
  bimi_authority_url: string | null;
  svg_valid: boolean | null;
  svg_validation: SVGValidation | null;
  cmc_status: string;
  generated_record: string;
  issues: string[];
}
