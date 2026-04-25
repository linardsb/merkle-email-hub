import useSWR from "swr";
import { authFetch } from "@/lib/auth-fetch";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";

export interface KeyHealth {
  key_hash: string;
  status: "healthy" | "cooled_down" | "unhealthy";
  failure_count: number;
  last_failure_code: number | null;
  cooldown_remaining_s: number;
}

export interface ServiceHealth {
  service: string;
  key_count: number;
  healthy: number;
  cooled_down: number;
  unhealthy: number;
  keys: KeyHealth[];
}

export interface CredentialHealth {
  services: ServiceHealth[];
  total_keys: number;
  healthy_total: number;
  cooled_down_total: number;
  unhealthy_total: number;
}

const fetcher = (url: string) => authFetch(url).then((r) => r.json());

export function useCredentialHealth() {
  const refreshInterval = useSmartPolling(POLL.background);
  return useSWR<CredentialHealth>("/api/v1/credentials/health", fetcher, {
    ...SWR_PRESETS.polling,
    refreshInterval,
  });
}
