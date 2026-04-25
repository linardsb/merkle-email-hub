/** Frontend DesignSystem type matching the API response */
export interface DesignSystemConfig {
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
    link: string;
    dark_background: string | null;
    dark_text: string | null;
  };
  typography: {
    heading_font: string;
    body_font: string;
    base_size: string;
  };
  colors: Record<string, string>;
  fonts: Record<string, string>;
  font_sizes: Record<string, string>;
  spacing: Record<string, string>;
  button_border_radius: string;
  button_style: "filled" | "outlined" | "text";
}

/** Helper to extract palette swatches from a DesignSystemConfig */
export function extractPaletteSwatches(ds: DesignSystemConfig): { role: string; hex: string }[] {
  const swatches: { role: string; hex: string }[] = [];

  // Add named palette roles
  const { palette } = ds;
  for (const [role, hex] of Object.entries(palette)) {
    if (hex) swatches.push({ role, hex });
  }

  // Add extra colors from the colors map
  for (const [role, hex] of Object.entries(ds.colors)) {
    if (hex && !swatches.some((s) => s.hex === hex)) {
      swatches.push({ role, hex });
    }
  }

  return swatches;
}
