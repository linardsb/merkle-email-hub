"use client";

import { Monitor, Smartphone } from "../../icons";
import { Switch } from "@email-hub/ui/components/ui/switch";
import { Label } from "@email-hub/ui/components/ui/label";
import { Input } from "@email-hub/ui/components/ui/input";
import type { BuilderSection, ResponsiveOverrides } from "@/types/visual-builder";

interface ResponsiveTabProps {
  section: BuilderSection;
  onUpdate: (updates: Partial<BuilderSection>) => void;
  previewMode: "desktop" | "mobile";
  onPreviewModeChange: (mode: "desktop" | "mobile") => void;
}

export function ResponsiveTab({
  section,
  onUpdate,
  previewMode,
  onPreviewModeChange,
}: ResponsiveTabProps) {
  const { responsive } = section;

  const updateResponsive = (updates: Partial<ResponsiveOverrides>) => {
    onUpdate({ responsive: { ...responsive, ...updates } });
  };

  return (
    <div className="space-y-5 p-4">
      {/* Preview mode toggle */}
      <div className="space-y-2">
        <Label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
          {"Preview Mode"}
        </Label>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => onPreviewModeChange("desktop")}
            className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs transition-colors ${
              previewMode === "desktop"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Monitor className="h-3.5 w-3.5" />
            {"Desktop"}
          </button>
          <button
            type="button"
            onClick={() => onPreviewModeChange("mobile")}
            className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs transition-colors ${
              previewMode === "mobile"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Smartphone className="h-3.5 w-3.5" />
            {"Mobile"}
          </button>
        </div>
      </div>

      {/* Stack on mobile */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-xs font-medium">{"Stack on mobile"}</Label>
          <p className="text-muted-foreground text-[10px]">
            {"Convert side-by-side columns to stacked layout"}
          </p>
        </div>
        <Switch
          checked={responsive.stackOnMobile}
          onCheckedChange={(checked) => updateResponsive({ stackOnMobile: checked })}
        />
      </div>

      {/* Full width images */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-xs font-medium">{"Full width images on mobile"}</Label>
          <p className="text-muted-foreground text-[10px]">
            {"Images expand to fill container width"}
          </p>
        </div>
        <Switch
          checked={responsive.fullWidthImageOnMobile}
          onCheckedChange={(checked) => updateResponsive({ fullWidthImageOnMobile: checked })}
        />
      </div>

      {/* Mobile font size */}
      <div className="space-y-2">
        <Label className="text-xs font-medium">{"Mobile font size"}</Label>
        <div className="flex items-center gap-2">
          <Input
            value={responsive.mobileFontSize?.replace("px", "") ?? ""}
            onChange={(e) =>
              updateResponsive({
                mobileFontSize: e.target.value ? `${e.target.value}px` : null,
              })
            }
            placeholder="Default"
            className="h-8 w-20 text-sm"
            type="number"
            min={10}
            max={32}
          />
          <span className="text-muted-foreground text-xs">{"px"}</span>
        </div>
      </div>
    </div>
  );
}
