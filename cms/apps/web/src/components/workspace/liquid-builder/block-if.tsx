"use client";

import { useTranslations } from "next-intl";
import type { IfBlock } from "@/types/liquid-builder";

interface BlockIfProps {
  block: IfBlock;
  onUpdate: (updates: Partial<IfBlock>) => void;
}

export function BlockIf({ block, onUpdate }: BlockIfProps) {
  const t = useTranslations("liquidBuilder");

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">{t("ifCondition")}</span>
        <input
          type="text"
          value={block.condition}
          onChange={(e) => onUpdate({ condition: e.target.value })}
          className="flex-1 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
          placeholder="subscriber.tier == 'gold'"
        />
      </div>
      {block.children.length > 0 && (
        <div className="border-l-2 border-success/30 pl-3">
          <span className="text-[10px] uppercase tracking-wider text-success">{t("thenBranch")}</span>
          <p className="mt-1 text-xs text-muted-foreground">{t("childBlockCount", { count: block.children.length })}</p>
        </div>
      )}
      {block.elseChildren.length > 0 && (
        <div className="border-l-2 border-warning/30 pl-3">
          <span className="text-[10px] uppercase tracking-wider text-warning">{t("elseBranch")}</span>
          <p className="mt-1 text-xs text-muted-foreground">{t("childBlockCount", { count: block.elseChildren.length })}</p>
        </div>
      )}
    </div>
  );
}
