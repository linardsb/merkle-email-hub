export type DesignConnectionStatus = "connected" | "syncing" | "error" | "disconnected";

export type DesignProvider = "figma" | "sketch" | "canva" | "penpot" | "mock";

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
  error_message: string | null;
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

// ── Browse files (wizard) ──

export interface DesignFileBrowse {
  file_id: string;
  name: string;
  url: string;
  thumbnail_url: string | null;
  last_modified: string | null;
  folder: string | null;
}

export interface BrowseFilesResponse {
  provider: string;
  files: DesignFileBrowse[];
  total: number;
}

export interface BrowseFilesArg {
  provider: DesignProvider;
  access_token: string;
}

// ── File tree (12.7) ──

export interface DesignNode {
  id: string;
  name: string;
  type: string;
  children: DesignNode[];
  width: number | null;
  height: number | null;
  x: number | null;
  y: number | null;
  text_content: string | null;
}

export interface DesignFileStructure {
  connection_id: number;
  file_name: string;
  pages: DesignNode[];
}

// ── Components ──

export interface DesignComponent {
  component_id: string;
  name: string;
  description: string;
  thumbnail_url: string | null;
  containing_page: string | null;
}

export interface DesignComponentList {
  connection_id: number;
  components: DesignComponent[];
  total: number;
}

// ── Image export ──

export interface ExportedImage {
  node_id: string;
  url: string;
  format: string;
  expires_at: string | null;
}

export interface ImageExportResult {
  connection_id: number;
  images: ExportedImage[];
  total: number;
}

// ── Design import ──

export interface DesignImportAsset {
  id: number;
  node_id: string;
  node_name: string;
  file_path: string;
  width: number | null;
  height: number | null;
  format: string;
  usage: string | null;
  created_at: string;
}

export type ImportStatus = "pending" | "extracting" | "converting" | "completed" | "failed" | "cancelled";

export interface DesignImport {
  id: number;
  connection_id: number;
  project_id: number;
  status: ImportStatus;
  selected_node_ids: string[];
  structure_json: Record<string, unknown> | null;
  generated_brief: string | null;
  result_template_id: number | null;
  error_message: string | null;
  created_by_id: number;
  assets: DesignImportAsset[];
  created_at: string;
  updated_at: string;
}

// ── Brief generation ──

export interface GeneratedBrief {
  connection_id: number;
  brief: string;
  sections_detected: number;
  layout_summary: string;
}

// ── Component extraction ──

export interface ExtractComponentsResult {
  import_id: number;
  status: string;
  total_components: number;
}

// ── Mutation arg types ──

export interface ExportImagesArg {
  connection_id: number;
  node_ids: string[];
  format?: string;
  scale?: number;
}

export interface GenerateBriefArg {
  connection_id: number;
  selected_node_ids: string[];
  include_tokens?: boolean;
}

export interface CreateImportArg {
  connection_id: number;
  brief: string;
  selected_node_ids: string[];
  template_name?: string;
}

export interface ConvertImportArg {
  run_qa?: boolean;
  output_mode?: "html" | "structured";
}

export interface ExtractComponentsArg {
  component_ids?: string[];
  generate_html?: boolean;
}
