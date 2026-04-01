"use client";

import { MessageSquare, Wand2, Moon, PenTool, Wrench, Eye, Users, FileSearch, BookOpen, Lightbulb, ChevronDown } from "../../icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";
import { Button } from "@email-hub/ui/components/ui/button";
import type { AgentMode } from "@/types/chat";

interface AgentDef {
  id: AgentMode;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AGENT_GROUPS: { label: string; agents: AgentDef[] }[] = [
  {
    label: "Build",
    agents: [
      { id: "chat", label: "Chat", icon: MessageSquare },
      { id: "scaffolder", label: "Scaffolder", icon: Wand2 },
    ],
  },
  {
    label: "Optimize",
    agents: [
      { id: "dark_mode", label: "Dark Mode", icon: Moon },
      { id: "content", label: "Content", icon: PenTool },
      { id: "outlook_fixer", label: "Outlook Fixer", icon: Wrench },
      { id: "accessibility", label: "Accessibility", icon: Eye },
      { id: "personalisation", label: "Personalize", icon: Users },
    ],
  },
  {
    label: "Review",
    agents: [
      { id: "code_reviewer", label: "Reviewer", icon: FileSearch },
      { id: "knowledge", label: "Knowledge", icon: BookOpen },
      { id: "innovation", label: "Innovator", icon: Lightbulb },
    ],
  },
];

const ALL_AGENTS: AgentDef[] = AGENT_GROUPS.flatMap((g) => g.agents);
const DEFAULT_AGENT = ALL_AGENTS[0] as AgentDef;

interface AgentSelectorDropdownProps {
  agent: AgentMode;
  onSelect: (agent: AgentMode) => void;
}

export function AgentSelectorDropdown({ agent, onSelect }: AgentSelectorDropdownProps) {
  const current = ALL_AGENTS.find((a) => a.id === agent) ?? DEFAULT_AGENT;
  const Icon = current.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs">
          <Icon className="h-3.5 w-3.5" />
          {current.label}
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        {AGENT_GROUPS.map((group) => (
          <DropdownMenuGroup key={group.label}>
            <DropdownMenuLabel className="text-[10px] uppercase tracking-wider">
              {group.label}
            </DropdownMenuLabel>
            {group.agents.map((a) => {
              const AgentIcon = a.icon;
              return (
                <DropdownMenuItem
                  key={a.id}
                  onClick={() => onSelect(a.id)}
                  className={agent === a.id ? "bg-accent" : ""}
                >
                  <AgentIcon className="h-3.5 w-3.5" />
                  {a.label}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
