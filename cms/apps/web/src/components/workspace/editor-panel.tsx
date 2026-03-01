"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import type { SaveStatus } from "./save-indicator";

const MonacoEditor = dynamic(
  () =>
    import("@/components/workspace/editor/monaco-editor").then(
      (mod) => mod.MonacoEditor
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

interface EditorPanelProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
}

export function EditorPanel({ value, onChange, onSave, saveStatus, readOnly }: EditorPanelProps) {
  return (
    <div className="h-full overflow-hidden bg-background">
      <MonacoEditor
        value={value}
        onChange={onChange}
        onSave={onSave}
        saveStatus={saveStatus}
        readOnly={readOnly}
      />
    </div>
  );
}
