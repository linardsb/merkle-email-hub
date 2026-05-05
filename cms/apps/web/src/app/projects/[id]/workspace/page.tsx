"use client";

import { useCallback, useState } from "react";
import { notFound, useParams, useSearchParams, useRouter } from "next/navigation";
import { usePanelRef, type PanelSize } from "react-resizable-panels";
import { useSaveVersion, useCreateTemplate } from "@/hooks/use-templates";
import { useEmailPreview } from "@/hooks/use-email";
import { useQARun } from "@/hooks/use-qa";
import { usePersonas } from "@/hooks/use-personas";
import { WorkspaceToolbar } from "@/components/workspace/workspace-toolbar";
import { WorkspaceDialogs } from "@/components/workspace/workspace-dialogs";
import { WorkspaceMainPanels } from "@/components/workspace/workspace-main-panels";
import { WorkspaceRightRail } from "@/components/workspace/workspace-right-rail";
import { CommandPalette } from "@/components/workspace/command-palette";
import { useEditorBridge } from "@/hooks/use-editor-bridge";
import { useExportHistory } from "@/hooks/use-export-history";
import { useBrandConfig } from "@/hooks/use-brand";
import { useCollaboration } from "@/hooks/use-collaboration";
import { usePresence } from "@/hooks/use-presence";
import { useWorkspaceShortcuts } from "@/hooks/use-workspace-shortcuts";
import { useAgentMode } from "@/hooks/workspace/use-agent-mode";
import { useWorkspaceTemplate } from "@/hooks/workspace/use-workspace-template";
import { useWorkspaceDialogs } from "@/hooks/workspace/use-workspace-dialogs";
import { useWorkspaceFollowMode } from "@/hooks/workspace/use-workspace-follow-mode";
import { useEditorState } from "@/hooks/workspace/use-editor-state";
import { useAutoCompile } from "@/hooks/workspace/use-auto-compile";
import { useWorkspaceExportActions } from "@/hooks/workspace/use-workspace-export-actions";
import { useWorkspaceActions } from "@/hooks/workspace/use-workspace-actions";
import { useWorkspaceQA } from "@/hooks/workspace/use-workspace-qa";
import { ChevronUp } from "@/components/icons";
import type { PersonaResponse } from "@email-hub/sdk";
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
  if (Number.isNaN(projectId)) notFound();

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

  const editor = useEditorState(DEFAULT_TEMPLATE);
  const dialogs = useWorkspaceDialogs();

  const [compiledHtml, setCompiledHtml] = useState<string | null>(null);
  const [buildTimeMs, setBuildTimeMs] = useState<number | null>(null);
  const { trigger: triggerPreview, isMutating: isCompiling } = useEmailPreview();
  const { trigger: triggerQA, isMutating: isRunningQA } = useQARun();
  const { addRecord } = useExportHistory();
  const [lastBuildId, setLastBuildId] = useState<number | null>(null);

  const [designRefOpen, setDesignRefOpen] = useState(false);
  const [hasEditorSelection, setHasEditorSelection] = useState(false);
  const editorBridge = useEditorBridge();

  const orgId = project?.client_org_id ?? null;
  const { data: brandConfig } = useBrandConfig(orgId);
  const [brandViolations, setBrandViolations] = useState(0);

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

  const VALID_VIEWS: ViewMode[] = ["code", "builder", "split"];
  const viewParam = searchParams.get("view");
  const initialView: ViewMode =
    viewParam && VALID_VIEWS.includes(viewParam as ViewMode) ? (viewParam as ViewMode) : "code";
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);

  const { data: personas, isLoading: personasLoading } = usePersonas();
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(null);
  const handlePersonaSelect = useCallback((persona: PersonaResponse | null) => {
    setSelectedPersonaId(persona?.id ?? null);
  }, []);

  const qa = useWorkspaceQA({
    compiledHtml,
    triggerQA,
    onOpen: () => setDesignRefOpen(false),
  });

  const autoCompiledRef = useAutoCompile({
    htmlSource: latestVersion?.html_source,
    activeTemplateId,
    triggerPreview,
    collabDoc,
    setEditorContent: editor.setEditorContent,
    setSavedContent: editor.setSavedContent,
    setSaveStatus: editor.setSaveStatus,
    setCompiledHtml,
    setBuildTimeMs,
  });

  const { trigger: saveVersion, isMutating: isSaving } = useSaveVersion(activeTemplateId);
  const { trigger: createTemplate } = useCreateTemplate(projectId);

  const actions = useWorkspaceActions({
    defaultTemplate: DEFAULT_TEMPLATE,
    activeTemplateId,
    setActiveTemplateId,
    mutateTemplates,
    editorContent: editor.editorContent,
    setEditorContent: editor.setEditorContent,
    setSavedContent: editor.setSavedContent,
    saveStatus: editor.saveStatus,
    setSaveStatus: editor.setSaveStatus,
    savedTimerRef: editor.savedTimerRef,
    isDirty: editor.isDirty,
    saveVersion,
    isSaving,
    createTemplate,
    triggerPreview,
    setCompiledHtml,
    setBuildTimeMs,
    setQaResultData: qa.setQaResultData,
    setQaPanelOpen: qa.setQaPanelOpen,
    autoCompiledRef,
    dialogs,
  });

  const exportActions = useWorkspaceExportActions({
    compiledHtml,
    editorContent: editor.editorContent,
    activeTemplate,
    dialogs,
    addRecord,
    setLastBuildId,
    setEditorContent: editor.setEditorContent,
    setSaveStatus: editor.setSaveStatus,
    cursorOffsetRef: editor.cursorOffsetRef,
  });

  const chatPanelRef = usePanelRef();
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const handleChatResize = useCallback((size: PanelSize) => {
    setChatCollapsed(size.asPercentage === 0);
  }, []);

  const handleToggleQAPanel = useCallback(() => {
    qa.setQaPanelOpen((v) => {
      if (!v) setDesignRefOpen(false);
      return !v;
    });
  }, [qa]);

  const handleToggleChat = useCallback(() => {
    if (chatCollapsed) chatPanelRef.current?.expand();
    else chatPanelRef.current?.collapse();
  }, [chatCollapsed, chatPanelRef]);

  const handleToggleView = useCallback(() => {
    setViewMode((current) => {
      const cycle: ViewMode[] = ["code", "builder", "split"];
      const idx = cycle.indexOf(current);
      return cycle[(idx + 1) % cycle.length] as ViewMode;
    });
  }, []);

  const handleDesignRefToggle = useCallback(
    (open: boolean) => {
      setDesignRefOpen(open);
      if (open) qa.setQaPanelOpen(false);
    },
    [qa],
  );

  const openBlueprint = useCallback(() => dialogs.setBlueprintOpen(true), [dialogs]);
  const openImageGen = useCallback(() => dialogs.setImageGenOpen(true), [dialogs]);
  const openBrief = useCallback(() => dialogs.setBriefOpen(true), [dialogs]);
  const togglePresence = useCallback(() => setPresencePanelOpen((v) => !v), []);

  useWorkspaceShortcuts({
    onSave: actions.handleSave,
    onGenerate: openBlueprint,
    onRunQA: qa.handleRunQA,
    onExport: exportActions.handleExport,
    onToggleChat: handleToggleChat,
    onToggleSidebar: handleToggleQAPanel,
    onToggleView: handleToggleView,
  });

  useWorkspaceFollowMode({
    followTarget,
    collaborators,
    editorRef: editorBridge.editorRef,
  });

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
        onSelectTemplate={actions.handleSelectTemplate}
        onCreateTemplate={actions.handleCreateTemplate}
        onSave={actions.handleSave}
        saveStatus={editor.effectiveSaveStatus}
        isLoadingTemplates={templatesLoading}
        onRunQA={qa.handleRunQA}
        isRunningQA={isRunningQA}
        qaResult={qa.qaResultData}
        onToggleQAPanel={handleToggleQAPanel}
        designRefOpen={designRefOpen}
        onDesignRefToggle={handleDesignRefToggle}
        onExport={exportActions.handleExport}
        onPushToESP={exportActions.handlePushToESP}
        onSubmitForApproval={exportActions.handleSubmitForApproval}
        brandViolations={brandViolations}
        onGenerateImage={openImageGen}
        collaborators={collaborators}
        collaborationStatus={collabStatus}
        onTogglePresencePanel={togglePresence}
        onViewBrief={openBrief}
        onRunBlueprint={openBlueprint}
        commandPalette={
          <CommandPalette
            onSave={actions.handleSave}
            onRunBlueprint={openBlueprint}
            onRunQA={qa.handleRunQA}
            onExport={exportActions.handleExport}
            onPushToESP={exportActions.handlePushToESP}
            onSubmitForApproval={exportActions.handleSubmitForApproval}
            onGenerateImage={openImageGen}
            onToggleQAPanel={handleToggleQAPanel}
            onDesignRefToggle={handleDesignRefToggle}
            designRefOpen={designRefOpen}
            onToggleChat={handleToggleChat}
            onNavigateBack={() => router.push("/")}
          />
        }
      />

      <div className="flex flex-1 overflow-hidden">
        <WorkspaceMainPanels
          editorRef={editorBridge.editorRef}
          editorContent={editor.editorContent}
          onEditorChange={actions.handleEditorChange}
          onSave={actions.handleSave}
          effectiveSaveStatus={editor.effectiveSaveStatus}
          brandConfig={brandConfig}
          onBrandViolationsChange={setBrandViolations}
          onCursorOffsetChange={(offset) => {
            editor.cursorOffsetRef.current = offset;
          }}
          onSelectionChange={setHasEditorSelection}
          onViewChange={setViewMode}
          initialView={viewParam ? initialView : undefined}
          builderProps={{
            onRunQA: qa.handleRunQA,
            isRunningQA,
            onAISuggest: openBlueprint,
            onCopyHtml: exportActions.handleCopyHtml,
            onDownloadHtml: exportActions.handleDownloadHtml,
            onPushToESP: exportActions.handlePushToESP,
          }}
          projectId={projectId}
          collabDoc={collabDoc}
          awareness={awareness}
          collabStatus={collabStatus}
          compiledHtml={compiledHtml}
          isCompiling={isCompiling}
          buildTimeMs={buildTimeMs}
          onCompile={actions.handleCompile}
          personas={personas ?? []}
          selectedPersonaId={selectedPersonaId}
          onPersonaSelect={handlePersonaSelect}
          isLoadingPersonas={personasLoading}
          paramsId={params.id}
          initialAgent={initialAgent}
          activeTemplateId={activeTemplateId}
          latestVersionNumber={latestVersionNumber}
          onApplyToEditor={actions.handleApplyToEditor}
          onRestoreVersion={actions.handleRestoreVersion}
          chatPanelRef={chatPanelRef}
          chatCollapsed={chatCollapsed}
          onChatResize={handleChatResize}
        />

        <WorkspaceRightRail
          qa={{
            open: qa.qaPanelOpen,
            result: qa.qaResultData,
            onClose: () => qa.setQaPanelOpen(false),
            onOverrideSuccess: qa.handleQAOverrideSuccess,
            html: editor.editorContent,
            entityId: latestVersion?.id ?? 0,
            onHtmlUpdate: editor.setEditorContent,
          }}
          presence={{
            open: presencePanelOpen,
            onClose: () => setPresencePanelOpen(false),
            collaborators,
            followTarget,
            onFollow: startFollowing,
            onUnfollow: stopFollowing,
          }}
          designRef={{
            open: designRefOpen,
            onClose: () => setDesignRefOpen(false),
            projectId,
            templateId: activeTemplateId,
            editor: editorBridge,
            editorContent: editor.editorContent,
            hasEditorSelection,
          }}
        />
      </div>

      <WorkspaceDialogs
        dialogs={dialogs}
        projectId={projectId}
        activeTemplate={activeTemplate}
        editorContent={editor.editorContent}
        compiledHtml={compiledHtml}
        lastBuildId={lastBuildId}
        targetClients={project.target_clients ?? null}
        onExportComplete={exportActions.handleExportComplete}
        onApplyBlueprintResult={actions.handleApplyBlueprintResult}
        onInsertImage={exportActions.handleInsertImage}
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
