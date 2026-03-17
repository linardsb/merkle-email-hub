"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Save,
  Zap,
  ShieldCheck,
  Download,
  CloudUpload,
  ClipboardCheck,
  ImagePlus,
  Palette,
  MessageSquare,
  Wand2,
  Moon,
  PenTool,
  Wrench,
  Eye,
  Users,
  FileSearch,
  BookOpen,
  Lightbulb,
  ArrowLeft,
  PanelBottom,
  PanelRight,
} from "lucide-react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from "@email-hub/ui/components/ui/command";
import type { AgentMode } from "@/types/chat";

interface CommandPaletteProps {
  onSave?: () => void;
  onRunBlueprint?: () => void;
  onRunQA?: () => void;
  onExport?: () => void;
  onPushToESP?: () => void;
  onSubmitForApproval?: () => void;
  onGenerateImage?: () => void;
  onToggleQAPanel?: () => void;
  onDesignRefToggle?: (open: boolean) => void;
  designRefOpen?: boolean;
  onToggleChat?: () => void;
  onNavigateBack?: () => void;
  onSelectAgent?: (agent: AgentMode) => void;
}

const AGENT_ITEMS: { id: AgentMode; labelKey: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "chat", labelKey: "chatAgentChat", icon: MessageSquare },
  { id: "scaffolder", labelKey: "chatAgentScaffolder", icon: Wand2 },
  { id: "dark_mode", labelKey: "chatAgentDarkMode", icon: Moon },
  { id: "content", labelKey: "chatAgentContent", icon: PenTool },
  { id: "outlook_fixer", labelKey: "chatAgentOutlookFixer", icon: Wrench },
  { id: "accessibility", labelKey: "chatAgentAccessibility", icon: Eye },
  { id: "personalisation", labelKey: "chatAgentPersonalisation", icon: Users },
  { id: "code_reviewer", labelKey: "chatAgentCodeReviewer", icon: FileSearch },
  { id: "knowledge", labelKey: "chatAgentKnowledge", icon: BookOpen },
  { id: "innovation", labelKey: "chatAgentInnovation", icon: Lightbulb },
];

export function CommandPalette({
  onSave,
  onRunBlueprint,
  onRunQA,
  onExport,
  onPushToESP,
  onSubmitForApproval,
  onGenerateImage,
  onToggleQAPanel,
  onDesignRefToggle,
  designRefOpen,
  onToggleChat,
  onNavigateBack,
  onSelectAgent,
}: CommandPaletteProps) {
  const t = useTranslations("workspace");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const run = (fn?: () => void) => {
    setOpen(false);
    fn?.();
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <span className="font-medium">{t("commandPalette.hint")}</span>
      </button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder={t("commandPalette.placeholder")} />
        <CommandList>
          <CommandEmpty>{t("commandPalette.empty")}</CommandEmpty>

          <CommandGroup heading={t("commandPalette.groupActions")}>
            {onSave && (
              <CommandItem onSelect={() => run(onSave)}>
                <Save className="h-4 w-4" />
                {t("saveTemplate")}
                <CommandShortcut>⌘S</CommandShortcut>
              </CommandItem>
            )}
            {onRunBlueprint && (
              <CommandItem onSelect={() => run(onRunBlueprint)}>
                <Zap className="h-4 w-4" />
                {t("generateBlueprint")}
                <CommandShortcut>⌘⇧G</CommandShortcut>
              </CommandItem>
            )}
            {onRunQA && (
              <CommandItem onSelect={() => run(onRunQA)}>
                <ShieldCheck className="h-4 w-4" />
                {t("runQA")}
                <CommandShortcut>⌘⇧Q</CommandShortcut>
              </CommandItem>
            )}
            {onExport && (
              <CommandItem onSelect={() => run(onExport)}>
                <Download className="h-4 w-4" />
                {t("export")}
                <CommandShortcut>⌘⇧E</CommandShortcut>
              </CommandItem>
            )}
            {onPushToESP && (
              <CommandItem onSelect={() => run(onPushToESP)}>
                <CloudUpload className="h-4 w-4" />
                {t("pushToESP")}
              </CommandItem>
            )}
            {onSubmitForApproval && (
              <CommandItem onSelect={() => run(onSubmitForApproval)}>
                <ClipboardCheck className="h-4 w-4" />
                {t("submitForApproval")}
              </CommandItem>
            )}
            {onGenerateImage && (
              <CommandItem onSelect={() => run(onGenerateImage)}>
                <ImagePlus className="h-4 w-4" />
                {t("generateImage")}
              </CommandItem>
            )}
          </CommandGroup>

          <CommandGroup heading={t("commandPalette.groupPanels")}>
            {onToggleQAPanel && (
              <CommandItem onSelect={() => run(onToggleQAPanel)}>
                <PanelRight className="h-4 w-4" />
                {t("commandPalette.toggleQASidebar")}
                <CommandShortcut>⌘J</CommandShortcut>
              </CommandItem>
            )}
            {onDesignRefToggle && (
              <CommandItem onSelect={() => { setOpen(false); onDesignRefToggle(!designRefOpen); }}>
                <Palette className="h-4 w-4" />
                {t("designRefButton")}
              </CommandItem>
            )}
            {onToggleChat && (
              <CommandItem onSelect={() => run(onToggleChat)}>
                <PanelBottom className="h-4 w-4" />
                {t("commandPalette.toggleChat")}
                <CommandShortcut>⌘B</CommandShortcut>
              </CommandItem>
            )}
          </CommandGroup>

          <CommandGroup heading={t("commandPalette.groupAgents")}>
            {AGENT_ITEMS.map((a) => {
              const Icon = a.icon;
              return (
                <CommandItem
                  key={a.id}
                  onSelect={() => { setOpen(false); onSelectAgent?.(a.id); }}
                >
                  <Icon className="h-4 w-4" />
                  {t(a.labelKey)}
                </CommandItem>
              );
            })}
          </CommandGroup>

          <CommandGroup heading={t("commandPalette.groupNavigation")}>
            {onNavigateBack && (
              <CommandItem onSelect={() => run(onNavigateBack)}>
                <ArrowLeft className="h-4 w-4" />
                {t("backToDashboard")}
              </CommandItem>
            )}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
