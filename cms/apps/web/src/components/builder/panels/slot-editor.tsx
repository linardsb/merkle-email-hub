"use client";

import { Input } from "@email-hub/ui/components/ui/input";
import { Textarea } from "@email-hub/ui/components/ui/textarea";
import { Label } from "@email-hub/ui/components/ui/label";
import type { SlotDefinition } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import { PaletteColorPicker } from "./palette-color-picker";
import { extractPaletteSwatches } from "@/types/design-system-config";

interface SlotEditorProps {
  slot: SlotDefinition;
  value: string;
  onChange: (value: string) => void;
  designSystem: DesignSystemConfig | null;
}

export function SlotEditor({
  slot,
  value,
  onChange,
  designSystem,
}: SlotEditorProps) {
  const label = slot.label || slot.slot_id;
  const charCount = value.length;
  const overLimit = slot.max_chars !== null && charCount > slot.max_chars;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs font-medium">
          {label}
          {slot.required && (
            <span className="ml-0.5 text-destructive">{"*"}</span>
          )}
        </Label>
        {slot.max_chars !== null && (
          <span
            className={`text-[10px] ${overLimit ? "text-destructive" : "text-muted-foreground"}`}
          >
            {charCount}/{slot.max_chars}
          </span>
        )}
      </div>

      {renderControl(slot, value, onChange, designSystem)}
    </div>
  );
}

function renderControl(
  slot: SlotDefinition,
  value: string,
  onChange: (v: string) => void,
  designSystem: DesignSystemConfig | null
) {
  switch (slot.slot_type) {
    case "headline":
    case "subheadline":
      return (
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={slot.placeholder}
          className="h-8 text-sm"
        />
      );

    case "body":
    case "preheader":
    case "footer":
    case "nav":
      return (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={slot.placeholder}
          className="min-h-16 resize-y text-sm"
          rows={3}
        />
      );

    case "cta":
      return <CtaEditor value={value} onChange={onChange} placeholder={slot.placeholder} />;

    case "image":
      return <ImageEditor value={value} onChange={onChange} placeholder={slot.placeholder} />;

    case "social":
      return (
        <p className="text-xs text-muted-foreground">
          {"Configured in project design system"}
        </p>
      );

    case "divider":
      return (
        <DividerEditor
          value={value}
          onChange={onChange}
          designSystem={designSystem}
        />
      );

    default:
      return (
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={slot.placeholder}
          className="h-8 text-sm"
        />
      );
  }
}

/** CTA slot: button text + URL */
function CtaEditor({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  // Store as JSON: { text, url }
  let parsed: { text: string; url: string } = { text: "", url: "" };
  try {
    const p: unknown = JSON.parse(value);
    if (p && typeof p === "object" && "text" in p && "url" in p) {
      parsed = p as { text: string; url: string };
    }
  } catch {
    parsed = { text: value, url: "" };
  }

  const update = (field: "text" | "url", v: string) => {
    onChange(JSON.stringify({ ...parsed, [field]: v }));
  };

  return (
    <div className="space-y-1.5">
      <Input
        value={parsed.text}
        onChange={(e) => update("text", e.target.value)}
        placeholder={placeholder || "Button text"}
        className="h-8 text-sm"
      />
      <Input
        value={parsed.url}
        onChange={(e) => update("url", e.target.value)}
        placeholder="https://..."
        className="h-8 text-sm"
        type="url"
      />
    </div>
  );
}

/** Image slot: URL + alt text */
function ImageEditor({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  let parsed: { src: string; alt: string } = { src: "", alt: "" };
  try {
    const p: unknown = JSON.parse(value);
    if (p && typeof p === "object" && "src" in p && "alt" in p) {
      parsed = p as { src: string; alt: string };
    }
  } catch {
    parsed = { src: value, alt: "" };
  }

  const update = (field: "src" | "alt", v: string) => {
    onChange(JSON.stringify({ ...parsed, [field]: v }));
  };

  return (
    <div className="space-y-1.5">
      <Input
        value={parsed.src}
        onChange={(e) => update("src", e.target.value)}
        placeholder={placeholder || "Image URL"}
        className="h-8 text-sm"
        type="url"
      />
      <Input
        value={parsed.alt}
        onChange={(e) => update("alt", e.target.value)}
        placeholder="Alt text"
        className="h-8 text-sm"
      />
    </div>
  );
}

/** Divider slot: height + color */
function DividerEditor({
  value,
  onChange,
  designSystem,
}: {
  value: string;
  onChange: (v: string) => void;
  designSystem: DesignSystemConfig | null;
}) {
  let parsed: { height: string; color: string } = {
    height: "1",
    color: "#cccccc",
  };
  try {
    const p: unknown = JSON.parse(value);
    if (p && typeof p === "object" && "height" in p && "color" in p) {
      parsed = p as { height: string; color: string };
    }
  } catch {
    /* use defaults */
  }

  const update = (field: "height" | "color", v: string) => {
    onChange(JSON.stringify({ ...parsed, [field]: v }));
  };

  const palette = designSystem ? extractPaletteSwatches(designSystem) : [];

  return (
    <div className="flex items-center gap-2">
      <Input
        value={parsed.height}
        onChange={(e) => update("height", e.target.value)}
        placeholder="1"
        className="h-8 w-16 text-sm"
        type="number"
        min={1}
        max={20}
      />
      <span className="text-xs text-muted-foreground">{"px"}</span>
      {palette.length > 0 && (
        <PaletteColorPicker
          value={parsed.color}
          palette={palette}
          onChange={(hex) => update("color", hex)}
        />
      )}
    </div>
  );
}
