"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

// ── Types ──

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface EmailBrief {
  topic: string;
  sections: Array<{ type: string; description: string; content_hints: string[] }>;
  tone: string;
  cta_text: string | null;
  audience: string | null;
  constraints: string[];
}

type VoiceBriefStatus = "pending" | "transcribed" | "extracted" | "failed";

interface VoiceBriefSummary {
  id: number;
  project_id: number;
  status: VoiceBriefStatus;
  media_type: string;
  submitted_by: string;
  confidence: number | null;
  brief_topic: string | null;
  duration_seconds: number | null;
  created_at: string;
}

interface VoiceBriefDetail extends VoiceBriefSummary {
  transcript_text: string | null;
  transcript_segments: TranscriptSegment[];
  brief: EmailBrief | null;
}

interface VoiceBriefListResponse {
  items: VoiceBriefSummary[];
  total: number;
  page: number;
  page_size: number;
}

// ── Hooks ──

/** List voice briefs for a project (newest first) */
export function useVoiceBriefs(projectId: number | null, page = 1) {
  const interval = useSmartPolling(POLL.status);
  const key = projectId
    ? `/api/v1/projects/${projectId}/voice-briefs?page=${page}&page_size=20`
    : null;

  return useSWR<VoiceBriefListResponse>(key, fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
}

/** Single voice brief with full transcript + extracted brief */
export function useVoiceBrief(projectId: number | null, briefId: number | null) {
  const key = projectId && briefId ? `/api/v1/projects/${projectId}/voice-briefs/${briefId}` : null;

  return useSWR<VoiceBriefDetail>(key, fetcher, {
    revalidateOnFocus: false,
  });
}

/** Audio playback URL (returns streaming endpoint path) */
export function voiceBriefAudioUrl(projectId: number, briefId: number): string {
  return `/api/v1/projects/${projectId}/voice-briefs/${briefId}/audio`;
}

/** Trigger blueprint run from a voice brief */
export function useGenerateFromBrief(projectId: number | null) {
  const key = projectId ? `/api/v1/projects/${projectId}/voice-briefs/generate` : null;

  return useSWRMutation<
    Record<string, unknown>,
    Error,
    string | null,
    { brief_id: number; blueprint_name?: string; persona_ids?: number[]; template_id?: number }
  >(key, longMutationFetcher);
}

/** Dismiss / archive a voice brief */
export function useDeleteVoiceBrief(projectId: number | null) {
  return useSWRMutation<void, Error, string | null, { brief_id: number }>(
    projectId ? `/api/v1/projects/${projectId}/voice-briefs/delete` : null,
    async (url: string, { arg }: { arg: { brief_id: number } }) => {
      if (!projectId) return;
      const { authFetch } = await import("@/lib/auth-fetch");
      const res = await authFetch(`/api/v1/projects/${projectId}/voice-briefs/${arg.brief_id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete voice brief");
    },
  );
}

export type {
  VoiceBriefSummary,
  VoiceBriefDetail,
  VoiceBriefStatus,
  EmailBrief,
  TranscriptSegment,
};
