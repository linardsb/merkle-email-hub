"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import type { ForbiddenPattern } from "@/types/brand";

interface BrandForbiddenPatternsProps {
  patterns: ForbiddenPattern[];
  onChange: (patterns: ForbiddenPattern[]) => void;
  disabled?: boolean;
}

export function BrandForbiddenPatterns({
  patterns,
  onChange,
  disabled,
}: BrandForbiddenPatternsProps) {
  const t = useTranslations("brand");
  const [newPattern, setNewPattern] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const handleAdd = () => {
    if (!newPattern.trim() || !newDesc.trim()) return;
    onChange([
      ...patterns,
      {
        id: `fp-${Date.now()}`,
        pattern: newPattern.trim(),
        description: newDesc.trim(),
      },
    ]);
    setNewPattern("");
    setNewDesc("");
  };

  const handleRemove = (id: string) => {
    onChange(patterns.filter((p) => p.id !== id));
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-1.5 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">{t("forbiddenTitle")}</h3>

      {/* Existing patterns */}
      <div className="space-y-2">
        {patterns.map((p) => (
          <div
            key={p.id}
            className="flex items-start gap-2 rounded-md border border-card-border bg-card-bg px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs font-mono text-foreground">{p.pattern}</p>
              <p className="mt-0.5 text-xs text-foreground-muted">{p.description}</p>
            </div>
            {!disabled && (
              <button
                type="button"
                onClick={() => handleRemove(p.id)}
                className="mt-0.5 text-foreground-muted transition-colors hover:text-status-danger"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add new pattern */}
      {!disabled && (
        <div className="space-y-2">
          <input
            type="text"
            value={newPattern}
            onChange={(e) => setNewPattern(e.target.value)}
            placeholder={t("forbiddenPatternPlaceholder")}
            className={inputClass}
          />
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder={t("forbiddenDescPlaceholder")}
                className={inputClass}
              />
            </div>
            <button
              type="button"
              onClick={handleAdd}
              disabled={!newPattern.trim() || !newDesc.trim()}
              className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
            >
              <Plus className="h-3 w-3" />
              {t("addPattern")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
