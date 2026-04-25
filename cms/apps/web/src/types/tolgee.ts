// ── API Response Types (mirror backend schemas) ──────────────────────

export interface TolgeeLanguage {
  id: number;
  tag: string; // BCP-47
  name: string;
  original_name: string;
  flag_emoji: string;
  base: boolean;
}

export interface TolgeeConnectionResponse {
  id: number;
  name: string;
  status: string;
  credentials_hint: string;
  tolgee_project_id: number | null;
  project_id: number;
  last_synced_at: string | null;
  created_at: string;
}

export interface TranslationSyncResponse {
  keys_extracted: number;
  push_result: { created: number; updated: number; skipped: number };
  template_id: number;
}

export interface TranslationPullResponse {
  locale: string;
  translations_count: number;
  translations: Record<string, string>;
}

export interface LocaleBuildResult {
  locale: string;
  html: string;
  build_time_ms: number;
  gmail_clipping_warning: boolean;
  text_direction: "ltr" | "rtl";
}

export interface LocaleBuildResponse {
  template_id: number;
  results: LocaleBuildResult[];
  total_build_time_ms: number;
}

// ── UI State Types ───────────────────────────────────────────────────

export type TranslationStatus = "translated" | "untranslated" | "machine-translated";

export interface TranslationKeyRow {
  key: string;
  sourceText: string;
  statuses: Record<string, TranslationStatus>; // locale → status
  translations: Record<string, string>; // locale → translated text
}

export type LocaleQAStatus = "pass" | "fail" | "warning" | "pending";

export interface LocaleQACheck {
  check: string;
  status: LocaleQAStatus;
  message?: string;
}

export interface LocaleQASummary {
  locale: string;
  checks: LocaleQACheck[];
  overallStatus: LocaleQAStatus;
}
