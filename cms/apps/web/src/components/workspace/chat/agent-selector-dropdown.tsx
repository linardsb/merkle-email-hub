"use client";

import { useTranslations } from "next-intl";
import {
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
  ChevronDown,
} from "lucide-react";
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
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AGENT_GROUPS: { labelKey: string; agents: AgentDef[] }[] = [
  {
    labelKey: "agentGroupBuild",
    agents: [
      { id: "chat", labelKey: "chatAgentChat", icon: MessageSquare },
      { id: "scaffolder", labelKey: "chatAgentScaffolder", icon: Wand2 },
    ],
  },
  {
    labelKey: "agentGroupOptimize",
    agents: [
      { id: "dark_mode", labelKey: "chatAgentDarkMode", icon: Moon },
      { id: "content", labelKey: "chatAgentContent", icon: PenTool },
      { id: "outlook_fixer", labelKey: "chatAgentOutlookFixer", icon: Wrench },
      { id: "accessibility", labelKey: "chatAgentAccessibility", icon: Eye },
      { id: "personalisation", labelKey: "chatAgentPersonalisation", icon: Users },
    ],
  },
  {
    labelKey: "agentGroupReview",
    agents: [
      { id: "code_reviewer", labelKey: "chatAgentCodeReviewer", icon: FileSearch },
      { id: "knowledge", labelKey: "chatAgentKnowledge", icon: BookOpen },
      { id: "innovation", labelKey: "chatAgentInnovation", icon: Lightbulb },
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
  const t = useTranslations("workspace");
  const current = ALL_AGENTS.find((a) => a.id === agent) ?? DEFAULT_AGENT;
  const Icon = current.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs">
          <Icon className="h-3.5 w-3.5" />
          {t(current.labelKey)}
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        {AGENT_GROUPS.map((group) => (
          <DropdownMenuGroup key={group.labelKey}>
            <DropdownMenuLabel className="text-[10px] uppercase tracking-wider">
              {t(group.labelKey)}
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
                  {t(a.labelKey)}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
