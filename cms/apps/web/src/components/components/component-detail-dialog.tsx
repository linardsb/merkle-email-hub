"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Moon, Sun, Copy, Check, Plus, Camera } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@email-hub/ui/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@email-hub/ui/components/ui/command";
import { useSession } from "next-auth/react";
import { useComponent, useComponentVersions } from "@/hooks/use-components";
import { useProjects } from "@/hooks/use-projects";
import { ComponentPreview } from "./component-preview";
import { CompatibilityBadge } from "./compatibility-badge";
import { CompatibilityMatrix } from "./compatibility-matrix";
import { VisualQADialog } from "@/components/visual-qa/visual-qa-dialog";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";

interface ComponentDetailDialogProps {
  componentId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type Tab = "preview" | "source" | "versions" | "compatibility";

export function ComponentDetailDialog({
  componentId,
  open,
  onOpenChange,
}: ComponentDetailDialogProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("preview");
  const [darkMode, setDarkMode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [campaignOpen, setCampaignOpen] = useState(false);
  const [campaignSearch, setCampaignSearch] = useState("");
  const [visualQaOpen, setVisualQaOpen] = useState(false);
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canVisualQa = userRole === "admin" || userRole === "developer";

  const { data: component } = useComponent(componentId);
  const { data: versions } = useComponentVersions(componentId);
  const { data: projects } = useProjects({ search: campaignSearch, pageSize: 20 });

  const latestVersion = versions?.[0] ?? null;

  const copyToClipboard = useCallback(async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleSelectCampaign = useCallback(
    (projectId: number) => {
      setCampaignOpen(false);
      setCampaignSearch("");
      router.push(`/projects/${projectId}/workspace?componentId=${componentId}`);
    },
    [router, componentId]
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "preview", label: "Preview" },
    { key: "source", label: "Source" },
    { key: "versions", label: "Versions" },
    { key: "compatibility", label: "Compatibility" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {component?.name ?? "Component Details"}
            <CompatibilityBadge badge={component?.compatibility_badge} />
          </DialogTitle>
          {component?.description && (
            <p className="text-sm text-foreground-muted">
              {component.description}
            </p>
          )}
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-border" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-b-2 border-interactive text-foreground"
                  : "text-foreground-muted hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="mt-2 min-w-0 overflow-hidden">
          {activeTab === "preview" && (
            <div className="space-y-3">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setDarkMode((d) => !d)}
                  className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-surface-hover"
                  aria-label={"Dark mode"}
                >
                  {darkMode ? (
                    <Sun className="h-3.5 w-3.5" />
                  ) : (
                    <Moon className="h-3.5 w-3.5" />
                  )}
                  {"Dark mode"}
                </button>
              </div>
              <div className="overflow-hidden rounded-md border border-border">
                <ComponentPreview
                  html={latestVersion?.html_source ?? null}
                  darkMode={darkMode}
                  height={500}
                  interactive
                />
              </div>
            </div>
          )}

          {activeTab === "source" && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-foreground">
                    {"HTML Source"}
                  </h4>
                  {latestVersion?.html_source && (
                    <button
                      type="button"
                      onClick={() =>
                        copyToClipboard(latestVersion.html_source)
                      }
                      className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground"
                    >
                      {copied ? (
                        <>
                          <Check className="h-3 w-3" />
                          {"Copied to clipboard"}
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          {"Copy"}
                        </>
                      )}
                    </button>
                  )}
                </div>
                <div className="mt-2 max-h-80 overflow-auto rounded-md bg-surface-muted">
                  <pre className="p-4 text-xs text-foreground">
                    <code>
                      {latestVersion?.html_source ?? "No source available"}
                    </code>
                  </pre>
                </div>
              </div>

              {latestVersion?.css_source && (
                <div>
                  <h4 className="text-sm font-medium text-foreground">
                    {"CSS Source"}
                  </h4>
                  <div className="mt-2 max-h-60 overflow-auto rounded-md bg-surface-muted">
                    <pre className="p-4 text-xs text-foreground">
                      <code>{latestVersion.css_source}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "versions" && (
            <div>
              <h4 className="mb-3 text-sm font-medium text-foreground">
                {"Version History"}
              </h4>
              {versions && versions.length > 0 ? (
                <ScrollArea className="max-h-96">
                  <div className="space-y-3">
                    {versions.map((v) => (
                      <div
                        key={v.id}
                        className="rounded-md border border-border p-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground">
                            {`v${v.version_number}`}
                          </span>
                          <span className="text-xs text-foreground-muted">
                            {new Date(v.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-foreground-muted">
                          {`by User #${v.created_by_id}`}
                        </p>
                        {v.changelog ? (
                          <p className="mt-2 text-xs text-foreground">
                            {v.changelog}
                          </p>
                        ) : (
                          <p className="mt-2 text-xs text-foreground-muted italic">
                            {"No changelog"}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <p className="text-sm text-foreground-muted">
                  {"No versions"}
                </p>
              )}
            </div>
          )}

          {activeTab === "compatibility" && componentId && (
            <CompatibilityMatrix componentId={componentId} />
          )}
        </div>

        {/* Footer actions */}
        <div className="flex justify-end gap-2 border-t border-border pt-4">
          {canVisualQa && latestVersion?.html_source && latestVersion?.id && (
            <button
              type="button"
              onClick={() => setVisualQaOpen(true)}
              className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
            >
              <Camera className="h-4 w-4" />
              {"Visual QA"}
            </button>
          )}
          <Popover open={campaignOpen} onOpenChange={setCampaignOpen}>
            <PopoverTrigger asChild>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-on-interactive transition-colors hover:bg-interactive-hover"
              >
                <Plus className="h-4 w-4" />
                {"Add to Campaign"}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-0" align="end">
              <Command shouldFilter={false}>
                <CommandInput
                  placeholder={"Search campaigns..."}
                  value={campaignSearch}
                  onValueChange={setCampaignSearch}
                />
                <CommandList>
                  <CommandEmpty>{"No campaigns found"}</CommandEmpty>
                  <CommandGroup>
                    {projects?.items.map((project) => (
                      <CommandItem
                        key={project.id}
                        value={String(project.id)}
                        onSelect={() => handleSelectCampaign(project.id)}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm font-medium text-foreground">
                            {project.name}
                          </span>
                          <span className="text-xs text-foreground-muted">
                            {project.status}
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
      </DialogContent>

      {canVisualQa && latestVersion?.id && latestVersion?.html_source && (
        <VisualQADialog
          open={visualQaOpen}
          onClose={() => setVisualQaOpen(false)}
          html={latestVersion.html_source}
          entityType="component_version"
          entityId={latestVersion.id}
        />
      )}
    </Dialog>
  );
}
