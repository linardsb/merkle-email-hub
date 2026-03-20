"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import type { AppComponentsSchemasVersionResponse as VersionResponse } from "@email-hub/sdk";

interface ComponentVersionCompareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  componentId: number;
  versions: VersionResponse[];
}

export function ComponentVersionCompareDialog({
  open,
  onOpenChange,
  componentId: _componentId,
  versions,
}: ComponentVersionCompareDialogProps) {
  const sortedVersions = useMemo(
    () => [...versions].sort((a, b) => b.version_number - a.version_number),
    [versions]
  );

  const [beforeVersion, setBeforeVersion] = useState<number | null>(null);
  const [afterVersion, setAfterVersion] = useState<number | null>(null);

  const latestVersion = sortedVersions[0] ?? null;
  const secondLatest = sortedVersions[1] ?? null;
  const effectiveAfter =
    afterVersion ?? (latestVersion ? latestVersion.version_number : null);
  const effectiveBefore =
    beforeVersion ??
    (secondLatest ? secondLatest.version_number : effectiveAfter);

  const beforeData = sortedVersions.find(
    (v) => v.version_number === effectiveBefore
  );
  const afterData = sortedVersions.find(
    (v) => v.version_number === effectiveAfter
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[80vh] max-w-6xl flex-col">
        <DialogHeader>
          <DialogTitle>{"Compare Versions"}</DialogTitle>
          <DialogDescription>
            {"Side-by-side visual comparison of component versions"}
          </DialogDescription>
        </DialogHeader>

        {sortedVersions.length < 2 ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-foreground-muted">
              {"At least two versions are required for comparison"}
            </p>
          </div>
        ) : (
          <div className="flex flex-1 gap-4 overflow-hidden">
            <ComparePane
              label="Before"
              versions={sortedVersions}
              selectedVersion={effectiveBefore}
              onSelectVersion={setBeforeVersion}
              versionData={beforeData ?? null}
            />
            <div className="w-px bg-border" />
            <ComparePane
              label="After"
              versions={sortedVersions}
              selectedVersion={effectiveAfter}
              onSelectVersion={setAfterVersion}
              versionData={afterData ?? null}
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ComparePane({
  label,
  versions,
  selectedVersion,
  onSelectVersion,
  versionData,
}: {
  label: string;
  versions: VersionResponse[];
  selectedVersion: number | null;
  onSelectVersion: (v: number) => void;
  versionData: VersionResponse | null;
}) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-border">
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
              {`v${v.version_number}`}
            </option>
          ))}
        </select>
      </div>

      {versionData && (
        <div className="border-b border-border px-3 py-1.5 text-xs text-foreground-muted">
          <span>
            {`Created ${new Date(versionData.created_at).toLocaleDateString()}`}
          </span>
          {versionData.changelog ? (
            <span className="ml-2">&middot; {versionData.changelog}</span>
          ) : (
            <span className="ml-2 italic">&middot; {"No changelog"}</span>
          )}
        </div>
      )}

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
              {"Select version"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
