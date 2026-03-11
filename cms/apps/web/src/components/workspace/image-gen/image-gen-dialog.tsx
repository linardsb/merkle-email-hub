"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useGenerateImage, useProjectImages } from "@/hooks/use-image-gen";
import { StylePresetGrid } from "./style-preset-grid";
import { ImageGallery } from "./image-gallery";
import type { StylePreset, GeneratedImage } from "@/types/image-gen";

interface ImageGenDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  onInsertImage: (url: string, width: number, height: number, alt: string) => void;
}

export function ImageGenDialog({
  open,
  onOpenChange,
  projectId,
  onInsertImage,
}: ImageGenDialogProps) {
  const t = useTranslations("imageGen");
  const { trigger, isMutating } = useGenerateImage();
  const { data: gallery, isLoading: galleryLoading } = useProjectImages(open ? projectId : null);
  const { mutate } = useSWRConfig();

  const [activeTab, setActiveTab] = useState<"generate" | "gallery">("generate");
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState<StylePreset>("product");

  // Reset on open
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setPrompt("");
    setStyle("product");
    setActiveTab("generate");
  }
  if (open !== prevOpen) setPrevOpen(open);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    try {
      const result = await trigger({
        prompt: prompt.trim(),
        style,
        aspect_ratio: "4:3",
        project_id: projectId,
      });
      if (result?.image) {
        toast.success(t("generateSuccess"));
        setActiveTab("gallery");
        await mutate(
          (key: unknown) => typeof key === "string" && key.includes("/images"),
          undefined,
          { revalidate: true },
        );
      }
    } catch {
      toast.error(t("generateError"));
    }
  };

  const handleInsert = (image: GeneratedImage) => {
    onInsertImage(image.url, image.width, image.height, image.prompt);
    onOpenChange(false);
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[40rem]">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            type="button"
            onClick={() => setActiveTab("generate")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "generate"
                ? "border-b-2 border-interactive text-foreground"
                : "text-foreground-muted hover:text-foreground"
            }`}
          >
            {t("tabGenerate")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("gallery")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "gallery"
                ? "border-b-2 border-interactive text-foreground"
                : "text-foreground-muted hover:text-foreground"
            }`}
          >
            {t("tabGallery")}
          </button>
        </div>

        {activeTab === "generate" ? (
          <div className="space-y-4">
            {/* Prompt */}
            <div>
              <label htmlFor="img-prompt" className="mb-1.5 block text-sm font-medium text-foreground">
                {t("promptLabel")}
              </label>
              <textarea
                id="img-prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={t("promptPlaceholder")}
                rows={3}
                disabled={isMutating}
                className={inputClass}
              />
            </div>

            {/* Style Presets */}
            <div>
              <p className="mb-1.5 text-sm font-medium text-foreground">{t("styleLabel")}</p>
              <StylePresetGrid selected={style} onSelect={setStyle} />
            </div>

            {/* Generate button */}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={!prompt.trim() || isMutating}
                className="rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
              >
                {isMutating ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("generating")}
                  </span>
                ) : (
                  t("generate")
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="max-h-96 overflow-y-auto">
            <ImageGallery
              images={gallery}
              isLoading={galleryLoading}
              onInsert={handleInsert}
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
