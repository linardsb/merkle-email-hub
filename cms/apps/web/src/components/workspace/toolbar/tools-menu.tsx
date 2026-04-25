"use client";

import { ImagePlus, Palette, Mic, FileText, ChevronDown, Wrench } from "../../icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";

interface ToolsMenuProps {
  onGenerateImage?: () => void;
  onDesignRefToggle?: (open: boolean) => void;
  designRefOpen?: boolean;
  onToggleVoiceBriefs?: () => void;
  onViewBrief?: () => void;
}

export function ToolsMenu({
  onGenerateImage,
  onDesignRefToggle,
  designRefOpen,
  onToggleVoiceBriefs,
  onViewBrief,
}: ToolsMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:bg-accent hover:text-foreground flex items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors"
        >
          <Wrench className="h-3.5 w-3.5" />
          {"Tools"}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {onGenerateImage && (
          <DropdownMenuItem onClick={onGenerateImage}>
            <ImagePlus className="h-3.5 w-3.5" />
            {"Generate Image"}
          </DropdownMenuItem>
        )}
        {onDesignRefToggle && (
          <DropdownMenuItem onClick={() => onDesignRefToggle(!designRefOpen)}>
            <Palette className="h-3.5 w-3.5" />
            {"Design Ref"}
          </DropdownMenuItem>
        )}
        {onToggleVoiceBriefs && (
          <DropdownMenuItem onClick={onToggleVoiceBriefs}>
            <Mic className="h-3.5 w-3.5" />
            {"Voice Briefs"}
          </DropdownMenuItem>
        )}
        {onViewBrief && (
          <DropdownMenuItem onClick={onViewBrief}>
            <FileText className="h-3.5 w-3.5" />
            {"View Compatibility Brief"}
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
