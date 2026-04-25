"use client";

import {
  Monitor,
  Tablet,
  Smartphone,
  ShieldCheck,
  Zap,
  Copy,
  Download,
  CloudUpload,
} from "../icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@email-hub/ui/components/ui/dropdown-menu";

export type DevicePreview = "desktop" | "tablet" | "mobile";
export type ClientPreview = "none" | "gmail" | "outlook";

export const DEVICE_WIDTHS: Record<DevicePreview, string> = {
  desktop: "600px",
  tablet: "480px",
  mobile: "375px",
};

interface BuilderToolbarProps {
  devicePreview: DevicePreview;
  onDevicePreviewChange: (d: DevicePreview) => void;
  clientPreview: ClientPreview;
  onClientPreviewChange: (c: ClientPreview) => void;
  onRunQA?: () => void;
  isRunningQA?: boolean;
  onAISuggest?: () => void;
  onCopyHtml?: () => void;
  onDownloadHtml?: () => void;
  onPushToESP?: () => void;
}

const deviceButtons = [
  { value: "desktop" as const, icon: Monitor, label: "Desktop (600px)" },
  { value: "tablet" as const, icon: Tablet, label: "Tablet (480px)" },
  { value: "mobile" as const, icon: Smartphone, label: "Mobile (375px)" },
];

const clientOptions: { value: ClientPreview; label: string }[] = [
  { value: "none", label: "Default view" },
  { value: "gmail", label: "View as Gmail" },
  { value: "outlook", label: "View as Outlook" },
];

export function BuilderToolbar({
  devicePreview,
  onDevicePreviewChange,
  clientPreview,
  onClientPreviewChange,
  onRunQA,
  isRunningQA,
  onAISuggest,
  onCopyHtml,
  onDownloadHtml,
  onPushToESP,
}: BuilderToolbarProps) {
  return (
    <div
      className="border-border bg-card text-muted-foreground flex h-9 items-center justify-between border-b px-3 text-xs"
      data-builder-toolbar
    >
      {/* Left: Device preview segmented control */}
      <div className="flex items-center gap-3">
        <div className="border-border flex items-center rounded border">
          {deviceButtons.map(({ value, icon: Icon, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => onDevicePreviewChange(value)}
              className={`hover:bg-accent rounded p-1 transition-colors ${
                devicePreview === value ? "bg-accent text-foreground" : ""
              }`}
              title={label}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>

        {/* Client preview dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="border-border hover:bg-accent rounded border px-2 py-1 text-xs transition-colors"
            >
              {clientOptions.find((o) => o.value === clientPreview)?.label ?? "Default view"}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {clientOptions.map((opt) => (
              <DropdownMenuItem
                key={opt.value}
                onClick={() => onClientPreviewChange(opt.value)}
                className={clientPreview === opt.value ? "bg-accent" : ""}
              >
                {opt.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Right: QA + AI + Export */}
      <div className="flex items-center gap-2">
        {onRunQA && (
          <button
            type="button"
            onClick={onRunQA}
            disabled={isRunningQA}
            className="hover:bg-accent flex items-center gap-1 rounded px-2 py-1 transition-colors disabled:opacity-50"
            data-builder-qa
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>{isRunningQA ? "Running..." : "Run QA"}</span>
          </button>
        )}

        {onAISuggest && (
          <button
            type="button"
            onClick={onAISuggest}
            className="hover:bg-accent flex items-center gap-1 rounded px-2 py-1 transition-colors"
          >
            <Zap className="h-3.5 w-3.5" />
            <span>{"AI Suggest"}</span>
          </button>
        )}

        {/* Export dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="hover:bg-accent flex items-center gap-1 rounded px-2 py-1 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              <span>{"Export"}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {onCopyHtml && (
              <DropdownMenuItem onClick={onCopyHtml}>
                <Copy className="mr-2 h-3.5 w-3.5" />
                {"Copy HTML"}
              </DropdownMenuItem>
            )}
            {onDownloadHtml && (
              <DropdownMenuItem onClick={onDownloadHtml}>
                <Download className="mr-2 h-3.5 w-3.5" />
                {"Download .html"}
              </DropdownMenuItem>
            )}
            {onPushToESP && (
              <DropdownMenuItem onClick={onPushToESP}>
                <CloudUpload className="mr-2 h-3.5 w-3.5" />
                {"Push to ESP"}
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
