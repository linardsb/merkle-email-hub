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

function getCredentialLabel(platform: BriefPlatform) {
  switch (platform) {
    case "jira":
      return "API Token";
    case "asana":
      return "Personal Access Token";
    case "monday":
      return "API Key";
    case "clickup":
      return "API Token";
    case "trello":
      return "API Key";
    case "notion":
      return "Integration Token";
    case "wrike":
      return "Access Token";
    case "basecamp":
      return "Access Token";
  }
}

function buildCredentials(
  platform: BriefPlatform,
  credential: string,
  jiraEmail: string,
  trelloToken: string,
): Record<string, string> {
  switch (platform) {
    case "jira":
      return { email: jiraEmail.trim(), api_token: credential.trim() };
    case "asana":
      return { personal_access_token: credential.trim() };
    case "monday":
      return { api_key: credential.trim() };
    case "clickup":
      return { api_token: credential.trim() };
    case "trello":
      return { api_key: credential.trim(), api_token: trelloToken.trim() };
    case "notion":
      return { integration_token: credential.trim() };
    case "wrike":
      return { access_token: credential.trim() };
    case "basecamp":
      return { access_token: credential.trim() };
  }
}

export function ConnectBriefDialog({ open, onOpenChange }: ConnectBriefDialogProps) {
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
      toast.success("Platform connected successfully");
      onOpenChange(false);
    } catch {
      toast.error("Failed to connect platform");
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
          <DialogTitle>{"Connect Brief Platform"}</DialogTitle>
          <DialogDescription>
            {"Link a project management tool to import campaign briefs and tasks."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Connection Name */}
          <div>
            <label
              htmlFor="brief-name"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Connection Name"}
            </label>
            <input
              id="brief-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={"e.g., Spring Campaign Briefs"}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Platform */}
          <div>
            <label
              htmlFor="brief-platform"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Platform"}
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
            <label htmlFor="brief-url" className="text-foreground mb-1.5 block text-sm font-medium">
              {"Project / Board URL"}
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
              <label
                htmlFor="brief-jira-email"
                className="text-foreground mb-1.5 block text-sm font-medium"
              >
                {"Jira Account Email"}
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
            <label
              htmlFor="brief-credential"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {getCredentialLabel(platform)}
            </label>
            <input
              id="brief-credential"
              type="text"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder={
                platform === "jira"
                  ? "ATATT3x..."
                  : platform === "asana"
                    ? "1/12345..."
                    : "eyJhb..."
              }
              disabled={isMutating}
              className={inputClass}
            />
            <p className="text-foreground-muted mt-1 text-xs">
              {"Credentials are encrypted and never stored in plain text."}
            </p>
          </div>

          {/* Trello extra token (only for Trello) */}
          {needsTrelloToken && (
            <div>
              <label
                htmlFor="brief-trello-token"
                className="text-foreground mb-1.5 block text-sm font-medium"
              >
                {"API Token"}
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
            <label
              htmlFor="brief-project"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Link to Project"}
            </label>
            <select
              id="brief-project"
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
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
          >
            {"Cancel"}
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
