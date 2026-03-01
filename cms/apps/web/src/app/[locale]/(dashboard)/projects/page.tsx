"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { FolderOpen, Plus } from "lucide-react";
import { useProjects } from "@/hooks/use-projects";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonCard } from "@/components/ui/skeletons";

export default function ProjectsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale();
  const { data: projects, isLoading, error, mutate } = useProjects();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderOpen className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {t("projects")}
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

      {error ? (
        <ErrorState message={t("error")} onRetry={() => mutate()} retryLabel={t("retry")} />
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : projects?.items && projects.items.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.items.map((project) => (
            <Link
              key={project.id}
              href={`/${locale}/projects/${project.id}/workspace`}
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
      ) : (
        <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
          <FolderOpen className="mx-auto h-12 w-12 text-foreground-muted" />
          <h3 className="mt-4 text-lg font-semibold text-foreground">
            {t("noProjects")}
          </h3>
          <p className="mt-2 text-sm text-foreground-muted">
            {t("noProjectsDescription")}
          </p>
        </div>
      )}
    </div>
  );
}
