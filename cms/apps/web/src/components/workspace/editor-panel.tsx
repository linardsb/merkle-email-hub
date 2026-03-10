"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import type { SaveStatus } from "./save-indicator";
import type { BrandConfig } from "@/types/brand";

const CodeEditor = dynamic(
  () =>
    import("@/components/workspace/editor/code-editor").then(
      (mod) => mod.CodeEditor
    ),
  {
    ssr: false,
    loading: () => <EditorLoading />,
  }
);

const LiquidBuilderPanel = dynamic(
  () =>
    import("@/components/workspace/liquid-builder/liquid-builder-panel").then(
      (mod) => mod.LiquidBuilderPanel
    ),
  {
    ssr: false,
    loading: () => <EditorLoading />,
  }
);

function EditorLoading() {
  const t = useTranslations("workspace");
  return (
    <div className="flex h-full items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      <span className="ml-2 text-sm text-muted-foreground">
        {t("editorLoading")}
      </span>
    </div>
  );
}

type EditorTab = "code" | "visual";

interface EditorPanelProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
  brandConfig?: BrandConfig | null;
  onBrandViolationsChange?: (count: number) => void;
  onCursorOffsetChange?: (offset: number) => void;
}

export function EditorPanel({ value, onChange, onSave, saveStatus, readOnly, brandConfig, onBrandViolationsChange, onCursorOffsetChange }: EditorPanelProps) {
  const t = useTranslations("workspace");
  const [activeTab, setActiveTab] = useState<EditorTab>("code");

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Tab bar */}
      <div className="flex border-b border-default bg-surface">
        <button
          type="button"
          onClick={() => setActiveTab("code")}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            activeTab === "code"
              ? "border-b-2 border-interactive text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("editorTabCode")}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("visual")}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            activeTab === "visual"
              ? "border-b-2 border-interactive text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("editorTabVisual")}
        </button>
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "code" ? (
          <CodeEditor
            value={value}
            onChange={onChange}
            onSave={onSave}
            saveStatus={saveStatus}
            readOnly={readOnly}
            brandConfig={brandConfig}
            onBrandViolationsChange={onBrandViolationsChange}
            onCursorOffsetChange={onCursorOffsetChange}
          />
        ) : (
          <LiquidBuilderPanel code={value} onCodeChange={onChange} />
        )}
      </div>
    </div>
  );
}
