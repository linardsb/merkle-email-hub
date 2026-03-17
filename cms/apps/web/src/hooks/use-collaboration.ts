"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as Y from "yjs";
import type { Awareness } from "y-protocols/awareness";
import type {
  CollaborationStatus,
  Collaborator,
} from "@/types/collaboration";

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const USER_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#f43f16"];

function pickColor(clientId: number): string {
  return USER_COLORS[clientId % USER_COLORS.length]!;
}

export function useCollaboration(projectId: number, templateId: number | null) {
  const docRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<unknown>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<CollaborationStatus>("disconnected");
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [yText, setYText] = useState<Y.Text | null>(null);

  // Create stable room name
  const roomName = useMemo(
    () => (templateId ? `project-${projectId}-template-${templateId}` : null),
    [projectId, templateId],
  );

  useEffect(() => {
    if (!roomName) return;

    const doc = new Y.Doc();
    docRef.current = doc;
    setYText(doc.getText("content"));

    if (IS_DEMO) {
      // Demo mode: no WebSocket, use in-memory doc
      setStatus("connected");

      let awarenessInstance: Awareness | null = null;

      // Set local awareness state (async IIFE for dynamic import)
      (async () => {
        const { Awareness } = await import("y-protocols/awareness");
        const awareness = new Awareness(doc);
        awarenessInstance = awareness;

        awareness.setLocalState({
          name: "You",
          color: pickColor(doc.clientID),
        });

        // Start demo collaborator simulation
        const { startDemoCollaborator } = await import("@/lib/collaboration/demo-provider");
        cleanupRef.current = startDemoCollaborator(awareness);

        // Listen for awareness changes
        const updateCollaborators = () => {
          const states = awareness.getStates();
          const collabs: Collaborator[] = [];

          states.forEach((state, clientId) => {
            if (clientId === doc.clientID) return; // Skip self

            // Check for demo collaborators embedded in local state
            const demoCollabs = state?.demoCollaborators as Collaborator[] | undefined;
            if (demoCollabs) {
              collabs.push(...demoCollabs);
            }
          });

          // Also check own state for demo collaborators
          const localState = awareness.getLocalState();
          const demoCollabs = localState?.demoCollaborators as Collaborator[] | undefined;
          if (demoCollabs) {
            collabs.push(...demoCollabs);
          }

          setCollaborators(collabs);
        };

        awareness.on("change", updateCollaborators);
      })();

      return () => {
        cleanupRef.current?.();
        awarenessInstance?.destroy();
        doc.destroy();
        docRef.current = null;
        setYText(null);
        setStatus("disconnected");
        setCollaborators([]);
      };
    }

    // Production mode: WebSocket provider
    import("@/lib/collaboration/yjs-provider").then(
      ({ createWebSocketProvider }) => {
        const provider = createWebSocketProvider(roomName, doc);
        providerRef.current = provider;

        provider.on("status", ({ status: s }: { status: string }) => {
          if (s === "connected") setStatus("connected");
          else if (s === "connecting") setStatus("connecting");
          else setStatus("disconnected");
        });

        provider.awareness.setLocalState({
          name: "You",
          color: pickColor(doc.clientID),
        });

        const updateCollaborators = () => {
          const states = provider.awareness.getStates();
          const collabs: Collaborator[] = [];
          states.forEach((state, clientId) => {
            if (clientId === doc.clientID) return;
            if (state?.name) {
              collabs.push({
                clientId,
                name: state.name as string,
                color: (state.color as string) ?? pickColor(clientId),
                cursor: state.cursor as Collaborator["cursor"],
              });
            }
          });
          setCollaborators(collabs);
        };

        provider.awareness.on("change", updateCollaborators);
      },
    );

    return () => {
      cleanupRef.current?.();
      if (providerRef.current) {
        (providerRef.current as { destroy(): void }).destroy();
        providerRef.current = null;
      }
      doc.destroy();
      docRef.current = null;
      setYText(null);
      setStatus("disconnected");
      setCollaborators([]);
    };
  }, [roomName]);

  return { status, collaborators, yText, doc: docRef.current };
}
