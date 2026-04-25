"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { ExportHistoryRecord } from "@/types/connectors";

const STORAGE_KEY = "email-hub-export-history";
const MAX_RECORDS = 100;

const listeners = new Set<() => void>();
const EMPTY: ExportHistoryRecord[] = [];

let cachedRaw: string | null = null;
let cachedParsed: ExportHistoryRecord[] = EMPTY;

function notifyListeners() {
  for (const listener of listeners) {
    listener();
  }
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function isValidRecord(item: unknown): item is ExportHistoryRecord {
  if (typeof item !== "object" || item === null) return false;
  const r = item as Record<string, unknown>;
  return (
    typeof r.local_id === "string" &&
    typeof r.platform === "string" &&
    typeof r.name === "string" &&
    typeof r.status === "string" &&
    typeof r.created_at === "string"
  );
}

function getSnapshot(): ExportHistoryRecord[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === cachedRaw) return cachedParsed;
    cachedRaw = raw;
    if (!raw) {
      cachedParsed = EMPTY;
      return cachedParsed;
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      cachedParsed = EMPTY;
      return cachedParsed;
    }
    cachedParsed = parsed.filter(isValidRecord);
    return cachedParsed;
  } catch {
    return EMPTY;
  }
}

function getServerSnapshot(): ExportHistoryRecord[] {
  return EMPTY;
}

export function useExportHistory() {
  const records = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addRecord = useCallback((record: ExportHistoryRecord) => {
    const current = getSnapshot();
    const updated = [record, ...current].slice(0, MAX_RECORDS);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    notifyListeners();
  }, []);

  const updateRecord = useCallback((localId: string, updates: Partial<ExportHistoryRecord>) => {
    const current = getSnapshot();
    const updated = current.map((r) => (r.local_id === localId ? { ...r, ...updates } : r));
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    notifyListeners();
  }, []);

  return { records, addRecord, updateRecord };
}
