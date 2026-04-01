"use client";

import { useState } from "react";
import { AlignLeft, AlignCenter, AlignRight, Link2 } from "../../icons";
import { Label } from "@email-hub/ui/components/ui/label";
import { Input } from "@email-hub/ui/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@email-hub/ui/components/ui/select";
import type { BuilderSection } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import { extractPaletteSwatches } from "@/types/design-system-config";
import { PaletteColorPicker } from "./palette-color-picker";

interface StyleTabProps {
  section: BuilderSection;
  onUpdate: (updates: Partial<BuilderSection>) => void;
  designSystem: DesignSystemConfig | null;
}

/** Safely read a string value from the token overrides map */
function tokenStr(tokens: Record<string, unknown>, key: string): string {
  const v = tokens[key];
  return typeof v === "string" ? v : "";
}

export function StyleTab({ section, onUpdate, designSystem }: StyleTabProps) {
  const palette = designSystem ? extractPaletteSwatches(designSystem) : [];
  const tokens = section.tokenOverrides;
  const defaults = section.defaultTokens;

  const updateToken = (key: string, value: string) => {
    onUpdate({
      tokenOverrides: { ...section.tokenOverrides, [key]: value },
    });
  };

  // Collect available font choices
  const fontChoices: { value: string; label: string }[] = [];
  if (designSystem) {
    if (designSystem.typography.heading_font) {
      fontChoices.push({
        value: designSystem.typography.heading_font,
        label: `Heading: ${designSystem.typography.heading_font}`,
      });
    }
    if (designSystem.typography.body_font) {
      fontChoices.push({
        value: designSystem.typography.body_font,
        label: `Body: ${designSystem.typography.body_font}`,
      });
    }
    for (const [role, font] of Object.entries(designSystem.fonts)) {
      if (!fontChoices.some((f) => f.value === font)) {
        fontChoices.push({ value: font, label: role });
      }
    }
  }

  // Collect available font sizes
  const fontSizes: { value: string; label: string }[] = [];
  if (designSystem) {
    for (const [role, size] of Object.entries(designSystem.font_sizes)) {
      fontSizes.push({ value: size, label: `${role} (${size})` });
    }
  }

  return (
    <div className="space-y-5 p-4">
      {/* Color overrides */}
      {defaults?.colors && Object.keys(defaults.colors).length > 0 && (
        <div className="space-y-3">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {"Colors"}
          </Label>
          <div className="space-y-2">
            {Object.entries(defaults.colors).map(([role, defaultHex]) => (
              <div key={role} className="flex items-center justify-between">
                <span className="text-xs text-foreground">{role}</span>
                <PaletteColorPicker
                  value={tokenStr(tokens, `color_${role}`) || defaultHex}
                  palette={palette}
                  onChange={(hex) => updateToken(`color_${role}`, hex)}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Background */}
      {palette.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {"Background"}
          </Label>
          <div className="flex items-center justify-between">
            <span className="text-xs text-foreground">{"Background color"}</span>
            <PaletteColorPicker
              value={tokenStr(tokens, "background") || "#ffffff"}
              palette={palette}
              onChange={(hex) => updateToken("background", hex)}
            />
          </div>
        </div>
      )}

      {/* Font override */}
      {fontChoices.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {"Font"}
          </Label>
          <Select
            value={tokenStr(tokens, "font")}
            onValueChange={(v) => updateToken("font", v)}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Default" />
            </SelectTrigger>
            <SelectContent>
              {fontChoices.map((fc) => (
                <SelectItem key={fc.value} value={fc.value}>
                  {fc.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Font size */}
      {fontSizes.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {"Font Size"}
          </Label>
          <Select
            value={tokenStr(tokens, "font_size")}
            onValueChange={(v) => updateToken("font_size", v)}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Default" />
            </SelectTrigger>
            <SelectContent>
              {fontSizes.map((fs) => (
                <SelectItem key={fs.value} value={fs.value}>
                  {fs.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Spacing */}
      <SpacingEditor tokens={tokens} onUpdate={updateToken} tokenStr={tokenStr} />

      {/* Text alignment */}
      <div className="space-y-2">
        <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {"Text Alignment"}
        </Label>
        <AlignmentButtons
          value={tokenStr(tokens, "text_align") || "left"}
          onChange={(v) => updateToken("text_align", v)}
        />
      </div>

      {/* Empty state */}
      {!defaults && palette.length === 0 && fontChoices.length === 0 && (
        <p className="py-4 text-center text-xs text-muted-foreground">
          {"No design system configured. Add one in project settings."}
        </p>
      )}
    </div>
  );
}

function SpacingEditor({
  tokens,
  onUpdate,
  tokenStr: readToken,
}: {
  tokens: Record<string, unknown>;
  onUpdate: (key: string, value: string) => void;
  tokenStr: (tokens: Record<string, unknown>, key: string) => string;
}) {
  const [linked, setLinked] = useState(false);
  const sides = ["top", "right", "bottom", "left"] as const;

  const handleChange = (side: string, value: string) => {
    if (linked) {
      for (const s of sides) {
        onUpdate(`spacing_${s}`, value);
      }
    } else {
      onUpdate(`spacing_${side}`, value);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {"Spacing"}
        </Label>
        <button
          type="button"
          onClick={() => setLinked(!linked)}
          className={`rounded p-1 transition-colors ${linked ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"}`}
          aria-label="Link spacing values"
        >
          <Link2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        {sides.map((side) => (
          <div key={side} className="space-y-0.5">
            <span className="text-[10px] text-muted-foreground capitalize">
              {side}
            </span>
            <Input
              value={readToken(tokens, `spacing_${side}`)}
              onChange={(e) => handleChange(side, e.target.value)}
              placeholder="0"
              className="h-7 text-xs"
              type="number"
              min={0}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function AlignmentButtons({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const options = [
    { value: "left", Icon: AlignLeft },
    { value: "center", Icon: AlignCenter },
    { value: "right", Icon: AlignRight },
  ] as const;

  return (
    <div className="flex gap-1">
      {options.map(({ value: v, Icon }) => (
        <button
          key={v}
          type="button"
          onClick={() => onChange(v)}
          className={`rounded p-1.5 transition-colors ${
            value === v
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
          aria-label={`Align ${v}`}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  );
}
