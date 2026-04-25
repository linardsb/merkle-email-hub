"use client";

import type { BrandLogoRule } from "@/types/brand";

interface BrandLogoRulesProps {
  rules: BrandLogoRule | null;
  onChange: (rules: BrandLogoRule) => void;
  disabled?: boolean;
}

export function BrandLogoRules({ rules, onChange, disabled }: BrandLogoRulesProps) {
  const current: BrandLogoRule = rules ?? {
    minWidth: 120,
    minHeight: 40,
    clearSpace: 16,
    allowedFormats: ["png", "svg"],
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-1.5 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <div className="space-y-3">
      <h3 className="text-foreground text-sm font-medium">{"Logo Rules"}</h3>

      <div className="border-card-border bg-card-bg space-y-2 rounded-md border p-3">
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-foreground-muted mb-1 block text-xs">{"Min Width (px)"}</label>
            <input
              type="number"
              value={current.minWidth}
              onChange={(e) => onChange({ ...current, minWidth: Number(e.target.value) })}
              disabled={disabled}
              min={0}
              className={inputClass}
            />
          </div>
          <div>
            <label className="text-foreground-muted mb-1 block text-xs">{"Min Height (px)"}</label>
            <input
              type="number"
              value={current.minHeight}
              onChange={(e) => onChange({ ...current, minHeight: Number(e.target.value) })}
              disabled={disabled}
              min={0}
              className={inputClass}
            />
          </div>
          <div>
            <label className="text-foreground-muted mb-1 block text-xs">{"Clear Space (px)"}</label>
            <input
              type="number"
              value={current.clearSpace}
              onChange={(e) => onChange({ ...current, clearSpace: Number(e.target.value) })}
              disabled={disabled}
              min={0}
              className={inputClass}
            />
          </div>
        </div>
        <div>
          <label className="text-foreground-muted mb-1 block text-xs">{"Allowed Formats"}</label>
          <input
            type="text"
            value={current.allowedFormats.join(", ")}
            onChange={(e) =>
              onChange({
                ...current,
                allowedFormats: e.target.value.split(",").map((f) => f.trim()),
              })
            }
            disabled={disabled}
            placeholder="png, svg, jpg"
            className={inputClass}
          />
        </div>
      </div>
    </div>
  );
}
