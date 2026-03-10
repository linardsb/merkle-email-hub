import type { GeneratedImage } from "@/types/image-gen";

export const DEMO_GENERATED_IMAGES: Record<number, GeneratedImage[]> = {
  1: [
    {
      id: 1,
      url: "https://placehold.co/600x400/1a5276/ffffff?text=Spring+Hero+Banner",
      prompt: "Modern email hero banner with spring flowers",
      style: "lifestyle",
      aspect_ratio: "4:3",
      width: 600,
      height: 400,
      created_at: "2026-03-01T10:00:00Z",
    },
    {
      id: 2,
      url: "https://placehold.co/600x600/f5f5f5/333333?text=Product+Shot",
      prompt: "Professional product photography on white background",
      style: "product",
      aspect_ratio: "1:1",
      width: 600,
      height: 600,
      created_at: "2026-03-01T11:00:00Z",
    },
    {
      id: 3,
      url: "https://placehold.co/800x400/4a148c/e1bee7?text=Abstract+Gradient",
      prompt: "Abstract gradient background blue and purple",
      style: "abstract",
      aspect_ratio: "16:9",
      width: 800,
      height: 400,
      created_at: "2026-02-28T14:00:00Z",
    },
    {
      id: 4,
      url: "https://placehold.co/600x400/2e7d32/c8e6c9?text=Sale+Banner",
      prompt: "Summer sale promotional banner with bold typography",
      style: "lifestyle",
      aspect_ratio: "4:3",
      width: 600,
      height: 400,
      created_at: "2026-02-28T15:00:00Z",
    },
  ],
};
