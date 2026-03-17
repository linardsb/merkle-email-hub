"use client";

import { useCallback, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Upload, X } from "lucide-react";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

interface DesignReferenceUploadProps {
  onImageSelected: (base64: string, mediaType: string) => void;
  onClear: () => void;
  currentImage: string | null;
}

export function DesignReferenceUpload({
  onImageSelected,
  onClear,
  currentImage,
}: DesignReferenceUploadProps) {
  const t = useTranslations("designReference");
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    (file: File) => {
      setError(null);

      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError(t("invalidFormat"));
        return;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setError(t("fileTooLarge"));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1];
        if (base64) onImageSelected(base64, file.type);
      };
      reader.readAsDataURL(file);
    },
    [onImageSelected, t],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  if (currentImage) {
    return (
      <div className="relative rounded-lg border border-default bg-card p-2">
        <img
          src={`data:image/png;base64,${currentImage}`}
          alt={t("designReference")}
          className="max-h-40 w-full rounded object-contain"
        />
        <button
          type="button"
          onClick={onClear}
          className="absolute right-1 top-1 rounded-full bg-surface p-1 text-muted-foreground shadow-sm hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
        <p className="mt-1 text-center text-xs text-muted-foreground">{t("referenceAttached")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragActive
            ? "border-interactive bg-interactive/5"
            : "border-border hover:border-interactive/50 hover:bg-surface-muted"
        }`}
      >
        <Upload className="h-6 w-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">{t("dropzoneLabel")}</p>
        <p className="text-xs text-muted-foreground/60">{t("acceptedFormats")}</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) processFile(file);
          }}
          className="hidden"
        />
      </div>
      {error && <p className="text-xs text-status-danger">{error}</p>}
    </div>
  );
}
