"use client";

import { useMemo, useState } from "react";
import {
  Users,
  AlertTriangle,
  BookOpen,
  Puzzle,
  ChevronDown,
  ChevronUp,
  Shield,
  Moon,
} from "lucide-react";
import { useCompatibilityBrief } from "@/hooks/use-compatibility-brief";
import {
  useFailurePatternStats,
  useFailurePatterns,
} from "@/hooks/use-failure-patterns";
import { useAgentSkills } from "@/hooks/use-agent-skills";
import { detectComponentRefs } from "@/lib/detect-components";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { Badge } from "@email-hub/ui/components/ui/badge";

interface AgentContextPanelProps {
  projectId: number;
  editorContent: string;
}

// ── Collapsible Section ──
function Section({
  icon: Icon,
  title,
  badge,
  defaultOpen = true,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent/50"
      >
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="flex-1 text-left">{title}</span>
        {badge && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {badge}
          </Badge>
        )}
        {open ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  );
}

// ── Audience Section ──
function AudienceSection({ projectId }: { projectId: number }) {
  const { data: brief, isLoading } = useCompatibilityBrief(projectId);

  if (isLoading) {
    return <p className="text-xs text-muted-foreground">{"Loading..."}</p>;
  }

  if (!brief || !brief.clients || brief.clients.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">{"No priority clients set. All 25 email clients are weighted equally."}</p>
    );
  }

  return (
    <div className="space-y-2">
      {/* Client badges */}
      <div className="flex flex-wrap gap-1.5">
        {brief.clients.map((client) => (
          <span
            key={client.id}
            className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground"
          >
            {client.name}
          </span>
        ))}
      </div>
      {/* Summary pills */}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {brief.dark_mode_warning && (
          <span className="flex items-center gap-1">
            <Moon className="h-3 w-3" /> {"Dark mode required"}
          </span>
        )}
        {brief.total_risky_properties > 0 && (
          <span className="flex items-center gap-1">
            <Shield className="h-3 w-3" />
            {`${brief.total_risky_properties} risky CSS properties`}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Failure Patterns Section ──
function FailurePatternsSection({ projectId }: { projectId: number }) {
  const { data: stats, isLoading } = useFailurePatternStats(projectId);
  const { data: patterns } = useFailurePatterns({
    projectId,
    pageSize: 5,
  });

  if (isLoading) {
    return <p className="text-xs text-muted-foreground">{"Loading..."}</p>;
  }

  if (!stats || stats.total_patterns === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        {"No failure patterns recorded for this project."}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {/* Top patterns list */}
      {patterns?.items.slice(0, 5).map((p) => (
        <div key={p.id} className="flex items-start gap-2 text-xs">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-destructive" />
          <div>
            <span className="font-medium text-foreground">{p.agent_name}</span>
            <span className="text-muted-foreground"> → {p.qa_check}</span>
            {p.frequency != null && p.frequency > 1 && (
              <span className="text-muted-foreground"> (×{p.frequency})</span>
            )}
            {p.client_ids.length > 0 && (
              <span className="text-muted-foreground">
                {" "}
                — {p.client_ids.join(", ")}
              </span>
            )}
          </div>
        </div>
      ))}
      {/* Summary */}
      <div className="flex gap-3 text-[10px] text-muted-foreground">
        {stats.top_agent && (
          <span>{`Top agent: ${stats.top_agent}`}</span>
        )}
        {stats.top_check && (
          <span>{`Top check: ${stats.top_check}`}</span>
        )}
      </div>
    </div>
  );
}

// ── Agent Skills Section ──
function AgentSkillsSection() {
  const { data, isLoading } = useAgentSkills();

  if (isLoading) {
    return <p className="text-xs text-muted-foreground">{"Loading..."}</p>;
  }

  if (!data || data.agents.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">{"No agent skill data available."}</p>
    );
  }

  return (
    <div className="space-y-1">
      {data.agents.map((agent) => (
        <div key={agent.name} className="flex items-center gap-2 text-xs">
          <span className="w-28 truncate font-medium text-foreground">
            {agent.name}
          </span>
          {agent.skill_file ? (
            <span className="text-muted-foreground">
              SKILL.md
              {agent.l3_files.length > 0 &&
                ` + ${agent.l3_files.length} L3`}
            </span>
          ) : (
            <span className="text-muted-foreground italic">
              {"no SKILL.md"}
            </span>
          )}
          {agent.has_failure_warnings && (
            <AlertTriangle
              className="h-3 w-3 text-destructive"
              aria-label={"Failure warnings active — criteria below 85% pass rate"}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Component Context Section ──
function ComponentContextSection({
  editorContent,
}: {
  editorContent: string;
}) {
  const refs = useMemo(
    () => detectComponentRefs(editorContent),
    [editorContent]
  );

  if (refs.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        {"No component references detected in current template."}
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {refs.map((slug) => (
        <span
          key={slug}
          className="rounded bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground"
        >
          {slug}
        </span>
      ))}
    </div>
  );
}

// ── Main Panel ──
export function AgentContextPanel({
  projectId,
  editorContent,
}: AgentContextPanelProps) {
  const { data: stats } = useFailurePatternStats(projectId);

  return (
    <ScrollArea className="h-full">
      <div className="divide-y divide-border">
        <Section icon={Users} title={"Audience Profile"} defaultOpen={true}>
          <AudienceSection projectId={projectId} />
        </Section>

        <Section
          icon={AlertTriangle}
          title={"Failure Patterns"}
          badge={
            stats?.total_patterns ? String(stats.total_patterns) : undefined
          }
          defaultOpen={true}
        >
          <FailurePatternsSection projectId={projectId} />
        </Section>

        <Section
          icon={BookOpen}
          title={"Agent Skills"}
          defaultOpen={false}
        >
          <AgentSkillsSection />
        </Section>

        <Section
          icon={Puzzle}
          title={"Component Context"}
          defaultOpen={true}
        >
          <ComponentContextSection editorContent={editorContent} />
        </Section>
      </div>
    </ScrollArea>
  );
}
