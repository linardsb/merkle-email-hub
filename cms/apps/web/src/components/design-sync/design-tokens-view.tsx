"use client";

import { Loader2, Palette } from "../icons";
import { useDesignTokens, useTokenDiff } from "@/hooks/use-design-sync";
import { EmptyState } from "@/components/ui/empty-state";

interface DesignTokensViewProps {
  connectionId: number;
}

export function DesignTokensView({ connectionId }: DesignTokensViewProps) {
  const { data: tokens, isLoading, error } = useDesignTokens(connectionId);
  const { data: diff } = useTokenDiff(connectionId);

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
        <p className="text-foreground-muted text-sm">{"Failed to load design tokens"}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="text-interactive mt-2 text-sm font-medium hover:underline"
        >
          {"Try again"}
        </button>
      </div>
    );
  }

  if (!tokens) {
    return (
      <EmptyState
        icon={Palette}
        title={"No design tokens"}
        description={"Design tokens will appear here once extracted from a connected design file."}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Token warnings */}
      {tokens.warnings && tokens.warnings.length > 0 && (
        <div className="border-warning-border bg-warning-bg rounded-md border px-3 py-2">
          <p className="text-warning-text text-xs font-medium">
            {"Token warnings"} ({tokens.warnings.length})
          </p>
          <ul className="mt-1 space-y-0.5">
            {tokens.warnings.map((w, i) => (
              <li key={i} className="text-foreground-muted text-xs">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Token diff summary */}
      {diff && diff.has_previous && diff.entries.length > 0 && (
        <div className="border-card-border bg-card-bg rounded-md border px-3 py-2">
          <p className="text-foreground text-xs font-medium">{"Changes since last sync"}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {diff.entries.map((e, i) => (
              <span
                key={i}
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  e.change === "added"
                    ? "bg-success-bg text-success-text"
                    : e.change === "removed"
                      ? "bg-destructive-bg text-destructive-text"
                      : "bg-warning-bg text-warning-text"
                }`}
              >
                {e.change === "added" ? "+" : e.change === "removed" ? "\u2212" : "~"} {e.category}:{" "}
                {e.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Colors */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          {"Colors"} ({tokens.colors.length})
        </h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {tokens.colors.map((color, i) => (
            <div key={`${color.hex}-${i}`} className="flex flex-col items-center gap-1.5">
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

      {/* Dark Mode Colors */}
      {tokens.dark_colors && tokens.dark_colors.length > 0 && (
        <section>
          <h3 className="text-foreground mb-3 text-sm font-medium">
            {"Dark Mode Colors"} ({tokens.dark_colors.length})
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
            {tokens.dark_colors.map((color, i) => (
              <div key={`dark-${color.hex}-${i}`} className="flex flex-col items-center gap-1.5">
                <div
                  className="border-card-border h-10 w-10 rounded-lg border"
                  style={{ backgroundColor: color.hex, opacity: color.opacity }}
                />
                <span className="text-foreground text-xs font-medium">{color.name}</span>
                <span className="text-foreground-muted text-xs">{color.hex}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Typography */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          {"Typography"} ({tokens.typography.length})
        </h3>
        <div className="space-y-2">
          {tokens.typography.map((typo, i) => (
            <div
              key={`${typo.family}-${typo.size}-${i}`}
              className="border-card-border bg-card-bg flex items-center justify-between rounded-md border px-3 py-2"
            >
              <div>
                <p className="text-foreground text-sm font-medium">{typo.name}</p>
                <p className="text-foreground-muted text-xs">
                  {typo.family} · {typo.weight} · {typo.size}px / {typo.lineHeight}px
                  {typo.letterSpacing != null && ` · ls ${typo.letterSpacing}px`}
                  {typo.textTransform && ` · ${typo.textTransform}`}
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

      {/* Gradients */}
      {tokens.gradients && tokens.gradients.length > 0 && (
        <section>
          <h3 className="text-foreground mb-3 text-sm font-medium">
            {"Gradients"} ({tokens.gradients.length})
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {tokens.gradients.map((g, i) => (
              <div key={`grad-${i}`} className="flex flex-col items-center gap-1.5">
                <div
                  className="border-card-border h-10 w-full rounded-lg border"
                  style={{
                    background: `linear-gradient(${g.angle}deg, ${g.stops.map((s) => `${s.hex} ${Math.round(s.position * 100)}%`).join(", ")})`,
                  }}
                />
                <span className="text-foreground text-xs font-medium">{g.name}</span>
                <span className="text-foreground-muted text-xs">
                  {g.type} · {g.angle}°
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Spacing */}
      <section>
        <h3 className="text-foreground mb-3 text-sm font-medium">
          {"Spacing"} ({tokens.spacing.length})
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
