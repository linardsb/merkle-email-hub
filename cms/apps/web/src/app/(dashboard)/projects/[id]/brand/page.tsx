"use client";

import { useState, useCallback } from "react";
import { useParams, notFound } from "next/navigation";
import { Palette, Loader2 } from "@/components/icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useProject } from "@/hooks/use-projects";
import { useBrandConfig, useUpdateBrandConfig } from "@/hooks/use-brand";
import { BrandColorEditor } from "@/components/brand/brand-color-editor";
import { BrandTypographyEditor } from "@/components/brand/brand-typography-editor";
import { BrandLogoRules } from "@/components/brand/brand-logo-rules";
import { BrandForbiddenPatterns } from "@/components/brand/brand-forbidden-patterns";
import type { BrandColor, BrandTypography, BrandLogoRule, ForbiddenPattern } from "@/types/brand";

export default function BrandSettingsPage() {
  const params = useParams<{ id: string }>();
  const projectId = Number(params.id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { data: project } = useProject(projectId);
  const orgId = project?.client_org_id ?? null;
  const { data: brandConfig, isLoading, error } = useBrandConfig(orgId);
  const { trigger: updateBrand, isMutating } = useUpdateBrandConfig();
  const { mutate } = useSWRConfig();

  const [colors, setColors] = useState<BrandColor[] | null>(null);
  const [typography, setTypography] = useState<BrandTypography[] | null>(null);
  const [logoRules, setLogoRules] = useState<BrandLogoRule | null | undefined>(undefined);
  const [forbiddenPatterns, setForbiddenPatterns] = useState<ForbiddenPattern[] | null>(null);

  // Use local state if edited, otherwise use server data
  const effectiveColors = colors ?? brandConfig?.colors ?? [];
  const effectiveTypography = typography ?? brandConfig?.typography ?? [];
  const effectiveLogoRules = logoRules !== undefined ? logoRules : (brandConfig?.logoRules ?? null);
  const effectiveForbidden = forbiddenPatterns ?? brandConfig?.forbiddenPatterns ?? [];

  const handleSave = useCallback(async () => {
    try {
      await updateBrand({
        org_id: orgId ?? 1,
        colors: effectiveColors,
        typography: effectiveTypography,
        logoRules: effectiveLogoRules,
        forbiddenPatterns: effectiveForbidden,
        updated_at: new Date().toISOString(),
      });
      await mutate((key: unknown) => typeof key === "string" && key.includes("/brand"), undefined, {
        revalidate: true,
      });
      toast.success("Brand configuration saved");
    } catch {
      toast.error("Failed to save brand configuration");
    }
  }, [
    orgId,
    effectiveColors,
    effectiveTypography,
    effectiveLogoRules,
    effectiveForbidden,
    updateBrand,
    mutate,
  ]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="text-foreground-muted h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-foreground text-2xl font-bold">{"Brand Guardrails"}</h1>
        <div className="border-card-border bg-card-bg rounded-lg border px-4 py-12 text-center">
          <p className="text-foreground-muted text-sm">{"Failed to load brand configuration"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Palette className="text-foreground h-6 w-6" />
          <div>
            <h1 className="text-foreground text-2xl font-bold">{"Brand Guardrails"}</h1>
            <p className="text-foreground-muted text-sm">
              {"Define brand colors, typography, logo rules, and forbidden patterns"}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={isMutating}
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
        >
          {isMutating ? (
            <span className="flex items-center gap-1.5">
              <Loader2 className="h-4 w-4 animate-spin" />
              {"Saving…"}
            </span>
          ) : (
            "Save Changes"
          )}
        </button>
      </div>

      {/* Brand Color Palette */}
      <div className="border-card-border bg-card-bg rounded-lg border p-5">
        <BrandColorEditor colors={effectiveColors} onChange={setColors} />
      </div>

      {/* Typography Rules */}
      <div className="border-card-border bg-card-bg rounded-lg border p-5">
        <BrandTypographyEditor typography={effectiveTypography} onChange={setTypography} />
      </div>

      {/* Logo Rules */}
      <div className="border-card-border bg-card-bg rounded-lg border p-5">
        <BrandLogoRules rules={effectiveLogoRules} onChange={setLogoRules} />
      </div>

      {/* Forbidden Patterns */}
      <div className="border-card-border bg-card-bg rounded-lg border p-5">
        <BrandForbiddenPatterns patterns={effectiveForbidden} onChange={setForbiddenPatterns} />
      </div>
    </div>
  );
}
