"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X } from "../icons";

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
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    (file: File) => {
      setError(null);

      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError("Invalid format. Use PNG, JPEG, or WebP.");
        return;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setError("File too large. Maximum size is 10MB.");
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
    [onImageSelected],
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
      <div className="border-default bg-card relative rounded-lg border p-2">
        <img
          src={`data:image/png;base64,${currentImage}`}
          alt={"Design Reference"}
          className="max-h-40 w-full rounded object-contain"
        />
        <button
          type="button"
          onClick={onClear}
          className="bg-surface text-muted-foreground hover:text-foreground absolute right-1 top-1 rounded-full p-1 shadow-sm"
        >
          <X className="h-3.5 w-3.5" />
        </button>
        <p className="text-muted-foreground mt-1 text-center text-xs">
          {"Design reference attached"}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragActive
            ? "border-interactive bg-interactive/5"
            : "border-border hover:border-interactive/50 hover:bg-surface-muted"
        }`}
      >
        <Upload className="text-muted-foreground h-6 w-6" />
        <p className="text-muted-foreground text-xs">
          {"Drop a design screenshot or click to upload"}
        </p>
        <p className="text-muted-foreground/60 text-xs">{"PNG, JPEG, or WebP — max 10MB"}</p>
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
      {error && <p className="text-status-danger text-xs">{error}</p>}
    </div>
  );
}
