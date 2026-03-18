"use client";

import { Loader2, Palette } from "lucide-react";
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
        <Loader2 className="h-6 w-6 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg px-4 py-8 text-center">
        <p className="text-sm text-foreground-muted">Failed to load design tokens</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-2 text-sm font-medium text-interactive hover:underline"
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
        <h3 className="mb-3 text-sm font-medium text-foreground">
          Colors ({tokens.colors.length})
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {tokens.colors.map((color) => (
            <div key={color.name} className="flex flex-col items-center gap-1.5">
              <div
                className="h-10 w-10 rounded-lg border border-card-border"
                style={{
                  backgroundColor: color.hex,
                  opacity: color.opacity,
                }}
              />
              <span className="text-xs font-medium text-foreground">{color.name}</span>
              <span className="text-xs text-foreground-muted">{color.hex}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Typography */}
      <section>
        <h3 className="mb-3 text-sm font-medium text-foreground">
          Typography ({tokens.typography.length})
        </h3>
        <div className="space-y-2">
          {tokens.typography.map((typo) => (
            <div
              key={typo.name}
              className="flex items-center justify-between rounded-md border border-card-border bg-card-bg px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{typo.name}</p>
                <p className="text-xs text-foreground-muted">
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
        <h3 className="mb-3 text-sm font-medium text-foreground">
          Spacing ({tokens.spacing.length})
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {tokens.spacing.map((sp) => (
            <div key={sp.name} className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div
                  className="h-3 rounded-sm bg-interactive"
                  style={{ width: `${Math.min(sp.value, 80)}px` }}
                />
                <span className="text-xs text-foreground-muted">{sp.value}px</span>
              </div>
              <span className="text-xs font-medium text-foreground">{sp.name}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
