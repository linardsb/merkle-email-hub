"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import { SWR_PRESETS } from "@/lib/swr-constants";
import type { EmailClientResponse } from "@email-hub/sdk";

export function useEmailClients() {
  return useSWR<EmailClientResponse[]>("/api/v1/ontology/clients", fetcher, {
    ...SWR_PRESETS.reference,
  });
}
