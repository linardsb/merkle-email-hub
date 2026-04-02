"use client";

import { useState } from "react";
import Link from "next/link";
import { LayoutDashboard, FolderOpen, FileCode, CheckCircle2, ClipboardCheck, Target, Brain, Plus } from "../../components/icons";
import { useProjects } from "@/hooks/use-projects";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonCard } from "@/components/ui/skeletons";
import { useOrgs } from "@/hooks/use-orgs";
import { useComponents } from "@/hooks/use-components";
import { useQADashboard } from "@/hooks/use-qa-dashboard";
import { useQAResults } from "@/hooks/use-qa";
import { useApprovals } from "@/hooks/use-approvals";
import { CreateProjectDialog } from "@/components/dashboard/create-project-dialog";

export default function DashboardPage() {
  const [createOpen, setCreateOpen] = useState(false);

  // Data sources
  const { data: projects, isLoading: projectsLoading, error: projectsError, mutate: mutateProjects } = useProjects();
  const { data: orgs, isLoading: orgsLoading } = useOrgs();
  const { data: components } = useComponents({ pageSize: 1 });
  const { metrics: qaMetrics } = useQADashboard();
  const { data: recentQA } = useQAResults({ page: 1, pageSize: 5 });

  // Approvals for first project
  const firstProjectId = projects?.items?.[0]?.id ?? null;
  const { data: approvals } = useApprovals(firstProjectId);
  const pendingCount = approvals?.filter((a) => a.status === "pending").length ?? 0;

  const isLoading = projectsLoading || orgsLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {"Dashboard"}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {firstProjectId && (
            <Link
              href={`/projects/${firstProjectId}/workspace`}
              className="rounded-md border border-card-border bg-card-bg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
            >
              {"Open Workspace"}
            </Link>
          )}
          <Link
            href={`/components`}
            className="rounded-md border border-card-border bg-card-bg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            {"Browse Components"}
          </Link>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            <Plus className="h-4 w-4" />
            {"New Project"}
          </button>
        </div>
      </div>

      {/* Stats row — 4 cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {"Total Projects"}
            </p>
          </div>
          <p className="mt-2 text-3xl font-semibold text-foreground">
            {isLoading ? "\u2014" : (projects?.total ?? 0)}
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <FileCode className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {"Components"}
            </p>
          </div>
          <p className="mt-2 text-3xl font-semibold text-foreground">
            {components?.total ?? "\u2014"}
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {"QA Pass Rate"}
            </p>
          </div>
          <p
            className={`mt-2 text-3xl font-semibold ${
              qaMetrics.totalRuns === 0
                ? "text-foreground"
                : qaMetrics.passRate >= 0.8
                  ? "text-status-success"
                  : "text-status-danger"
            }`}
          >
            {qaMetrics.totalRuns === 0
              ? "\u2014"
              : `${Math.round(qaMetrics.passRate * 100)}%`}
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {"Pending Approvals"}
            </p>
          </div>
          <p
            className={`mt-2 text-3xl font-semibold ${
              pendingCount > 0 ? "text-status-warning" : "text-foreground"
            }`}
          >
            {pendingCount}
          </p>
        </div>
      </div>

      {/* Quality Overview + Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Quality Overview — 2/3 width */}
        <div className="rounded-lg border border-card-border bg-card-bg p-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5 text-foreground-muted" />
              <h2 className="text-lg font-semibold text-foreground">
                {"Quality Overview"}
              </h2>
            </div>
            <Link
              href={`/intelligence`}
              className="text-sm text-interactive hover:underline"
            >
              {"View Intelligence"}
            </Link>
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {"QA gate performance across all templates"}
          </p>

          {qaMetrics.totalRuns === 0 ? (
            <p className="mt-4 text-sm text-foreground-muted">
              {"No recent activity"}
            </p>
          ) : (
            <div className="mt-4 space-y-4">
              {/* Inline stats */}
              <div className="flex gap-6">
                <div>
                  <p className="text-xs font-medium text-foreground-muted">
                    {"Avg Score"}
                  </p>
                  <p className="text-xl font-semibold text-foreground">
                    {Math.round(qaMetrics.avgScore * 100)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-foreground-muted">
                    {"Total Runs"}
                  </p>
                  <p className="text-xl font-semibold text-foreground">
                    {qaMetrics.totalRuns}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-foreground-muted">
                    {"Overrides"}
                  </p>
                  <p className="text-xl font-semibold text-foreground">
                    {qaMetrics.overrideCount}
                  </p>
                </div>
              </div>

              {/* Mini trend dots */}
              <div className="flex items-center gap-1.5">
                {qaMetrics.scoreTrend.slice(-10).map((point, i) => (
                  <div
                    key={i}
                    className={`h-2.5 w-2.5 rounded-full ${
                      point.passed ? "bg-status-success" : "bg-status-danger"
                    }`}
                    title={`${Math.round(point.score * 100)}%`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity — 1/3 width */}
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">
              {"Recent Activity"}
            </h2>
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {"Latest QA runs across your projects"}
          </p>

          <div className="mt-4">
            {!recentQA || recentQA.items.length === 0 ? (
              <p className="py-4 text-center text-sm text-foreground-muted">
                {"Activity will appear here as you run QA checks on your templates."}
              </p>
            ) : (
              <div className="divide-y divide-border">
                {recentQA.items.map((result) => (
                  <div
                    key={result.id}
                    className="flex items-center justify-between py-2.5"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          result.passed
                            ? "bg-status-success"
                            : "bg-status-danger"
                        }`}
                      />
                      <span className="text-sm text-foreground">
                        {"QA Run"}
                      </span>
                      <span className="text-xs text-foreground-muted">
                        {`Score: ${Math.round(result.overall_score * 100)}%`}
                      </span>
                    </div>
                    <span className="text-xs text-foreground-muted">
                      {new Date(result.created_at).toLocaleDateString(
                        undefined,
                        {
                          month: "short",
                          day: "numeric",
                        }
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Projects section */}
      {projectsError ? (
        <ErrorState message={"Failed to load dashboard data"} onRetry={() => mutateProjects()} retryLabel={"Try again"} />
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : projects?.items && projects.items.length > 0 ? (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">
              {"Projects"}
            </h2>
            {(projects.total ?? 0) > 3 && (
              <Link
                href={`/projects`}
                className="text-sm text-interactive hover:underline"
              >
                {"View All"}
              </Link>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.items.slice(0, 3).map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}/workspace`}
                className="block rounded-lg border border-card-border bg-card-bg p-6 transition-colors hover:bg-surface-hover"
              >
                <h3 className="font-medium text-foreground">{project.name}</h3>
                <p className="mt-1 line-clamp-2 text-sm text-foreground-muted">
                  {project.description || "\u2014"}
                </p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="rounded-full bg-badge-default-bg px-2 py-0.5 text-xs font-medium text-badge-default-text">
                    {project.status}
                  </span>
                  <span className="text-xs text-foreground-muted">
                    {new Date(project.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
          <FolderOpen className="mx-auto h-12 w-12 text-foreground-muted" />
          <h3 className="mt-4 text-lg font-semibold text-foreground">
            {"No projects yet"}
          </h3>
          <p className="mt-2 text-sm text-foreground-muted">
            {"Create your first project to get started with email development."}
          </p>
        </div>
      )}

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
