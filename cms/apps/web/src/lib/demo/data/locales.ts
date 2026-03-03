/**
 * Demo translation entries for the translation management table.
 * Shows a subset of keys across all supported locales.
 */

import type { TranslationEntry } from "@/types/locale";

export const DEMO_TRANSLATIONS: TranslationEntry[] = [
  {
    namespace: "nav",
    key: "dashboard",
    values: { en: "Dashboard", ar: "لوحة التحكم", de: "Dashboard", es: "Panel", fr: "Tableau de bord", ja: "ダッシュボード" },
  },
  {
    namespace: "nav",
    key: "projects",
    values: { en: "Projects", ar: "المشاريع", de: "Projekte", es: "Proyectos", fr: "Projets", ja: "プロジェクト" },
  },
  {
    namespace: "nav",
    key: "components",
    values: { en: "Components", ar: "المكونات", de: "Komponenten", es: "Componentes", fr: "Composants", ja: "コンポーネント" },
  },
  {
    namespace: "nav",
    key: "approvals",
    values: { en: "Approvals", ar: "الموافقات", de: "Genehmigungen", es: "Aprobaciones", fr: "Approbations", ja: "承認" },
  },
  {
    namespace: "nav",
    key: "connectors",
    values: { en: "Connectors", ar: "الموصلات", de: "Konnektoren", es: "Conectores", fr: "Connecteurs", ja: "コネクタ" },
  },
  {
    namespace: "nav",
    key: "settings",
    values: { en: "Settings", ar: "الإعدادات", de: "Einstellungen", es: "Configuración", fr: "Paramètres", ja: "設定" },
  },
  {
    namespace: "login",
    key: "title",
    values: { en: "Sign In", ar: "تسجيل الدخول", de: "Anmelden", es: "Iniciar sesión", fr: "Connexion", ja: "サインイン" },
  },
  {
    namespace: "login",
    key: "username",
    values: { en: "Username", ar: "اسم المستخدم", de: "Benutzername", es: "Usuario", fr: "Nom d'utilisateur", ja: "ユーザー名" },
  },
  {
    namespace: "login",
    key: "password",
    values: { en: "Password", ar: "كلمة المرور", de: "Passwort", es: "Contraseña", fr: "Mot de passe", ja: "パスワード" },
  },
  {
    namespace: "dashboard",
    key: "title",
    values: { en: "Dashboard", ar: "لوحة التحكم", de: "Dashboard", es: "Panel", fr: "Tableau de bord", ja: "ダッシュボード" },
  },
  {
    namespace: "dashboard",
    key: "totalProjects",
    values: { en: "Total Projects", ar: "إجمالي المشاريع", de: "Projekte insgesamt", es: "Total de proyectos", fr: "Total des projets", ja: "プロジェクト総数" },
  },
  {
    namespace: "dashboard",
    key: "systemStatus",
    values: { en: "System Status", ar: "حالة النظام", de: "Systemstatus", es: "Estado del sistema", fr: "État du système", ja: "システム状態" },
  },
  {
    namespace: "errors",
    key: "generic",
    values: { en: "Something went wrong. Please try again.", ar: "حدث خطأ ما. يرجى المحاولة مرة أخرى.", de: "Etwas ist schief gelaufen. Bitte versuchen Sie es erneut.", es: "Algo salió mal. Por favor, inténtelo de nuevo.", fr: "Une erreur s'est produite. Veuillez réessayer.", ja: "問題が発生しました。もう一度お試しください。" },
  },
  {
    namespace: "settings",
    key: "title",
    values: { en: "Settings", ar: "الإعدادات", de: "Einstellungen", es: "Configuración", fr: "Paramètres", ja: "設定" },
  },
  {
    namespace: "settings",
    key: "languageTitle",
    values: { en: "Language", ar: "اللغة", de: "Sprache", es: "Idioma", fr: "Langue", ja: "言語" },
  },
];

export const DEMO_LOCALES = [
  { code: "en", name: "English", nativeName: "English", dir: "ltr", keysTranslated: 120, keysTotal: 120, coverage: 100 },
  { code: "ar", name: "Arabic", nativeName: "العربية", dir: "rtl", keysTranslated: 30, keysTotal: 120, coverage: 25 },
  { code: "de", name: "German", nativeName: "Deutsch", dir: "ltr", keysTranslated: 30, keysTotal: 120, coverage: 25 },
  { code: "es", name: "Spanish", nativeName: "Español", dir: "ltr", keysTranslated: 30, keysTotal: 120, coverage: 25 },
  { code: "fr", name: "French", nativeName: "Français", dir: "ltr", keysTranslated: 30, keysTotal: 120, coverage: 25 },
  { code: "ja", name: "Japanese", nativeName: "日本語", dir: "ltr", keysTranslated: 30, keysTotal: 120, coverage: 25 },
];
