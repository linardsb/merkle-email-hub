export interface BrandColor {
  name: string;
  hex: string;
}

export interface BrandTypography {
  family: string;
  weights: string[];
  minSize: number;
  maxSize: number;
}

export interface BrandLogoRule {
  minWidth: number;
  minHeight: number;
  clearSpace: number;
  allowedFormats: string[];
}

export interface ForbiddenPattern {
  id: string;
  pattern: string;
  description: string;
}

export interface BrandConfig {
  org_id: number;
  colors: BrandColor[];
  typography: BrandTypography[];
  logoRules: BrandLogoRule | null;
  forbiddenPatterns: ForbiddenPattern[];
  updated_at: string;
}

export interface BrandViolation {
  type: "color" | "font" | "pattern";
  message: string;
  from: number;
  to: number;
}
