import type { LocaleConfig } from "@/types/locale";

export const SUPPORTED_LOCALES: LocaleConfig[] = [
  { code: "en", name: "English", nativeName: "English", dir: "ltr", dateFormat: "MM/DD/YYYY" },
  { code: "ar", name: "Arabic", nativeName: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629", dir: "rtl", dateFormat: "DD/MM/YYYY" },
  { code: "de", name: "German", nativeName: "Deutsch", dir: "ltr", dateFormat: "DD.MM.YYYY" },
  { code: "es", name: "Spanish", nativeName: "Espa\u00f1ol", dir: "ltr", dateFormat: "DD/MM/YYYY" },
  { code: "fr", name: "French", nativeName: "Fran\u00e7ais", dir: "ltr", dateFormat: "DD/MM/YYYY" },
  { code: "ja", name: "Japanese", nativeName: "\u65E5\u672C\u8A9E", dir: "ltr", dateFormat: "YYYY/MM/DD" },
];

export function getLocaleConfig(code: string): LocaleConfig {
  return SUPPORTED_LOCALES.find((l) => l.code === code) ?? SUPPORTED_LOCALES[0]!;
}

export const DEFAULT_LOCALE = "en";
