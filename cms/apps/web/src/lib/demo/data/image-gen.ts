import type { GeneratedImage } from "@/types/image-gen";

function svgPlaceholder(w: number, h: number, bg: string, fg: string, text: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect fill="${bg}" width="${w}" height="${h}"/><text fill="${fg}" font-family="system-ui,sans-serif" font-size="24" font-weight="600" text-anchor="middle" dominant-baseline="central" x="${w / 2}" y="${h / 2}">${text}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export const DEMO_GENERATED_IMAGES: Record<number, GeneratedImage[]> = {
  1: [
    {
      id: 1,
      url: svgPlaceholder(600, 400, "#1a5276", "#ffffff", "Spring Hero Banner"),
      prompt: "Modern email hero banner with spring flowers",
      style: "lifestyle",
      aspect_ratio: "4:3",
      width: 600,
      height: 400,
      created_at: "2026-03-01T10:00:00Z",
    },
    {
      id: 2,
      url: svgPlaceholder(600, 600, "#f5f5f5", "#333333", "Product Shot"),
      prompt: "Professional product photography on white background",
      style: "product",
      aspect_ratio: "1:1",
      width: 600,
      height: 600,
      created_at: "2026-03-01T11:00:00Z",
    },
    {
      id: 3,
      url: svgPlaceholder(800, 400, "#4a148c", "#e1bee7", "Abstract Gradient"),
      prompt: "Abstract gradient background blue and purple",
      style: "abstract",
      aspect_ratio: "16:9",
      width: 800,
      height: 400,
      created_at: "2026-02-28T14:00:00Z",
    },
    {
      id: 4,
      url: svgPlaceholder(600, 400, "#2e7d32", "#c8e6c9", "Sale Banner"),
      prompt: "Summer sale promotional banner with bold typography",
      style: "lifestyle",
      aspect_ratio: "4:3",
      width: 600,
      height: 400,
      created_at: "2026-02-28T15:00:00Z",
    },
  ],
};
