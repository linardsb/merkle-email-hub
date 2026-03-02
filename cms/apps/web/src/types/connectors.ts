export type ConnectorPlatform = "braze" | "sfmc" | "adobe_campaign" | "taxi" | "raw_html";

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
