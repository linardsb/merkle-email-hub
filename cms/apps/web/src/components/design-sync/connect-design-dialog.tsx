"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2, Check, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import {
  useCreateDesignConnection,
  useBrowseDesignFiles,
} from "@/hooks/use-design-sync";
import { useProjects } from "@/hooks/use-projects";
import type { DesignProvider, DesignFileBrowse } from "@/types/design-sync";
import { ApiError } from "@/lib/api-error";

interface ConnectDesignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PROVIDERS: { value: DesignProvider; label: string }[] = [
  { value: "figma", label: "Figma" },
  { value: "sketch", label: "Sketch" },
  { value: "canva", label: "Canva" },
  { value: "penpot", label: "Penpot" },
  { value: "mock", label: "Mock (Demo)" },
];

const TOKEN_GUIDE: Record<string, string> = {
  figma: "Generate a new Personal Access Token at figma.com/developers/api#access-tokens",
  penpot: "Generate a new token in your Penpot Account Settings > Access Tokens",
  sketch: "Check your Sketch Cloud API token in your account settings",
  canva: "Check your Canva Connect API credentials",
};

const URL_FORMATS: Record<string, string> = {
  figma: "figma.com/design/<file_key>/...",
  penpot: "design.penpot.app/#/workspace/<project>/<file>",
  sketch: "sketch.cloud/s/<document-id>",
  canva: "canva.com/design/<design-id>/...",
};

type WizardStep = 1 | 2 | 3;

