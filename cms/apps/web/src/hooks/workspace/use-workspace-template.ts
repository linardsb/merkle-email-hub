"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useTemplates, useTemplateVersion } from "@/hooks/use-templates";

/**
 * Owns project + template list + active template selection + latest version
 * fetch. Encapsulates two effects: sync-from-URL (?template=N) and
 * auto-select-first when no selection.
 */
export function useWorkspaceTemplate(projectId: number) {
  const searchParams = useSearchParams();
  const templateIdParam = searchParams.get("template");

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(projectId);
  const {
    data: templateData,
    isLoading: templatesLoading,
    mutate: mutateTemplates,
  } = useTemplates(projectId);

  const templates = templateData?.items ?? [];

  const [activeTemplateId, setActiveTemplateId] = useState<number | null>(
    templateIdParam ? Number(templateIdParam) : null,
  );
  const activeTemplate = templates.find((tpl) => tpl.id === activeTemplateId) ?? null;

  // Sync activeTemplateId when URL param changes (e.g. after design sync import).
  // Intentionally omits activeTemplateId from deps — including it would re-run
  // on every selection change and clobber unrelated UI state.
  useEffect(() => {
    if (templateIdParam) {
      const paramId = Number(templateIdParam);
      if (paramId !== activeTemplateId) {
        setActiveTemplateId(paramId);
      }
    }
  }, [templateIdParam]);

  // Auto-select first template when templates load and none selected
  useEffect(() => {
    const first = templates[0];
    if (!activeTemplateId && first) {
      setActiveTemplateId(first.id);
    }
  }, [activeTemplateId, templates]);

  const latestVersionNumber = activeTemplate?.latest_version ?? null;
  const { data: latestVersion } = useTemplateVersion(activeTemplateId, latestVersionNumber);

  return {
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
  };
}
