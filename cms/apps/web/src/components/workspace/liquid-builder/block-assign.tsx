"use client";

import { useTranslations } from "next-intl";
import type { AssignBlock } from "@/types/liquid-builder";

interface BlockAssignProps {
  block: AssignBlock;
  onUpdate: (updates: Partial<AssignBlock>) => void;
}

export function BlockAssign({ block, onUpdate }: BlockAssignProps) {
  const t = useTranslations("liquidBuilder");

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={block.name}
        onChange={(e) => onUpdate({ name: e.target.value })}
        className="w-28 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
        placeholder="variable"
      />
      <span className="text-xs text-muted-foreground">=</span>
      <input
        type="text"
        value={block.expression}
        onChange={(e) => onUpdate({ expression: e.target.value })}
        className="flex-1 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
        placeholder={t("assignExpressionPlaceholder")}
      />
    </div>
  );
}
