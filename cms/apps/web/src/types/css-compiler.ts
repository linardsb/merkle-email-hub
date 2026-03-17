/**
 * CSS Compiler types.
 * Local interfaces matching backend schemas (app/email_engine/schemas.py).
 * TODO: Replace with SDK re-exports after `make sdk` regeneration.
 */

export interface CSSCompileRequest {
  html: string;
  target_clients?: string[];
  css_variables?: Record<string, string>;
}

export interface CSSConversionSchema {
  original_property: string;
  original_value: string;
  replacement_property: string;
  replacement_value: string;
  reason: string;
  affected_clients: string[];
}

export interface CSSCompileResponse {
  html: string;
  original_size: number;
  compiled_size: number;
  reduction_pct: number;
  removed_properties: string[];
  conversions: CSSConversionSchema[];
  warnings: string[];
  compile_time_ms: number;
}
