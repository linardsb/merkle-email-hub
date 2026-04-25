"use client";

import { useState, useCallback } from "react";
import { Plus, Trash2, Code2, AlertTriangle } from "../../icons";
import { Input } from "@email-hub/ui/components/ui/input";
import { Label } from "@email-hub/ui/components/ui/label";
import { Checkbox } from "@email-hub/ui/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import type { BuilderSection, AdvancedConfig } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import { extractPaletteSwatches } from "@/types/design-system-config";
import { PaletteColorPicker } from "./palette-color-picker";

const BLOCKED_ATTR_PREFIXES = ["on"];
const BLOCKED_ATTR_NAMES = ["style"];
const BLOCKED_VALUE_PATTERNS = [/^javascript:/i, /^data:/i, /^vbscript:/i];
const CSS_CLASS_PATTERN = /^[a-zA-Z_-][\w-]*$/;

function isBlockedAttr(name: string): boolean {
  const lower = name.toLowerCase();
  if (BLOCKED_ATTR_NAMES.includes(lower)) return true;
  return BLOCKED_ATTR_PREFIXES.some((prefix) => lower.startsWith(prefix));
}

function isBlockedValue(value: string): boolean {
  return BLOCKED_VALUE_PATTERNS.some((pat) => pat.test(value.trim()));
}

interface AdvancedTabProps {
  section: BuilderSection;
  onUpdate: (updates: Partial<BuilderSection>) => void;
  designSystem: DesignSystemConfig | null;
}

