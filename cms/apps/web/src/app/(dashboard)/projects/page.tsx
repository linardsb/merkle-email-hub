"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { FolderOpen, Plus, Trash2 } from "../../../components/icons";
import { toast } from "sonner";
import { authFetch } from "@/lib/auth-fetch";
import { useProjects } from "@/hooks/use-projects";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonCard } from "@/components/ui/skeletons";
import { CreateProjectDialog } from "@/components/dashboard/create-project-dialog";

export default function ProjectsPage() {
  const { data: projects, isLoading, error, mutate } = useProjects();
  const [createOpen, setCreateOpen] = useState(false);

  const handleDelete = useCallback(
    async (e: React.MouseEvent, projectId: number, projectName: string) => {
      e.preventDefault();
      e.stopPropagation();
      // eslint-disable-next-line no-alert -- replace with modal confirm; tracked in eslint-debt.md
      if (!confirm(`Delete "${projectName}"? This cannot be undone.`)) return;
      try {
        const res = await authFetch(`/api/v1/projects/${projectId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete");
        toast.success("Project deleted");
        await mutate();
      } catch {
        toast.error("Failed to delete project");
      }
    },
    [mutate],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderOpen className="text-foreground-accent h-8 w-8" />
          <h1 className="text-foreground text-2xl font-semibold">{"Projects"}</h1>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          {"New Project"}
        </button>
      </div>

      {error ? (
        <ErrorState
          message={"Failed to load dashboard data"}
          onRetry={() => mutate()}
          retryLabel={"Try again"}
        />
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
              href={`/projects/${project.id}/workspace`}
              className="border-card-border bg-card-bg hover:bg-surface-hover group relative block rounded-lg border p-6 transition-colors"
            >
              <button
                type="button"
                onClick={(e) => handleDelete(e, project.id, project.name)}
                className="text-foreground-muted hover:bg-destructive/10 hover:text-destructive absolute right-3 top-3 rounded p-1.5 opacity-0 transition-opacity group-hover:opacity-100"
                title="Delete project"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <h3 className="text-foreground font-medium">{project.name}</h3>
              <p className="text-foreground-muted mt-1 line-clamp-2 text-sm">
                {project.description || "\u2014"}
              </p>
              {project.target_clients && project.target_clients.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {project.target_clients.slice(0, 4).map((clientId) => (
                    <span
                      key={clientId}
                      className="bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[11px]"
                    >
                      {clientId.replace(/_/g, " ")}
                    </span>
                  ))}
                  {project.target_clients.length > 4 && (
                    <span className="bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[11px]">
                      +{project.target_clients.length - 4}
                    </span>
                  )}
                </div>
              )}
              <div className="mt-4 flex items-center justify-between">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    project.status === "active"
                      ? "bg-status-success/10 text-status-success"
                      : "bg-badge-default-bg text-badge-default-text"
                  }`}
                >
                  {project.status}
                </span>
                <span className="text-foreground-muted text-xs">
                  {new Date(project.updated_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="border-card-border bg-card-bg rounded-lg border p-8 text-center">
          <FolderOpen className="text-foreground-muted mx-auto h-12 w-12" />
          <h3 className="text-foreground mt-4 text-lg font-semibold">{"No projects yet"}</h3>
          <p className="text-foreground-muted mt-2 text-sm">
            {"Create your first project to get started with email development."}
          </p>
        </div>
      )}
      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
