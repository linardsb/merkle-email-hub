"use client";

import { useTranslations } from "next-intl";
import { UserCheck, Monitor, Smartphone, Moon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@merkle-email-hub/ui/components/ui/dropdown-menu";
import type { PersonaResponse } from "@merkle-email-hub/sdk";

interface PersonaSelectorProps {
  personas: PersonaResponse[];
  selectedPersonaId: number | null;
  onSelect: (persona: PersonaResponse | null) => void;
  isLoading?: boolean;
}

export function PersonaSelector({
  personas,
  selectedPersonaId,
  onSelect,
  isLoading,
}: PersonaSelectorProps) {
  const t = useTranslations("workspace");

  const selectedPersona = personas.find((p) => p.id === selectedPersonaId);
  const label = selectedPersona?.name ?? t("personaLabel");

  if (isLoading) {
    return (
      <div className="flex h-7 items-center px-2 text-xs text-muted-foreground">
        {t("personaLoading")}
      </div>
    );
  }

  if (personas.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex h-7 items-center gap-1.5 rounded px-2 text-xs transition-colors hover:bg-accent"
      >
        <UserCheck className="h-3.5 w-3.5" />
        <span className="max-w-[8rem] truncate">{label}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[14rem] bg-popover border border-border shadow-lg">
        <DropdownMenuItem onSelect={() => onSelect(null)}>
          <span className="text-muted-foreground">{t("personaNone")}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {personas.map((persona) => {
          const isMobile = persona.device_type === "mobile";
          const DeviceIcon = isMobile ? Smartphone : Monitor;

          return (
            <DropdownMenuItem
              key={persona.id}
              onSelect={() => onSelect(persona)}
              className={persona.id === selectedPersonaId ? "bg-accent" : ""}
            >
              <span className="truncate">{persona.name}</span>
              <span className="ml-auto flex items-center gap-1.5 text-muted-foreground">
                {persona.dark_mode && <Moon className="h-3 w-3" />}
                <DeviceIcon className="h-3 w-3" />
                <span className="text-[0.65rem]">
                  {t("personaViewport", { width: persona.viewport_width ?? 600 })}
                </span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
