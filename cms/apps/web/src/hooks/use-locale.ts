"use client";

import { useCallback } from "react";
import { DEFAULT_LOCALE } from "@/lib/locales";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]!) : null;
}

function setCookie(name: string, value: string, days = 365) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires};path=/;SameSite=Lax`;
}

export function useLocale() {
  const currentLocale = getCookie("NEXT_LOCALE") ?? DEFAULT_LOCALE;

  const setLocale = useCallback((locale: string) => {
    setCookie("NEXT_LOCALE", locale);
    window.location.reload();
  }, []);

  return { locale: currentLocale, setLocale };
}
