import type { ComponentResponse, VersionResponse, ComponentCompatibilityResponse, ClientCompatibility } from "@email-hub/sdk";
import { DEMO_EMAIL_CLIENTS } from "./email-clients";

const COMPAT_FULL: Record<string, string> = {
  gmail: "full",
  outlook_365: "full",
  outlook_2019: "full",
  apple_mail: "full",
  ios_mail: "full",
  yahoo: "full",
  samsung_mail: "full",
  outlook_com: "full",
};

const COMPAT_PARTIAL_SAMSUNG: Record<string, string> = {
  ...COMPAT_FULL,
  samsung_mail: "partial",
};

// --- Inline SVG placeholder images (render in sandboxed iframes without external requests) ---
function _img(w: number, h: number, bg: string, label: string, fg = "#fff"): string {
  const fs = Math.max(11, Math.min(28, Math.floor(Math.min(w, h) / 4)));
  return `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect fill="${bg}" width="${w}" height="${h}" rx="4"/><text x="${w / 2}" y="${h / 2 + Math.floor(fs / 3)}" fill="${fg}" font-family="Arial,sans-serif" font-size="${fs}" font-weight="bold" text-anchor="middle">${label}</text></svg>`
  )}`;
}

const IMG_LOGO = _img(150, 40, "#555", "Logo");
const IMG_HERO = _img(600, 300, "#4a5568", "Hero Image");
const IMG_LARGE = _img(600, 400, "#4a5568", "Image");
const IMG_FB = _img(32, 32, "#1877F2", "f");
const IMG_X = _img(32, 32, "#000", "X");
const IMG_LI = _img(32, 32, "#0A66C2", "in");
const IMG_IG = _img(32, 32, "#E4405F", "ig");

interface ComponentSeed {
  component: ComponentResponse;
  version: VersionResponse;
  compatibility: Record<string, string>;
}

const seeds: ComponentSeed[] = [
  {
    component: {
      id: 1, name: "Email Header", slug: "email-header",
      description: "Logo with optional navigation links. Full-width container with centered content.",
      category: "structure", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 101, component_id: 1, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) {
    .header-bg { background-color: #1a1a2e !important; }
    .header-link { color: #8ecae6 !important; }
  }
  [data-ogsc] .header-bg { background-color: #1a1a2e !important; }
</style>
<!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr><td style="padding: 20px 24px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="width: 150px;"><img src="${IMG_LOGO}" alt="Company Logo" width="150" height="40" style="display: block; border: 0;" /></td>
        <td style="text-align: right; vertical-align: middle;">
          <a href="https://example.com" class="header-link" style="color: #333; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; padding: 0 8px;">Home</a>
          <a href="https://example.com/products" class="header-link" style="color: #333; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; padding: 0 8px;">Products</a>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 2, name: "Email Footer", slug: "email-footer",
      description: "Unsubscribe link, company address, and legal text. GDPR-compliant footer.",
      category: "structure", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 102, component_id: 2, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) {
    .footer-bg { background-color: #1a1a2e !important; }
    .footer-text { color: #b0b0b0 !important; }
    .footer-link { color: #8ecae6 !important; }
  }
  [data-ogsc] .footer-bg { background-color: #1a1a2e !important; }
</style>
<!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f5f5;">
  <tr><td style="padding: 32px 24px; text-align: center;">
    <p class="footer-text" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 12px; color: #666; line-height: 1.5;">&copy; 2026 Company Name. All rights reserved.</p>
    <p style="margin: 0; font-family: Arial, sans-serif; font-size: 12px;">
      <a href="#" class="footer-link" style="color: #0066cc; text-decoration: underline;">Unsubscribe</a> &nbsp;|&nbsp;
      <a href="#" class="footer-link" style="color: #0066cc; text-decoration: underline;">Privacy Policy</a>
    </p>
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 3, name: "CTA Button", slug: "cta-button",
      description: "Centered call-to-action button with VML fallback for Outlook.",
      category: "action", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 103, component_id: 3, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) { .cta-btn { background-color: #4895ef !important; } }
  [data-ogsc] .cta-btn { background-color: #4895ef !important; }
</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="padding: 24px 0; text-align: center;">
    <!--[if mso]>
    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="https://example.com/cta" style="height:48px;v-text-anchor:middle;width:220px;" arcsize="10%" fillcolor="#0066cc">
      <center style="color:#fff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Shop Now</center>
    </v:roundrect>
    <![endif]-->
    <!--[if !mso]><!-->
    <table role="presentation" class="cta-btn" cellpadding="0" cellspacing="0" border="0" align="center" style="background-color:#0066cc;border-radius:4px;">
      <tr><td style="padding:12px 32px;">
        <a href="https://example.com/cta" style="color:#fff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Shop Now</a>
      </td></tr>
    </table>
    <!--<![endif]-->
  </td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 4, name: "Hero Block", slug: "hero-block",
      description: "Full-width hero with background image, headline, subtext, and CTA. VML background for Outlook.",
      category: "content", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 104, component_id: 4, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) {
    .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }
    .hero-title { color: #ffffff !important; }
  }
</style>
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
  <v:fill type="frame" src="${IMG_HERO}" />
  <v:textbox inset="0,0,0,0">
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image:url('${IMG_HERO}');background-size:cover;">
  <tr><td class="hero-overlay" style="padding:48px 24px;text-align:center;background-color:rgba(0,0,0,0.4);">
    <h1 class="hero-title" style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:32px;font-weight:bold;color:#fff;">Discover What's New</h1>
    <p style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#e0e0e0;">Explore our latest collection.</p>
    <a href="#" style="display:inline-block;padding:12px 32px;background-color:#fff;color:#333;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Learn More</a>
  </td></tr>
</table>
<!--[if mso]></v:textbox></v:rect><![endif]-->`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_PARTIAL_SAMSUNG,
  },
  {
    component: {
      id: 5, name: "Product Card", slug: "product-card",
      description: "Product image with title, price, description, and CTA. Table-based layout.",
      category: "commerce", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 105, component_id: 5, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) {
    .product-card { background-color: #2d2d44 !important; }
    .product-title { color: #e0e0e0 !important; }
    .product-price { color: #8ecae6 !important; }
  }
</style>
<table role="presentation" class="product-card" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
  <tr><td><img src="${IMG_HERO}" alt="Product Image" width="600" style="display:block;width:100%;height:auto;border:0;" /></td></tr>
  <tr><td style="padding:20px 24px;">
    <h2 class="product-title" style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:20px;font-weight:bold;color:#333;">Product Name</h2>
    <p class="product-price" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:18px;font-weight:bold;color:#0066cc;">&pound;49.99</p>
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;color:#666;line-height:1.5;">A short product description.</p>
    <a href="#" style="display:inline-block;padding:10px 24px;background-color:#0066cc;color:#fff;text-decoration:none;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;border-radius:4px;">View Product</a>
  </td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 6, name: "Spacer", slug: "spacer",
      description: "Adjustable-height transparent spacer. Works consistently across all clients.",
      category: "structure", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 106, component_id: 6, version_number: 1,
      html_source: `<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td height="32" style="font-size:0;line-height:0;">&nbsp;</td></tr></table>
<![endif]-->
<!--[if !mso]><!-->
<div style="height: 32px; line-height: 32px; font-size: 1px;">&nbsp;</div>
<!--<![endif]-->`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 7, name: "Social Icons", slug: "social-icons",
      description: "Row of social media icon links. Centered layout with consistent spacing.",
      category: "social", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 107, component_id: 7, version_number: 1,
      html_source: `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
  <tr><td style="padding:24px 0;text-align:center;">
    <p style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:14px;color:#666;">Follow us</p>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
      <tr>
        <td style="padding:0 8px;"><a href="#"><img src="${IMG_FB}" alt="Facebook" width="32" height="32" style="display:block;border:0;" /></a></td>
        <td style="padding:0 8px;"><a href="#"><img src="${IMG_X}" alt="X" width="32" height="32" style="display:block;border:0;" /></a></td>
        <td style="padding:0 8px;"><a href="#"><img src="${IMG_LI}" alt="LinkedIn" width="32" height="32" style="display:block;border:0;" /></a></td>
        <td style="padding:0 8px;"><a href="#"><img src="${IMG_IG}" alt="Instagram" width="32" height="32" style="display:block;border:0;" /></a></td>
      </tr>
    </table>
  </td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 8, name: "Image Block", slug: "image-block",
      description: "Responsive image with alt text, explicit dimensions, and optional caption.",
      category: "content", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 108, component_id: 8, version_number: 1,
      html_source: `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="text-align:center;"><img src="${IMG_LARGE}" alt="Descriptive alt text" width="600" style="display:block;width:100%;max-width:600px;height:auto;border:0;" /></td></tr>
  <tr><td style="padding:8px 24px;"><p style="margin:0;font-family:Arial,sans-serif;font-size:12px;color:#999;text-align:center;font-style:italic;">Image caption</p></td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 9, name: "Text Block", slug: "text-block",
      description: "Heading and paragraph text with configurable alignment. Core content component.",
      category: "content", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 109, component_id: 9, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) {
    .textblock-bg { background-color: #1a1a2e !important; }
    .textblock-heading { color: #e0e0e0 !important; }
    .textblock-body { color: #cccccc !important; }
  }
</style>
<table role="presentation" class="textblock-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
  <tr><td style="padding:24px;">
    <h2 class="textblock-heading" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:24px;font-weight:bold;color:#333;">Section Heading</h2>
    <p class="textblock-body" style="margin:0;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.6;">Body text goes here. Supports multiple paragraphs and customisable styles.</p>
  </td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
  {
    component: {
      id: 10, name: "Divider", slug: "divider",
      description: "Horizontal line separator with configurable colour and spacing.",
      category: "structure", created_by_id: 1, latest_version: 1,
      created_at: "2025-12-01T10:00:00Z", updated_at: "2025-12-01T10:00:00Z",
    },
    version: {
      id: 110, component_id: 10, version_number: 1,
      html_source: `<style>
  @media (prefers-color-scheme: dark) { .divider-line { border-top-color: #444466 !important; } }
</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="padding:16px 24px;">
    <div class="divider-line" style="border-top:1px solid #e0e0e0;font-size:1px;line-height:1px;">&nbsp;</div>
  </td></tr>
</table>`,
      css_source: null, changelog: "Initial version", created_by_id: 1,
      created_at: "2025-12-01T10:00:00Z",
    },
    compatibility: COMPAT_FULL,
  },
];

export const DEMO_COMPONENTS: ComponentResponse[] = seeds.map((s) => ({
  ...s.component,
  compatibility_badge: Object.values(s.compatibility).includes("none")
    ? "issues"
    : Object.values(s.compatibility).includes("partial")
      ? "partial"
      : "full",
}));
export const DEMO_COMPONENT_VERSIONS: VersionResponse[] = seeds.map((s) => s.version);
export const DEMO_COMPONENT_COMPATIBILITY: Record<number, Record<string, string>> =
  Object.fromEntries(seeds.map((s) => [s.component.id, s.compatibility]));

export function buildCompatibilityResponse(componentId: number): ComponentCompatibilityResponse | null {
  const compat = DEMO_COMPONENT_COMPATIBILITY[componentId];
  const comp = DEMO_COMPONENTS.find((c) => c.id === componentId);
  if (!compat || !comp) return null;

  const clients: ClientCompatibility[] = DEMO_EMAIL_CLIENTS.map((ec) => ({
    client_id: ec.id,
    client_name: ec.name,
    level: compat[ec.id] ?? compat[ec.family] ?? "full",
    platform: ec.platform,
  }));

  const full_count = clients.filter((c) => c.level === "full").length;
  const partial_count = clients.filter((c) => c.level === "partial").length;
  const none_count = clients.filter((c) => c.level === "none").length;

  return {
    component_id: componentId,
    component_name: comp.name,
    version_number: comp.latest_version ?? 1,
    full_count,
    partial_count,
    none_count,
    clients,
    qa_score: none_count === 0 && partial_count === 0 ? 1.0 : partial_count > 0 ? 0.85 : 0.6,
    last_checked: "2026-03-10T14:30:00Z",
  };
}
