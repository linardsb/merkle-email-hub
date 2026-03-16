"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "lucide-react";
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

const CREDENTIAL_FIELDS: Record<ESPType, { key: string; labelKey: string; placeholderKey: string; type?: string }[]> = {
  braze: [
    { key: "api_key", labelKey: "credApiKey", placeholderKey: "credApiKeyPlaceholder", type: "password" },
  ],
  sfmc: [
    { key: "client_id", labelKey: "credClientId", placeholderKey: "credClientIdPlaceholder" },
    { key: "client_secret", labelKey: "credClientSecret", placeholderKey: "credClientSecretPlaceholder", type: "password" },
    { key: "subdomain", labelKey: "credSubdomain", placeholderKey: "credSubdomainPlaceholder" },
  ],
  adobe_campaign: [
    { key: "client_id", labelKey: "credClientId", placeholderKey: "credClientIdPlaceholder" },
    { key: "client_secret", labelKey: "credClientSecret", placeholderKey: "credClientSecretPlaceholder", type: "password" },
    { key: "org_id", labelKey: "credOrgId", placeholderKey: "credOrgIdPlaceholder" },
  ],
  taxi: [
    { key: "api_key", labelKey: "credApiKey", placeholderKey: "credApiKeyPlaceholder", type: "password" },
  ],
};

export function CreateESPConnectionDialog({ open, onOpenChange }: CreateESPConnectionDialogProps) {
  const t = useTranslations("espSync");
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
      toast.success(t("createSuccess"));
      onOpenChange(false);
    } catch {
      toast.error(t("createError"));
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
          <DialogTitle>{t("createTitle")}</DialogTitle>
          <DialogDescription>{t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Provider */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              {t("createProvider")}
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
              {t("createName")}
            </label>
            <input
              id="esp-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("createNamePlaceholder")}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Project */}
          <div>
            <label htmlFor="esp-project" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("createProject")}
            </label>
            <select
              id="esp-project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              disabled={isMutating}
              className={selectClass}
            >
              <option value="">{t("createProjectPlaceholder")}</option>
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
                {t(field.labelKey as "credApiKey")}
              </label>
              <input
                id={`esp-cred-${field.key}`}
                type={field.type ?? "text"}
                autoComplete="off"
                value={credentials[field.key] ?? ""}
                onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                placeholder={t(field.placeholderKey as "credApiKeyPlaceholder")}
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
            {t("createCancel")}
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
                {t("createSubmitting")}
              </span>
            ) : (
              t("createSubmit")
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
