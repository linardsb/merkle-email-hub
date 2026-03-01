"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft, Save, Users } from "lucide-react";
import { ThemeToggle } from "@merkle-email-hub/ui/components/theme-toggle";
import { TemplateSelector } from "./template-selector";
import { SaveIndicator, type SaveStatus } from "./save-indicator";
import type { TemplateResponse } from "@/types/templates";

interface WorkspaceToolbarProps {
  projectName: string;
  memberCount?: number;
  templates: TemplateResponse[];
  activeTemplateId: number | null;
  onSelectTemplate: (template: TemplateResponse) => void;
  onCreateTemplate: () => void;
  onSave: () => void;
  saveStatus: SaveStatus;
  isLoadingTemplates?: boolean;
}

export function WorkspaceToolbar({
  projectName,
  memberCount,
  templates,
  activeTemplateId,
  onSelectTemplate,
  onCreateTemplate,
  onSave,
  saveStatus,
  isLoadingTemplates,
}: WorkspaceToolbarProps) {
  const t = useTranslations("workspace");
  const locale = useLocale();

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card px-4">
      <div className="flex items-center gap-3">
        <Link
          href={`/${locale}/dashboard`}
          className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("backToDashboard")}
        </Link>
        <span className="text-muted-foreground">/</span>
        <h1 className="text-sm font-semibold text-foreground">
          {projectName}
        </h1>
        <span className="text-muted-foreground">/</span>
        <TemplateSelector
          templates={templates}
          activeTemplateId={activeTemplateId}
          onSelect={onSelectTemplate}
          onCreate={onCreateTemplate}
          isLoading={isLoadingTemplates}
        />
      </div>
      <div className="flex items-center gap-3">
        <SaveIndicator status={saveStatus} />
        <button
          type="button"
          onClick={onSave}
          disabled={saveStatus === "saving" || saveStatus === "idle"}
          className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
          title={`${t("saveTemplate")} (\u2318S)`}
        >
          <Save className="h-3.5 w-3.5" />
          {t("saveTemplate")}
        </button>
        {memberCount !== undefined && (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Users className="h-3.5 w-3.5" />
            {memberCount} {t("members")}
          </span>
        )}
        <ThemeToggle />
      </div>
    </header>
  );
}
