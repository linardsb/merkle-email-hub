"use client";

import { Download, ImagePlus } from "../../icons";
import type { GeneratedImage } from "@/types/image-gen";

interface ImagePreviewCardProps {
  image: GeneratedImage;
  onInsert: (image: GeneratedImage) => void;
}

export function ImagePreviewCard({ image, onInsert }: ImagePreviewCardProps) {
  const createdDate = new Date(image.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <div className="group rounded-md border border-card-border bg-card-bg overflow-hidden">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.url}
        alt={image.prompt}
        className="aspect-square w-full object-cover"
        loading="lazy"
      />
      <div className="p-2">
        <p className="text-xs text-foreground line-clamp-2">{image.prompt}</p>
        <div className="mt-1 flex items-center justify-between text-xs text-foreground-muted">
          <span>{createdDate}</span>
          <span>{image.style}</span>
        </div>
        <div className="mt-2 flex gap-1">
          <button
            type="button"
            onClick={() => onInsert(image)}
            className="flex flex-1 items-center justify-center gap-1 rounded border border-border px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            <ImagePlus className="h-3 w-3" />
            {"Insert"}
          </button>
          <a
            href={image.url}
            download
            className="flex items-center justify-center rounded border border-border px-2 py-1 text-xs text-foreground-muted transition-colors hover:bg-surface-hover"
          >
            <Download className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
