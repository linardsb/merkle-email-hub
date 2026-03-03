"use client";

import { useTranslations } from "next-intl";
import { GitBranch, Repeat, Variable, Braces, Code } from "lucide-react";
import type { LiquidBlockType } from "@/types/liquid-builder";

const PALETTE_ITEMS: { type: LiquidBlockType; icon: React.ReactNode }[] = [
  { type: "if", icon: <GitBranch className="h-4 w-4" /> },
  { type: "for", icon: <Repeat className="h-4 w-4" /> },
  { type: "assign", icon: <Variable className="h-4 w-4" /> },
  { type: "output", icon: <Braces className="h-4 w-4" /> },
  { type: "raw", icon: <Code className="h-4 w-4" /> },
];

interface BlockPaletteProps {
  onAddBlock: (type: LiquidBlockType) => void;
}

export function BlockPalette({ onAddBlock }: BlockPaletteProps) {
  const t = useTranslations("liquidBuilder");

  return (
    <div className="space-y-1 p-2">
      <h3 className="px-1 text-[10px] uppercase tracking-wider text-muted">
        {t("paletteTitle")}
      </h3>
      {PALETTE_ITEMS.map((item) => (
        <button
          key={item.type}
          type="button"
          onClick={() => onAddBlock(item.type)}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-foreground transition-colors hover:bg-surface-raised"
        >
          {item.icon}
          <span>{t(`blockType_${item.type}`)}</span>
        </button>
      ))}
    </div>
  );
}
