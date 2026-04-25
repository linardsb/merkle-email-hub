"use client";

import { ChevronDown, Plus, FileCode } from "../icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";
import type { TemplateResponse } from "@/types/templates";

interface TemplateSelectorProps {
  templates: TemplateResponse[];
  activeTemplateId: number | null;
  onSelect: (template: TemplateResponse) => void;
  onCreate: () => void;
  isLoading?: boolean;
}

export function TemplateSelector({
  templates,
  activeTemplateId,
  onSelect,
  onCreate,
  isLoading,
}: TemplateSelectorProps) {
  const activeTemplate = templates.find((tpl) => tpl.id === activeTemplateId);
  const label = activeTemplate?.name ?? "Select template";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="text-foreground hover:bg-accent flex h-7 items-center gap-1.5 rounded px-2 text-sm font-medium transition-colors disabled:opacity-50"
        disabled={isLoading}
      >
        <FileCode className="h-3.5 w-3.5" />
        <span className="max-w-[12rem] truncate">{label}</span>
        <ChevronDown className="h-3 w-3 opacity-50" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[16rem]">
        {templates.length === 0 && (
          <div className="text-muted-foreground px-2 py-3 text-center text-xs">
            {"No templates yet"}
          </div>
        )}
        {templates.map((tpl) => (
          <DropdownMenuItem
            key={tpl.id}
            onSelect={() => onSelect(tpl)}
            className={tpl.id === activeTemplateId ? "bg-accent" : ""}
          >
            <span className="truncate">{tpl.name}</span>
            {tpl.latest_version != null && (
              <span className="text-muted-foreground ml-auto text-xs">v{tpl.latest_version}</span>
            )}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onCreate}>
          <Plus className="mr-2 h-3.5 w-3.5" />
          {"New Template"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
