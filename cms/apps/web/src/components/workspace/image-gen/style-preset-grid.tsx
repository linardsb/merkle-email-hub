"use client";

import { Package, Camera, Sparkles } from "../../icons";
import type { StylePreset } from "@/types/image-gen";
import type { LucideIcon } from "../../icons";

const PRESETS: { value: StylePreset; icon: LucideIcon; label: string }[] = [
  { value: "product", icon: Package, label: "Product" },
  { value: "lifestyle", icon: Camera, label: "Lifestyle" },
  { value: "abstract", icon: Sparkles, label: "Abstract" },
];

interface StylePresetGridProps {
  selected: StylePreset;
  onSelect: (style: StylePreset) => void;
}

export function StylePresetGrid({ selected, onSelect }: StylePresetGridProps) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {PRESETS.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => onSelect(value)}
          className={`flex flex-col items-center gap-1.5 rounded-md border p-3 text-xs transition-colors ${
            selected === value
              ? "border-interactive bg-interactive/10 text-foreground"
              : "border-card-border bg-card-bg text-foreground-muted hover:bg-surface-hover"
          }`}
        >
          <Icon className="h-5 w-5" />
          {label}
        </button>
      ))}
    </div>
  );
}
