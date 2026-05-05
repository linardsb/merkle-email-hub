"use client";

import type { Ref } from "react";
import type { PersonaResponse } from "@email-hub/sdk";
import { Group, Panel, Separator, type PanelSize } from "react-resizable-panels";
import type { Awareness } from "y-protocols/awareness";
import type * as Y from "yjs";
import { GripVertical, GripHorizontal } from "@/components/icons";
import { EditorPanel } from "@/components/workspace/editor-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { BottomPanel } from "@/components/workspace/bottom-panel";
import type { CollaborationStatus } from "@/types/collaboration";
import type { ViewMode } from "@/components/workspace/view-switcher";
import type { CodeEditorHandle } from "@/hooks/use-editor-bridge";
import type { SaveStatus } from "@/components/workspace/save-indicator";
import { getCursorColor } from "@/lib/collaboration/awareness";

interface WorkspaceMainPanelsProps {
  // Editor
  editorRef: Ref<CodeEditorHandle>;
  editorContent: string;
  onEditorChange: (s: string) => void;
  onSave: () => Promise<void> | void;
  effectiveSaveStatus: SaveStatus;
  brandConfig: ReturnType<typeof import("@/hooks/use-brand").useBrandConfig>["data"];
  onBrandViolationsChange: (n: number) => void;
  onCursorOffsetChange: (n: number) => void;
  onSelectionChange: (b: boolean) => void;
  onViewChange: (v: ViewMode) => void;
  initialView: ViewMode | undefined;
  builderProps: NonNullable<React.ComponentProps<typeof EditorPanel>["builderProps"]>;
  projectId: number;
  // Collaboration
  collabDoc: Y.Doc | null;
  awareness: Awareness | null;
  collabStatus: CollaborationStatus;
  // Preview
  compiledHtml: string | null;
  isCompiling: boolean;
  buildTimeMs: number | null;
  onCompile: () => Promise<void> | void;
  personas: PersonaResponse[];
  selectedPersonaId: number | null;
  onPersonaSelect: (p: PersonaResponse | null) => void;
  isLoadingPersonas: boolean;
  // Bottom panel
  paramsId: string;
  initialAgent: ReturnType<typeof import("@/hooks/workspace/use-agent-mode").useAgentMode>;
  activeTemplateId: number | null;
  latestVersionNumber: number | null;
  onApplyToEditor: (html: string) => void;
  onRestoreVersion: (html: string, versionNumber: number) => void;
  // Chat panel
  chatPanelRef: ReturnType<typeof import("react-resizable-panels").usePanelRef>;
  chatCollapsed: boolean;
  onChatResize: (size: PanelSize) => void;
}

export function WorkspaceMainPanels(props: WorkspaceMainPanelsProps) {
  const {
    editorRef,
    editorContent,
    onEditorChange,
    onSave,
    effectiveSaveStatus,
    brandConfig,
    onBrandViolationsChange,
    onCursorOffsetChange,
    onSelectionChange,
    onViewChange,
    initialView,
    builderProps,
    projectId,
    collabDoc,
    awareness,
    collabStatus,
    compiledHtml,
    isCompiling,
    buildTimeMs,
    onCompile,
    personas,
    selectedPersonaId,
    onPersonaSelect,
    isLoadingPersonas,
    paramsId,
    initialAgent,
    activeTemplateId,
    latestVersionNumber,
    onApplyToEditor,
    onRestoreVersion,
    chatPanelRef,
    chatCollapsed,
    onChatResize,
  } = props;

  return (
    <Group orientation="vertical" className="flex-1">
      <Panel defaultSize={75} minSize={40}>
        <Group orientation="horizontal">
          <Panel defaultSize={50} minSize={25}>
            <EditorPanel
              ref={editorRef}
              value={editorContent}
              onChange={onEditorChange}
              onSave={onSave}
              saveStatus={effectiveSaveStatus}
              brandConfig={brandConfig}
              onBrandViolationsChange={onBrandViolationsChange}
              onCursorOffsetChange={onCursorOffsetChange}
              onSelectionChange={onSelectionChange}
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
              onViewChange={onViewChange}
              initialView={initialView}
              builderProps={builderProps}
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
              onCompile={onCompile}
              hasContent={editorContent.trim().length > 0}
              personas={personas}
              selectedPersonaId={selectedPersonaId}
              onPersonaSelect={onPersonaSelect}
              isLoadingPersonas={isLoadingPersonas}
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
        onResize={onChatResize}
      >
        <BottomPanel
          projectId={paramsId}
          projectIdNum={projectId}
          onApplyToEditor={onApplyToEditor}
          initialAgent={initialAgent}
          editorContent={editorContent}
          templateId={activeTemplateId}
          currentVersionNumber={latestVersionNumber}
          onRestoreVersion={onRestoreVersion}
        />
      </Panel>
    </Group>
  );
}
