"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2, Check } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useImportBrief, useBriefItems } from "@/hooks/use-briefs";
import type { BriefConnection } from "@/types/briefs";

interface BriefImportDialogProps {
  connection: BriefConnection | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BriefImportDialog({ connection, open, onOpenChange }: BriefImportDialogProps) {
  const { trigger, isMutating } = useImportBrief();
  const { mutate } = useSWRConfig();
  const { data: items } = useBriefItems(open && connection ? connection.id : null);

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [projectName, setProjectName] = useState("");

  // Reset on open
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setSelectedIds(new Set());
    setProjectName("");
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const toggleItem = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const isValid = selectedIds.size > 0 && projectName.trim().length >= 1;

  const handleImport = async () => {
    if (!isValid) return;
    try {
      await trigger({
        brief_item_ids: Array.from(selectedIds),
        project_name: projectName.trim(),
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/projects"),
        undefined,
        { revalidate: true },
      );
      toast.success("Project created from briefs");
      onOpenChange(false);
    } catch {
      toast.error("Failed to import briefs");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <DialogTitle>{"Import Briefs to Project"}</DialogTitle>
          <DialogDescription>
            {"Select brief items and create a new project from them."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Project name */}
          <div>
            <label
              htmlFor="import-project-name"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Project Name"}
            </label>
            <input
              id="import-project-name"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder={"e.g., Spring Sale Campaign"}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Brief items selection */}
          <div>
            <p className="text-foreground mb-1.5 text-sm font-medium">
              {"Select briefs to import"}
            </p>
            <div className="border-card-border max-h-48 space-y-1 overflow-y-auto rounded border p-2">
              {items?.map((item) => (
                <label
                  key={item.id}
                  className="text-foreground hover:bg-surface-hover flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm"
                >
                  <span
                    className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                      selectedIds.has(item.id)
                        ? "border-interactive bg-interactive text-foreground-inverse"
                        : "border-input-border bg-input-bg"
                    }`}
                  >
                    {selectedIds.has(item.id) && <Check className="h-3 w-3" />}
                  </span>
                  <span className="truncate">
                    {item.external_id} — {item.title}
                  </span>
                </label>
              )) ?? (
                <p className="text-foreground-muted py-2 text-center text-xs">{"No brief items"}</p>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={!isValid || isMutating}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Creating…"}
              </span>
            ) : (
              "Create Project"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
