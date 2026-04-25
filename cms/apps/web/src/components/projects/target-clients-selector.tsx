"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "../icons";
import { useEmailClients } from "@/hooks/use-email-clients";
import type { EmailClientResponse } from "@email-hub/sdk";

const COMMON_CLIENTS = ["gmail_web", "outlook_2019_win", "apple_mail_ios", "apple_mail_macos"];

const ENGINE_STYLES: Record<string, string> = {
  word: "bg-destructive/10 text-destructive",
  webkit: "bg-primary/10 text-primary",
  blink: "bg-accent text-accent-foreground",
  custom: "bg-muted text-muted-foreground",
  gecko: "bg-muted text-muted-foreground",
  presto: "bg-muted text-muted-foreground",
};

const ENGINE_LABELS: Record<string, string> = {
  word: "Word",
  webkit: "WebKit",
  blink: "Blink",
  gecko: "Gecko",
  custom: "Custom",
  presto: "Presto",
};

interface TargetClientsSelectorProps {
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}

export function TargetClientsSelector({
  selected,
  onChange,
  disabled = false,
}: TargetClientsSelectorProps) {
  const { data: clients, isLoading } = useEmailClients();
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const grouped = useMemo(() => {
    if (!clients) return {};
    const filtered = search
      ? clients.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
      : clients;

    const groups: Record<string, EmailClientResponse[]> = {};
    for (const client of filtered) {
      const family = client.family;
      if (!groups[family]) groups[family] = [];
      groups[family].push(client);
    }
    return groups;
  }, [clients, search]);

  const toggleClient = (id: string) => {
    if (disabled) return;
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  const handleSelectCommon = () => {
    if (disabled) return;
    const availableIds = clients?.map((c) => c.id) ?? [];
    const commonAvailable = COMMON_CLIENTS.filter((id) => availableIds.includes(id));
    onChange(commonAvailable);
  };

  const toggleFamily = (family: string) => {
    setCollapsed((prev) => ({ ...prev, [family]: !prev[family] }));
  };

  const selectedCountForFamily = (family: string): number => {
    const familyClients = grouped[family] ?? [];
    return familyClients.filter((c) => selected.includes(c.id)).length;
  };

  if (isLoading) {
    return (
      <div className="border-input-border bg-input-bg text-muted-foreground rounded-md border p-4 text-center text-sm">
        {"Loading..."}
      </div>
    );
  }

  return (
    <div className="border-input-border bg-input-bg rounded-md border">
      {/* Header: search + common preset */}
      <div className="border-border flex items-center gap-2 border-b p-2">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={"Search clients..."}
            disabled={disabled}
            className="text-foreground placeholder:text-input-placeholder w-full rounded border-0 bg-transparent py-1 pl-7 pr-2 text-sm focus:outline-none disabled:opacity-50"
          />
        </div>
        <button
          type="button"
          onClick={handleSelectCommon}
          disabled={disabled}
          className="text-interactive hover:bg-interactive/10 shrink-0 rounded px-2 py-1 text-xs font-medium transition-colors disabled:opacity-50"
        >
          {"Select Common"}
        </button>
      </div>

      {/* Client list grouped by family */}
      <div className="max-h-[16rem] overflow-y-auto">
        {Object.entries(grouped).map(([family, familyClients]) => {
          const isCollapsed = collapsed[family] ?? false;
          const selCount = selectedCountForFamily(family);
          return (
            <div key={family}>
              <button
                type="button"
                onClick={() => toggleFamily(family)}
                className="text-foreground hover:bg-surface-hover flex w-full items-center gap-1.5 px-3 py-2 text-left text-sm font-medium transition-colors"
              >
                {isCollapsed ? (
                  <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
                )}
                <span>{family}</span>
                {selCount > 0 && (
                  <span className="text-interactive ml-auto text-xs">
                    {`${selCount} clients selected`}
                  </span>
                )}
              </button>
              {!isCollapsed &&
                familyClients.map((client) => (
                  <label
                    key={client.id}
                    className="hover:bg-surface-hover flex cursor-pointer items-center gap-2 px-3 py-1.5 pl-8 text-sm transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selected.includes(client.id)}
                      onChange={() => toggleClient(client.id)}
                      disabled={disabled}
                      className="accent-interactive"
                    />
                    <span className="text-foreground flex-1">{client.name}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${ENGINE_STYLES[client.engine] ?? ENGINE_STYLES.custom}`}
                    >
                      {ENGINE_LABELS[client.engine] ?? "Custom"}
                    </span>
                    <span className="text-muted-foreground w-10 text-right text-xs">
                      {client.market_share}%
                    </span>
                  </label>
                ))}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-border text-muted-foreground border-t px-3 py-1.5 text-xs">
        {selected.length > 0
          ? `${selected.length} clients selected`
          : "No priority clients \u2014 all 25 clients treated equally"}
      </div>
    </div>
  );
}