export function ConnectDesignDialog({ open, onOpenChange }: ConnectDesignDialogProps) {
  const { trigger: createConnection, isMutating: isCreating } = useCreateDesignConnection();
  const { trigger: browseFiles, isMutating: isBrowsing } = useBrowseDesignFiles();
  const { mutate } = useSWRConfig();
  const { data: projects } = useProjects({ pageSize: 50 });

  // Wizard state
  const [step, setStep] = useState<WizardStep>(1);

  // Step 1: auth
  const [provider, setProvider] = useState<DesignProvider>("figma");
  const [accessToken, setAccessToken] = useState("");

  // Step 2: file selection
  const [files, setFiles] = useState<DesignFileBrowse[]>([]);
  const [selectedFile, setSelectedFile] = useState<DesignFileBrowse | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [browseUnsupported, setBrowseUnsupported] = useState(false);
  const [manualUrl, setManualUrl] = useState("");

  // Step 3: configure
  const [name, setName] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);

  // Reset form when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setStep(1);
    setProvider("figma");
    setAccessToken("");
    setFiles([]);
    setSelectedFile(null);
    setSearchQuery("");
    setBrowseUnsupported(false);
    setManualUrl("");
    setName("");
    setProjectId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  // Group files by folder
  const groupedFiles = useMemo(() => {
    const filtered = searchQuery
      ? files.filter((f) =>
          f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (f.folder?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false)
        )
      : files;

    const groups: Record<string, DesignFileBrowse[]> = {};
    for (const file of filtered) {
      const folder = file.folder ?? "Other";
      if (!groups[folder]) groups[folder] = [];
      groups[folder].push(file);
    }
    return groups;
  }, [files, searchQuery]);

  // Step 1: Browse files
  const handleBrowse = async () => {
    if (!accessToken.trim()) return;
    try {
      const result = await browseFiles({
        provider,
        access_token: accessToken.trim(),
      });
      if (result.total === 0) {
        setBrowseUnsupported(true);
        setFiles([]);
      } else {
        setBrowseUnsupported(false);
        setFiles(result.files);
      }
      setStep(2);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      const label = PROVIDERS.find((p) => p.value === provider)?.label ?? provider;
      const status = err instanceof ApiError ? err.status : 0;
      if (status === 429) {
        toast.error("Too many requests. Please wait a moment and try again.", {
          description: "The server is rate-limiting requests. Wait a few seconds before retrying.",
          duration: 8000,
        });
      } else if (message.includes("access denied") || message.includes("403")) {
        toast.error(`${label} access denied. Check your access token is valid.`, {
          description: `Generate a new token from your ${label} account settings.`,
          duration: 8000,
        });
      } else if (message.includes("not supported")) {
        toast.error(`${label} is not yet fully supported.`, {
          description: "Use the manual URL entry to connect your file.",
          duration: 6000,
        });
      } else {
        toast.error(`Failed to browse ${label} files.`, {
          description: message || "Check your access token and try again.",
          duration: 6000,
        });
      }
    }
  };

  // Step 2: Select file → go to step 3
  const handleSelectFile = (file: DesignFileBrowse) => {
    setSelectedFile(file);
    setName(file.name);
    setManualUrl(file.url);
    setStep(3);
  };

  // Step 2 (fallback): Manual URL → go to step 3
  const handleManualContinue = () => {
    if (!manualUrl.trim()) return;
    setSelectedFile(null);
    setName("");
    setStep(3);
  };

  // Step 3: Connect
  const fileUrl = selectedFile?.url ?? manualUrl.trim();
  const isStep3Valid = name.trim().length >= 1 && fileUrl.length >= 1;

  const handleConnect = async () => {
    if (!isStep3Valid) return;
    try {
      await createConnection({
        name: name.trim(),
        provider,
        file_url: fileUrl,
        access_token: accessToken.trim(),
        project_id: projectId,
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
        undefined,
        { revalidate: true },
      );
      toast.success("Design file connected successfully");
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      const label = PROVIDERS.find((p) => p.value === provider)?.label ?? provider;
      const status = err instanceof ApiError ? err.status : 0;
      if (status === 429) {
        toast.error("Too many requests. Please wait a moment and try again.", {
          description: "The server is rate-limiting requests. Wait a few seconds before retrying.",
          duration: 8000,
        });
      } else if (message.includes("access denied")) {
        toast.error(`${label} access denied. Your token may have been revoked.`, {
          description: TOKEN_GUIDE[provider] ?? `Check your ${label} access token.`,
          duration: 8000,
        });
      } else if (message.includes("not found")) {
        toast.error("Design file not found.", {
          description: `Check the file URL and ensure the file hasn't been deleted from ${label}.`,
          duration: 6000,
        });
      } else if (message.includes("Invalid") && message.includes("URL")) {
        toast.error("Invalid file URL.", {
          description: `Expected format: ${URL_FORMATS[provider] ?? "a valid design file URL"}`,
          duration: 6000,
        });
      } else {
        toast.error(`Failed to connect to ${label}`, {
          description: message || "Check the browser console for details.",
          duration: 6000,
        });
      }
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const isLoading = isBrowsing || isCreating;

  return (
    <Dialog open={open} onOpenChange={isLoading ? undefined : onOpenChange}>
      <DialogContent className="max-w-[36rem]">
        <DialogHeader>
          <DialogTitle>{"Connect Design File"}</DialogTitle>
          <DialogDescription>
            {step === 1
              ? "Choose your design tool and enter your access token."
              : step === 2
                ? "Select a design file from your account."
                : "Configure your connection and link it to a project."}
          </DialogDescription>
        </DialogHeader>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 py-2">
          {([1, 2, 3] as const).map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium transition-colors ${
                  s < step
                    ? "bg-success-muted text-success"
                    : s === step
                      ? "bg-interactive text-foreground-inverse"
                      : "bg-surface-sunken text-foreground-muted"
                }`}
              >
                {s < step ? <Check className="h-3.5 w-3.5" /> : s}
              </div>
              {s < 3 && (
                <div
                  className={`h-px w-8 ${
                    s < step ? "bg-success-muted" : "bg-border"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Authenticate */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label htmlFor="design-provider" className="mb-1.5 block text-sm font-medium text-foreground">
                {"Design Tool"}
              </label>
              <select
                id="design-provider"
                value={provider}
                onChange={(e) => setProvider(e.target.value as DesignProvider)}
                disabled={isLoading}
                className={selectClass}
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="design-token" className="mb-1.5 block text-sm font-medium text-foreground">
                {"Access Token"}
              </label>
              <input
                id="design-token"
                type="password"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                placeholder={
                  provider === "figma"
                    ? "figd_..."
                    : provider === "mock"
                      ? "demo-token"
                      : "Paste access token…"
                }
                disabled={isLoading}
                className={inputClass}
              />
              <p className="mt-1 text-xs text-foreground-muted">
                {provider === "mock"
                  ? "Any value works for demo mode."
                  : "Generate a token from your design tool's developer settings."}
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleBrowse}
                disabled={!accessToken.trim() || isLoading}
                className="flex items-center gap-1.5 rounded-md bg-interactive px-4 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
              >
                {isBrowsing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {"Browsing…"}
                  </>
                ) : (
                  <>
                    {"Browse Files"}
                    <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Browse & Pick */}
        {step === 2 && (
          <div className="space-y-3">
            {browseUnsupported ? (
              /* Fallback: manual URL input */
              <div className="space-y-3">
                <p className="text-sm text-foreground-muted">
                  {`File browsing is not yet supported for ${PROVIDERS.find((p) => p.value === provider)?.label ?? provider}. Enter a file URL manually.`}
                </p>
                <div>
                  <label htmlFor="manual-url" className="mb-1.5 block text-sm font-medium text-foreground">
                    {"Design File URL"}
                  </label>
                  <input
                    id="manual-url"
                    type="url"
                    value={manualUrl}
                    onChange={(e) => setManualUrl(e.target.value)}
                    placeholder={
                      provider === "figma"
                        ? "https://www.figma.com/design/..."
                        : "Paste file URL…"
                    }
                    disabled={isLoading}
                    className={inputClass}
                  />
                </div>
                <div className="flex justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {"Back"}
                  </button>
                  <button
                    type="button"
                    onClick={handleManualContinue}
                    disabled={!manualUrl.trim()}
                    className="flex items-center gap-1.5 rounded-md bg-interactive px-4 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
                  >
                    {"Continue"}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ) : (
              /* Visual file grid */
              <>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-foreground-muted" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search files…"
                    className={`${inputClass} pl-8`}
                  />
                </div>

                <div className="max-h-[20rem] overflow-y-auto rounded-md border border-border">
                  {Object.keys(groupedFiles).length === 0 ? (
                    <p className="p-4 text-center text-sm text-foreground-muted">
                      {"No files found."}
                    </p>
                  ) : (
                    Object.entries(groupedFiles).map(([folder, folderFiles]) => (
                      <div key={folder}>
                        <div className="sticky top-0 border-b border-border bg-surface-sunken px-3 py-1.5 text-xs font-medium text-foreground-muted">
                          {folder}
                        </div>
                        <div className="grid grid-cols-2 gap-2 p-2">
                          {folderFiles.map((file) => (
                            <button
                              key={file.file_id}
                              type="button"
                              onClick={() => handleSelectFile(file)}
                              className="group flex flex-col overflow-hidden rounded-md border border-border text-left transition-colors hover:border-interactive hover:bg-surface-hover"
                            >
                              {file.thumbnail_url ? (
                                <div className="flex h-24 items-center justify-center overflow-hidden bg-surface-sunken">
                                  {/* eslint-disable-next-line @next/next/no-img-element */}
                                  <img
                                    src={file.thumbnail_url}
                                    alt={file.name}
                                    className="h-full w-full object-cover"
                                  />
                                </div>
                              ) : (
                                <div className="flex h-24 items-center justify-center bg-surface-sunken">
                                  <span className="text-2xl text-foreground-muted">
                                    {file.name.charAt(0).toUpperCase()}
                                  </span>
                                </div>
                              )}
                              <div className="px-2 py-1.5">
                                <p className="truncate text-xs font-medium text-foreground">
                                  {file.name}
                                </p>
                                {file.last_modified && (
                                  <p className="text-[10px] text-foreground-muted">
                                    {new Date(file.last_modified).toLocaleDateString()}
                                  </p>
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="flex justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {"Back"}
                  </button>
                  <span className="text-xs text-foreground-muted self-center">
                    {`${files.length} file${files.length === 1 ? "" : "s"}`}
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        {/* Step 3: Configure & Connect */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <label htmlFor="design-name" className="mb-1.5 block text-sm font-medium text-foreground">
                {"Connection Name"}
              </label>
              <input
                id="design-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Campaign Design System"
                maxLength={200}
                disabled={isCreating}
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="design-url-readonly" className="mb-1.5 block text-sm font-medium text-foreground">
                {"Design File URL"}
              </label>
              <input
                id="design-url-readonly"
                type="text"
                value={fileUrl}
                readOnly={!!selectedFile}
                onChange={selectedFile ? undefined : (e) => setManualUrl(e.target.value)}
                disabled={isCreating}
                className={`${inputClass} ${selectedFile ? "bg-surface-sunken" : ""}`}
              />
            </div>

            <div>
              <label htmlFor="design-project" className="mb-1.5 block text-sm font-medium text-foreground">
                {"Link to Project"}
              </label>
              <select
                id="design-project"
                value={projectId ?? ""}
                onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
                disabled={isCreating}
                className={selectClass}
              >
                <option value="">{"None"}</option>
                {projects?.items?.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-between pt-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                disabled={isCreating}
                className="flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
              >
                <ChevronLeft className="h-4 w-4" />
                {"Back"}
              </button>
              <button
                type="button"
                onClick={handleConnect}
                disabled={!isStep3Valid || isCreating}
                className="rounded-md bg-interactive px-4 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
              >
                {isCreating ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {"Connecting…"}
                  </span>
                ) : (
                  "Connect"
                )}
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
