"use client";

import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { ImagePreviewCard } from "./image-preview-card";
import type { GeneratedImage } from "@/types/image-gen";

interface ImageGalleryProps {
  images: GeneratedImage[] | undefined;
  isLoading: boolean;
  onInsert: (image: GeneratedImage) => void;
}

export function ImageGallery({ images, isLoading, onInsert }: ImageGalleryProps) {
  const t = useTranslations("imageGen");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        {t("galleryEmpty")}
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {images.map((image) => (
        <ImagePreviewCard key={image.id} image={image} onInsert={onInsert} />
      ))}
    </div>
  );
}
