"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreateDesignConnection } from "@/hooks/use-design-sync";
import { useProjects } from "@/hooks/use-projects";
import type { DesignProvider } from "@/types/design-sync";

interface ConnectDesignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PROVIDERS: { value: DesignProvider; label: string }[] = [
  { value: "figma", label: "Figma" },
  { value: "sketch", label: "Sketch" },
  { value: "canva", label: "Canva" },
];

export function ConnectDesignDialog({ open, onOpenChange }: ConnectDesignDialogProps) {
  const { trigger, isMutating } = useCreateDesignConnection();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  const [name, setName] = useState("");
  const [provider, setProvider] = useState<DesignProvider>("figma");
  const [fileUrl, setFileUrl] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);

  // Reset form when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setProvider("figma");
    setFileUrl("");
    setAccessToken("");
    setProjectId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const isValid = name.trim().length >= 1 && fileUrl.trim().length >= 1 && accessToken.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await trigger({
        name: name.trim(),
        provider,
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
          <DialogTitle>{"Connect Design File"}</DialogTitle>
          <DialogDescription>{"Link a design file to extract design tokens and sync your design system."}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Provider */}
          <div>
            <label htmlFor="design-provider" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Design Tool"}
            </label>
            <select
              id="design-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value as DesignProvider)}
              disabled={isMutating}
              className={selectClass}
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* Connection Name */}
          <div>
            <label htmlFor="design-name" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Connection Name"}
            </label>
            <input
              id="design-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={"e.g., Campaign Design System"}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* File URL */}
          <div>
            <label htmlFor="design-url" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Design File URL"}
            </label>
            <input
              id="design-url"
              type="url"
              value={fileUrl}
              onChange={(e) => setFileUrl(e.target.value)}
              placeholder={provider === "figma" ? "https://www.figma.com/design/..." : "Paste file URL…"}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Access Token */}
          <div>
            <label htmlFor="design-token" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Access Token"}
            </label>
            <input
              id="design-token"
              type="text"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder={provider === "figma" ? "figd_..." : "Paste access token…"}
              disabled={isMutating}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-foreground-muted">{"Generate a token from your design tool's developer settings."}</p>
          </div>

          {/* Link to Project */}
          <div>
            <label htmlFor="design-project" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Link to Project"}
            </label>
            <select
              id="design-project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">{"None"}</option>
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
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || isMutating}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Connecting…"}
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
