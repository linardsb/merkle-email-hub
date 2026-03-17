"use client";

import { useTranslations } from "next-intl";
import { Download, CloudUpload, ClipboardCheck, ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";

interface DeliverMenuProps {
  onExport?: () => void;
  onPushToESP?: () => void;
  onSubmitForApproval?: () => void;
  disabled?: boolean;
}

export function DeliverMenu({ onExport, onPushToESP, onSubmitForApproval, disabled }: DeliverMenuProps) {
  const t = useTranslations("workspace");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={disabled}
          className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
        >
          <Download className="h-3.5 w-3.5" />
          {t("deliverMenu")}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {onExport && (
          <DropdownMenuItem onClick={onExport}>
            <Download className="h-3.5 w-3.5" />
            {t("export")}
          </DropdownMenuItem>
        )}
        {onPushToESP && (
          <DropdownMenuItem onClick={onPushToESP}>
            <CloudUpload className="h-3.5 w-3.5" />
            {t("pushToESP")}
          </DropdownMenuItem>
        )}
        {onSubmitForApproval && (
          <DropdownMenuItem onClick={onSubmitForApproval}>
            <ClipboardCheck className="h-3.5 w-3.5" />
            {t("submitForApproval")}
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
