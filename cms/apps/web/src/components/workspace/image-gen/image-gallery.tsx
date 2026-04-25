"use client";

import { Loader2 } from "../../icons";
import { ImagePreviewCard } from "./image-preview-card";
import type { GeneratedImage } from "@/types/image-gen";

interface ImageGalleryProps {
  images: GeneratedImage[] | undefined;
  isLoading: boolean;
  onInsert: (image: GeneratedImage) => void;
}

export function ImageGallery({ images, isLoading, onInsert }: ImageGalleryProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="text-foreground-muted h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <p className="text-foreground-muted py-8 text-center text-sm">
        {"No generated images yet. Generate your first image above."}
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
