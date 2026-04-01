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
      <div className="flex items-center gap-2 py-8 text-sm text-foreground-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        {"Loading remote templates…"}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 py-8">
        <p className="text-sm text-status-danger">{"Failed to load templates"}</p>
        <button
          type="button"
          onClick={() => mutate()}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
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
        <h3 className="text-sm font-medium text-foreground">{"Remote Templates"}</h3>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={"Search templates…"}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
        />
      </div>

      {/* Template list */}
      {filtered.length === 0 ? (
        <p className="py-4 text-center text-sm text-foreground-muted">
          {"No templates found on this ESP"}
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((tpl) => (
            <div
              key={tpl.id}
              className="flex items-center justify-between rounded-md border border-card-border bg-card-bg p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{tpl.name}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-foreground-muted">
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
                  className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
                >
                  <Eye className="h-3.5 w-3.5" />
                  {"Template Preview"}
                </button>
                <button
                  type="button"
                  onClick={() => onImport(tpl.id)}
                  disabled={importing === tpl.id}
                  className="flex items-center gap-1.5 rounded-md bg-interactive px-2.5 py-1 text-xs font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
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
