"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { ExportHistoryRecord } from "@/types/connectors";

const STORAGE_KEY = "merkle-export-history";
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

function getSnapshot(): ExportHistoryRecord[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === cachedRaw) return cachedParsed;
    cachedRaw = raw;
    cachedParsed = raw ? (JSON.parse(raw) as ExportHistoryRecord[]) : EMPTY;
    return cachedParsed;
  } catch {
    return EMPTY;
  }
}

function getServerSnapshot(): ExportHistoryRecord[] {
  return EMPTY;
}

let demoSeeded = false;

function seedDemoData() {
  if (demoSeeded) return;
  demoSeeded = true;

  try {
    const existing = sessionStorage.getItem(STORAGE_KEY);
    if (existing) return; // Already has data

    // Lazy import to avoid bundling demo data in production
    import("@/lib/demo/data/connectors").then(({ DEMO_EXPORT_HISTORY }) => {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(DEMO_EXPORT_HISTORY));
      cachedRaw = null; // Invalidate cache
      cachedParsed = EMPTY;
      notifyListeners();
    });
  } catch {
    // sessionStorage not available (SSR)
  }
}

export function useExportHistory() {
  // Seed demo data on first client-side mount
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    seedDemoData();
  }

  const records = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addRecord = useCallback((record: ExportHistoryRecord) => {
    const current = getSnapshot();
    const updated = [record, ...current].slice(0, MAX_RECORDS);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    notifyListeners();
  }, []);

  const updateRecord = useCallback(
    (localId: string, updates: Partial<ExportHistoryRecord>) => {
      const current = getSnapshot();
      const updated = current.map((r) =>
        r.local_id === localId ? { ...r, ...updates } : r
      );
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      notifyListeners();
    },
    []
  );

  return { records, addRecord, updateRecord };
}
