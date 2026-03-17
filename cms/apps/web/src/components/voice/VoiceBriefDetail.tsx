"use client";

import { useCallback, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Play, Pause, Sparkles, Trash2, Clock, User, BarChart3,
} from "lucide-react";
import { toast } from "sonner";
import { mutate } from "swr";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@email-hub/ui/components/ui/dialog";
import {
  useVoiceBrief,
  useGenerateFromBrief,
  useDeleteVoiceBrief,
  voiceBriefAudioUrl,
} from "@/hooks/use-voice-briefs";
import type { TranscriptSegment } from "@/hooks/use-voice-briefs";

interface VoiceBriefDetailProps {
  projectId: number;
  briefId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function VoiceBriefDetail({
  projectId,
  briefId,
  open,
  onOpenChange,
}: VoiceBriefDetailProps) {
  const t = useTranslations("voiceBriefs");
  const { data: brief, isLoading } = useVoiceBrief(projectId, briefId);
  const { trigger: generate, isMutating: isGenerating } = useGenerateFromBrief(projectId);
  const { trigger: deleteBrief } = useDeleteVoiceBrief(projectId);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const togglePlayback = useCallback(() => {
    if (!audioRef.current) return;
    if (isPlaying) audioRef.current.pause();
    else void audioRef.current.play();
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const handleGenerate = async () => {
    const result = await generate({ brief_id: briefId });
    if (result) {
      toast.success(t("generateStarted"));
      onOpenChange(false);
      void mutate((key: string) => typeof key === "string" && key.includes("blueprint-runs"));
    }
  };

  const handleDelete = async () => {
    await deleteBrief({ brief_id: briefId });
    toast.success(t("briefDismissed"));
    void mutate((key: string) => typeof key === "string" && key.includes("voice-briefs"));
    onOpenChange(false);
  };

  const isSegmentActive = (seg: TranscriptSegment) =>
    currentTime >= seg.start && currentTime < seg.end;

  const audioSrc = voiceBriefAudioUrl(projectId, briefId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            {brief?.brief?.topic ?? t("voiceBrief")}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col gap-3 py-4">
            <div className="h-4 w-3/4 animate-pulse rounded bg-skeleton" />
            <div className="h-20 animate-pulse rounded bg-skeleton" />
            <div className="h-32 animate-pulse rounded bg-skeleton" />
          </div>
        ) : brief ? (
          <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto py-2">
            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {brief.submitted_by}
              </span>
              {brief.duration_seconds != null && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {Math.floor(brief.duration_seconds / 60)}:{String(Math.round(brief.duration_seconds % 60)).padStart(2, "0")}
                </span>
              )}
              {brief.confidence != null && (
                <span className="flex items-center gap-1">
                  <BarChart3 className="h-3 w-3" />
                  {t("confidence")}: {Math.round(brief.confidence * 100)}%
                </span>
              )}
            </div>

            {/* Audio player */}
            <div className="flex items-center gap-2">
              <audio
                ref={audioRef}
                src={audioSrc}
                onTimeUpdate={() => {
                  if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
                }}
                onEnded={() => setIsPlaying(false)}
              />
              <button
                type="button"
                onClick={togglePlayback}
                className="flex items-center gap-2 rounded px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                {isPlaying ? t("pause") : t("playAudio")}
              </button>
            </div>

            {/* Transcript with segment highlighting */}
            {brief.transcript_text && (
              <div className="rounded-md border border-default bg-surface-muted p-3">
                <p className="mb-1 text-xs font-medium text-muted-foreground">{t("transcript")}</p>
                <div className="text-sm leading-relaxed text-foreground">
                  {brief.transcript_segments.length > 0
                    ? brief.transcript_segments.map((seg, i) => (
                        <span
                          key={i}
                          className={`transition-colors ${isSegmentActive(seg) ? "rounded bg-interactive/20 px-0.5" : ""}`}
                        >
                          {seg.text}{" "}
                        </span>
                      ))
                    : brief.transcript_text}
                </div>
              </div>
            )}

            {/* Extracted brief */}
            {brief.brief && (
              <div className="rounded-md border border-default bg-surface-muted p-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground">{t("extractedBrief")}</p>
                <div className="grid gap-2 text-xs">
                  <div>
                    <span className="font-medium text-foreground">{t("briefTopic")}:</span>{" "}
                    <span className="text-muted-foreground">{brief.brief.topic}</span>
                  </div>
                  <div>
                    <span className="font-medium text-foreground">{t("briefTone")}:</span>{" "}
                    <span className="text-muted-foreground">{brief.brief.tone}</span>
                  </div>
                  {brief.brief.cta_text && (
                    <div>
                      <span className="font-medium text-foreground">{t("briefCta")}:</span>{" "}
                      <span className="text-muted-foreground">{brief.brief.cta_text}</span>
                    </div>
                  )}
                  {brief.brief.audience && (
                    <div>
                      <span className="font-medium text-foreground">{t("briefAudience")}:</span>{" "}
                      <span className="text-muted-foreground">{brief.brief.audience}</span>
                    </div>
                  )}
                  <div>
                    <span className="font-medium text-foreground">{t("briefSections")}:</span>
                    <ul className="ml-4 mt-1 list-disc text-muted-foreground">
                      {brief.brief.sections.map((s, i) => (
                        <li key={i}>
                          <span className="font-medium">{s.type}</span>: {s.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {brief.brief.constraints.length > 0 && (
                    <div>
                      <span className="font-medium text-foreground">{t("briefConstraints")}:</span>
                      <ul className="ml-4 mt-1 list-disc text-muted-foreground">
                        {brief.brief.constraints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : null}

        <DialogFooter className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={handleDelete}
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-status-danger"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t("dismiss")}
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              {t("close")}
            </button>
            {brief?.status === "extracted" && (
              <button
                type="button"
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex items-center gap-2 rounded-md px-4 py-1.5 text-xs font-medium bg-interactive text-foreground-inverse hover:bg-interactive/90 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {isGenerating ? t("generating") : t("generateEmail")}
              </button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
