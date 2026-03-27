"use client";

import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";

/**
 * Message shape pushed by the backend when a Figma webhook triggers a design sync.
 */
interface DesignSyncUpdate {
  type: "design_sync_update";
  connection_id: number;
  diff_summary: string;
  total_changes: number;
  preview_url: string | null;
  timestamp: string;
}

/**
 * Subscribe to live design sync updates via the collaboration WebSocket.
 *
 * When a Figma FILE_UPDATE webhook triggers a token re-sync, the backend
 * broadcasts a `design_sync_update` message to the project room. This hook
 * listens for those messages and shows a toast notification.
 *
 * @param connectionId - The design connection ID to watch (null to disable).
 * @param onUpdate     - Optional callback invoked with the update payload.
 */
export function useDesignSyncLive(
  connectionId: number | null,
  onUpdate?: (update: DesignSyncUpdate) => void,
) {
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      if (!connectionId) return;

      let data: DesignSyncUpdate;
      try {
        data =
          typeof event.data === "string"
            ? (JSON.parse(event.data) as DesignSyncUpdate)
            : (event.data as DesignSyncUpdate);
      } catch {
        return; // Not JSON — ignore (binary Yjs sync frames, etc.)
      }

      if (data.type !== "design_sync_update") return;
      if (data.connection_id !== connectionId) return;

      // Debounce rapid updates (300ms)
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        toast.info(`Design updated — ${data.diff_summary}`);
        onUpdateRef.current?.(data);
      }, 300);
    },
    [connectionId],
  );

  useEffect(() => {
    if (!connectionId) return;

    // Listen on the global "design-sync-update" custom event dispatched by
    // the collaboration WebSocket handler when it receives a JSON message
    // with type === "design_sync_update".
    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      clearTimeout(debounceRef.current);
    };
  }, [connectionId, handleMessage]);
}
