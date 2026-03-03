"use client";

import { useTranslations } from "next-intl";
import type { OutputBlock } from "@/types/liquid-builder";

interface BlockOutputProps {
  block: OutputBlock;
  onUpdate: (updates: Partial<OutputBlock>) => void;
}

export function BlockOutput({ block, onUpdate }: BlockOutputProps) {
  const t = useTranslations("liquidBuilder");

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-xs text-muted">{"{{"}</span>
      <input
        type="text"
        value={block.expression}
        onChange={(e) => onUpdate({ expression: e.target.value })}
        className="flex-1 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
        placeholder={t("outputPlaceholder")}
      />
      <span className="font-mono text-xs text-muted">{"}}"}</span>
    </div>
  );
}
