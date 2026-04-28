"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PersonaResponse } from "@email-hub/sdk";
import { notFound, useParams, useSearchParams, useRouter } from "next/navigation";
import { Group, Panel, Separator, usePanelRef, type PanelSize } from "react-resizable-panels";
import { toast } from "sonner";
import { sanitizeHtml } from "@/lib/sanitize-html";
import { stripAnnotations } from "@/lib/builder-sync";
import { useSaveVersion, useCreateTemplate } from "@/hooks/use-templates";
import { useEmailPreview } from "@/hooks/use-email";
import { useQARun } from "@/hooks/use-qa";
import { usePersonas } from "@/hooks/use-personas";
import { fetcher } from "@/lib/swr-fetcher";
import { WorkspaceToolbar } from "@/components/workspace/workspace-toolbar";
import { EditorPanel } from "@/components/workspace/editor-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { BottomPanel } from "@/components/workspace/bottom-panel";
import { ToolSidebar } from "@/components/workspace/sidebar/tool-sidebar";
import { DesignReferencePanel } from "@/components/workspace/design-reference-panel";
import { useEditorBridge } from "@/hooks/use-editor-bridge";
import { ExportDialog } from "@/components/connectors/export-dialog";
import { useExportHistory } from "@/hooks/use-export-history";
import { useBrandConfig } from "@/hooks/use-brand";
import { useCollaboration } from "@/hooks/use-collaboration";
import { usePresence } from "@/hooks/use-presence";
import { PresencePanel } from "@/components/collaboration";
import { getCursorColor } from "@/lib/collaboration/awareness";
import { ImageGenDialog } from "@/components/workspace/image-gen/image-gen-dialog";
import { CompatibilityBriefDialog } from "@/components/workspace/compatibility-brief-dialog";
import { BlueprintRunDialog } from "@/components/workspace/blueprint-run-dialog";
import { PushToESPDialog } from "@/components/connectors/push-to-esp-dialog";
import { ApprovalRequestDialog } from "@/components/approvals/approval-request-dialog";
import { CommandPalette } from "@/components/workspace/command-palette";
import { useWorkspaceShortcuts } from "@/hooks/use-workspace-shortcuts";
import { useAgentMode } from "@/hooks/workspace/use-agent-mode";
import { useWorkspaceTemplate } from "@/hooks/workspace/use-workspace-template";
import { useWorkspaceDialogs } from "@/hooks/workspace/use-workspace-dialogs";
import { useWorkspaceFollowMode } from "@/hooks/workspace/use-workspace-follow-mode";
import { useEditorState } from "@/hooks/workspace/use-editor-state";
import { ChevronUp, GripVertical, GripHorizontal } from "@/components/icons";
import type { TemplateResponse } from "@/types/templates";
import type { QAResultResponse } from "@/types/qa";
import type { ViewMode } from "@/components/workspace/view-switcher";

