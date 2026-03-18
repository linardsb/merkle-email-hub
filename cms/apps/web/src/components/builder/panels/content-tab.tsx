"use client";

import type { BuilderSection } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import { SlotEditor } from "./slot-editor";

interface ContentTabProps {
  section: BuilderSection;
  onUpdate: (updates: Partial<BuilderSection>) => void;
  designSystem: DesignSystemConfig | null;
}

export function ContentTab({ section, onUpdate, designSystem }: ContentTabProps) {
  if (section.slotDefinitions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center px-4 py-8 text-center">
        <p className="text-sm text-muted-foreground">
          {"No editable content slots"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {"This component does not expose any configurable slots."}
        </p>
      </div>
    );
  }

  const handleSlotChange = (slotId: string, value: string) => {
    onUpdate({
      slotFills: { ...section.slotFills, [slotId]: value },
    });
  };

  return (
    <div className="space-y-4 p-4">
      {section.slotDefinitions.map((slot) => (
        <SlotEditor
          key={slot.slot_id}
          slot={slot}
          value={section.slotFills[slot.slot_id] ?? ""}
          onChange={(v) => handleSlotChange(slot.slot_id, v)}
          designSystem={designSystem}
        />
      ))}
    </div>
  );
}
