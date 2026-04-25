"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreateFigmaConnection } from "@/hooks/use-figma";
import { useProjects } from "@/hooks/use-projects";

interface ConnectFigmaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectFigmaDialog({ open, onOpenChange }: ConnectFigmaDialogProps) {
  const { trigger, isMutating } = useCreateFigmaConnection();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  const [name, setName] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);

  // Reset form when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setFileUrl("");
    setAccessToken("");
    setProjectId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const isValid =
    name.trim().length >= 1 && fileUrl.trim().length >= 1 && accessToken.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await trigger({
        name: name.trim(),
        file_url: fileUrl.trim(),
        access_token: accessToken.trim(),
        project_id: projectId,
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
        undefined,
        { revalidate: true },
      );
      toast.success("Design file connected successfully");
      onOpenChange(false);
    } catch {
      toast.error("Failed to connect design file");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <DialogTitle>Connect Design File</DialogTitle>
          <DialogDescription>
            Link a design file to extract design tokens and sync your design system.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Connection Name */}
          <div>
            <label
              htmlFor="figma-name"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              Connection Name
            </label>
            <input
              id="figma-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Campaign Design System"
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Figma File URL */}
          <div>
            <label htmlFor="figma-url" className="text-foreground mb-1.5 block text-sm font-medium">
              Design File URL
            </label>
            <input
              id="figma-url"
              type="url"
              value={fileUrl}
              onChange={(e) => setFileUrl(e.target.value)}
              placeholder="https://www.figma.com/design/..."
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Personal Access Token */}
          <div>
            <label
              htmlFor="figma-token"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              Access Token
            </label>
            <input
              id="figma-token"
              type="text"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="figd_..."
              disabled={isMutating}
              className={inputClass}
            />
            <p className="text-foreground-muted mt-1 text-xs">
              Generate a token from your design tool&apos;s developer settings.
            </p>
          </div>

          {/* Link to Project */}
          <div>
            <label
              htmlFor="figma-project"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              Link to Project
            </label>
            <select
              id="figma-project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">None</option>
              {projects?.items?.map((proj) => (
                <option key={proj.id} value={proj.id}>
                  {proj.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || isMutating}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                Connecting&hellip;
              </span>
            ) : (
              "Connect"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
