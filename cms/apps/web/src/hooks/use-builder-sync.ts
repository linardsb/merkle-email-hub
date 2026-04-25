"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { SectionNode, SyncStatus } from "@/types/visual-builder";
import { BuilderSyncEngine } from "@/lib/builder-sync";

interface UseBuilderSyncOptions {
  /** Whether sync is enabled (false when only one view is active) */
  enabled: boolean;
}

interface UseBuilderSyncReturn {
  /** Current sync status */
  syncStatus: SyncStatus;
  /** Parse error message (null when no error) */
  parseError: string | null;
  /** Notify sync engine of code editor changes */
  handleCodeChange: (html: string) => void;
  /** Notify sync engine of builder section changes */
  handleBuilderChange: (sections: SectionNode[]) => void;
  /** Sections parsed from code (for builder consumption) */
  parsedSections: SectionNode[];
  /** HTML serialized from builder (for code editor consumption) */
  serializedHtml: string | null;
  /** Clear parse error and revert to last valid state */
  dismissParseError: () => void;
}

export function useBuilderSync({ enabled }: UseBuilderSyncOptions): UseBuilderSyncReturn {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("synced");
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedSections, setParsedSections] = useState<SectionNode[]>([]);
  const [serializedHtml, setSerializedHtml] = useState<string | null>(null);
  const engineRef = useRef<BuilderSyncEngine | null>(null);

  useEffect(() => {
    if (!enabled) {
      engineRef.current?.dispose();
      engineRef.current = null;
      return;
    }

    const engine = new BuilderSyncEngine({
      onBuilderUpdate: (sections) => {
        setParsedSections(sections);
        setParseError(null);
      },
      onCodeUpdate: (html) => {
        setSerializedHtml(html);
      },
      onStatusChange: setSyncStatus,
      onParseError: setParseError,
    });

    engineRef.current = engine;
    return () => engine.dispose();
  }, [enabled]);

  const handleCodeChange = useCallback((html: string) => engineRef.current?.onCodeChange(html), []);

  const handleBuilderChange = useCallback(
    (sections: SectionNode[]) => engineRef.current?.onBuilderChange(sections),
    [],
  );

  const dismissParseError = useCallback(() => {
    setParseError(null);
    setSyncStatus("synced");
  }, []);

  return {
    syncStatus,
    parseError,
    handleCodeChange,
    handleBuilderChange,
    parsedSections,
    serializedHtml,
    dismissParseError,
  };
}
