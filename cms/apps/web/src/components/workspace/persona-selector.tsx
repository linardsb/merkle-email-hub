"use client";

import { useState } from "react";
import { UserCheck, Monitor, Smartphone, Moon, Plus } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";
import type { PersonaResponse } from "@email-hub/sdk";
import { CreatePersonaDialog } from "./create-persona-dialog";

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
  const [createOpen, setCreateOpen] = useState(false);

  const selectedPersona = personas.find((p) => p.id === selectedPersonaId);
  const label = selectedPersona?.name ?? "Test as";

  if (isLoading) {
    return (
      <div className="flex h-7 items-center px-2 text-xs text-muted-foreground">
        {"Loading personas..."}
      </div>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          className="flex h-7 items-center gap-1.5 rounded px-2 text-xs transition-colors hover:bg-accent"
        >
          <UserCheck className="h-3.5 w-3.5" />
          <span className="max-w-[8rem] truncate">{label}</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[14rem] bg-popover border border-border shadow-lg">
          <DropdownMenuItem onSelect={() => onSelect(null)}>
            <span className="text-muted-foreground">{"No persona"}</span>
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
                    {`\${persona.viewport_width ?? 600}px`}
                  </span>
                </span>
              </DropdownMenuItem>
            );
          })}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">
              {"Create custom…"}
            </span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CreatePersonaDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(persona) => onSelect(persona)}
      />
    </>
  );
}
