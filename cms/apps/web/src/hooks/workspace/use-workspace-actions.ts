import {
  useCallback,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { sanitizeHtml } from "@/lib/sanitize-html";
import { stripAnnotations } from "@/lib/builder-sync";
import type { useEmailPreview } from "@/hooks/use-email";
import type { useSaveVersion, useCreateTemplate } from "@/hooks/use-templates";
import type { useWorkspaceDialogs } from "@/hooks/workspace/use-workspace-dialogs";
import type { TemplateResponse } from "@/types/templates";
import type { SaveStatus } from "@/components/workspace/save-indicator";

interface ActionsArgs {
  defaultTemplate: string;
  activeTemplateId: number | null;
  setActiveTemplateId: (id: number | null) => void;
  mutateTemplates: () => Promise<unknown> | void;
  editorContent: string;
  setEditorContent: Dispatch<SetStateAction<string>>;
  setSavedContent: (s: string) => void;
  saveStatus: SaveStatus;
  setSaveStatus: Dispatch<SetStateAction<SaveStatus>>;
  savedTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
  isDirty: boolean;
  saveVersion: ReturnType<typeof useSaveVersion>["trigger"];
  isSaving: boolean;
  createTemplate: ReturnType<typeof useCreateTemplate>["trigger"];
  triggerPreview: ReturnType<typeof useEmailPreview>["trigger"];
  setCompiledHtml: Dispatch<SetStateAction<string | null>>;
  setBuildTimeMs: Dispatch<SetStateAction<number | null>>;
  setQaResultData: (data: null) => void;
  setQaPanelOpen: (open: boolean) => void;
  autoCompiledRef: MutableRefObject<boolean>;
  dialogs: ReturnType<typeof useWorkspaceDialogs>;
}

export function useWorkspaceActions(args: ActionsArgs) {
  const {
    defaultTemplate,
    activeTemplateId,
    setActiveTemplateId,
    mutateTemplates,
    editorContent,
    setEditorContent,
    setSavedContent,
    saveStatus,
    setSaveStatus,
    savedTimerRef,
    isDirty,
    saveVersion,
    isSaving,
    createTemplate,
    triggerPreview,
    setCompiledHtml,
    setBuildTimeMs,
    setQaResultData,
    setQaPanelOpen,
    autoCompiledRef,
    dialogs,
  } = args;
  const router = useRouter();

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
    setCompiledHtml,
    setBuildTimeMs,
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
  }, [editorContent, triggerPreview, setCompiledHtml, setBuildTimeMs]);

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
    [
      router,
      setActiveTemplateId,
      setSaveStatus,
      setCompiledHtml,
      setBuildTimeMs,
      setQaResultData,
      setQaPanelOpen,
      autoCompiledRef,
    ],
  );

  const handleCreateTemplate = useCallback(async () => {
    try {
      const result = await createTemplate({
        name: "Untitled Template",
        html_source: defaultTemplate,
      });
      if (result) {
        await mutateTemplates();
        setActiveTemplateId(result.id);
        setEditorContent(defaultTemplate);
        setSavedContent(defaultTemplate);
        setSaveStatus("idle");
        toast.success("Template created");
      }
    } catch {
      toast.error("Failed to save");
    }
  }, [
    defaultTemplate,
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
    [
      mutateTemplates,
      triggerPreview,
      setEditorContent,
      setSavedContent,
      setSaveStatus,
      setCompiledHtml,
      setBuildTimeMs,
      autoCompiledRef,
    ],
  );

  return {
    handleEditorChange,
    handleSave,
    handleCompile,
    handleSelectTemplate,
    handleCreateTemplate,
    handleApplyToEditor,
    handleApplyBlueprintResult,
    handleRestoreVersion,
  };
}