const DEFAULT_TEMPLATE = `---
title: "New Email Template"
preheader: ""
---

<extends src="src/layouts/main.html">
  <block name="content">
    <!-- Start editing your email template here -->

  </block>
</extends>
`;

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = Number(params.id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const initialAgent = useAgentMode();

  const {
    project,
    projectLoading,
    projectError,
    templates,
    templatesLoading,
    mutateTemplates,
    activeTemplateId,
    setActiveTemplateId,
    activeTemplate,
    latestVersion,
    latestVersionNumber,
  } = useWorkspaceTemplate(projectId);

  const {
    editorContent,
    setEditorContent,
    savedContent,
    setSavedContent,
    saveStatus,
    setSaveStatus,
    isDirty,
    effectiveSaveStatus,
    savedTimerRef,
    cursorOffsetRef,
  } = useEditorState(DEFAULT_TEMPLATE);

  const dialogs = useWorkspaceDialogs();

  // ── Preview / QA / Push / Approval ──
  const [compiledHtml, setCompiledHtml] = useState<string | null>(null);
  const [buildTimeMs, setBuildTimeMs] = useState<number | null>(null);
  const { trigger: triggerPreview, isMutating: isCompiling } = useEmailPreview();
  const { trigger: triggerQA, isMutating: isRunningQA } = useQARun();
  const [qaResultData, setQaResultData] = useState<QAResultResponse | null>(null);
  const [qaPanelOpen, setQaPanelOpen] = useState(false);
  const { addRecord } = useExportHistory();
  const [lastBuildId, setLastBuildId] = useState<number | null>(null);

  // ── Design Reference Panel ──
  const [designRefOpen, setDesignRefOpen] = useState(false);
  const [hasEditorSelection, setHasEditorSelection] = useState(false);
  const editorBridge = useEditorBridge();

  // ── Brand Config ──
  const orgId = project?.client_org_id ?? null;
  const { data: brandConfig } = useBrandConfig(orgId);
  const [brandViolations, setBrandViolations] = useState(0);

  // ── Collaboration ──
  const {
    status: collabStatus,
    doc: collabDoc,
    awareness,
  } = useCollaboration(projectId, activeTemplateId);
  const { collaborators, followTarget, startFollowing, stopFollowing } = usePresence({
    awareness,
    role: "developer",
  });
  const [presencePanelOpen, setPresencePanelOpen] = useState(false);

  // ── View Mode ──
  const VALID_VIEWS: ViewMode[] = ["code", "builder", "split"];
  const viewParam = searchParams.get("view");
  const initialView: ViewMode =
    viewParam && VALID_VIEWS.includes(viewParam as ViewMode) ? (viewParam as ViewMode) : "code";
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);

  // ── Persona State ──
  const { data: personas, isLoading: personasLoading } = usePersonas();
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(null);

  const handlePersonaSelect = useCallback((persona: PersonaResponse | null) => {
    setSelectedPersonaId(persona?.id ?? null);
  }, []);

  // Sync editor content when version data loads + auto-compile once per template
  const autoCompiledRef = useRef(false);
  useEffect(() => {
    if (latestVersion?.html_source) {
      setEditorContent(latestVersion.html_source);
      setSavedContent(latestVersion.html_source);
      setSaveStatus("idle");

      if (collabDoc) {
        const yText = collabDoc.getText("content");
        if (yText.length === 0) {
          yText.insert(0, latestVersion.html_source);
        }
      }

      if (!autoCompiledRef.current) {
        autoCompiledRef.current = true;
        const sanitized = sanitizeHtml(stripAnnotations(latestVersion.html_source));
        triggerPreview({ source_html: sanitized })
          .then((r) => {
            if (r?.compiled_html) {
              setCompiledHtml(r.compiled_html);
              setBuildTimeMs(r.build_time_ms);
            } else {
              setCompiledHtml(sanitized);
            }
          })
          .catch(() => {
            setCompiledHtml(sanitized);
          });
      }
    }
  }, [
    latestVersion?.html_source,
    triggerPreview,
    collabDoc,
    setEditorContent,
    setSavedContent,
    setSaveStatus,
  ]);

  // Reset auto-compile flag when template changes
  useEffect(() => {
    autoCompiledRef.current = false;
  }, [activeTemplateId]);

  // ── Mutations ──
  const { trigger: saveVersion, isMutating: isSaving } = useSaveVersion(activeTemplateId);
  const { trigger: createTemplate } = useCreateTemplate(projectId);

  // ── Handlers ──
  const handleEditorChange = useCallback(
    (newValue: string) => {
      setEditorContent(newValue);
      if (saveStatus === "saved") setSaveStatus("idle");
    },
    [saveStatus, setEditorContent, setSaveStatus],
  );

  const handleSave = useCallback(async () => {
    if (!activeTemplateId || isSaving) return;

    const sanitized = sanitizeHtml(stripAnnotations(editorContent));

    triggerPreview({ source_html: sanitized })
      .then((r) => {
        if (r?.compiled_html) {
          setCompiledHtml(r.compiled_html);
          setBuildTimeMs(r.build_time_ms);
        } else {
          setCompiledHtml(sanitized);
        }
      })
      .catch(() => {
        setCompiledHtml(sanitized);
      });

    if (!isDirty) return;

    setSaveStatus("saving");
    try {
      const result = await saveVersion({ html_source: sanitized });
      if (result) {
        setSavedContent(editorContent);
        setSaveStatus("saved");
        mutateTemplates();
        toast.success(`Changes saved as version ${result.version_number}`);

        if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
        savedTimerRef.current = setTimeout(() => setSaveStatus("idle"), 3000);
      }
    } catch {
      setSaveStatus("error");
      toast.error("Failed to save");
    }
  }, [
    activeTemplateId,
    isDirty,
    isSaving,
    editorContent,
    saveVersion,
    mutateTemplates,
    triggerPreview,
    setSavedContent,
    setSaveStatus,
    savedTimerRef,
  ]);

  const handleCompile = useCallback(async () => {
    if (!editorContent.trim()) return;
    try {
      const sanitized = sanitizeHtml(stripAnnotations(editorContent));
      const result = await triggerPreview({ source_html: sanitized });
      if (result) {
        setCompiledHtml(result.compiled_html);
        setBuildTimeMs(result.build_time_ms);
      }
    } catch {
      toast.error("Failed to compile preview");
    }
  }, [editorContent, triggerPreview]);

  const handleSelectTemplate = useCallback(
    (template: TemplateResponse) => {
      setActiveTemplateId(template.id);
      setSaveStatus("idle");
      setCompiledHtml(null);
      setBuildTimeMs(null);
      setQaResultData(null);
      setQaPanelOpen(false);
      autoCompiledRef.current = false;
      const url = new URL(window.location.href);
      url.searchParams.set("template", String(template.id));
      router.replace(url.pathname + url.search, { scroll: false });
    },
    [router, setActiveTemplateId, setSaveStatus],
  );

  const handleCreateTemplate = useCallback(async () => {
    try {
      const result = await createTemplate({
        name: "Untitled Template",
        html_source: DEFAULT_TEMPLATE,
      });
      if (result) {
        await mutateTemplates();
        setActiveTemplateId(result.id);
        setEditorContent(DEFAULT_TEMPLATE);
        setSavedContent(DEFAULT_TEMPLATE);
        setSaveStatus("idle");
        toast.success("Template created");
      }
    } catch {
      toast.error("Failed to save");
    }
  }, [
    createTemplate,
    mutateTemplates,
    setActiveTemplateId,
    setEditorContent,
    setSavedContent,
    setSaveStatus,
  ]);

  const handleApplyToEditor = useCallback(
    (html: string) => {
      setEditorContent(html);
      setSaveStatus("idle");
      toast.success("AI output applied to editor");
    },
    [setEditorContent, setSaveStatus],
  );

  const handleApplyBlueprintResult = useCallback(
    (html: string) => {
      setEditorContent(html);
      setSaveStatus("idle");
      dialogs.setBlueprintOpen(false);
      toast.success("AI output applied to editor");
    },
    [setEditorContent, setSaveStatus, dialogs],
  );

  const handleRestoreVersion = useCallback(
    (html: string, _versionNumber: number) => {
      setEditorContent(html);
      setSavedContent(html);
      setSaveStatus("idle");
      setCompiledHtml(null);
      autoCompiledRef.current = false;
      mutateTemplates();

      const sanitized = sanitizeHtml(stripAnnotations(html));
      triggerPreview({ source_html: sanitized })
        .then((r) => {
          if (r?.compiled_html) {
            setCompiledHtml(r.compiled_html);
            setBuildTimeMs(r.build_time_ms);
          } else {
            setCompiledHtml(sanitized);
          }
        })
        .catch(() => {
          setCompiledHtml(sanitized);
        });
    },
    [mutateTemplates, triggerPreview, setEditorContent, setSavedContent, setSaveStatus],
  );

  // ── QA Handlers ──
  const handleRunQA = useCallback(async () => {
    if (!compiledHtml?.trim()) {
      toast.error("Compile the template first before running QA");
      return;
    }
    try {
      const result = await triggerQA({ html: compiledHtml });
      if (result) {
        setQaResultData(result);
        setQaPanelOpen(true);
        if (result.passed) {
          toast.success("All QA checks passed");
        } else {
          toast.warning(`${result.checks_total - result.checks_passed} QA check(s) failed`);
        }
      }
    } catch {
      toast.error("QA check failed");
    }
  }, [compiledHtml, triggerQA]);

  const handleQAOverrideSuccess = useCallback(() => {
    if (qaResultData?.id) {
      fetcher<QAResultResponse>(`/api/v1/qa/results/${qaResultData.id}`)
        .then((updated) => setQaResultData(updated))
        .catch(() => {
          /* override succeeded; panel will show stale data until next QA run */
        });
    }
  }, [qaResultData?.id]);

  // ── Export / Push / Approval Handlers ──
  const handleExport = useCallback(() => {
    if (!compiledHtml?.trim()) {
      toast.error("Compile the template first before exporting");
      return;
    }
    dialogs.setExportOpen(true);
  }, [compiledHtml, dialogs]);

  const handleCopyHtml = useCallback(() => {
    const html = sanitizeHtml(stripAnnotations(editorContent));
    navigator.clipboard.writeText(html).then(
      () => toast.success("HTML copied to clipboard"),
      () => toast.error("Failed to copy HTML"),
    );
  }, [editorContent]);

  const handleDownloadHtml = useCallback(() => {
    const html = sanitizeHtml(stripAnnotations(editorContent));
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeTemplate?.name ?? "email"}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("HTML downloaded");
  }, [editorContent, activeTemplate?.name]);

  const handleExportComplete = useCallback(
    (record: Parameters<typeof addRecord>[0]) => {
      if (record.build_id) setLastBuildId(record.build_id);
      addRecord(record);
    },
    [addRecord],
  );

  const handleSubmitForApproval = useCallback(() => {
    if (!compiledHtml?.trim()) {
      toast.error("Compile the template first before submitting for approval");
      return;
    }
    dialogs.setApprovalOpen(true);
  }, [compiledHtml, dialogs]);

  const handlePushToESP = useCallback(() => {
    if (!compiledHtml?.trim()) {
      toast.error("Compile the template first before pushing to ESP");
      return;
    }
    dialogs.setPushOpen(true);
  }, [compiledHtml, dialogs]);

  const handleInsertImage = useCallback(
    (url: string, width: number, height: number, alt: string) => {
      const escapeAttr = (s: string): string =>
        s
          .replace(/&/g, "&amp;")
          .replace(/"/g, "&quot;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
      const imgTag = `<img src="${escapeAttr(url)}" alt="${escapeAttr(alt)}" width="${width}" height="${height}" style="max-width: 100%; height: auto;" />`;
      setEditorContent((prev) => {
        const offset = Math.min(cursorOffsetRef.current, prev.length);
        return prev.slice(0, offset) + imgTag + prev.slice(offset);
      });
      setSaveStatus("idle");
      toast.success("AI output applied to editor");
    },
    [setEditorContent, setSaveStatus, cursorOffsetRef],
  );

  // ── Panel State ──
  const chatPanelRef = usePanelRef();
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const handleChatResize = useCallback((size: PanelSize) => {
    setChatCollapsed(size.asPercentage === 0);
  }, []);

  const handleToggleQAPanel = useCallback(() => {
    setQaPanelOpen((v) => {
      if (!v) setDesignRefOpen(false);
      return !v;
    });
  }, []);

  const handleToggleChat = useCallback(() => {
    if (chatCollapsed) {
      chatPanelRef.current?.expand();
    } else {
      chatPanelRef.current?.collapse();
    }
  }, [chatCollapsed, chatPanelRef]);

  const handleToggleView = useCallback(() => {
    setViewMode((current) => {
      const cycle: ViewMode[] = ["code", "builder", "split"];
      const idx = cycle.indexOf(current);
      return cycle[(idx + 1) % cycle.length] as ViewMode;
    });
  }, []);

  // ── Keyboard Shortcuts ──
  useWorkspaceShortcuts({
    onSave: handleSave,
    onGenerate: () => dialogs.setBlueprintOpen(true),
    onRunQA: handleRunQA,
    onExport: handleExport,
    onToggleChat: handleToggleChat,
    onToggleSidebar: handleToggleQAPanel,
    onToggleView: handleToggleView,
  });

  // ── Follow Mode ──
  useWorkspaceFollowMode({
    followTarget,
    collaborators,
    editorRef: editorBridge.editorRef,
  });

  // ── Render ──
  if (projectLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground text-sm">{"Loading workspace..."}</p>
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-destructive text-sm">
          {projectError?.status === 403
            ? "You don't have access to this project"
            : "Project not found"}
        </p>
      </div>
    );
  }

  return (
    <>
      <WorkspaceToolbar
        projectName={project.name}
        templates={templates}
        activeTemplateId={activeTemplateId}
        onSelectTemplate={handleSelectTemplate}
        onCreateTemplate={handleCreateTemplate}
        onSave={handleSave}
        saveStatus={effectiveSaveStatus}
        isLoadingTemplates={templatesLoading}
        onRunQA={handleRunQA}
        isRunningQA={isRunningQA}
        qaResult={qaResultData}
        onToggleQAPanel={handleToggleQAPanel}
        designRefOpen={designRefOpen}
        onDesignRefToggle={(open) => {
          setDesignRefOpen(open);
          if (open) setQaPanelOpen(false);
        }}
        onExport={handleExport}
        onPushToESP={handlePushToESP}
        onSubmitForApproval={handleSubmitForApproval}
        brandViolations={brandViolations}
        onGenerateImage={() => dialogs.setImageGenOpen(true)}
        collaborators={collaborators}
        collaborationStatus={collabStatus}
        onTogglePresencePanel={() => setPresencePanelOpen((v) => !v)}
        onViewBrief={() => dialogs.setBriefOpen(true)}
        onRunBlueprint={() => dialogs.setBlueprintOpen(true)}
        commandPalette={
          <CommandPalette
            onSave={handleSave}
            onRunBlueprint={() => dialogs.setBlueprintOpen(true)}
            onRunQA={handleRunQA}
            onExport={handleExport}
            onPushToESP={handlePushToESP}
            onSubmitForApproval={handleSubmitForApproval}
            onGenerateImage={() => dialogs.setImageGenOpen(true)}
            onToggleQAPanel={handleToggleQAPanel}
            onDesignRefToggle={(open) => {
              setDesignRefOpen(open);
              if (open) setQaPanelOpen(false);
            }}
            designRefOpen={designRefOpen}
            onToggleChat={handleToggleChat}
            onNavigateBack={() => router.push("/")}
          />
        }
      />

      <div className="flex flex-1 overflow-hidden">
        <Group orientation="vertical" className="flex-1">
          <Panel defaultSize={75} minSize={40}>
            <Group orientation="horizontal">
              <Panel defaultSize={50} minSize={25}>
                <EditorPanel
                  ref={editorBridge.editorRef}
                  value={editorContent}
                  onChange={handleEditorChange}
                  onSave={handleSave}
                  saveStatus={effectiveSaveStatus}
                  brandConfig={brandConfig}
                  onBrandViolationsChange={setBrandViolations}
                  onCursorOffsetChange={(offset) => {
                    cursorOffsetRef.current = offset;
                  }}
                  onSelectionChange={setHasEditorSelection}
                  collaborative={
                    collabDoc && awareness && collabStatus === "connected"
                      ? {
                          doc: collabDoc,
                          awareness,
                          user: {
                            name: "You",
                            color: getCursorColor(collabDoc.clientID),
                            role: "developer",
                          },
                        }
                      : undefined
                  }
                  projectId={projectId}
                  onViewChange={setViewMode}
                  initialView={viewParam ? initialView : undefined}
                  builderProps={{
                    onRunQA: handleRunQA,
                    isRunningQA,
                    onAISuggest: () => dialogs.setBlueprintOpen(true),
                    onCopyHtml: handleCopyHtml,
                    onDownloadHtml: handleDownloadHtml,
                    onPushToESP: handlePushToESP,
                  }}
                />
              </Panel>

              <Separator className="bg-border hover:bg-primary/50 data-[resize-handle-active]:bg-primary/50 flex w-1.5 items-center justify-center transition-colors">
                <GripVertical className="text-muted-foreground h-4 w-4" />
              </Separator>

              <Panel defaultSize={50} minSize={25}>
                <PreviewPanel
                  compiledHtml={compiledHtml}
                  isCompiling={isCompiling}
                  buildTimeMs={buildTimeMs}
                  onCompile={handleCompile}
                  hasContent={editorContent.trim().length > 0}
                  personas={personas ?? []}
                  selectedPersonaId={selectedPersonaId}
                  onPersonaSelect={handlePersonaSelect}
                  isLoadingPersonas={personasLoading}
                />
              </Panel>
            </Group>
          </Panel>

          <Separator className="bg-border hover:bg-primary/50 data-[resize-handle-active]:bg-primary/50 flex h-1.5 items-center justify-center transition-colors">
            <GripHorizontal className="text-muted-foreground h-4 w-4" />
          </Separator>

          <Panel
            panelRef={chatPanelRef}
            defaultSize={25}
            minSize={0}
            collapsible
            collapsedSize={0}
            onResize={handleChatResize}
          >
            <BottomPanel
              projectId={params.id}
              projectIdNum={projectId}
              onApplyToEditor={handleApplyToEditor}
              initialAgent={initialAgent}
              editorContent={editorContent}
              templateId={activeTemplateId}
              currentVersionNumber={latestVersionNumber}
              onRestoreVersion={handleRestoreVersion}
            />
          </Panel>
        </Group>

        {qaPanelOpen && qaResultData && (
          <ToolSidebar
            result={qaResultData}
            onClose={() => setQaPanelOpen(false)}
            onOverrideSuccess={handleQAOverrideSuccess}
            html={editorContent}
            entityType="golden_template"
            entityId={latestVersion?.id ?? 0}
            onHtmlUpdate={setEditorContent}
          />
        )}

        {presencePanelOpen && (
          <PresencePanel
            collaborators={collaborators}
            followTarget={followTarget}
            onFollow={startFollowing}
            onUnfollow={stopFollowing}
            onClose={() => setPresencePanelOpen(false)}
          />
        )}

        {designRefOpen && (
          <DesignReferencePanel
            projectId={projectId}
            templateId={activeTemplateId}
            editor={editorBridge}
            editorContent={editorContent}
            hasEditorSelection={hasEditorSelection}
            onClose={() => setDesignRefOpen(false)}
          />
        )}
      </div>

      <ExportDialog
        open={dialogs.exportOpen}
        onOpenChange={dialogs.setExportOpen}
        compiledHtml={compiledHtml}
        projectId={projectId}
        templateName={activeTemplate?.name ?? "email"}
        sourceHtml={editorContent}
        buildId={lastBuildId}
        onExportComplete={handleExportComplete}
      />

      <ImageGenDialog
        open={dialogs.imageGenOpen}
        onOpenChange={dialogs.setImageGenOpen}
        projectId={projectId}
        onInsertImage={handleInsertImage}
      />

      <CompatibilityBriefDialog
        open={dialogs.briefOpen}
        onOpenChange={dialogs.setBriefOpen}
        projectId={projectId}
        targetClients={project.target_clients ?? null}
      />

      <BlueprintRunDialog
        open={dialogs.blueprintOpen}
        onOpenChange={dialogs.setBlueprintOpen}
        projectId={projectId}
        currentHtml={editorContent}
        onApplyResult={handleApplyBlueprintResult}
      />

      <PushToESPDialog
        open={dialogs.pushOpen}
        onOpenChange={dialogs.setPushOpen}
        templateId={activeTemplate?.id ?? 0}
        templateName={activeTemplate?.name ?? "email"}
        projectId={projectId}
        compiledHtml={compiledHtml}
        buildId={lastBuildId}
      />

      <ApprovalRequestDialog
        open={dialogs.approvalOpen}
        onOpenChange={dialogs.setApprovalOpen}
        buildId={lastBuildId}
        projectId={projectId}
        compiledHtml={compiledHtml}
        onSubmitted={() => {
          dialogs.setApprovalOpen(false);
        }}
      />

      {chatCollapsed && (
        <button
          type="button"
          onClick={() => chatPanelRef.current?.expand()}
          className="border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground flex w-full items-center justify-center gap-2 border-t py-1.5 text-xs transition-colors"
        >
          <ChevronUp className="h-3.5 w-3.5" />
          {"Expand AI Assistant"}
        </button>
      )}
    </>
  );
}
