"use client";

import { ExportDialog } from "@/components/connectors/export-dialog";
import { useExportHistory } from "@/hooks/use-export-history";
import { ImageGenDialog } from "@/components/workspace/image-gen/image-gen-dialog";
import { CompatibilityBriefDialog } from "@/components/workspace/compatibility-brief-dialog";
import { BlueprintRunDialog } from "@/components/workspace/blueprint-run-dialog";
import { PushToESPDialog } from "@/components/connectors/push-to-esp-dialog";
import { ApprovalRequestDialog } from "@/components/approvals/approval-request-dialog";
import type { useWorkspaceDialogs } from "@/hooks/workspace/use-workspace-dialogs";
import type { TemplateResponse } from "@/types/templates";

interface WorkspaceDialogsProps {
  dialogs: ReturnType<typeof useWorkspaceDialogs>;
  projectId: number;
  activeTemplate: TemplateResponse | null;
  editorContent: string;
  compiledHtml: string | null;
  lastBuildId: number | null;
  targetClients: string[] | null;
  onExportComplete: (
    record: Parameters<ReturnType<typeof useExportHistory>["addRecord"]>[0],
  ) => void;
  onApplyBlueprintResult: (html: string) => void;
  onInsertImage: (url: string, width: number, height: number, alt: string) => void;
}

export function WorkspaceDialogs({
  dialogs,
  projectId,
  activeTemplate,
  editorContent,
  compiledHtml,
  lastBuildId,
  targetClients,
  onExportComplete,
  onApplyBlueprintResult,
  onInsertImage,
}: WorkspaceDialogsProps) {
  return (
    <>
      <ExportDialog
        open={dialogs.exportOpen}
        onOpenChange={dialogs.setExportOpen}
        compiledHtml={compiledHtml}
        projectId={projectId}
        templateName={activeTemplate?.name ?? "email"}
        sourceHtml={editorContent}
        buildId={lastBuildId}
        onExportComplete={onExportComplete}
      />

      <ImageGenDialog
        open={dialogs.imageGenOpen}
        onOpenChange={dialogs.setImageGenOpen}
        projectId={projectId}
        onInsertImage={onInsertImage}
      />

      <CompatibilityBriefDialog
        open={dialogs.briefOpen}
        onOpenChange={dialogs.setBriefOpen}
        projectId={projectId}
        targetClients={targetClients}
      />

      <BlueprintRunDialog
        open={dialogs.blueprintOpen}
        onOpenChange={dialogs.setBlueprintOpen}
        projectId={projectId}
        currentHtml={editorContent}
        onApplyResult={onApplyBlueprintResult}
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
    </>
  );
}
