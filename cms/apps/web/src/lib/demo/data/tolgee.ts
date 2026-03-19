import type {
  TolgeeLanguage,
  TolgeeConnectionResponse,
  TranslationSyncResponse,
  TranslationPullResponse,
  LocaleBuildResponse,
} from "@/types/tolgee";

export const DEMO_LANGUAGES: TolgeeLanguage[] = [
  {
    id: 1,
    tag: "en",
    name: "English",
    original_name: "English",
    flag_emoji: "\u{1F1EC}\u{1F1E7}",
    base: true,
  },
  {
    id: 2,
    tag: "de",
    name: "German",
    original_name: "Deutsch",
    flag_emoji: "\u{1F1E9}\u{1F1EA}",
    base: false,
  },
  {
    id: 3,
    tag: "fr",
    name: "French",
    original_name: "Fran\u00e7ais",
    flag_emoji: "\u{1F1EB}\u{1F1F7}",
    base: false,
  },
  {
    id: 4,
    tag: "es",
    name: "Spanish",
    original_name: "Espa\u00f1ol",
    flag_emoji: "\u{1F1EA}\u{1F1F8}",
    base: false,
  },
  {
    id: 5,
    tag: "ar-SA",
    name: "Arabic",
    original_name: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629",
    flag_emoji: "\u{1F1F8}\u{1F1E6}",
    base: false,
  },
  {
    id: 6,
    tag: "ja",
    name: "Japanese",
    original_name: "\u65E5\u672C\u8A9E",
    flag_emoji: "\u{1F1EF}\u{1F1F5}",
    base: false,
  },
];

export const DEMO_CONNECTION: TolgeeConnectionResponse = {
  id: 1,
  name: "Production Tolgee",
  status: "connected",
  credentials_hint: "****a1b2",
  tolgee_project_id: 42,
  project_id: 1,
  last_synced_at: "2026-03-15T10:30:00Z",
  created_at: "2026-03-01T09:00:00Z",
};

const DEMO_TRANSLATIONS_EN: Record<string, string> = {
  "template_1.hero.heading": "Welcome to our Newsletter",
  "template_1.hero.subheading": "The latest updates for you",
  "template_1.content.body":
    "Discover our latest offers and features designed just for you.",
  "template_1.cta.button": "Explore Now",
  "template_1.footer.unsubscribe": "Unsubscribe",
  "template_1.footer.legal":
    "You are receiving this email because you signed up for our newsletter.",
  "template_1.meta.subject": "Your Weekly Newsletter",
  "template_1.meta.preheader": "This week's top stories and deals",
};

const DEMO_TRANSLATIONS_DE: Record<string, string> = {
  "template_1.hero.heading": "Willkommen bei unserem Newsletter",
  "template_1.hero.subheading": "Die neuesten Updates f\u00fcr Sie",
  "template_1.content.body":
    "Entdecken Sie unsere neuesten Angebote und Funktionen.",
  "template_1.cta.button": "Jetzt entdecken",
  "template_1.footer.unsubscribe": "Abmelden",
  "template_1.footer.legal":
    "Sie erhalten diese E-Mail, weil Sie sich f\u00fcr unseren Newsletter angemeldet haben.",
  "template_1.meta.subject": "Ihr w\u00f6chentlicher Newsletter",
  "template_1.meta.preheader": "Die Top-Geschichten und Angebote dieser Woche",
};

const DEMO_TRANSLATIONS_FR: Record<string, string> = {
  "template_1.hero.heading": "Bienvenue dans notre newsletter",
  "template_1.hero.subheading": "Les derni\u00e8res nouvelles pour vous",
  "template_1.content.body":
    "D\u00e9couvrez nos derni\u00e8res offres et fonctionnalit\u00e9s.",
  "template_1.cta.button": "D\u00e9couvrir",
  "template_1.footer.unsubscribe": "Se d\u00e9sabonner",
};

const DEMO_TRANSLATIONS_ES: Record<string, string> = {
  "template_1.hero.heading": "Bienvenido a nuestro bolet\u00edn",
  "template_1.hero.subheading": "\u00DAltimas novedades para ti",
  "template_1.cta.button": "Explorar ahora",
};

const LOCALE_TRANSLATIONS: Record<string, Record<string, string>> = {
  en: DEMO_TRANSLATIONS_EN,
  de: DEMO_TRANSLATIONS_DE,
  fr: DEMO_TRANSLATIONS_FR,
  es: DEMO_TRANSLATIONS_ES,
  "ar-SA": {},
  ja: {},
};

export const DEMO_SYNC_RESPONSE: TranslationSyncResponse = {
  keys_extracted: Object.keys(DEMO_TRANSLATIONS_EN).length,
  push_result: { created: 3, updated: 5, skipped: 0 },
  template_id: 1,
};

export function buildDemoPullResponse(
  locales: string[],
): TranslationPullResponse[] {
  return locales.map((locale) => {
    const translations = LOCALE_TRANSLATIONS[locale] ?? {};
    return {
      locale,
      translations_count: Object.keys(translations).length,
      translations,
    };
  });
}

const DEMO_EMAIL_HTML = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Newsletter</title></head>
<body style="margin:0;padding:0;background:#f5f5f5;">
<table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;">
<tr><td style="padding:32px;text-align:center;">
<h1 style="margin:0;font-size:24px;color:#333;">Welcome to our Newsletter</h1>
<p style="color:#666;font-size:16px;">The latest updates for you</p>
</td></tr>
<tr><td style="padding:16px 32px;">
<p style="color:#333;font-size:14px;">Discover our latest offers and features designed just for you.</p>
</td></tr>
<tr><td style="padding:16px 32px;text-align:center;">
<a href="#" style="background:#E4002B;color:#fff;padding:12px 24px;text-decoration:none;font-weight:bold;display:inline-block;">Explore Now</a>
</td></tr>
</table></body></html>`;

export function buildDemoLocaleBuildResponse(
  templateId: number,
  locales: string[],
): LocaleBuildResponse {
  const RTL_LOCALES = new Set(["ar", "ar-SA", "he", "fa", "ur"]);
  const results = locales.map((locale) => ({
    locale,
    html: DEMO_EMAIL_HTML.replace("en", locale),
    build_time_ms: 80 + Math.random() * 120,
    gmail_clipping_warning: false,
    text_direction: (RTL_LOCALES.has(locale) ? "rtl" : "ltr") as
      | "ltr"
      | "rtl",
  }));

  return {
    template_id: templateId,
    results,
    total_build_time_ms: results.reduce((s, r) => s + r.build_time_ms, 0),
  };
}
