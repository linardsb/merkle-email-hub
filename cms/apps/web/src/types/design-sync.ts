export type DesignConnectionStatus = "connected" | "syncing" | "error" | "disconnected";

export type DesignProvider = "figma" | "sketch" | "canva";

export interface DesignConnection {
  id: number;
  name: string;
  provider: DesignProvider;
  file_key: string;
  file_url: string;
  access_token_last4: string;
  status: DesignConnectionStatus;
  last_synced_at: string | null;
  project_id: number | null;
  project_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface DesignColor {
  name: string;
  hex: string;
  opacity: number;
}

export interface DesignTypography {
  name: string;
  family: string;
  weight: string;
  size: number;
  lineHeight: number;
}

export interface DesignSpacing {
  name: string;
  value: number;
}

export interface DesignTokens {
  connection_id: number;
  colors: DesignColor[];
  typography: DesignTypography[];
  spacing: DesignSpacing[];
  extracted_at: string;
}

export interface DesignConnectionCreate {
  file_url: string;
  access_token: string;
  project_id: number | null;
  name: string;
  provider: DesignProvider;
}
