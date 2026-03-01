"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PersonaResponse } from "@merkle-email-hub/sdk";
import { useTranslations } from "next-intl";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import {
  Group,
  Panel,
  Separator,
  usePanelRef,
  type PanelSize,
} from "react-resizable-panels";
import { toast } from "sonner";
import { useProject } from "@/hooks/use-projects";
import {
  useTemplates,
  useTemplateVersion,
  useSaveVersion,
  useCreateTemplate,
} from "@/hooks/use-templates";
import { sanitizeHtml } from "@/lib/sanitize-html";
import { useEmailPreview } from "@/hooks/use-email";
import { useQARun } from "@/hooks/use-qa";
import { usePersonas } from "@/hooks/use-personas";
import { fetcher } from "@/lib/swr-fetcher";
import { WorkspaceToolbar } from "@/components/workspace/workspace-toolbar";
import { EditorPanel } from "@/components/workspace/editor-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { ChatPanel } from "@/components/workspace/chat-panel";
import { QAResultsPanel } from "@/components/workspace/qa-results-panel";
import { ChevronUp, GripVertical, GripHorizontal } from "lucide-react";
import type { SaveStatus } from "@/components/workspace/save-indicator";
import type { TemplateResponse } from "@/types/templates";
import type { QAResultResponse } from "@/types/qa";

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
  const t = useTranslations("workspace");
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = Number(params.id);

  // ── Data Fetching ──
  const {
    data: project,
    isLoading: projectLoading,
    error: projectError,
  } = useProject(projectId);
  const {
    data: templateData,
    isLoading: templatesLoading,
    mutate: mutateTemplates,
  } = useTemplates(projectId);
  const templates = templateData?.items ?? [];

  // ── Active Template ──
  const templateIdParam = searchParams.get("template");
  const [activeTemplateId, setActiveTemplateId] = useState<number | null>(
    templateIdParam ? Number(templateIdParam) : null
  );
  const activeTemplate =
    templates.find((tpl) => tpl.id === activeTemplateId) ?? null;

  // Auto-select first template when templates load and none selected
  useEffect(() => {
    const first = templates[0];
    if (!activeTemplateId && first) {
      setActiveTemplateId(first.id);
    }
  }, [activeTemplateId, templates]);

  // Load latest version content
  const latestVersionNumber = activeTemplate?.latest_version ?? null;
  const { data: latestVersion } = useTemplateVersion(
    activeTemplateId,
    latestVersionNumber
  );

  // ── Editor State ──
  const [editorContent, setEditorContent] = useState(DEFAULT_TEMPLATE);
  const [savedContent, setSavedContent] = useState(DEFAULT_TEMPLATE);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Preview State ──
  const [compiledHtml, setCompiledHtml] = useState<string | null>(null);
  const [buildTimeMs, setBuildTimeMs] = useState<number | null>(null);
  const { trigger: triggerPreview, isMutating: isCompiling } =
    useEmailPreview();

  // ── QA State ──
  const { trigger: triggerQA, isMutating: isRunningQA } = useQARun();
  const [qaResultData, setQaResultData] = useState<QAResultResponse | null>(
    null
  );
  const [qaPanelOpen, setQaPanelOpen] = useState(false);

  // ── Persona State ──
  const { data: personas, isLoading: personasLoading } = usePersonas();
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(
    null
  );

  const handlePersonaSelect = useCallback(
    (persona: PersonaResponse | null) => {
      setSelectedPersonaId(persona?.id ?? null);
    },
    []
  );

  // Sync editor content when version data loads
  useEffect(() => {
    if (latestVersion?.html_source) {
      setEditorContent(latestVersion.html_source);
      setSavedContent(latestVersion.html_source);
      setSaveStatus("idle");
    }
  }, [latestVersion?.html_source]);

  // Track dirty state
  const isDirty = editorContent !== savedContent;
  const effectiveSaveStatus: SaveStatus =
    saveStatus === "saving"
      ? "saving"
      : saveStatus === "error"
        ? "error"
        : saveStatus === "saved"
          ? "saved"
          : isDirty
            ? "unsaved"
            : "idle";

  // ── Mutations ──
  const { trigger: saveVersion, isMutating: isSaving } =
    useSaveVersion(activeTemplateId);
  const { trigger: createTemplate } = useCreateTemplate(projectId);

  // ── Handlers ──
  const handleEditorChange = useCallback(
    (newValue: string) => {
      setEditorContent(newValue);
      if (saveStatus === "saved") setSaveStatus("idle");
    },
    [saveStatus]
  );

  const handleSave = useCallback(async () => {
    if (!activeTemplateId || !isDirty || isSaving) return;

    setSaveStatus("saving");
    try {
      const sanitized = sanitizeHtml(editorContent);
      const result = await saveVersion({ html_source: sanitized });
      if (result) {
        setSavedContent(editorContent);
        setSaveStatus("saved");
        mutateTemplates();
        toast.success(
          t("templateSaved", { version: result.version_number })
        );

        // Auto-clear "saved" indicator after 3s
        if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
        savedTimerRef.current = setTimeout(() => setSaveStatus("idle"), 3000);

        // Auto-compile after successful save
        triggerPreview({ source_html: sanitized })
          .then((r) => {
            if (r) {
              setCompiledHtml(r.compiled_html);
              setBuildTimeMs(r.build_time_ms);
            }
          })
          .catch(() => {
            /* save succeeded, silently fail preview */
          });
      }
    } catch {
      setSaveStatus("error");
      toast.error(t("saveError"));
    }
  }, [
    activeTemplateId,
    isDirty,
    isSaving,
    editorContent,
    saveVersion,
    mutateTemplates,
    triggerPreview,
    t,
  ]);

  const handleCompile = useCallback(async () => {
    if (!editorContent.trim()) return;
    try {
      const sanitized = sanitizeHtml(editorContent);
      const result = await triggerPreview({ source_html: sanitized });
      if (result) {
        setCompiledHtml(result.compiled_html);
        setBuildTimeMs(result.build_time_ms);
      }
    } catch {
      toast.error(t("previewCompileError"));
    }
  }, [editorContent, triggerPreview, t]);

  const handleSelectTemplate = useCallback(
    (template: TemplateResponse) => {
      setActiveTemplateId(template.id);
      setSaveStatus("idle");
      setCompiledHtml(null);
      setBuildTimeMs(null);
      setQaResultData(null);
      setQaPanelOpen(false);
      const url = new URL(window.location.href);
      url.searchParams.set("template", String(template.id));
      router.replace(url.pathname + url.search, { scroll: false });
    },
    [router]
  );

  const handleCreateTemplate = useCallback(async () => {
    try {
      const result = await createTemplate({
        name: t("newTemplateName"),
        html_source: DEFAULT_TEMPLATE,
      });
      if (result) {
        await mutateTemplates();
        setActiveTemplateId(result.id);
        setEditorContent(DEFAULT_TEMPLATE);
        setSavedContent(DEFAULT_TEMPLATE);
        setSaveStatus("idle");
        toast.success(t("templateCreated"));
      }
    } catch {
      toast.error(t("saveError"));
    }
  }, [createTemplate, mutateTemplates, t]);

  const handleApplyToEditor = useCallback(
    (html: string) => {
      setEditorContent(html);
      setSaveStatus("idle");
      toast.success(t("chatApplied"));
    },
    [t]
  );

  // ── QA Handlers ──
  const tQA = useTranslations("qa");

  const handleRunQA = useCallback(async () => {
    if (!compiledHtml?.trim()) {
      toast.error(tQA("qaNoCompiledHtml"));
      return;
    }
    try {
      const result = await triggerQA({ html: compiledHtml });
      if (result) {
        setQaResultData(result);
        setQaPanelOpen(true);
        if (result.passed) {
          toast.success(tQA("qaPassed"));
        } else {
          toast.warning(
            tQA("qaFailed", {
              failed: result.checks_total - result.checks_passed,
            })
          );
        }
      }
    } catch {
      toast.error(tQA("qaError"));
    }
  }, [compiledHtml, triggerQA, tQA]);

  const handleQAOverrideSuccess = useCallback(() => {
    if (qaResultData?.id) {
      fetcher<QAResultResponse>(
        `/api/v1/qa/results/${qaResultData.id}`
      )
        .then((updated) => setQaResultData(updated))
        .catch(() => {
          /* override succeeded; panel will show stale data until next QA run */
        });
    }
  }, [qaResultData?.id]);

  // ── Panel State ──
  const chatPanelRef = usePanelRef();
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const handleChatResize = useCallback((size: PanelSize) => {
    setChatCollapsed(size.asPercentage === 0);
  }, []);

  // ── Render ──
  if (projectLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-destructive">
          {projectError?.status === 403 ? t("noAccess") : t("notFound")}
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
        onToggleQAPanel={() => setQaPanelOpen((v) => !v)}
      />

      <div className="flex flex-1 overflow-hidden">
        <Group orientation="vertical" className="flex-1">
          {/* Top: Editor + Preview (horizontal split) */}
          <Panel defaultSize={75} minSize={40}>
            <Group orientation="horizontal">
              <Panel defaultSize={50} minSize={25}>
                <EditorPanel
                  value={editorContent}
                  onChange={handleEditorChange}
                  onSave={handleSave}
                  saveStatus={effectiveSaveStatus}
                />
              </Panel>

              <Separator className="flex w-1.5 items-center justify-center bg-border transition-colors hover:bg-primary/50 data-[resize-handle-active]:bg-primary/50">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
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

          {/* Horizontal resize handle */}
          <Separator className="flex h-1.5 items-center justify-center bg-border transition-colors hover:bg-primary/50 data-[resize-handle-active]:bg-primary/50">
            <GripHorizontal className="h-4 w-4 text-muted-foreground" />
          </Separator>

          {/* Bottom: AI Chat (collapsible) */}
          <Panel
            panelRef={chatPanelRef}
            defaultSize={25}
            minSize={0}
            collapsible
            collapsedSize={0}
            onResize={handleChatResize}
          >
            <ChatPanel onApplyToEditor={handleApplyToEditor} />
          </Panel>
        </Group>

        {/* QA Results Panel (right sidebar) */}
        {qaPanelOpen && qaResultData && (
          <QAResultsPanel
            result={qaResultData}
            onClose={() => setQaPanelOpen(false)}
            onOverrideSuccess={handleQAOverrideSuccess}
          />
        )}
      </div>

      {chatCollapsed && (
        <button
          type="button"
          onClick={() => chatPanelRef.current?.expand()}
          className="flex w-full items-center justify-center gap-2 border-t border-border bg-card py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ChevronUp className="h-3.5 w-3.5" />
          {t("expandChat")}
        </button>
      )}
    </>
  );
}
