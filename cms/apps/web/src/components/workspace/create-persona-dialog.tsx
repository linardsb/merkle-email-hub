"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@merkle-email-hub/ui/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useCreatePersona } from "@/hooks/use-personas";
import type { PersonaResponse } from "@merkle-email-hub/sdk";

const EMAIL_CLIENTS = [
  { value: "gmail", label: "Gmail" },
  { value: "outlook_365", label: "Outlook 365" },
  { value: "outlook_2019", label: "Outlook Classic" },
  { value: "apple_mail", label: "Apple Mail" },
  { value: "ios_mail", label: "iOS Mail" },
  { value: "samsung_mail", label: "Samsung Mail" },
  { value: "yahoo", label: "Yahoo Mail" },
  { value: "thunderbird", label: "Thunderbird" },
] as const;

const DEVICE_TYPES = [
  { value: "desktop", label: "Desktop" },
  { value: "mobile", label: "Mobile" },
] as const;

const OS_OPTIONS = [
  { value: "macOS", label: "macOS" },
  { value: "Windows", label: "Windows" },
  { value: "iOS", label: "iOS" },
  { value: "Android", label: "Android" },
  { value: "Linux", label: "Linux" },
] as const;

function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

interface CreatePersonaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (persona: PersonaResponse) => void;
}

export function CreatePersonaDialog({
  open,
  onOpenChange,
  onCreated,
}: CreatePersonaDialogProps) {
  const t = useTranslations("workspace");
  const { trigger, isMutating } = useCreatePersona();
  const { mutate } = useSWRConfig();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [emailClient, setEmailClient] = useState("gmail");
  const [deviceType, setDeviceType] = useState("desktop");
  const [viewportWidth, setViewportWidth] = useState(600);
  const [darkMode, setDarkMode] = useState(false);
  const [osName, setOsName] = useState("macOS");

  // Reset form when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setDescription("");
    setEmailClient("gmail");
    setDeviceType("desktop");
    setViewportWidth(600);
    setDarkMode(false);
    setOsName("macOS");
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const isValid = name.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      const persona = await trigger({
        name: name.trim(),
        slug: toSlug(name.trim()),
        description: description.trim() || undefined,
        email_client: emailClient,
        device_type: deviceType,
        viewport_width: viewportWidth,
        dark_mode: darkMode,
        os_name: osName,
      });
      await mutate("/api/v1/personas");
      toast.success(t("personaCreateSuccess"));
      onOpenChange(false);
      if (persona) onCreated?.(persona);
    } catch {
      toast.error(t("personaCreateError"));
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle>{t("personaCreateTitle")}</DialogTitle>
          <DialogDescription>
            {t("personaCreateDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label
              htmlFor="persona-name"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("personaFieldName")}
            </label>
            <input
              id="persona-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("personaFieldNamePlaceholder")}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="persona-description"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("personaFieldDescription")}
            </label>
            <input
              id="persona-description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("personaFieldDescriptionPlaceholder")}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Email Client + Device Type row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="persona-email-client"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t("personaFieldEmailClient")}
              </label>
              <select
                id="persona-email-client"
                value={emailClient}
                onChange={(e) => setEmailClient(e.target.value)}
                disabled={isMutating}
                className={selectClass}
              >
                {EMAIL_CLIENTS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="persona-device-type"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t("personaFieldDeviceType")}
              </label>
              <select
                id="persona-device-type"
                value={deviceType}
                onChange={(e) => setDeviceType(e.target.value)}
                disabled={isMutating}
                className={selectClass}
              >
                {DEVICE_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Viewport Width + OS row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="persona-viewport"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t("personaFieldViewportWidth")}
              </label>
              <input
                id="persona-viewport"
                type="number"
                min={200}
                max={2000}
                value={viewportWidth}
                onChange={(e) =>
                  setViewportWidth(
                    Math.max(200, Math.min(2000, Number(e.target.value) || 600))
                  )
                }
                disabled={isMutating}
                className={inputClass}
              />
            </div>

            <div>
              <label
                htmlFor="persona-os"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t("personaFieldOs")}
              </label>
              <select
                id="persona-os"
                value={osName}
                onChange={(e) => setOsName(e.target.value)}
                disabled={isMutating}
                className={selectClass}
              >
                {OS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Dark Mode */}
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={darkMode}
              onChange={(e) => setDarkMode(e.target.checked)}
              disabled={isMutating}
              className="accent-interactive"
            />
            <span className="text-foreground">
              {t("personaFieldDarkMode")}
            </span>
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
          >
            {t("personaCreateCancel")}
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
                {t("personaCreateSubmitting")}
              </span>
            ) : (
              t("personaCreateSubmit")
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
