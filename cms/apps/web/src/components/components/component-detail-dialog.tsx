"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Moon, Sun, Copy, Check, Plus, Camera, Pencil, Trash2 } from "../icons";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@email-hub/ui/components/ui/popover";
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
import { EditComponentDialog } from "./edit-component-dialog";
import { DeleteComponentDialog } from "./delete-component-dialog";
import { CreateVersionDialog } from "./create-version-dialog";
import { ComponentVersionTimeline } from "./component-version-timeline";
import { ComponentVersionCompareDialog } from "./component-version-compare-dialog";
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
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [createVersionOpen, setCreateVersionOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canVisualQa = userRole === "admin" || userRole === "developer";
  const canEdit = userRole === "admin" || userRole === "developer";
  const canDelete = userRole === "admin";

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
    [router, componentId],
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
            <span className="flex-1" />
            {canEdit && component && (
              <button
                type="button"
                onClick={() => setEditOpen(true)}
                className="text-foreground-muted hover:bg-surface-hover hover:text-foreground rounded-md p-1.5 transition-colors"
                aria-label="Edit component"
              >
                <Pencil className="h-4 w-4" />
              </button>
            )}
            {canDelete && component && (
              <button
                type="button"
                onClick={() => setDeleteOpen(true)}
                className="text-foreground-muted hover:bg-surface-hover hover:text-status-danger rounded-md p-1.5 transition-colors"
                aria-label="Delete component"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </DialogTitle>
          {component?.description && (
            <p className="text-foreground-muted text-sm">{component.description}</p>
          )}
        </DialogHeader>

        {/* Tab bar */}
        <div className="border-border flex gap-1 border-b" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-interactive text-foreground border-b-2"
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
                  className="border-border text-foreground hover:bg-surface-hover flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs transition-colors"
                  aria-label={"Dark mode"}
                >
                  {darkMode ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                  {"Dark mode"}
                </button>
              </div>
              <div className="border-border overflow-hidden rounded-md border">
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
                  <h4 className="text-foreground text-sm font-medium">{"HTML Source"}</h4>
                  {latestVersion?.html_source && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(latestVersion.html_source)}
                      className="text-foreground-muted hover:bg-surface-hover hover:text-foreground flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors"
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
                <div className="bg-surface-muted mt-2 max-h-80 overflow-auto rounded-md">
                  <pre className="text-foreground p-4 text-xs">
                    <code>{latestVersion?.html_source ?? "No source available"}</code>
                  </pre>
                </div>
              </div>

              {latestVersion?.css_source && (
                <div>
                  <h4 className="text-foreground text-sm font-medium">{"CSS Source"}</h4>
                  <div className="bg-surface-muted mt-2 max-h-60 overflow-auto rounded-md">
                    <pre className="text-foreground p-4 text-xs">
                      <code>{latestVersion.css_source}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "versions" && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h4 className="text-foreground text-sm font-medium">{"Version History"}</h4>
                <div className="flex gap-2">
                  {versions && versions.length >= 2 && (
                    <button
                      type="button"
                      onClick={() => setCompareOpen(true)}
                      className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1 text-xs transition-colors"
                    >
                      {"Compare Versions"}
                    </button>
                  )}
                  {canEdit && componentId && (
                    <button
                      type="button"
                      onClick={() => setCreateVersionOpen(true)}
                      className="bg-interactive text-on-interactive hover:bg-interactive-hover inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors"
                    >
                      <Plus className="h-3 w-3" />
                      {"New Version"}
                    </button>
                  )}
                </div>
              </div>
              {componentId && (
                <ComponentVersionTimeline componentId={componentId} versions={versions ?? []} />
              )}
            </div>
          )}

          {activeTab === "compatibility" && componentId && (
            <CompatibilityMatrix componentId={componentId} />
          )}
        </div>

        {/* Footer actions */}
        <div className="border-border flex justify-end gap-2 border-t pt-4">
          {canVisualQa && latestVersion?.html_source && latestVersion?.id && (
            <button
              type="button"
              onClick={() => setVisualQaOpen(true)}
              className="border-border text-foreground hover:bg-surface-hover inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors"
            >
              <Camera className="h-4 w-4" />
              {"Visual QA"}
            </button>
          )}
          <Popover open={campaignOpen} onOpenChange={setCampaignOpen}>
            <PopoverTrigger asChild>
              <button
                type="button"
                className="bg-interactive text-on-interactive hover:bg-interactive-hover inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors"
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
                          <span className="text-foreground text-sm font-medium">
                            {project.name}
                          </span>
                          <span className="text-foreground-muted text-xs">{project.status}</span>
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

      {component && (
        <>
          <EditComponentDialog open={editOpen} onOpenChange={setEditOpen} component={component} />
          <DeleteComponentDialog
            open={deleteOpen}
            onOpenChange={(o) => {
              setDeleteOpen(o);
              if (!o) onOpenChange(false);
            }}
            componentId={component.id}
            componentName={component.name}
          />
        </>
      )}

      {componentId && (
        <>
          <CreateVersionDialog
            open={createVersionOpen}
            onOpenChange={setCreateVersionOpen}
            componentId={componentId}
          />
          <ComponentVersionCompareDialog
            open={compareOpen}
            onOpenChange={setCompareOpen}
            componentId={componentId}
            versions={versions ?? []}
          />
        </>
      )}
    </Dialog>
  );
}
