"use client";

import { useEffect, useState } from "react";
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
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from "@email-hub/ui/components/ui/command";
import {
  Dialog,
  DialogContent,
} from "@email-hub/ui/components/ui/dialog";
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

const AGENT_ITEMS: { id: AgentMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "scaffolder", label: "Scaffolder", icon: Wand2 },
  { id: "dark_mode", label: "Dark Mode", icon: Moon },
  { id: "content", label: "Content", icon: PenTool },
  { id: "outlook_fixer", label: "Outlook Fixer", icon: Wrench },
  { id: "accessibility", label: "Accessibility", icon: Eye },
  { id: "personalisation", label: "Personalize", icon: Users },
  { id: "code_reviewer", label: "Reviewer", icon: FileSearch },
  { id: "knowledge", label: "Knowledge", icon: BookOpen },
  { id: "innovation", label: "Innovator", icon: Lightbulb },
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
        <span className="font-medium">{"⌘K"}</span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-[52rem] overflow-hidden p-0">
          <Command className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-3 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-3 [&_[cmdk-item]]:py-2.5 [&_[cmdk-item]_svg]:h-4 [&_[cmdk-item]_svg]:w-4">
            <CommandInput placeholder={"Type a command or search..."} />
            <CommandList className="max-h-[min(70vh,36rem)] p-2">
              <CommandEmpty>{"No results found."}</CommandEmpty>

              {/* Actions & Panels side by side */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-border p-2">
                  <CommandGroup heading={"Actions"}>
                    {onSave && (
                      <CommandItem onSelect={() => run(onSave)}>
                        <Save className="h-4 w-4" />
                        {"Save"}
                        <CommandShortcut>⌘S</CommandShortcut>
                      </CommandItem>
                    )}
                    {onRunBlueprint && (
                      <CommandItem onSelect={() => run(onRunBlueprint)}>
                        <Zap className="h-4 w-4" />
                        {"Generate"}
                        <CommandShortcut>⌘⇧G</CommandShortcut>
                      </CommandItem>
                    )}
                    {onRunQA && (
                      <CommandItem onSelect={() => run(onRunQA)}>
                        <ShieldCheck className="h-4 w-4" />
                        {"Run QA"}
                        <CommandShortcut>⌘⇧Q</CommandShortcut>
                      </CommandItem>
                    )}
                    {onExport && (
                      <CommandItem onSelect={() => run(onExport)}>
                        <Download className="h-4 w-4" />
                        {"Export"}
                        <CommandShortcut>⌘⇧E</CommandShortcut>
                      </CommandItem>
                    )}
                    {onPushToESP && (
                      <CommandItem onSelect={() => run(onPushToESP)}>
                        <CloudUpload className="h-4 w-4" />
                        {"Push to ESP"}
                      </CommandItem>
                    )}
                    {onSubmitForApproval && (
                      <CommandItem onSelect={() => run(onSubmitForApproval)}>
                        <ClipboardCheck className="h-4 w-4" />
                        {"Submit for Approval"}
                      </CommandItem>
                    )}
                    {onGenerateImage && (
                      <CommandItem onSelect={() => run(onGenerateImage)}>
                        <ImagePlus className="h-4 w-4" />
                        {"Generate Image"}
                      </CommandItem>
                    )}
                  </CommandGroup>
                </div>

                <div className="space-y-3">
                  <div className="rounded-lg border border-border p-2">
                    <CommandGroup heading={"Panels"}>
                      {onToggleQAPanel && (
                        <CommandItem onSelect={() => run(onToggleQAPanel)}>
                          <PanelRight className="h-4 w-4" />
                          {"Toggle QA Sidebar"}
                          <CommandShortcut>⌘J</CommandShortcut>
                        </CommandItem>
                      )}
                      {onDesignRefToggle && (
                        <CommandItem onSelect={() => { setOpen(false); onDesignRefToggle(!designRefOpen); }}>
                          <Palette className="h-4 w-4" />
                          {"Design Ref"}
                        </CommandItem>
                      )}
                      {onToggleChat && (
                        <CommandItem onSelect={() => run(onToggleChat)}>
                          <PanelBottom className="h-4 w-4" />
                          {"Toggle Chat Panel"}
                          <CommandShortcut>⌘B</CommandShortcut>
                        </CommandItem>
                      )}
                    </CommandGroup>
                  </div>

                  <div className="rounded-lg border border-border p-2">
                    <CommandGroup heading={"Navigation"}>
                      {onNavigateBack && (
                        <CommandItem onSelect={() => run(onNavigateBack)}>
                          <ArrowLeft className="h-4 w-4" />
                          {"Back to Dashboard"}
                        </CommandItem>
                      )}
                    </CommandGroup>
                  </div>
                </div>
              </div>

              {/* Agents in its own bordered section, 2-col grid */}
              <div className="mt-3 rounded-lg border border-border p-2">
                <CommandGroup heading={"Agents"}>
                  <div className="grid grid-cols-2 gap-1">
                    {AGENT_ITEMS.map((a) => {
                      const Icon = a.icon;
                      return (
                        <CommandItem
                          key={a.id}
                          onSelect={() => { setOpen(false); onSelectAgent?.(a.id); }}
                        >
                          <Icon className="h-4 w-4" />
                          {a.label}
                        </CommandItem>
                      );
                    })}
                  </div>
                </CommandGroup>
              </div>
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>
    </>
  );
}
