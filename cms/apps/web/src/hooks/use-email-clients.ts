"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { EmailClientResponse } from "@merkle-email-hub/sdk";

export function useEmailClients() {
  return useSWR<EmailClientResponse[]>(
    "/api/v1/ontology/clients",
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );
}
