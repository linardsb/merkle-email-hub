"use client";

import Link from "next/link";
import { ArrowLeft, Save, ShieldCheck, Zap, Palette } from "../icons";
import { ThemeToggle } from "@email-hub/ui/components/theme-toggle";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@email-hub/ui/components/ui/tooltip";
import { TemplateSelector } from "./template-selector";
import { SaveIndicator, type SaveStatus } from "./save-indicator";
import { CollaborationBanner } from "@/components/collaboration";
import { DeliverMenu } from "./toolbar/deliver-menu";
import { ToolsMenu } from "./toolbar/tools-menu";
import type { TemplateResponse } from "@/types/templates";
import type { Collaborator, CollaborationStatus } from "@/types/collaboration";

interface WorkspaceToolbarProps {
  projectName: string;
  templates: TemplateResponse[];
  activeTemplateId: number | null;
  onSelectTemplate: (template: TemplateResponse) => void;
  onCreateTemplate: () => void;
  onSave: () => void;
  saveStatus: SaveStatus;
  isLoadingTemplates?: boolean;
  onRunQA?: () => void;
  isRunningQA?: boolean;
  qaResult?: {
    passed: boolean;
    checks_passed: number;
    checks_total: number;
  } | null;
  onToggleQAPanel?: () => void;
  onExport?: () => void;
  onSubmitForApproval?: () => void;
  brandViolations?: number;
  onGenerateImage?: () => void;
  collaborators?: Collaborator[];
  collaborationStatus?: CollaborationStatus;
  isViewOnly?: boolean;
  onTogglePresencePanel?: () => void;
  onViewBrief?: () => void;
  onRunBlueprint?: () => void;
  onPushToESP?: () => void;
  designRefOpen?: boolean;
  onDesignRefToggle?: (open: boolean) => void;
  onToggleVoiceBriefs?: () => void;
  commandPalette?: React.ReactNode;
}

export function WorkspaceToolbar({
  projectName,
  templates,
  activeTemplateId,
  onSelectTemplate,
  onCreateTemplate,
  onSave,
  saveStatus,
  isLoadingTemplates,
  onRunQA,
  isRunningQA,
  qaResult,
  onToggleQAPanel,
  onExport,
  onSubmitForApproval,
  brandViolations,
  onGenerateImage,
  collaborators,
  collaborationStatus,
  isViewOnly,
  onTogglePresencePanel,
  onViewBrief,
  onRunBlueprint,
  onPushToESP,
  designRefOpen,
  onDesignRefToggle,
  onToggleVoiceBriefs,
  commandPalette,
}: WorkspaceToolbarProps) {
  return (
    <header className="border-border bg-card flex h-12 shrink-0 items-center justify-between border-b px-4">
      {/* Left zone: Navigation */}
      <div className="flex items-center gap-3">
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                href="/"
                className="text-muted-foreground hover:text-foreground flex items-center transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              {"Back to Dashboard"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <h1 className="text-foreground max-w-32 truncate text-sm font-semibold">{projectName}</h1>
        <span className="text-muted-foreground">/</span>
        <TemplateSelector
          templates={templates}
          activeTemplateId={activeTemplateId}
          onSelect={onSelectTemplate}
          onCreate={onCreateTemplate}
          isLoading={isLoadingTemplates}
        />
      </div>

      {/* Center zone: Primary workflow actions */}
      <div className="flex items-center gap-2">
        <SaveIndicator status={saveStatus} />
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={onSave}
                disabled={saveStatus === "saving" || saveStatus === "idle"}
                className="text-muted-foreground hover:bg-accent hover:text-foreground flex items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                {"Save"}
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              {"Save"} (⌘S)
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {onRunBlueprint && (
          <>
            <div className="bg-border h-4 w-px" />
            <button
              type="button"
              onClick={onRunBlueprint}
              className="bg-interactive text-on-interactive flex items-center gap-1.5 rounded px-3 py-1 text-xs font-medium transition-colors hover:opacity-90"
            >
              <Zap className="h-3.5 w-3.5" />
              {"Generate"}
            </button>
          </>
        )}

        {onRunQA && (
          <>
            <div className="bg-border h-4 w-px" />
            <button
              type="button"
              onClick={onRunQA}
              disabled={isRunningQA || saveStatus === "saving"}
              className="text-muted-foreground hover:bg-accent hover:text-foreground flex items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors disabled:opacity-50"
            >
              <ShieldCheck className={`h-3.5 w-3.5 ${isRunningQA ? "animate-pulse" : ""}`} />
              {isRunningQA ? "Running..." : "Run QA"}
            </button>
          </>
        )}
        {qaResult && !isRunningQA && onToggleQAPanel && (
          <button
            type="button"
            onClick={onToggleQAPanel}
            className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
              qaResult.passed
                ? "bg-badge-success-bg text-badge-success-text hover:opacity-80"
                : "bg-badge-danger-bg text-badge-danger-text hover:opacity-80"
            }`}
            title={"View QA results"}
          >
            {qaResult.checks_passed}/{qaResult.checks_total}
          </button>
        )}
      </div>

      {/* Right zone: Grouped secondary */}
      <div className="flex items-center gap-2">
        <DeliverMenu
          onExport={onExport}
          onPushToESP={onPushToESP}
          onSubmitForApproval={onSubmitForApproval}
          disabled={saveStatus === "saving"}
        />

        <div className="bg-border h-4 w-px" />

        <ToolsMenu
          onGenerateImage={onGenerateImage}
          onDesignRefToggle={onDesignRefToggle}
          designRefOpen={designRefOpen}
          onToggleVoiceBriefs={onToggleVoiceBriefs}
          onViewBrief={onViewBrief}
        />

        <div className="bg-border h-4 w-px" />

        {/* Status cluster */}
        {brandViolations !== undefined && brandViolations > 0 && (
          <span
            className="bg-badge-warning-bg text-badge-warning-text flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
            title={`${brandViolations} brand violations`}
          >
            <Palette className="h-3 w-3" />
            {brandViolations}
          </span>
        )}
        {collaborationStatus && (
          <CollaborationBanner
            collaborators={collaborators ?? []}
            status={collaborationStatus}
            isViewOnly={isViewOnly}
            onTogglePresencePanel={onTogglePresencePanel ?? (() => {})}
          />
        )}
        <ThemeToggle />

        {commandPalette}
      </div>
    </header>
  );
}
