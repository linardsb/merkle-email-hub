"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { FileText, Wand2, Blocks, Copy, Loader2 } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreateProject, useProjects } from "@/hooks/use-projects";
import { useOrgs } from "@/hooks/use-orgs";
import { useComponents } from "@/hooks/use-components";
import type { AgentMode } from "@/types/chat";
import type { ConnectorPlatform } from "@/types/connectors";
import type { ProjectCategory, CreationMethod } from "@/types/projects";
import { TargetClientsSelector } from "@/components/projects/target-clients-selector";

const AGENT_LABELS: Record<AgentMode, string> = {
  chat: "Chat",
  scaffolder: "Scaffolder",
  dark_mode: "Dark Mode",
  content: "Content",
  outlook_fixer: "Outlook Fixer",
  accessibility: "Accessibility",
  personalisation: "Personalisation",
  code_reviewer: "Code Reviewer",
  knowledge: "Knowledge",
  innovation: "Innovation",
};

/** Agents available for project kickoff (excludes generic "chat") */
const PROJECT_AGENTS: AgentMode[] = [
  "scaffolder",
  "dark_mode",
  "content",
  "outlook_fixer",
  "accessibility",
  "personalisation",
  "code_reviewer",
  "knowledge",
  "innovation",
];

const CATEGORIES: { value: ProjectCategory; label: string }[] = [
  { value: "promotional", label: "Promotional" },
  { value: "transactional", label: "Transactional" },
  { value: "newsletter", label: "Newsletter" },
  { value: "welcome_series", label: "Welcome Series" },
  { value: "automated", label: "Automated" },
  { value: "other", label: "Other" },
];

const ESP_OPTIONS: { value: ConnectorPlatform; label: string }[] = [
  { value: "braze", label: "Braze" },
  { value: "sfmc", label: "SFMC" },
  { value: "adobe_campaign", label: "Adobe Campaign" },
  { value: "taxi", label: "Taxi for Email" },
  { value: "raw_html", label: "Raw HTML" },
];

