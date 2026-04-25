"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2, CheckCircle2 } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreateTolgeeConnection, useTolgeeLanguages } from "@/hooks/use-tolgee";
import { useProjects } from "@/hooks/use-projects";
import type { TolgeeLanguage } from "@/types/tolgee";

interface TolgeeConnectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: (connectionId: number, languages: TolgeeLanguage[]) => void;
}

export function TolgeeConnectionDialog({
  open,
  onOpenChange,
  onConnected,
}: TolgeeConnectionDialogProps) {
  const { trigger, isMutating } = useCreateTolgeeConnection();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [pat, setPat] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);
  const [tolgeeProjectId, setTolgeeProjectId] = useState("");
  const [connectedId, setConnectedId] = useState<number | null>(null);

  const { data: languages } = useTolgeeLanguages(connectedId);

  // React 19 reset pattern
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setBaseUrl("");
    setPat("");
    setProjectId(null);
    setTolgeeProjectId("");
    setConnectedId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const tolgeeIdNum = parseInt(tolgeeProjectId, 10);
  const isValid =
    name.trim().length >= 1 &&
    pat.trim().length >= 1 &&
    projectId !== null &&
    !Number.isNaN(tolgeeIdNum) &&
    tolgeeIdNum > 0;

  const handleConnect = async () => {
    if (!isValid || projectId === null) return;
    try {
      const result = await trigger({
        name: name.trim(),
        project_id: projectId,
        tolgee_project_id: tolgeeIdNum,
        ...(baseUrl.trim() ? { base_url: baseUrl.trim() } : {}),
        pat: pat.trim(),
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/connectors/tolgee"),
        undefined,
        { revalidate: true },
      );
      setConnectedId(result.id);
      toast.success("Tolgee connection established");
    } catch {
      toast.error("Failed to connect — check your Tolgee URL and PAT");
    }
  };

  const handleDone = () => {
    if (connectedId && languages) {
      onConnected?.(connectedId, languages);
    }
    onOpenChange(false);
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <DialogTitle>{"Connect to Tolgee"}</DialogTitle>
          <DialogDescription>
            {"Set up a connection to your Tolgee translation management instance"}
          </DialogDescription>
        </DialogHeader>

        {connectedId && languages ? (
          // ── Post-connection: show languages ──
          <div className="space-y-4">
            <div className="text-status-success flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              <span className="text-sm font-medium">{"Connected successfully"}</span>
            </div>

            <div>
              <label className="text-foreground mb-1.5 block text-sm font-medium">
                {"Available Languages"}
              </label>
              <div className="flex flex-wrap gap-2">
                {languages.map((lang) => (
                  <span
                    key={lang.id}
                    className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-sm ${
                      lang.base
                        ? "border-interactive bg-interactive/10 text-interactive"
                        : "border-border bg-surface-elevated text-foreground"
                    }`}
                  >
                    <span>{lang.flag_emoji}</span>
                    <span>{lang.name}</span>
                    {lang.base && <span className="text-foreground-muted text-xs">{"(Base)"}</span>}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleDone}
                className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
              >
                {"Done"}
              </button>
            </div>
          </div>
        ) : (
          // ── Connection form ──
          <>
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="tolgee-name"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Connection Name"}
                </label>
                <input
                  id="tolgee-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Production Tolgee"
                  maxLength={200}
                  disabled={isMutating}
                  className={inputClass}
                />
              </div>

              <div>
                <label
                  htmlFor="tolgee-project"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Hub Project"}
                </label>
                <select
                  id="tolgee-project"
                  value={projectId ?? ""}
                  onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
                  disabled={isMutating}
                  className={selectClass}
                >
                  <option value="">{"Select a project"}</option>
                  {projects?.items?.map((proj) => (
                    <option key={proj.id} value={proj.id}>
                      {proj.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="tolgee-url"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Tolgee URL"}
                  <span className="text-foreground-muted ml-1">
                    {"(optional — uses default if blank)"}
                  </span>
                </label>
                <input
                  id="tolgee-url"
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://tolgee.example.com"
                  disabled={isMutating}
                  className={inputClass}
                />
              </div>

              <div>
                <label
                  htmlFor="tolgee-project-id"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Tolgee Project ID"}
                </label>
                <input
                  id="tolgee-project-id"
                  type="number"
                  value={tolgeeProjectId}
                  onChange={(e) => setTolgeeProjectId(e.target.value)}
                  placeholder="e.g., 42"
                  min={1}
                  disabled={isMutating}
                  className={inputClass}
                />
              </div>

              <div>
                <label
                  htmlFor="tolgee-pat"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Personal Access Token"}
                </label>
                <input
                  id="tolgee-pat"
                  type="password"
                  autoComplete="off"
                  value={pat}
                  onChange={(e) => setPat(e.target.value)}
                  placeholder="tgpat_..."
                  disabled={isMutating}
                  className={inputClass}
                />
              </div>
            </div>

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
                onClick={handleConnect}
                disabled={!isValid || isMutating}
                className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isMutating ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {"Validating…"}
                  </span>
                ) : (
                  "Connect"
                )}
              </button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
