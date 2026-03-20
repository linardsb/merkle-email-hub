"use client";

import { useState } from "react";
import { MoreVertical, Pencil, Trash2 } from "lucide-react";
import { useSession } from "next-auth/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";
import { useComponentVersions } from "@/hooks/use-components";
import { ComponentPreview } from "./component-preview";
import { CompatibilityBadge } from "./compatibility-badge";
import { EditComponentDialog } from "./edit-component-dialog";
import { DeleteComponentDialog } from "./delete-component-dialog";
import type { ComponentResponse } from "@email-hub/sdk";

interface ComponentCardProps {
  component: ComponentResponse;
  onClick: () => void;
}

export function ComponentCard({ component, onClick }: ComponentCardProps) {
  const { data: versions } = useComponentVersions(component.id);
  const latestHtml = versions?.[0]?.html_source ?? null;
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canEdit = userRole === "admin" || userRole === "developer";
  const canDelete = userRole === "admin";
  const showMenu = canEdit || canDelete;

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        }}
        className="cursor-pointer overflow-hidden rounded-lg border border-card-border bg-card-bg transition-colors hover:border-interactive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-interactive"
      >
        <ComponentPreview html={latestHtml} height={200} />

        <div className="border-t border-card-border p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-medium text-foreground">
                {component.name}
              </h3>
              {component.description && (
                <p className="mt-0.5 truncate text-xs text-foreground-muted">
                  {component.description}
                </p>
              )}
            </div>
            {showMenu && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    onClick={(e) => e.stopPropagation()}
                    className="rounded-md p-1 text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground"
                    aria-label="Component actions"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {canEdit && (
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditOpen(true);
                      }}
                    >
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      {"Edit"}
                    </DropdownMenuItem>
                  )}
                  {canDelete && (
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteOpen(true);
                      }}
                      className="text-status-danger focus:text-status-danger"
                    >
                      <Trash2 className="mr-2 h-3.5 w-3.5" />
                      {"Delete"}
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          <div className="mt-3 flex items-center gap-2">
            {component.category && (
              <span className="rounded-full bg-badge-default-bg px-2 py-0.5 text-xs font-medium text-badge-default-text">
                {component.category}
              </span>
            )}
            <CompatibilityBadge badge={component.compatibility_badge} />
            <span className="text-xs text-foreground-muted">
              {component.latest_version
                ? `v${component.latest_version}`
                : "No versions"}
            </span>
          </div>
        </div>
      </div>

      <EditComponentDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        component={component}
      />
      <DeleteComponentDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        componentId={component.id}
        componentName={component.name}
      />
    </>
  );
}