const METHOD_CONFIG: {
  value: CreationMethod;
  label: string;
  description: string;
  icon: typeof FileText;
  dynamic?: boolean;
}[] = [
  {
    value: "blank",
    label: "Blank Template",
    description: "Start from scratch with an empty template",
    icon: FileText,
  },
  {
    value: "ai_scaffolder",
    label: "AI Scaffolder",
    description: "Describe your campaign and let AI generate the initial template",
    icon: Wand2,
    dynamic: true,
  },
  {
    value: "from_components",
    label: "From Components",
    description: "Build from existing component library",
    icon: Blocks,
  },
  {
    value: "clone_existing",
    label: "Clone Existing",
    description: "Duplicate an existing project as a starting point",
    icon: Copy,
  },
];

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProjectDialog({ open, onOpenChange }: CreateProjectDialogProps) {
  const router = useRouter();
  const { trigger, isMutating } = useCreateProject();
  const { mutate } = useSWRConfig();

  const { data: orgs } = useOrgs();
  const { data: components } = useComponents({ pageSize: 50 });
  const { data: existingProjects } = useProjects({ pageSize: 50 });

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [clientOrgId, setClientOrgId] = useState<number | null>(null);
  const [category, setCategory] = useState<ProjectCategory>("promotional");
  const [targetEsp, setTargetEsp] = useState<ConnectorPlatform | "">("");
  const [method, setMethod] = useState<CreationMethod>("blank");
  const [aiBrief, setAiBrief] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<AgentMode>("scaffolder");
  const [selectedComponents, setSelectedComponents] = useState<number[]>([]);
  const [cloneProjectId, setCloneProjectId] = useState<number | null>(null);
  const [figmaUrl, setFigmaUrl] = useState("");
  const [targetClients, setTargetClients] = useState<string[]>([]);

  // Reset form when dialog opens (React 19 pattern — no useEffect)
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setDescription("");
    setClientOrgId(null);
    setCategory("promotional");
    setTargetEsp("");
    setMethod("blank");
    setAiBrief("");
    setSelectedAgent("scaffolder");
    setSelectedComponents([]);
    setCloneProjectId(null);
    setFigmaUrl("");
    setTargetClients([]);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  // Auto-select first org if only one available
  const orgItems = orgs?.items ?? [];
  const firstOrg = orgItems[0];
  if (clientOrgId === null && orgItems.length === 1 && firstOrg) {
    setClientOrgId(firstOrg.id);
  }

  const isValid = name.trim().length >= 1 && clientOrgId !== null;

  const handleToggleComponent = (id: number) => {
    setSelectedComponents((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  };

  const handleSubmit = async () => {
    if (!isValid || clientOrgId === null) return;
    try {
      const project = await trigger({
        name: name.trim(),
        description: description.trim() || undefined,
        client_org_id: clientOrgId,
        target_clients: targetClients.length > 0 ? targetClients : undefined,
      });
      // Revalidate projects list
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/projects"),
        undefined,
        { revalidate: true },
      );
      // Auto-create Figma connection if URL provided
      if (figmaUrl.trim() && project) {
        try {
          const { mutationFetcher: mf } = await import("@/lib/mutation-fetcher");
          await mf("/api/v1/design-sync/connections", {
            arg: {
              name: name.trim(),
              file_url: figmaUrl.trim(),
              access_token: "auto-linked",
              project_id: project.id,
            },
          });
        } catch {
          // Non-blocking — project was created successfully
        }
      }

      toast.success("Project created successfully");
      onOpenChange(false);

      // Build workspace URL with method-specific query params
      if (project) {
        const params = new URLSearchParams();
        if (method === "ai_scaffolder") {
          params.set("agent", selectedAgent);
        } else if (method === "from_components" && selectedComponents.length > 0) {
          params.set("components", selectedComponents.join(","));
        }
        const query = params.toString();
        router.push(`/projects/${project.id}/workspace${query ? `?${query}` : ""}`);
      }
    } catch {
      toast.error("Failed to create project");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-[36rem] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{"Create New Project"}</DialogTitle>
          <DialogDescription>
            {"Set up a new email project with your preferred starting point."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {/* ── Project Details ── */}

          {/* Name */}
          <div>
            <label
              htmlFor="project-name"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Project Name"}
            </label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={"e.g., Q2 Summer Campaign"}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="project-description"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Description"}
            </label>
            <textarea
              id="project-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={"Brief overview of this email project..."}
              rows={2}
              disabled={isMutating}
              className={inputClass + " resize-none"}
            />
          </div>

          {/* Org + Category row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="project-org"
                className="text-foreground mb-1.5 block text-sm font-medium"
              >
                {"Client Organization"}
              </label>
              <select
                id="project-org"
                value={clientOrgId ?? ""}
                onChange={(e) => setClientOrgId(e.target.value ? Number(e.target.value) : null)}
                disabled={isMutating}
                className={selectClass}
              >
                <option value="">{"Select organization"}</option>
                {orgItems.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="project-category"
                className="text-foreground mb-1.5 block text-sm font-medium"
              >
                {"Category"}
              </label>
              <select
                id="project-category"
                value={category}
                onChange={(e) => setCategory(e.target.value as ProjectCategory)}
                disabled={isMutating}
                className={selectClass}
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Target ESP */}
          <div>
            <label
              htmlFor="project-esp"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Target ESP"}
            </label>
            <select
              id="project-esp"
              value={targetEsp}
              onChange={(e) => setTargetEsp(e.target.value as ConnectorPlatform | "")}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">{"Decide later"}</option>
              {ESP_OPTIONS.map((esp) => (
                <option key={esp.value} value={esp.value}>
                  {esp.label}
                </option>
              ))}
            </select>
          </div>

          {/* Target Email Clients */}
          <div>
            <label className="text-foreground mb-1.5 block text-sm font-medium">
              {"Priority Email Clients"}
            </label>
            <TargetClientsSelector
              selected={targetClients}
              onChange={setTargetClients}
              disabled={isMutating}
            />
            <p className="text-foreground-muted mt-1 text-xs">
              {
                "QA checks all 25 clients. Priority clients get prominent display in results and drive agent retry focus."
              }
            </p>
          </div>

          {/* Figma File URL (optional) */}
          <div>
            <label
              htmlFor="project-figma-url"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Figma File URL"}
            </label>
            <input
              id="project-figma-url"
              type="url"
              value={figmaUrl}
              onChange={(e) => setFigmaUrl(e.target.value)}
              placeholder={"https://www.figma.com/design/..."}
              disabled={isMutating}
              className={inputClass}
            />
            <p className="text-foreground-muted mt-1 text-xs">
              {"Optional — link a Figma design file to this project"}
            </p>
          </div>

          {/* ── Separator ── */}
          <div className="border-border border-t" />

          {/* ── Creation Method ── */}
          <div>
            <p className="text-foreground mb-3 text-sm font-medium">
              {"How do you want to start?"}
            </p>
            <div className="grid grid-cols-2 gap-3">
              {METHOD_CONFIG.map((m) => {
                const Icon = m.icon;
                const selected = method === m.value;
                return (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => setMethod(m.value)}
                    disabled={isMutating}
                    className={`flex flex-col items-start gap-1.5 rounded-lg border-2 p-3.5 text-left transition-colors ${
                      selected
                        ? "border-interactive bg-interactive/5"
                        : "border-card-border bg-card-bg hover:bg-surface-hover"
                    } disabled:opacity-50`}
                  >
                    <Icon
                      className={`h-5 w-5 ${
                        selected ? "text-interactive" : "text-foreground-muted"
                      }`}
                    />
                    <span className="text-foreground text-sm font-medium">
                      {m.dynamic && selected ? AGENT_LABELS[selectedAgent] : m.label}
                    </span>
                    <span className="text-foreground-muted text-xs leading-snug">
                      {m.dynamic && selected
                        ? "Describe your campaign and let AI generate the initial template"
                        : m.description}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Method-specific sub-options ── */}

          {/* AI Scaffolder: agent picker + brief */}
          {method === "ai_scaffolder" && (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="project-agent"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"AI Agent"}
                </label>
                <select
                  id="project-agent"
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value as AgentMode)}
                  disabled={isMutating}
                  className={selectClass}
                >
                  {PROJECT_AGENTS.map((agent) => (
                    <option key={agent} value={agent}>
                      {AGENT_LABELS[agent]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="project-ai-brief"
                  className="text-foreground mb-1.5 block text-sm font-medium"
                >
                  {"Campaign Brief"}
                </label>
                <textarea
                  id="project-ai-brief"
                  value={aiBrief}
                  onChange={(e) => setAiBrief(e.target.value)}
                  placeholder={
                    "Describe the campaign: audience, goal, tone, key content sections..."
                  }
                  rows={3}
                  disabled={isMutating}
                  className={inputClass + " resize-none"}
                />
              </div>
            </div>
          )}

          {/* Component picker */}
          {method === "from_components" && (
            <div>
              <p className="text-foreground mb-2 text-sm font-medium">
                {"Select components to include:"}
              </p>
              <div className="border-card-border bg-card-bg max-h-[10rem] space-y-1.5 overflow-y-auto rounded-md border p-2">
                {components?.items && components.items.length > 0 ? (
                  components.items.map((comp) => (
                    <label
                      key={comp.id}
                      className="hover:bg-surface-hover flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedComponents.includes(comp.id)}
                        onChange={() => handleToggleComponent(comp.id)}
                        disabled={isMutating}
                        className="accent-interactive"
                      />
                      <span className="text-foreground">{comp.name}</span>
                      <span className="text-foreground-muted ml-auto text-xs">{comp.category}</span>
                    </label>
                  ))
                ) : (
                  <p className="text-foreground-muted py-2 text-center text-xs">
                    No components available
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Clone project picker */}
          {method === "clone_existing" && (
            <div>
              <label
                htmlFor="project-clone-source"
                className="text-foreground mb-1.5 block text-sm font-medium"
              >
                {"Select project to clone from:"}
              </label>
              <select
                id="project-clone-source"
                value={cloneProjectId ?? ""}
                onChange={(e) => setCloneProjectId(e.target.value ? Number(e.target.value) : null)}
                disabled={isMutating}
                className={selectClass}
              >
                <option value="">—</option>
                {existingProjects?.items?.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* ── Actions ── */}
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
                {"Creating..."}
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