export function AdvancedTab({ section, onUpdate, designSystem }: AdvancedTabProps) {
  const [viewSourceOpen, setViewSourceOpen] = useState(false);
  const { advanced } = section;
  const palette = designSystem ? extractPaletteSwatches(designSystem) : [];

  const updateAdvanced = useCallback(
    (updates: Partial<AdvancedConfig>) => {
      onUpdate({ advanced: { ...advanced, ...updates } });
    },
    [advanced, onUpdate],
  );

  const cssClassValid =
    advanced.customCssClass === "" || CSS_CLASS_PATTERN.test(advanced.customCssClass);

  return (
    <div className="space-y-5 p-4">
      {/* Custom CSS class */}
      <div className="space-y-2">
        <Label className="text-xs font-medium">{"Custom CSS class"}</Label>
        <Input
          value={advanced.customCssClass}
          onChange={(e) => updateAdvanced({ customCssClass: e.target.value })}
          placeholder="my-section-class"
          className={`h-8 text-sm ${!cssClassValid ? "border-destructive" : ""}`}
        />
        {!cssClassValid && (
          <p className="text-destructive flex items-center gap-1 text-[10px]">
            <AlertTriangle className="h-3 w-3" />
            {"Class name must start with a letter, underscore, or hyphen"}
          </p>
        )}
      </div>

      {/* MSO conditional */}
      <div className="flex items-start gap-3">
        <Checkbox
          id="mso-conditional"
          checked={advanced.msoConditional}
          onCheckedChange={(checked) => updateAdvanced({ msoConditional: checked === true })}
        />
        <div className="space-y-0.5">
          <Label htmlFor="mso-conditional" className="text-xs font-medium">
            {"MSO conditional wrapper"}
          </Label>
          <p className="text-muted-foreground text-[10px]">
            {"Wrap in <!--[if mso]> for Outlook compatibility"}
          </p>
        </div>
      </div>

      {/* Dark mode overrides */}
      {palette.length > 0 && (
        <KeyColorList
          label="Dark mode overrides"
          description="Override colors for dark mode rendering"
          entries={advanced.darkModeOverrides}
          palette={palette}
          onChange={(entries) => updateAdvanced({ darkModeOverrides: entries })}
        />
      )}

      {/* HTML attributes */}
      <HtmlAttributeList
        entries={advanced.htmlAttributes}
        onChange={(entries) => updateAdvanced({ htmlAttributes: entries })}
      />

      {/* View source */}
      <div>
        <button
          type="button"
          onClick={() => setViewSourceOpen(true)}
          className="text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-1.5 rounded px-3 py-1.5 text-xs transition-colors"
        >
          <Code2 className="h-3.5 w-3.5" />
          {"View Source"}
        </button>
      </div>

      <Dialog open={viewSourceOpen} onOpenChange={setViewSourceOpen}>
        <DialogContent className="max-w-[40rem]">
          <DialogHeader>
            <DialogTitle>{"Section HTML Source"}</DialogTitle>
          </DialogHeader>
          <pre className="bg-muted text-foreground max-h-96 overflow-auto rounded p-3 font-mono text-xs">
            {section.html}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** Key → palette color list for dark mode overrides */
function KeyColorList({
  label,
  description,
  entries,
  palette,
  onChange,
}: {
  label: string;
  description: string;
  entries: Record<string, string>;
  palette: { role: string; hex: string }[];
  onChange: (entries: Record<string, string>) => void;
}) {
  const pairs = Object.entries(entries);

  const addEntry = () => {
    onChange({ ...entries, [`element-${pairs.length + 1}`]: palette[0]?.hex ?? "#000000" });
  };

  const removeEntry = (key: string) => {
    const next = { ...entries };
    delete next[key];
    onChange(next);
  };

  const updateKey = (oldKey: string, newKey: string) => {
    const next: Record<string, string> = {};
    for (const [k, v] of Object.entries(entries)) {
      next[k === oldKey ? newKey : k] = v;
    }
    onChange(next);
  };

  const updateValue = (key: string, hex: string) => {
    onChange({ ...entries, [key]: hex });
  };

  return (
    <div className="space-y-2">
      <Label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
        {label}
      </Label>
      <p className="text-muted-foreground text-[10px]">{description}</p>
      <div className="space-y-1.5">
        {pairs.map(([key, hex]) => (
          <div key={key} className="flex items-center gap-1.5">
            <Input
              value={key}
              onChange={(e) => updateKey(key, e.target.value)}
              className="h-7 flex-1 text-xs"
              placeholder="Element"
            />
            <PaletteColorPicker
              value={hex}
              palette={palette}
              onChange={(c) => updateValue(key, c)}
            />
            <button
              type="button"
              onClick={() => removeEntry(key)}
              className="text-muted-foreground hover:text-destructive rounded p-1"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addEntry}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
      >
        <Plus className="h-3.5 w-3.5" />
        {"Add override"}
      </button>
    </div>
  );
}

/** HTML attribute key-value editor with security validation */
function HtmlAttributeList({
  entries,
  onChange,
}: {
  entries: Record<string, string>;
  onChange: (entries: Record<string, string>) => void;
}) {
  const pairs = Object.entries(entries);

  const addEntry = () => {
    onChange({ ...entries, [`data-attr-${pairs.length + 1}`]: "" });
  };

  const removeEntry = (key: string) => {
    const next = { ...entries };
    delete next[key];
    onChange(next);
  };

  const updateKey = (oldKey: string, newKey: string) => {
    if (isBlockedAttr(newKey)) return; // silently block
    const next: Record<string, string> = {};
    for (const [k, v] of Object.entries(entries)) {
      next[k === oldKey ? newKey : k] = v;
    }
    onChange(next);
  };

  const updateValue = (key: string, value: string) => {
    if (isBlockedValue(value)) return; // silently block
    onChange({ ...entries, [key]: value });
  };

  return (
    <div className="space-y-2">
      <Label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
        {"HTML Attributes"}
      </Label>
      <p className="text-muted-foreground text-[10px]">
        {"Event handlers (on*), style, and script URIs are blocked."}
      </p>
      <div className="space-y-1.5">
        {pairs.map(([key, val]) => {
          const keyBlocked = isBlockedAttr(key);
          const valBlocked = isBlockedValue(val);
          return (
            <div key={key} className="flex items-center gap-1.5">
              <Input
                value={key}
                onChange={(e) => updateKey(key, e.target.value)}
                className={`h-7 flex-1 text-xs ${keyBlocked ? "border-destructive" : ""}`}
                placeholder="Attribute"
              />
              <Input
                value={val}
                onChange={(e) => updateValue(key, e.target.value)}
                className={`h-7 flex-1 text-xs ${valBlocked ? "border-destructive" : ""}`}
                placeholder="Value"
              />
              <button
                type="button"
                onClick={() => removeEntry(key)}
                className="text-muted-foreground hover:text-destructive rounded p-1"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        onClick={addEntry}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
      >
        <Plus className="h-3.5 w-3.5" />
        {"Add attribute"}
      </button>
    </div>
  );
}
