"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { BrandColor } from "@/types/brand";

interface BrandColorEditorProps {
  colors: BrandColor[];
  onChange: (colors: BrandColor[]) => void;
  disabled?: boolean;
}

export function BrandColorEditor({ colors, onChange, disabled }: BrandColorEditorProps) {
  const [newName, setNewName] = useState("");
  const [newHex, setNewHex] = useState("#000000");

  const handleAdd = () => {
    if (!newName.trim() || !newHex.trim()) return;
    onChange([...colors, { name: newName.trim(), hex: newHex.trim() }]);
    setNewName("");
    setNewHex("#000000");
  };

  const handleRemove = (index: number) => {
    onChange(colors.filter((_, i) => i !== index));
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-1.5 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">{"Brand Colors"}</h3>

      {/* Existing colors */}
      <div className="flex flex-wrap gap-2">
        {colors.map((color, i) => (
          <div
            key={`${color.name}-${i}`}
            className="flex items-center gap-2 rounded-md border border-card-border bg-card-bg px-2.5 py-1.5"
          >
            <span
              className="h-4 w-4 rounded border border-border"
              style={{ backgroundColor: color.hex }}
            />
            <span className="text-xs font-medium text-foreground">{color.name}</span>
            <span className="text-xs text-foreground-muted">{color.hex}</span>
            {!disabled && (
              <button
                type="button"
                onClick={() => handleRemove(i)}
                className="text-foreground-muted transition-colors hover:text-status-danger"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add new color */}
      {!disabled && (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={"Color name (e.g., Primary)"}
              className={inputClass}
            />
          </div>
          <div className="w-24">
            <input
              type="color"
              value={newHex}
              onChange={(e) => setNewHex(e.target.value)}
              className="h-8 w-full cursor-pointer rounded border border-input-border"
            />
          </div>
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newName.trim()}
            className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
          >
            <Plus className="h-3 w-3" />
            {"Add"}
          </button>
        </div>
      )}
    </div>
  );
}
