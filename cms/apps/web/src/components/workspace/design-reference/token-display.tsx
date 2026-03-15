"use client";

import { useTranslations } from "next-intl";
import { Search, ArrowRightLeft, AlertTriangle } from "lucide-react";
import { useMemo } from "react";
import { toast } from "sonner";
import type { DesignTokens, DesignColor, DesignTypography } from "@/types/design-sync";
import type { EditorBridge } from "@/hooks/use-editor-bridge";
import { ColorContextMenu, FontContextMenu } from "./token-context-menu";
import { CssVariablesGenerator } from "./css-variables-generator";
import { countHexOccurrences, findOffBrandColors } from "@/lib/color-utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@email-hub/ui/components/ui/tooltip";

interface TokenDisplayProps {
  tokens: DesignTokens;
  editor: EditorBridge;
  editorContent: string;
  hasSelection: boolean;
}

function ColorSwatch({
  color,
  count,
  editor,
  hasSelection,
  t,
}: {
  color: DesignColor;
  count: number;
  editor: EditorBridge;
  hasSelection: boolean;
  t: (key: string) => string;
}) {
  const handleClick = () => {
    if (hasSelection) {
      editor.replaceInSelection(color.hex);
      toast.success(t("replacedInSelection"));
    } else {
      editor.insertAtCursor(`color: ${color.hex};`);
      toast.success(t("insertedAtCursor"));
    }
  };

  const handleFind = (e: React.MouseEvent) => {
    e.stopPropagation();
    editor.findAndHighlight(color.hex);
  };

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", `color: ${color.hex};`);
    e.dataTransfer.setData("application/x-design-token", color.hex);
    e.dataTransfer.effectAllowed = "copy";
  };

  const handleMouseEnter = () => editor.spotlight(color.hex);
  const handleMouseLeave = () => editor.clearHighlights();

  return (
    <ColorContextMenu hex={color.hex} name={color.name}>
      <div
        className="group relative flex cursor-pointer flex-col items-center gap-1"
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        draggable
        onDragStart={handleDragStart}
      >
        <div
          className="h-8 w-8 border border-card-border transition-shadow hover:shadow-md"
          style={{ backgroundColor: color.hex, opacity: color.opacity }}
        />
        <span
          className={`absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center text-[10px] font-semibold ${
            count === 0
              ? "bg-warning text-on-warning"
              : "bg-surface-elevated text-foreground-muted"
          } border border-border`}
        >
          {count}
        </span>
        <span className="text-[10px] text-foreground-muted">{color.hex}</span>
        <button
          type="button"
          onClick={handleFind}
          className="absolute -left-1 -top-1 hidden h-4 w-4 items-center justify-center bg-surface text-foreground-muted hover:text-foreground group-hover:flex"
          title={t("findInCode")}
        >
          <Search className="h-3 w-3" />
        </button>
      </div>
    </ColorContextMenu>
  );
}

function FontRow({
  typo,
  editor,
  t,
}: {
  typo: DesignTypography;
  editor: EditorBridge;
  t: (key: string) => string;
}) {
  const handleClick = () => {
    editor.insertAtCursor(`font-family: '${typo.family}';`);
    toast.success(t("insertedAtCursor"));
  };

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData(
      "text/plain",
      `font: ${typo.weight} ${typo.size}px/${typo.lineHeight}px '${typo.family}';`,
    );
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <FontContextMenu
      family={typo.family}
      weight={typo.weight}
      size={typo.size}
      lineHeight={typo.lineHeight}
    >
      <div
        className="group flex cursor-pointer items-center justify-between border border-border px-2 py-1.5 transition-colors hover:bg-surface-elevated"
        onClick={handleClick}
        draggable
        onDragStart={handleDragStart}
      >
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{typo.name}</p>
          <span className="text-[10px] text-foreground-muted">
            {typo.family} · {typo.weight} · {typo.size}px
          </span>
        </div>
        <span
          className="shrink-0 text-sm"
          style={{
            fontFamily: typo.family,
            fontWeight: typo.weight,
            fontSize: `${Math.min(typo.size, 18)}px`,
          }}
        >
          Aa
        </span>
      </div>
    </FontContextMenu>
  );
}

export function TokenDisplay({ tokens, editor, editorContent, hasSelection }: TokenDisplayProps) {
  const t = useTranslations("workspace.designReference");

  const colorCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const color of tokens.colors) {
      counts.set(color.hex, countHexOccurrences(editorContent, color.hex));
    }
    return counts;
  }, [tokens.colors, editorContent]);

  const offBrandColors = useMemo(() => {
    const tokenHexes = tokens.colors.map((c) => c.hex);
    return findOffBrandColors(editorContent, tokenHexes);
  }, [tokens.colors, editorContent]);

  return (
    <div className="space-y-4">
      {(tokens.colors.length > 0 || tokens.typography.length > 0) && (
        <CssVariablesGenerator tokens={tokens} editor={editor} />
      )}

      {tokens.colors.length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
            {t("colors")}
          </h4>
          <div className="grid grid-cols-4 gap-3">
            {tokens.colors.map((color) => (
              <ColorSwatch
                key={color.name}
                color={color}
                count={colorCounts.get(color.hex) ?? 0}
                editor={editor}
                hasSelection={hasSelection}
                t={t}
              />
            ))}
          </div>
        </section>
      )}

      {offBrandColors.length > 0 && (
        <section>
          <h4 className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-warning">
            <AlertTriangle className="h-3 w-3" />
            {t("offBrandColors")}
          </h4>
          <div className="space-y-1">
            {offBrandColors.map((obc) => (
              <TooltipProvider key={obc.hex}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 border border-border px-2 py-1 text-xs transition-colors hover:bg-surface-elevated"
                      onClick={() => {
                        editor.replaceAll(obc.hex, obc.closestHex);
                        toast.success(
                          t("correctedColor", { from: obc.hex, to: obc.closestHex }),
                        );
                      }}
                    >
                      <div className="flex items-center gap-1">
                        <div
                          className="h-4 w-4 border border-card-border"
                          style={{ backgroundColor: obc.hex }}
                        />
                        <ArrowRightLeft className="h-3 w-3 text-foreground-muted" />
                        <div
                          className="h-4 w-4 border border-card-border"
                          style={{ backgroundColor: obc.closestHex }}
                        />
                      </div>
                      <span className="text-foreground-muted">
                        {obc.hex} → {obc.closestHex}
                      </span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{t("clickToCorrect")}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
          </div>
        </section>
      )}

      {tokens.typography.length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
            {t("typography")}
          </h4>
          <div className="space-y-1.5">
            {tokens.typography.map((typo) => (
              <FontRow key={typo.name} typo={typo} editor={editor} t={t} />
            ))}
          </div>
        </section>
      )}

      {tokens.spacing.length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
            {t("spacing")}
          </h4>
          <div className="grid grid-cols-3 gap-2">
            {tokens.spacing.map((sp) => (
              <div
                key={sp.name}
                className="group flex cursor-pointer flex-col gap-0.5"
                onClick={() => {
                  editor.insertAtCursor(`padding: ${sp.value}px;`);
                  toast.success(t("insertedAtCursor"));
                }}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData("text/plain", `${sp.value}px`);
                  e.dataTransfer.effectAllowed = "copy";
                }}
              >
                <div
                  className="h-2 bg-interactive"
                  style={{ width: `${Math.min(sp.value, 60)}px` }}
                />
                <span className="text-[10px] text-foreground-muted">
                  {sp.name}: {sp.value}px
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
