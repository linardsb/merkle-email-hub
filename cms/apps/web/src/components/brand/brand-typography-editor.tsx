"use client";

import type { BrandTypography } from "@/types/brand";

interface BrandTypographyEditorProps {
  typography: BrandTypography[];
  onChange: (typography: BrandTypography[]) => void;
  disabled?: boolean;
}

export function BrandTypographyEditor({
  typography,
  onChange,
  disabled,
}: BrandTypographyEditorProps) {
  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-1.5 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const handleFieldChange = (
    index: number,
    field: keyof BrandTypography,
    value: string | number | string[],
  ) => {
    const updated = [...typography];
    updated[index] = { ...updated[index]!, [field]: value };
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-foreground text-sm font-medium">{"Typography"}</h3>

      {typography.map((typo, i) => (
        <div key={i} className="border-card-border bg-card-bg space-y-2 rounded-md border p-3">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-foreground-muted mb-1 block text-xs">{"Font Family"}</label>
              <input
                type="text"
                value={typo.family}
                onChange={(e) => handleFieldChange(i, "family", e.target.value)}
                disabled={disabled}
                className={inputClass}
              />
            </div>
            <div>
              <label className="text-foreground-muted mb-1 block text-xs">{"Weights"}</label>
              <input
                type="text"
                value={typo.weights.join(", ")}
                onChange={(e) =>
                  handleFieldChange(
                    i,
                    "weights",
                    e.target.value.split(",").map((w) => w.trim()),
                  )
                }
                disabled={disabled}
                placeholder="400, 500, 600, 700"
                className={inputClass}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-foreground-muted mb-1 block text-xs">{"Min Size (px)"}</label>
              <input
                type="number"
                value={typo.minSize}
                onChange={(e) => handleFieldChange(i, "minSize", Number(e.target.value))}
                disabled={disabled}
                min={8}
                max={100}
                className={inputClass}
              />
            </div>
            <div>
              <label className="text-foreground-muted mb-1 block text-xs">{"Max Size (px)"}</label>
              <input
                type="number"
                value={typo.maxSize}
                onChange={(e) => handleFieldChange(i, "maxSize", Number(e.target.value))}
                disabled={disabled}
                min={8}
                max={200}
                className={inputClass}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
