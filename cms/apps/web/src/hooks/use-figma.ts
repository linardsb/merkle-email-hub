"use client";

/**
 * Figma-specific convenience hooks — thin wrappers over the unified
 * design-sync API (`/api/v1/design-sync/`).
 *
 * New code should prefer `use-design-sync.ts` directly.
 */

import { useCreateDesignConnection, useDesignTokens } from "@/hooks/use-design-sync";
import type { DesignConnectionCreate } from "@/types/design-sync";

// Re-export Figma-compatible types from design-sync
export type { DesignConnection as FigmaConnection } from "@/types/design-sync";
export type { DesignTokens as FigmaDesignTokens } from "@/types/design-sync";
export type { DesignConnectionCreate as FigmaConnectionCreate } from "@/types/design-sync";

/**
 * Create a design connection pre-filled with provider="figma".
 */
export function useCreateFigmaConnection() {
  const mutation = useCreateDesignConnection();
  return {
    ...mutation,
    trigger: (arg: Omit<DesignConnectionCreate, "provider">) =>
      mutation.trigger({ ...arg, provider: "figma" as const }),
  };
}

/**
 * Fetch design tokens for a given connection (provider-agnostic).
 */
export function useFigmaDesignTokens(connectionId: number | null) {
  return useDesignTokens(connectionId);
}
