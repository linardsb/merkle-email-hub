"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreateESPConnection } from "@/hooks/use-esp-sync";
import { useProjects } from "@/hooks/use-projects";
import type { ESPType } from "@/types/esp-sync";

interface CreateESPConnectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ESP_PROVIDERS: { value: ESPType; label: string }[] = [
  { value: "braze", label: "Braze" },
  { value: "sfmc", label: "SFMC" },
  { value: "adobe_campaign", label: "Adobe Campaign" },
  { value: "taxi", label: "Taxi" },
];

const CREDENTIAL_FIELDS: Record<ESPType, { key: string; label: string; placeholder: string; type?: string }[]> = {
  braze: [
    { key: "api_key", label: "API Key", placeholder: "Enter API key", type: "password" },
  ],
  sfmc: [
    { key: "client_id", label: "Client ID", placeholder: "Enter client ID" },
    { key: "client_secret", label: "Client Secret", placeholder: "Enter client secret", type: "password" },
    { key: "subdomain", label: "Subdomain", placeholder: "e.g., mc563885gzdyr890y1re4gym8znk" },
  ],
  adobe_campaign: [
    { key: "client_id", label: "Client ID", placeholder: "Enter client ID" },
    { key: "client_secret", label: "Client Secret", placeholder: "Enter client secret", type: "password" },
    { key: "org_id", label: "Organization ID", placeholder: "Enter Adobe IMS org ID" },
  ],
  taxi: [
    { key: "api_key", label: "API Key", placeholder: "Enter API key", type: "password" },
  ],
};

export function CreateESPConnectionDialog({ open, onOpenChange }: CreateESPConnectionDialogProps) {
  const { trigger, isMutating } = useCreateESPConnection();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  const [name, setName] = useState("");
  const [espType, setEspType] = useState<ESPType>("braze");
  const [projectId, setProjectId] = useState<number | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});

  // Reset form when dialog opens (React 19 pattern)
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setEspType("braze");
    setProjectId(null);
    setCredentials({});
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const fields = CREDENTIAL_FIELDS[espType];
  const allCredentialsFilled = fields.every((f) => (credentials[f.key] ?? "").trim().length > 0);
  const isValid = name.trim().length >= 1 && projectId !== null && allCredentialsFilled;

  const handleCredentialChange = (key: string, value: string) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!isValid || projectId === null) return;
    try {
      await trigger({
        name: name.trim(),
        esp_type: espType,
        project_id: projectId,
        credentials,
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/connectors/sync"),
        undefined,
        { revalidate: true },
      );
      toast.success("ESP connection created");
      onOpenChange(false);
    } catch {
      toast.error("Failed to connect — check credentials");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <DialogTitle>{"Connect to ESP"}</DialogTitle>
          <DialogDescription>{"Add a connection to an email service provider. For local demo, use Braze with any API key."}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Provider */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              {"Provider"}
            </label>
            <div className="flex gap-2">
              {ESP_PROVIDERS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => {
                    setEspType(p.value);
                    setCredentials({});
                  }}
                  disabled={isMutating}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    espType === p.value
                      ? "bg-interactive text-foreground-inverse"
                      : "border border-input-border bg-input-bg text-foreground hover:bg-surface-hover"
                  } disabled:opacity-50`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Connection Name */}
          <div>
            <label htmlFor="esp-name" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Connection Name"}
            </label>
            <input
              id="esp-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={"e.g., Production Braze"}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Project */}
          <div>
            <label htmlFor="esp-project" className="mb-1.5 block text-sm font-medium text-foreground">
              {"Project"}
            </label>
            <select
              id="esp-project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">{"Select a project"}</option>
              {projects?.items?.map((proj) => (
                <option key={proj.id} value={proj.id}>
                  {proj.name}
                </option>
              ))}
            </select>
          </div>

          {/* Dynamic credential fields */}
          {fields.map((field) => (
            <div key={field.key}>
              <label htmlFor={`esp-cred-${field.key}`} className="mb-1.5 block text-sm font-medium text-foreground">
                {field.label}
              </label>
              <input
                id={`esp-cred-${field.key}`}
                type={field.type ?? "text"}
                autoComplete="off"
                value={credentials[field.key] ?? ""}
                onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                disabled={isMutating}
                className={inputClass}
              />
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || isMutating}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Validating…"}
              </span>
            ) : (
              "Connect"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
