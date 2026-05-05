import { useCallback, type Dispatch, type SetStateAction, type MutableRefObject } from "react";
import { toast } from "sonner";
import { sanitizeHtml } from "@/lib/sanitize-html";
import { stripAnnotations } from "@/lib/builder-sync";
import type { useExportHistory } from "@/hooks/use-export-history";
import type { useWorkspaceDialogs } from "@/hooks/workspace/use-workspace-dialogs";
import type { TemplateResponse } from "@/types/templates";
import type { SaveStatus } from "@/components/workspace/save-indicator";

interface ExportActionsArgs {
  compiledHtml: string | null;
  editorContent: string;
  activeTemplate: TemplateResponse | null;
  dialogs: ReturnType<typeof useWorkspaceDialogs>;
  addRecord: ReturnType<typeof useExportHistory>["addRecord"];
  setLastBuildId: Dispatch<SetStateAction<number | null>>;
  setEditorContent: Dispatch<SetStateAction<string>>;
  setSaveStatus: Dispatch<SetStateAction<SaveStatus>>;
  cursorOffsetRef: MutableRefObject<number>;
}

export function useWorkspaceExportActions(args: ExportActionsArgs) {
  const {
    compiledHtml,
    editorContent,
    activeTemplate,
    dialogs,
    addRecord,
    setLastBuildId,
    setEditorContent,
    setSaveStatus,
    cursorOffsetRef,
  } = args;

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
    [addRecord, setLastBuildId],
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

  return {
    handleExport,
    handleCopyHtml,
    handleDownloadHtml,
    handleExportComplete,
    handleSubmitForApproval,
    handlePushToESP,
    handleInsertImage,
  };
}
