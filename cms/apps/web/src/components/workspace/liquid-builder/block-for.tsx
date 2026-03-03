"use client";

import { useTranslations } from "next-intl";
import type { ForBlock } from "@/types/liquid-builder";

interface BlockForProps {
  block: ForBlock;
  onUpdate: (updates: Partial<ForBlock>) => void;
}

export function BlockFor({ block, onUpdate }: BlockForProps) {
  const t = useTranslations("liquidBuilder");

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted">{t("forVariable")}</span>
        <input
          type="text"
          value={block.variable}
          onChange={(e) => onUpdate({ variable: e.target.value })}
          className="w-24 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
          placeholder="item"
        />
        <span className="text-xs text-muted">{t("forIn")}</span>
        <input
          type="text"
          value={block.collection}
          onChange={(e) => onUpdate({ collection: e.target.value })}
          className="flex-1 rounded border border-default bg-input px-2 py-1 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
          placeholder="products"
        />
      </div>
      {block.children.length > 0 && (
        <div className="border-l-2 border-interactive/30 pl-3">
          <p className="text-xs text-muted">{t("childBlockCount", { count: block.children.length })}</p>
        </div>
      )}
    </div>
  );
}
