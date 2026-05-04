"use client";

import { useMemo, useState } from "react";
import { Download, Eye, Loader2, RefreshCw, Search } from "../icons";
import { useESPTemplates } from "@/hooks/use-esp-sync";
import { ESP_LABELS } from "@/types/esp-sync";
import type { ESPTemplate } from "@/types/esp-sync";

interface ESPTemplateBrowserProps {
  connectionId: number;
  espType: string;
  onPreview: (template: ESPTemplate) => void;
  onImport: (templateId: string) => void;
  importing: string | null; // template ID currently importing, or null
}

export function ESPTemplateBrowser({
  connectionId,
  espType,
  onPreview,
  onImport,
  importing,
}: ESPTemplateBrowserProps) {
  const { data, error, isLoading, mutate } = useESPTemplates(connectionId);
  const [search, setSearch] = useState("");

  const templates = data?.templates ?? [];
  const filtered = useMemo(() => {
    if (!search.trim()) return templates;
    const q = search.toLowerCase();
    return templates.filter((tpl) => tpl.name.toLowerCase().includes(q));
  }, [templates, search]);

  const espInfo = ESP_LABELS[espType] ?? {
    label: espType,
    color: "bg-surface-muted text-foreground-muted",
  };

  if (isLoading) {
    return (
      <div className="text-foreground-muted flex items-center gap-2 py-8 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        {"Loading remote templates…"}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 py-8">
        <p className="text-status-danger text-sm">{"Failed to load templates"}</p>
        <button
          type="button"
          onClick={() => mutate()}
          className="border-border text-foreground hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {"Retry"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-foreground text-sm font-medium">{"Remote Templates"}</h3>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="text-foreground-muted absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={"Search templates…"}
          className="border-input-border bg-input-bg text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:ring-input-focus w-full rounded-md border py-2 pr-3 pl-9 text-sm focus:ring-1 focus:outline-none"
        />
      </div>

      {/* Template list */}
      {filtered.length === 0 ? (
        <p className="text-foreground-muted py-4 text-center text-sm">
          {"No templates found on this ESP"}
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((tpl) => (
            <div
              key={tpl.id}
              className="border-card-border bg-card-bg flex items-center justify-between rounded-md border p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-foreground truncate text-sm font-medium">{tpl.name}</p>
                <div className="text-foreground-muted mt-1 flex items-center gap-2 text-xs">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${espInfo.color}`}>
                    {espInfo.label}
                  </span>
                  <span>
                    {new Date(tpl.updated_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onPreview(tpl)}
                  className="border-border text-foreground hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors"
                >
                  <Eye className="h-3.5 w-3.5" />
                  {"Template Preview"}
                </button>
                <button
                  type="button"
                  onClick={() => onImport(tpl.id)}
                  disabled={importing === tpl.id}
                  className="bg-interactive text-foreground-inverse hover:bg-interactive-hover flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {importing === tpl.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}
                  {"Import"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
