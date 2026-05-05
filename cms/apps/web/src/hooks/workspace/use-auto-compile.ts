import { useEffect, useRef, type MutableRefObject } from "react";
import type * as Y from "yjs";
import { sanitizeHtml } from "@/lib/sanitize-html";
import { stripAnnotations } from "@/lib/builder-sync";
import type { useEmailPreview } from "@/hooks/use-email";
import type { SaveStatus } from "@/components/workspace/save-indicator";

interface AutoCompileArgs {
  htmlSource: string | null | undefined;
  activeTemplateId: number | null;
  triggerPreview: ReturnType<typeof useEmailPreview>["trigger"];
  collabDoc: Y.Doc | null;
  setEditorContent: (s: string) => void;
  setSavedContent: (s: string) => void;
  setSaveStatus: (s: SaveStatus) => void;
  setCompiledHtml: (s: string | null) => void;
  setBuildTimeMs: (n: number | null) => void;
}

/**
 * Auto-compile freshly-loaded template HTML once per template, syncing into the
 * editor and the collab Y.Doc. Returns a ref so callers (e.g. version restore)
 * can re-arm the one-shot.
 */
export function useAutoCompile(args: AutoCompileArgs): MutableRefObject<boolean> {
  const {
    htmlSource,
    activeTemplateId,
    triggerPreview,
    collabDoc,
    setEditorContent,
    setSavedContent,
    setSaveStatus,
    setCompiledHtml,
    setBuildTimeMs,
  } = args;
  const autoCompiledRef = useRef(false);

  useEffect(() => {
    if (!htmlSource) return;
    setEditorContent(htmlSource);
    setSavedContent(htmlSource);
    setSaveStatus("idle");

    if (collabDoc) {
      const yText = collabDoc.getText("content");
      if (yText.length === 0) yText.insert(0, htmlSource);
    }

    if (autoCompiledRef.current) return;
    autoCompiledRef.current = true;
    const sanitized = sanitizeHtml(stripAnnotations(htmlSource));
    triggerPreview({ source_html: sanitized })
      .then((r) => {
        if (r?.compiled_html) {
          setCompiledHtml(r.compiled_html);
          setBuildTimeMs(r.build_time_ms);
        } else {
          setCompiledHtml(sanitized);
        }
      })
      .catch(() => {
        setCompiledHtml(sanitized);
      });
  }, [
    htmlSource,
    triggerPreview,
    collabDoc,
    setEditorContent,
    setSavedContent,
    setSaveStatus,
    setCompiledHtml,
    setBuildTimeMs,
  ]);

  useEffect(() => {
    autoCompiledRef.current = false;
  }, [activeTemplateId]);

  return autoCompiledRef;
}
