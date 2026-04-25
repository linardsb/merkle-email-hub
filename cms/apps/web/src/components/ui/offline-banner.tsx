"use client";

import { WifiOff } from "../icons";
import { useNetworkStatus } from "@/hooks/use-network-status";

export function OfflineBanner() {
  const isOnline = useNetworkStatus();
  if (isOnline) return null;

  return (
    <div className="bg-status-warning text-foreground-inverse flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium">
      <WifiOff className="h-4 w-4" />
      {"You appear to be offline. Some features may be unavailable."}
    </div>
  );
}
