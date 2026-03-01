"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@merkle-email-hub/ui/components/ui/dialog";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { useTemplates, useTemplateVersions } from "@/hooks/use-templates";
import type { VersionResponse } from "@/types/templates";
import type { BuildResponse } from "@merkle-email-hub/sdk";

interface VersionCompareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  build: BuildResponse;
}

export function VersionCompareDialog({
  open,
  onOpenChange,
  build,
}: VersionCompareDialogProps) {
  const t = useTranslations("approvals");

  // Look up template by matching build's template_name within the project
  const { data: templatesData } = useTemplates(open ? build.project_id : null);
  const template = useMemo(
    () =>
      templatesData?.items.find(
        (tmpl) => tmpl.name === build.template_name
      ) ?? null,
    [templatesData, build.template_name]
  );

  // Fetch all versions for this template
  const { data: versions, isLoading: versionsLoading } = useTemplateVersions(
    template?.id ?? null
  );

  // Sort versions descending (latest first)
  const sortedVersions = useMemo(
    () =>
      versions
        ? [...versions].sort((a, b) => b.version_number - a.version_number)
        : [],
    [versions]
  );

  // Selected version numbers for left (before) and right (after) panes
  const [beforeVersion, setBeforeVersion] = useState<number | null>(null);
  const [afterVersion, setAfterVersion] = useState<number | null>(null);

  // Auto-select: After = latest, Before = second-latest (or same if only one)
  const latestVersion = sortedVersions[0] ?? null;
  const secondLatest = sortedVersions[1] ?? null;
  const effectiveAfter =
    afterVersion ?? (latestVersion ? latestVersion.version_number : null);
  const effectiveBefore =
    beforeVersion ??
    (secondLatest
      ? secondLatest.version_number
      : effectiveAfter);

  const beforeData = sortedVersions.find(
    (v) => v.version_number === effectiveBefore
  );
  const afterData = sortedVersions.find(
    (v) => v.version_number === effectiveAfter
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[85vh] max-w-7xl flex-col">
        <DialogHeader>
          <DialogTitle>{t("compareTitle")}</DialogTitle>
          <DialogDescription>{t("compareDescription")}</DialogDescription>
        </DialogHeader>

        {versionsLoading ? (
          <div className="flex flex-1 gap-4">
            <Skeleton className="flex-1 rounded-lg" />
            <Skeleton className="flex-1 rounded-lg" />
          </div>
        ) : sortedVersions.length === 0 ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-foreground-muted">
              {t("compareNoVersions")}
            </p>
          </div>
        ) : (
          <div className="flex flex-1 gap-4 overflow-hidden">
            {/* Before pane */}
            <VersionPane
              label={t("compareBefore")}
              versions={sortedVersions}
              selectedVersion={effectiveBefore}
              onSelectVersion={setBeforeVersion}
              versionData={beforeData ?? null}
              t={t}
            />

            {/* Divider */}
            <div className="w-px bg-border" />

            {/* After pane */}
            <VersionPane
              label={t("compareAfter")}
              versions={sortedVersions}
              selectedVersion={effectiveAfter}
              onSelectVersion={setAfterVersion}
              versionData={afterData ?? null}
              t={t}
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** One side of the comparison — version selector + iframe preview. */
function VersionPane({
  label,
  versions,
  selectedVersion,
  onSelectVersion,
  versionData,
  t,
}: {
  label: string;
  versions: VersionResponse[];
  selectedVersion: number | null;
  onSelectVersion: (v: number) => void;
  versionData: VersionResponse | null;
  t: ReturnType<typeof useTranslations>;
}) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-border">
      {/* Header: label + version selector */}
      <div className="flex items-center justify-between border-b border-border bg-surface-muted px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
          {label}
        </span>
        <select
          value={selectedVersion ?? ""}
          onChange={(e) => onSelectVersion(Number(e.target.value))}
          className="rounded-md border border-input-border bg-surface px-2 py-1 text-sm text-foreground"
        >
          {versions.map((v) => (
            <option key={v.version_number} value={v.version_number}>
              {t("compareVersion", { version: v.version_number })}
            </option>
          ))}
        </select>
      </div>

      {/* Version metadata */}
      {versionData && (
        <div className="border-b border-border px-3 py-1.5 text-xs text-foreground-muted">
          <span>
            {t("compareCreated", {
              date: new Date(versionData.created_at).toLocaleDateString(),
            })}
          </span>
          {versionData.changelog ? (
            <span className="ml-2">&middot; {versionData.changelog}</span>
          ) : (
            <span className="ml-2 italic">
              &middot; {t("compareNoChangelog")}
            </span>
          )}
        </div>
      )}

      {/* Preview iframe */}
      <div className="flex-1 overflow-auto bg-surface-muted p-2">
        {versionData ? (
          <iframe
            srcDoc={versionData.html_source}
            sandbox=""
            title={`${label} — v${versionData.version_number}`}
            className="h-full w-full border-0 bg-surface"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-foreground-muted">
              {t("compareSelectVersion")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
