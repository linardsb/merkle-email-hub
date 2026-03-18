export type PluginStatus = "active" | "disabled" | "degraded" | "error";
export type PluginHealthStatus = "healthy" | "degraded" | "unhealthy";

export interface PluginInfo {
  name: string;
  version: string;
  plugin_type: string;
  permissions: string[];
  status: PluginStatus;
  loaded_at: string | null;
  error: string | null;
  description: string;
  author: string;
  tags: string[];
}

export interface PluginListResponse {
  plugins: PluginInfo[];
  total: number;
}

export interface PluginHealth {
  name: string;
  status: PluginHealthStatus;
  message: string | null;
  latency_ms: number;
}

export interface PluginHealthSummary {
  plugins: PluginHealth[];
  total: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
}
