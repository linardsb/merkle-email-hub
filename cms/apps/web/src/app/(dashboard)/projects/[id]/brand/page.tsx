"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { Palette, Loader2 } from "lucide-react";
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
  const t = useTranslations("brand");
  const params = useParams<{ id: string }>();
  const projectId = Number(params.id);

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
  const effectiveLogoRules = logoRules !== undefined ? logoRules : brandConfig?.logoRules ?? null;
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
      await mutate(
        (key: unknown) => typeof key === "string" && key.includes("/brand"),
        undefined,
        { revalidate: true },
      );
      toast.success(t("saveSuccess"));
    } catch {
      toast.error(t("saveError"));
    }
  }, [orgId, effectiveColors, effectiveTypography, effectiveLogoRules, effectiveForbidden, updateBrand, mutate, t]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
          <p className="text-sm text-foreground-muted">{t("error")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Palette className="h-6 w-6 text-foreground" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={isMutating}
          className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
        >
          {isMutating ? (
            <span className="flex items-center gap-1.5">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("saving")}
            </span>
          ) : (
            t("save")
          )}
        </button>
      </div>

      {/* Brand Color Palette */}
      <div className="rounded-lg border border-card-border bg-card-bg p-5">
        <BrandColorEditor
          colors={effectiveColors}
          onChange={setColors}
        />
      </div>

      {/* Typography Rules */}
      <div className="rounded-lg border border-card-border bg-card-bg p-5">
        <BrandTypographyEditor
          typography={effectiveTypography}
          onChange={setTypography}
        />
      </div>

      {/* Logo Rules */}
      <div className="rounded-lg border border-card-border bg-card-bg p-5">
        <BrandLogoRules
          rules={effectiveLogoRules}
          onChange={setLogoRules}
        />
      </div>

      {/* Forbidden Patterns */}
      <div className="rounded-lg border border-card-border bg-card-bg p-5">
        <BrandForbiddenPatterns
          patterns={effectiveForbidden}
          onChange={setForbiddenPatterns}
        />
      </div>
    </div>
  );
}
