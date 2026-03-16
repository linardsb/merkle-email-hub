// Types matching backend Pydantic schemas in app/connectors/sync_schemas.py

export type ESPType = "braze" | "sfmc" | "adobe_campaign" | "taxi";

export interface ESPConnectionCreate {
  esp_type: ESPType;
  name: string;
  project_id: number;
  credentials: Record<string, string>;
}

export interface ESPConnectionResponse {
  id: number;
  esp_type: string;
  name: string;
  status: string; // "connected" | "error"
  credentials_hint: string;
  project_id: number;
  project_name: string | null;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ESPTemplate {
  id: string;
  name: string;
  html: string;
  esp_type: string;
  created_at: string;
  updated_at: string;
}

export interface ESPTemplateList {
  templates: ESPTemplate[];
  count: number;
}

export interface ESPImportRequest {
  template_id: string; // remote ESP template ID
}

export interface ESPPushRequest {
  template_id: number; // local Hub template ID
}
