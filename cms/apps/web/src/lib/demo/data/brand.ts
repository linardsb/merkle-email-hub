import type { BrandConfig } from "@/types/brand";

export const DEMO_BRAND_CONFIG: Record<number, BrandConfig> = {
  1: {
    org_id: 1,
    colors: [
      { name: "Primary", hex: "#538FE4" },
      { name: "Secondary", hex: "#6C63FF" },
      { name: "Dark", hex: "#1A1A2E" },
      { name: "Light", hex: "#F8F9FA" },
    ],
    typography: [
      {
        family: "Inter",
        weights: ["400", "500", "600", "700"],
        minSize: 12,
        maxSize: 48,
      },
    ],
    logoRules: {
      minWidth: 120,
      minHeight: 40,
      clearSpace: 16,
      allowedFormats: ["png", "svg"],
    },
    forbiddenPatterns: [
      {
        id: "fp-1",
        pattern: "font-family:\\s*['\"]?Comic Sans",
        description: "Comic Sans is not an approved brand font",
      },
      {
        id: "fp-2",
        pattern: "color:\\s*#ff0000",
        description: "Pure red (#ff0000) is not an approved brand color",
      },
    ],
    updated_at: "2026-02-28T14:30:00Z",
  },
};
