"use client";

import { useTranslations } from "next-intl";
import { ImagePlus, Palette, Mic, FileText, ChevronDown, Wrench } from "lucide-react";
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
  const t = useTranslations("workspace");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Wrench className="h-3.5 w-3.5" />
          {t("toolsMenu")}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {onGenerateImage && (
          <DropdownMenuItem onClick={onGenerateImage}>
            <ImagePlus className="h-3.5 w-3.5" />
            {t("generateImage")}
          </DropdownMenuItem>
        )}
        {onDesignRefToggle && (
          <DropdownMenuItem onClick={() => onDesignRefToggle(!designRefOpen)}>
            <Palette className="h-3.5 w-3.5" />
            {t("designRefButton")}
          </DropdownMenuItem>
        )}
        {onToggleVoiceBriefs && (
          <DropdownMenuItem onClick={onToggleVoiceBriefs}>
            <Mic className="h-3.5 w-3.5" />
            {t("voiceBriefs")}
          </DropdownMenuItem>
        )}
        {onViewBrief && (
          <DropdownMenuItem onClick={onViewBrief}>
            <FileText className="h-3.5 w-3.5" />
            {t("viewCompatibilityBrief")}
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
