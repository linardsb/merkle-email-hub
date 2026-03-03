export interface LocaleConfig {
  code: string;
  name: string;
  nativeName: string;
  dir: "ltr" | "rtl";
  dateFormat: string;
}

export interface TranslationEntry {
  namespace: string;
  key: string;
  values: Record<string, string>;
}
