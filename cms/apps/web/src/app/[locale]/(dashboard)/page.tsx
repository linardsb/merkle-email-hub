"use client";

import { useTranslations } from "next-intl";
import {
  LayoutDashboard,
  FolderOpen,
  Building2,
  Plus,
  Activity,
} from "lucide-react";
import { useProjects } from "@/hooks/use-projects";
import { useOrgs } from "@/hooks/use-orgs";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const {
    data: projectsData,
    isLoading: projectsLoading,
    error: projectsError,
  } = useProjects();
  const { data: orgsData, isLoading: orgsLoading } = useOrgs();

  const isLoading = projectsLoading || orgsLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
        </div>
        <button
          type="button"
          className="flex items-center gap-2 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
        >
          <Plus className="h-4 w-4" />
          {t("createProject")}
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {t("totalProjects")}
            </p>
          </div>
          <p className="mt-2 text-3xl font-semibold text-foreground">
            {isLoading ? "\u2014" : (projectsData?.total ?? 0)}
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {t("activeOrgs")}
            </p>
          </div>
          <p className="mt-2 text-3xl font-semibold text-foreground">
            {isLoading ? "\u2014" : (orgsData?.total ?? 0)}
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {t("systemStatus")}
            </p>
          </div>
          <p className="mt-2 text-3xl font-semibold text-status-success">
            {t("healthy")}
          </p>
        </div>
      </div>

      {/* Project list / empty state */}
      {projectsError ? (
        <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
          <p className="text-sm text-status-danger">{t("error")}</p>
        </div>
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-lg border border-card-border bg-surface-muted"
            />
          ))}
        </div>
      ) : projectsData?.items.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
          <FolderOpen className="mx-auto h-12 w-12 text-foreground-muted" />
          <h3 className="mt-4 text-lg font-semibold text-foreground">
            {t("noProjects")}
          </h3>
          <p className="mt-2 text-sm text-foreground-muted">
            {t("noProjectsDescription")}
          </p>
        </div>
      ) : (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            {t("projects")}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projectsData?.items.map((project) => (
              <div
                key={project.id}
                className="cursor-pointer rounded-lg border border-card-border bg-card-bg p-6 transition-colors hover:bg-surface-hover"
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
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Getting started */}
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <h2 className="text-lg font-semibold text-foreground">
          {t("gettingStarted")}
        </h2>
        <p className="mt-2 text-sm text-foreground-muted">
          {t("gettingStartedDescription")}
        </p>
      </div>
    </div>
  );
}
