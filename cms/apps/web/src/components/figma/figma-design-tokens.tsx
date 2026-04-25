"use client";

import { Loader2, Palette } from "../icons";
import { useFigmaDesignTokens } from "@/hooks/use-figma";
import { EmptyState } from "@/components/ui/empty-state";

interface FigmaDesignTokensViewProps {
  connectionId: number;
}

export function FigmaDesignTokensView({ connectionId }: FigmaDesignTokensViewProps) {
  const { data: tokens, isLoading, error } = useFigmaDesignTokens(connectionId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="text-foreground-muted h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border px-4 py-8 text-center">
        <p className="text-foreground-muted text-sm">Failed to load design tokens</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="text-interactive mt-2 text-sm font-medium hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!tokens) {
    return (
      <EmptyState
        icon={Palette}
        title="No design tokens"
        description="Design tokens will appear here once extracted from a connected design file."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Colors */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          Colors ({tokens.colors.length})
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {tokens.colors.map((color) => (
            <div key={color.name} className="flex flex-col items-center gap-1.5">
              <div
                className="border-card-border h-10 w-10 rounded-lg border"
                style={{
                  backgroundColor: color.hex,
                  opacity: color.opacity,
                }}
              />
              <span className="text-foreground text-xs font-medium">{color.name}</span>
              <span className="text-foreground-muted text-xs">{color.hex}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Typography */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          Typography ({tokens.typography.length})
        </h3>
        <div className="space-y-2">
          {tokens.typography.map((typo) => (
            <div
              key={typo.name}
              className="border-card-border bg-card-bg flex items-center justify-between rounded-md border px-3 py-2"
            >
              <div>
                <p className="text-foreground text-sm font-medium">{typo.name}</p>
                <p className="text-foreground-muted text-xs">
                  {typo.family} · {typo.weight} · {typo.size}px / {typo.lineHeight}px
                </p>
              </div>
              <span
                className="text-foreground-muted"
                style={{
                  fontFamily: typo.family,
                  fontWeight: typo.weight,
                  fontSize: `${Math.min(typo.size, 24)}px`,
                  lineHeight: 1,
                }}
              >
                Aa
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Spacing */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          Spacing ({tokens.spacing.length})
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {tokens.spacing.map((sp) => (
            <div key={sp.name} className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div
                  className="bg-interactive h-3 rounded-sm"
                  style={{ width: `${Math.min(sp.value, 80)}px` }}
                />
                <span className="text-foreground-muted text-xs">{sp.value}px</span>
              </div>
              <span className="text-foreground text-xs font-medium">{sp.name}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
