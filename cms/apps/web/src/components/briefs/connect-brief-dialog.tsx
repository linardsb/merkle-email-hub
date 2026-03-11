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
import { useCreateBriefConnection } from "@/hooks/use-briefs";
import { useProjects } from "@/hooks/use-projects";
import type { BriefPlatform } from "@/types/briefs";

interface ConnectBriefDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PLATFORMS: { value: BriefPlatform; label: string }[] = [
  { value: "jira", label: "Jira" },
  { value: "asana", label: "Asana" },
  { value: "monday", label: "Monday.com" },
  { value: "clickup", label: "ClickUp" },
  { value: "trello", label: "Trello" },
  { value: "notion", label: "Notion" },
  { value: "wrike", label: "Wrike" },
  { value: "basecamp", label: "Basecamp" },
];

const URL_PLACEHOLDERS: Record<BriefPlatform, string> = {
  jira: "https://your-domain.atlassian.net/...",
  asana: "https://app.asana.com/...",
  monday: "https://your-org.monday.com/...",
  clickup: "https://app.clickup.com/...",
  trello: "https://trello.com/b/...",
  notion: "https://www.notion.so/...",
  wrike: "https://www.wrike.com/...",
  basecamp: "https://3.basecamp.com/...",
};

function getCredentialLabel(platform: BriefPlatform, t: ReturnType<typeof useTranslations<"briefs">>) {
  switch (platform) {
    case "jira": return t("connectJiraToken");
    case "asana": return t("connectAsanaPat");
    case "monday": return t("connectMondayKey");
    case "clickup": return t("connectClickupToken");
    case "trello": return t("connectTrelloKey");
    case "notion": return t("connectNotionToken");
    case "wrike": return t("connectWrikeToken");
    case "basecamp": return t("connectBasecampToken");
  }
}

function buildCredentials(platform: BriefPlatform, credential: string, jiraEmail: string, trelloToken: string): Record<string, string> {
  switch (platform) {
    case "jira": return { email: jiraEmail.trim(), api_token: credential.trim() };
    case "asana": return { personal_access_token: credential.trim() };
    case "monday": return { api_key: credential.trim() };
    case "clickup": return { api_token: credential.trim() };
    case "trello": return { api_key: credential.trim(), api_token: trelloToken.trim() };
    case "notion": return { integration_token: credential.trim() };
    case "wrike": return { access_token: credential.trim() };
    case "basecamp": return { access_token: credential.trim() };
  }
}

export function ConnectBriefDialog({ open, onOpenChange }: ConnectBriefDialogProps) {
  const t = useTranslations("briefs");
  const { trigger, isMutating } = useCreateBriefConnection();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  const [name, setName] = useState("");
  const [platform, setPlatform] = useState<BriefPlatform>("jira");
  const [projectUrl, setProjectUrl] = useState("");
  const [credential, setCredential] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [trelloToken, setTrelloToken] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);

  // Reset form when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setPlatform("jira");
    setProjectUrl("");
    setCredential("");
    setJiraEmail("");
    setTrelloToken("");
    setProjectId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const needsJiraEmail = platform === "jira";
  const needsTrelloToken = platform === "trello";

  const isValid =
    name.trim().length >= 1 &&
    projectUrl.trim().length >= 1 &&
    credential.trim().length >= 1 &&
    (!needsJiraEmail || jiraEmail.trim().length >= 1) &&
    (!needsTrelloToken || trelloToken.trim().length >= 1);

  const handleSubmit = async () => {
    if (!isValid) return;
    const credentials = buildCredentials(platform, credential, jiraEmail, trelloToken);

    try {
      await trigger({
        name: name.trim(),
        platform,
        project_url: projectUrl.trim(),
        credentials,
        project_id: projectId,
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/briefs"),
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
            <label htmlFor="brief-name" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectName")}
            </label>
            <input
              id="brief-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("connectNamePlaceholder")}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Platform */}
          <div>
            <label htmlFor="brief-platform" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectPlatformLabel")}
            </label>
            <select
              id="brief-platform"
              value={platform}
              onChange={(e) => setPlatform(e.target.value as BriefPlatform)}
              disabled={isMutating}
              className={selectClass}
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* Project URL */}
          <div>
            <label htmlFor="brief-url" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectProjectUrl")}
            </label>
            <input
              id="brief-url"
              type="url"
              value={projectUrl}
              onChange={(e) => setProjectUrl(e.target.value)}
              placeholder={URL_PLACEHOLDERS[platform]}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Jira email (only for Jira) */}
          {needsJiraEmail && (
            <div>
              <label htmlFor="brief-jira-email" className="mb-1.5 block text-sm font-medium text-foreground">
                {t("connectJiraEmail")}
              </label>
              <input
                id="brief-jira-email"
                type="email"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                placeholder="you@company.com"
                disabled={isMutating}
                className={inputClass}
              />
            </div>
          )}

          {/* Primary credential */}
          <div>
            <label htmlFor="brief-credential" className="mb-1.5 block text-sm font-medium text-foreground">
              {getCredentialLabel(platform, t)}
            </label>
            <input
              id="brief-credential"
              type="text"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder={
                platform === "jira" ? "ATATT3x..."
                  : platform === "asana" ? "1/12345..."
                  : "eyJhb..."
              }
              disabled={isMutating}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-foreground-muted">{t("connectCredentialHint")}</p>
          </div>

          {/* Trello extra token (only for Trello) */}
          {needsTrelloToken && (
            <div>
              <label htmlFor="brief-trello-token" className="mb-1.5 block text-sm font-medium text-foreground">
                {t("connectTrelloToken")}
              </label>
              <input
                id="brief-trello-token"
                type="text"
                value={trelloToken}
                onChange={(e) => setTrelloToken(e.target.value)}
                placeholder="ATTAb..."
                disabled={isMutating}
                className={inputClass}
              />
            </div>
          )}

          {/* Link to Project */}
          <div>
            <label htmlFor="brief-project" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("connectProject")}
            </label>
            <select
              id="brief-project"
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
