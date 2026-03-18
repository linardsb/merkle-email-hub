import type { PluginListResponse, PluginHealthSummary } from "@/types/plugins";

export const DEMO_PLUGINS: PluginListResponse = {
  plugins: [
    {
      name: "brand-guardian",
      version: "1.2.0",
      plugin_type: "qa_check",
      permissions: ["qa:read", "qa:write"],
      status: "active",
      loaded_at: "2026-03-18T08:00:00Z",
      error: null,
      description: "Enforces brand guidelines across all email templates",
      author: "Merkle Core",
      tags: ["brand", "compliance", "qa"],
    },
    {
      name: "analytics-tracker",
      version: "2.0.1",
      plugin_type: "post_processor",
      permissions: ["templates:read"],
      status: "active",
      loaded_at: "2026-03-18T08:00:00Z",
      error: null,
      description: "Injects UTM parameters and tracking pixels",
      author: "Merkle Core",
      tags: ["analytics", "tracking"],
    },
    {
      name: "spam-shield",
      version: "0.9.3",
      plugin_type: "qa_check",
      permissions: ["qa:read"],
      status: "degraded",
      loaded_at: "2026-03-18T07:55:00Z",
      error: null,
      description: "Advanced spam scoring with ML-based content analysis",
      author: "Community",
      tags: ["spam", "deliverability"],
    },
    {
      name: "legacy-formatter",
      version: "1.0.0",
      plugin_type: "post_processor",
      permissions: ["templates:read", "templates:write"],
      status: "disabled",
      loaded_at: null,
      error: null,
      description: "Formats HTML for legacy email clients",
      author: "Community",
      tags: ["legacy", "compatibility"],
    },
  ],
  total: 4,
};

export const DEMO_PLUGIN_HEALTH: PluginHealthSummary = {
  plugins: [
    { name: "brand-guardian", status: "healthy", message: null, latency_ms: 12 },
    { name: "analytics-tracker", status: "healthy", message: null, latency_ms: 8 },
    { name: "spam-shield", status: "degraded", message: "ML model loading slowly", latency_ms: 450 },
    { name: "legacy-formatter", status: "unhealthy", message: "Plugin disabled", latency_ms: 0 },
  ],
  total: 4,
  healthy: 2,
  degraded: 1,
  unhealthy: 1,
};
