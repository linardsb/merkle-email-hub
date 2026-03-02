export type FigmaConnectionStatus = "connected" | "syncing" | "error" | "disconnected";

export interface FigmaConnection {
  id: number;
  name: string;
  file_key: string;
  file_url: string;
  access_token_last4: string;
  status: FigmaConnectionStatus;
  last_synced_at: string | null;
  project_id: number | null;
  project_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface FigmaDesignColor {
  name: string;
  hex: string;
  opacity: number;
}

export interface FigmaDesignTypography {
  name: string;
  family: string;
  weight: string;
  size: number;
  lineHeight: number;
}

export interface FigmaDesignSpacing {
  name: string;
  value: number;
}

export interface FigmaDesignTokens {
  connection_id: number;
  colors: FigmaDesignColor[];
  typography: FigmaDesignTypography[];
  spacing: FigmaDesignSpacing[];
  extracted_at: string;
}

export interface FigmaConnectionCreate {
  file_url: string;
  access_token: string;
  project_id: number | null;
  name: string;
}
