export type ImageGenStatus = "idle" | "generating" | "completed" | "error";

export type StylePreset = "product" | "lifestyle" | "abstract";

export type AspectRatio = "4:3" | "16:9" | "1:1";

export interface ImageGenRequest {
  prompt: string;
  style: StylePreset;
  aspect_ratio: AspectRatio;
  project_id: number;
}

export interface GeneratedImage {
  id: number;
  url: string;
  prompt: string;
  style: StylePreset;
  aspect_ratio: AspectRatio;
  width: number;
  height: number;
  created_at: string;
}

export interface ImageGenResponse {
  image: GeneratedImage;
}
