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
    value: string | number | string[]
  ) => {
    const updated = [...typography];
    updated[index] = { ...updated[index]!, [field]: value };
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">{"Typography"}</h3>

      {typography.map((typo, i) => (
        <div
          key={i}
          className="rounded-md border border-card-border bg-card-bg p-3 space-y-2"
        >
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-xs text-foreground-muted">
                {"Font Family"}
              </label>
              <input
                type="text"
                value={typo.family}
                onChange={(e) => handleFieldChange(i, "family", e.target.value)}
                disabled={disabled}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-foreground-muted">
                {"Weights"}
              </label>
              <input
                type="text"
                value={typo.weights.join(", ")}
                onChange={(e) =>
                  handleFieldChange(
                    i,
                    "weights",
                    e.target.value.split(",").map((w) => w.trim())
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
              <label className="mb-1 block text-xs text-foreground-muted">
                {"Min Size (px)"}
              </label>
              <input
                type="number"
                value={typo.minSize}
                onChange={(e) =>
                  handleFieldChange(i, "minSize", Number(e.target.value))
                }
                disabled={disabled}
                min={8}
                max={100}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-foreground-muted">
                {"Max Size (px)"}
              </label>
              <input
                type="number"
                value={typo.maxSize}
                onChange={(e) =>
                  handleFieldChange(i, "maxSize", Number(e.target.value))
                }
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
