"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
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
import { useCreateFigmaConnection } from "@/hooks/use-figma";
import { useProjects } from "@/hooks/use-projects";

interface ConnectFigmaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectFigmaDialog({ open, onOpenChange }: ConnectFigmaDialogProps) {
  const t = useTranslations("figma");
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

  const isValid = name.trim().length >= 1 && fileUrl.trim().length >= 1 && accessToken.trim().length >= 1;

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
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/figma"),
        undefined,
        { revalidate: true },
      );
      toast.success(t("connectSuccess"));
      onOpenChange(false);
    } catch {
      toast.error(t("connectError"));
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
          <DialogTitle>{t("connectTitle")}</DialogTitle>
          <DialogDescription>{t("connectDescription")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Connection Name */}
          <div>
            <label htmlFor="figma-name" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectName")}
            </label>
            <input
              id="figma-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("connectNamePlaceholder")}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Figma File URL */}
          <div>
            <label htmlFor="figma-url" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectFileUrl")}
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
            <label htmlFor="figma-token" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectAccessToken")}
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
            <p className="mt-1 text-xs text-foreground-muted">{t("connectAccessTokenHint")}</p>
          </div>

          {/* Link to Project */}
          <div>
            <label htmlFor="figma-project" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectProject")}
            </label>
            <select
              id="figma-project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">{t("connectProjectNone")}</option>
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
            {t("connectCancel")}
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
                {t("connectSubmitting")}
              </span>
            ) : (
              t("connectSubmit")
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
