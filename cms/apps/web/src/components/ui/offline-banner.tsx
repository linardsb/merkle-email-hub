"use client";

import { useTranslations } from "next-intl";
import { WifiOff } from "lucide-react";
import { useNetworkStatus } from "@/hooks/use-network-status";

export function OfflineBanner() {
  const isOnline = useNetworkStatus();
  const t = useTranslations("errors");

  if (isOnline) return null;

  return (
    <div className="flex items-center justify-center gap-2 bg-status-warning px-4 py-2 text-sm font-medium text-foreground-inverse">
      <WifiOff className="h-4 w-4" />
      {t("offline")}
    </div>
  );
}
