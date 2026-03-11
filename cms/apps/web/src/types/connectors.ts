/**
 * Connector types — re-exported from SDK where available.
 * Frontend-only types kept locally.
 */
export type { ExportRequest, ExportResponse } from "@email-hub/sdk";

export type ConnectorPlatform = "braze" | "sfmc" | "adobe_campaign" | "taxi" | "raw_html";

/** Frontend-only: local export history record (not persisted to backend). */
export interface ExportHistoryRecord {
  local_id: string;
  platform: ConnectorPlatform;
  name: string;
  status: "success" | "failed" | "exporting";
  error_message: string | null;
  external_id: string | null;
  created_at: string;
  build_id: number | null;
}
