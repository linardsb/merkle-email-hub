"use client";

import { useState, useMemo, useCallback } from "react";
import { Globe, X as XIcon } from "../icons";
import type { TranslationKeyRow } from "@/types/tolgee";

interface InContextOverlayProps {
  html: string;
  translationKeys: TranslationKeyRow[];
  selectedLocale: string;
  isEditable: boolean;
  onTranslationEdit?: (key: string, locale: string, value: string) => void;
  enabled: boolean;
  onToggle: () => void;
}

/**
 * Escapes a string for safe injection into HTML attributes.
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Injects data-tolgee-key attributes and visual highlights into translatable
 * text spans in the email HTML. Uses string replacement on source text matches.
 */
function annotateHtml(
  html: string,
  keys: TranslationKeyRow[],
  locale: string,
): string {
  let annotated = html;

  for (const keyRow of keys) {
    const sourceText = keyRow.sourceText;
    if (!sourceText || sourceText.length < 2) continue;

    const status = keyRow.statuses[locale] ?? "untranslated";
    const outlineColor =
      status === "untranslated"
        ? "outline: 2px dashed #e67e22; outline-offset: 1px;"
        : "outline: 1px dashed #3498db; outline-offset: 1px;";

    const escapedSource = escapeHtml(sourceText);
    const wrapper = `<span data-tolgee-key="${escapeHtml(keyRow.key)}" style="${outlineColor} cursor: pointer; position: relative;" title="${escapeHtml(keyRow.key)}">${escapedSource}</span>`;

    // Replace only the first occurrence to avoid breaking repeated text
    annotated = annotated.replace(sourceText, wrapper);
  }

  return annotated;
}

export function InContextOverlay({
  html,
  translationKeys,
  selectedLocale,
  isEditable,
  onTranslationEdit,
  enabled,
  onToggle,
}: InContextOverlayProps) {
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const annotatedHtml = useMemo(() => {
    if (!enabled) return html;
    return annotateHtml(html, translationKeys, selectedLocale);
  }, [html, translationKeys, selectedLocale, enabled]);

  const activeKeyRow = useMemo(
    () => translationKeys.find((k) => k.key === editingKey),
    [translationKeys, editingKey],
  );

  const handleEditStart = useCallback(
    (key: string) => {
      if (!isEditable) return;
      const keyRow = translationKeys.find((k) => k.key === key);
      if (!keyRow) return;
      setEditingKey(key);
      setEditValue(keyRow.translations[selectedLocale] ?? "");
    },
    [isEditable, translationKeys, selectedLocale],
  );

  const handleEditSave = useCallback(() => {
    if (!editingKey) return;
    onTranslationEdit?.(editingKey, selectedLocale, editValue);
    setEditingKey(null);
    setEditValue("");
  }, [editingKey, selectedLocale, editValue, onTranslationEdit]);

  const handleEditCancel = useCallback(() => {
    setEditingKey(null);
    setEditValue("");
  }, []);

  return (
    <div className="relative h-full">
      {/* ── Toggle Button ── */}
      <button
        type="button"
        onClick={onToggle}
        className={`absolute right-3 top-3 z-20 flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium shadow-sm transition-colors ${
          enabled
            ? "bg-interactive text-foreground-inverse"
            : "bg-surface-elevated text-foreground hover:bg-surface-hover"
        }`}
        title={enabled ? "Disable translation overlay" : "Enable translation overlay"}
      >
        <Globe className="h-3.5 w-3.5" />
        {enabled ? "Overlay On" : "Overlay Off"}
      </button>

      {/* ── Edit Popover ── */}
      {editingKey && activeKeyRow && (
        <div className="absolute left-1/2 top-16 z-30 w-80 -translate-x-1/2 rounded-md border border-border bg-surface p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-foreground">
              {activeKeyRow.key}
            </span>
            <button
              type="button"
              onClick={handleEditCancel}
              className="text-foreground-muted hover:text-foreground"
            >
              <XIcon className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mb-2">
            <span className="text-[10px] text-foreground-muted">
              {"Source:"}
            </span>
            <p className="text-xs text-foreground">
              {activeKeyRow.sourceText}
            </p>
          </div>

          <div className="mb-2">
            <label
              htmlFor="overlay-edit"
              className="mb-1 block text-[10px] text-foreground-muted"
            >
              {`Translation (${selectedLocale}):`}
            </label>
            <textarea
              id="overlay-edit"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              rows={2}
              className="w-full rounded border border-input-border bg-input-bg px-2 py-1 text-xs text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
            />
          </div>

          <div className="flex justify-end gap-1.5">
            <button
              type="button"
              onClick={handleEditCancel}
              className="rounded px-2 py-1 text-xs text-foreground hover:bg-surface-hover"
            >
              {"Cancel"}
            </button>
            <button
              type="button"
              onClick={handleEditSave}
              className="rounded bg-interactive px-2 py-1 text-xs font-medium text-foreground-inverse hover:bg-interactive-hover"
            >
              {"Save"}
            </button>
          </div>
        </div>
      )}

      {/* ── Preview Iframe ── */}
      <iframe
        srcDoc={annotatedHtml}
        sandbox=""
        title="Email preview with translation overlay"
        className="h-full w-full border-0 bg-white"
      />
    </div>
  );
}
