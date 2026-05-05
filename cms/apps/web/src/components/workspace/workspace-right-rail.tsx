"use client";

import { ToolSidebar } from "@/components/workspace/sidebar/tool-sidebar";
import { DesignReferencePanel } from "@/components/workspace/design-reference-panel";
import { PresencePanel } from "@/components/collaboration";
import type { useEditorBridge } from "@/hooks/use-editor-bridge";
import type { Collaborator, FollowTarget } from "@/types/collaboration";
import type { QAResultResponse } from "@/types/qa";

interface WorkspaceRightRailProps {
  qa: {
    open: boolean;
    result: QAResultResponse | null;
    onClose: () => void;
    onOverrideSuccess: () => void;
    html: string;
    entityId: number;
    onHtmlUpdate: (html: string) => void;
  };
  presence: {
    open: boolean;
    onClose: () => void;
    collaborators: Collaborator[];
    followTarget: FollowTarget | null;
    onFollow: (clientId: number, name: string) => void;
    onUnfollow: () => void;
  };
  designRef: {
    open: boolean;
    onClose: () => void;
    projectId: number;
    templateId: number | null;
    editor: ReturnType<typeof useEditorBridge>;
    editorContent: string;
    hasEditorSelection: boolean;
  };
}

export function WorkspaceRightRail({ qa, presence, designRef }: WorkspaceRightRailProps) {
  return (
    <>
      {qa.open && qa.result && (
        <ToolSidebar
          result={qa.result}
          onClose={qa.onClose}
          onOverrideSuccess={qa.onOverrideSuccess}
          html={qa.html}
          entityType="golden_template"
          entityId={qa.entityId}
          onHtmlUpdate={qa.onHtmlUpdate}
        />
      )}

      {presence.open && (
        <PresencePanel
          collaborators={presence.collaborators}
          followTarget={presence.followTarget}
          onFollow={presence.onFollow}
          onUnfollow={presence.onUnfollow}
          onClose={presence.onClose}
        />
      )}

      {designRef.open && (
        <DesignReferencePanel
          projectId={designRef.projectId}
          templateId={designRef.templateId}
          editor={designRef.editor}
          editorContent={designRef.editorContent}
          hasEditorSelection={designRef.hasEditorSelection}
          onClose={designRef.onClose}
        />
      )}
    </>
  );
}
