"use client";

import { useTranslations } from "next-intl";
import { Package, Camera, Sparkles, Grid3X3, Pencil, Square } from "lucide-react";
import type { StylePreset } from "@/types/image-gen";
import type { LucideIcon } from "lucide-react";

const PRESETS: { value: StylePreset; icon: LucideIcon; labelKey: string }[] = [
  { value: "product", icon: Package, labelKey: "styleProduct" },
  { value: "lifestyle", icon: Camera, labelKey: "styleLifestyle" },
  { value: "abstract", icon: Sparkles, labelKey: "styleAbstract" },
  { value: "pattern", icon: Grid3X3, labelKey: "stylePattern" },
  { value: "illustration", icon: Pencil, labelKey: "styleIllustration" },
  { value: "flat", icon: Square, labelKey: "styleFlat" },
];

interface StylePresetGridProps {
  selected: StylePreset;
  onSelect: (style: StylePreset) => void;
}

export function StylePresetGrid({ selected, onSelect }: StylePresetGridProps) {
  const t = useTranslations("imageGen");

  return (
    <div className="grid grid-cols-3 gap-2">
      {PRESETS.map(({ value, icon: Icon, labelKey }) => (
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
          {t(labelKey)}
        </button>
      ))}
    </div>
  );
}
