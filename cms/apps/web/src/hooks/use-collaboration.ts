"use client";

import { useEffect, useMemo, useRef, useState, startTransition } from "react";
import * as Y from "yjs";
import type { Awareness } from "y-protocols/awareness";
import type { CollaborationStatus, Collaborator } from "@/types/collaboration";

const USER_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#f43f16"];

function pickColor(clientId: number): string {
  return USER_COLORS[clientId % USER_COLORS.length]!;
}

export function useCollaboration(projectId: number, templateId: number | null) {
  const providerRef = useRef<unknown>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<CollaborationStatus>("disconnected");
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [yText, setYText] = useState<Y.Text | null>(null);
  const [doc, setDoc] = useState<Y.Doc | null>(null);
  const [awareness, setAwareness] = useState<Awareness | null>(null);

  // Create stable room name
  const roomName = useMemo(
    () => (templateId ? `project-${projectId}-template-${templateId}` : null),
    [projectId, templateId],
  );

  useEffect(() => {
    if (!roomName) return;

    let cancelled = false;
    const ydoc = new Y.Doc();
    setDoc(ydoc);
    setYText(ydoc.getText("content"));

    // Production mode: Hub-authenticated WebSocket provider
    import("@/lib/collaboration/yjs-provider")
      .then(({ createHubProvider }) => {
        if (cancelled) return;
        // TODO(24.2): Retrieve JWT token from session for auth
        const token = "";
        const provider = createHubProvider(roomName, ydoc, { token });
        providerRef.current = provider;

        provider.on("status", ({ status: s }: { status: string }) => {
          if (s === "connected") setStatus("connected");
          else if (s === "connecting") setStatus("connecting");
          else setStatus("disconnected");
        });

        setAwareness(provider.awareness);

        provider.awareness.setLocalState({
          name: "You",
          color: pickColor(ydoc.clientID),
        });

        const updateCollaborators = () => {
          const states = provider.awareness.getStates();
          const collabs: Collaborator[] = [];
          states.forEach((state: Record<string, unknown>, clientId: number) => {
            if (clientId === ydoc.clientID) return;
            if (state?.name) {
              collabs.push({
                clientId,
                name: state.name as string,
                color: (state.color as string) ?? pickColor(clientId),
                role: (state.role as string) ?? "developer",
                cursor: state.cursor as Collaborator["cursor"],
                selection: (state.selection as Collaborator["selection"]) ?? null,
                activity: (state.activity as Collaborator["activity"]) ?? "editing",
                lastActiveAt: (state.lastActiveAt as number) ?? Date.now(),
              });
            }
          });
          queueMicrotask(() => {
            startTransition(() => setCollaborators(collabs));
          });
        };

        provider.awareness.on("change", updateCollaborators);
      })
      .catch(() => {
        // WebSocket provider unavailable — stay disconnected, editor works in single-user mode
        if (!cancelled) {
          setStatus("disconnected");
        }
      });

    return () => {
      cancelled = true;
      cleanupRef.current?.();
      if (providerRef.current) {
        (providerRef.current as { destroy(): void }).destroy();
        providerRef.current = null;
      }
      ydoc.destroy();
      setDoc(null);
      setAwareness(null);
      setYText(null);
      setStatus("disconnected");
      setCollaborators([]);
    };
  }, [roomName]);

  return { status, collaborators, yText, doc, awareness };
}
