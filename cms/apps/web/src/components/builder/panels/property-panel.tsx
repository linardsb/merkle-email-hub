"use client";

import { useEffect, useState } from "react";
import { X } from "../../icons";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@email-hub/ui/components/ui/tabs";
import { Badge } from "@email-hub/ui/components/ui/badge";
import type { BuilderSection } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import { ContentTab } from "./content-tab";
import { StyleTab } from "./style-tab";
import { ResponsiveTab } from "./responsive-tab";
import { AdvancedTab } from "./advanced-tab";

interface PropertyPanelProps {
  section: BuilderSection;
  onUpdate: (updates: Partial<BuilderSection>) => void;
  designSystem: DesignSystemConfig | null;
  onClose: () => void;
  previewMode: "desktop" | "mobile";
  onPreviewModeChange: (mode: "desktop" | "mobile") => void;
}

export function PropertyPanel({
  section,
  onUpdate,
  designSystem,
  onClose,
  previewMode,
  onPreviewModeChange,
}: PropertyPanelProps) {
  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [onClose]);

  const [activeTab, setActiveTab] = useState("content");

  return (
    <div className="border-default bg-card flex h-full w-80 flex-shrink-0 flex-col border-l">
      {/* Header */}
      <div className="border-default flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="text-foreground truncate text-sm font-medium">
            {section.componentName}
          </span>
          <Badge variant="outline" className="text-[10px]">
            {section.category}
          </Badge>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground rounded p-1 transition-colors"
          aria-label="Close property panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex flex-1 flex-col overflow-hidden"
      >
        <TabsList className="border-default grid w-full grid-cols-4 rounded-none border-b bg-transparent px-1">
          <TabsTrigger value="content" className="text-[10px]">
            {"Content"}
          </TabsTrigger>
          <TabsTrigger value="style" className="text-[10px]">
            {"Style"}
          </TabsTrigger>
          <TabsTrigger value="responsive" className="text-[10px]">
            {"Responsive"}
          </TabsTrigger>
          <TabsTrigger value="advanced" className="text-[10px]">
            {"Advanced"}
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="flex-1">
          <TabsContent value="content" className="mt-0">
            <ContentTab section={section} onUpdate={onUpdate} designSystem={designSystem} />
          </TabsContent>
          <TabsContent value="style" className="mt-0">
            <StyleTab section={section} onUpdate={onUpdate} designSystem={designSystem} />
          </TabsContent>
          <TabsContent value="responsive" className="mt-0">
            <ResponsiveTab
              section={section}
              onUpdate={onUpdate}
              previewMode={previewMode}
              onPreviewModeChange={onPreviewModeChange}
            />
          </TabsContent>
          <TabsContent value="advanced" className="mt-0">
            <AdvancedTab section={section} onUpdate={onUpdate} designSystem={designSystem} />
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </div>
  );
}
