"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Awareness } from "y-protocols/awareness";
import type { Collaborator, FollowTarget, ActivityState } from "@/types/collaboration";
import {
  getEnrichedCollaborators,
  setLocalActivity,
  setLocalCursorState,
} from "@/lib/collaboration/awareness";

const ACTIVITY_POLL_MS = 15_000;

interface UsePresenceOptions {
  awareness: Awareness | null;
  role: string;
}

interface UsePresenceReturn {
  collaborators: Collaborator[];
  followTarget: FollowTarget | null;
  startFollowing: (clientId: number, name: string) => void;
  stopFollowing: () => void;
  reportCursorMove: (
    cursor: { line: number; col: number },
    selection: { anchor: number; head: number } | null,
  ) => void;
}

export function usePresence({ awareness, role }: UsePresenceOptions): UsePresenceReturn {
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [followTarget, setFollowTarget] = useState<FollowTarget | null>(null);
  const roleRef = useRef(role);
  roleRef.current = role;

  // Listen to awareness changes
  useEffect(() => {
    if (!awareness) return;

    const update = () => setCollaborators(getEnrichedCollaborators(awareness));
    awareness.on("change", update);
    update();

    // Poll for idle transitions (since they're time-based)
    const interval = setInterval(update, ACTIVITY_POLL_MS);

    return () => {
      awareness.off("change", update);
      clearInterval(interval);
    };
  }, [awareness]);

  // Set initial activity based on role
  useEffect(() => {
    if (!awareness) return;
    const activity: ActivityState = roleRef.current === "viewer" ? "viewing" : "editing";
    setLocalActivity(awareness, activity);
  }, [awareness]);

  const reportCursorMove = useCallback(
    (
      cursor: { line: number; col: number },
      selection: { anchor: number; head: number } | null,
    ) => {
      if (!awareness) return;
      setLocalCursorState(awareness, cursor, selection);
    },
    [awareness],
  );

  const startFollowing = useCallback((clientId: number, name: string) => {
    setFollowTarget({ clientId, name });
  }, []);

  const stopFollowing = useCallback(() => {
    setFollowTarget(null);
  }, []);

  // Clear follow target if the followed user disconnects
  useEffect(() => {
    if (!followTarget) return;
    const found = collaborators.some((c) => c.clientId === followTarget.clientId);
    if (!found) setFollowTarget(null);
  }, [collaborators, followTarget]);

  return { collaborators, followTarget, startFollowing, stopFollowing, reportCursorMove };
}
