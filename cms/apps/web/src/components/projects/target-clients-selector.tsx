"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { useEmailClients } from "@/hooks/use-email-clients";
import type { EmailClientResponse } from "@merkle-email-hub/sdk";

const COMMON_CLIENTS = [
  "gmail_web",
  "outlook_2019_win",
  "apple_mail_ios",
  "apple_mail_macos",
];

const ENGINE_STYLES: Record<string, string> = {
  word: "bg-destructive/10 text-destructive",
  webkit: "bg-primary/10 text-primary",
  blink: "bg-accent text-accent-foreground",
  custom: "bg-muted text-muted-foreground",
  gecko: "bg-muted text-muted-foreground",
  presto: "bg-muted text-muted-foreground",
};

const ENGINE_LABEL_KEYS: Record<string, string> = {
  word: "engineWord",
  webkit: "engineWebkit",
  blink: "engineBlink",
  gecko: "engineGecko",
  custom: "engineCustom",
  presto: "enginePresto",
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
  const t = useTranslations("projects");
  const td = useTranslations("dashboard");
  const { data: clients, isLoading } = useEmailClients();
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const grouped = useMemo(() => {
    if (!clients) return {};
    const filtered = search
      ? clients.filter((c) =>
          c.name.toLowerCase().includes(search.toLowerCase())
        )
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
    onChange(
      selected.includes(id)
        ? selected.filter((s) => s !== id)
        : [...selected, id]
    );
  };

  const handleSelectCommon = () => {
    if (disabled) return;
    const availableIds = clients?.map((c) => c.id) ?? [];
    const commonAvailable = COMMON_CLIENTS.filter((id) =>
      availableIds.includes(id)
    );
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
      <div className="rounded-md border border-input-border bg-input-bg p-4 text-center text-sm text-muted-foreground">
        {td("loading")}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-input-border bg-input-bg">
      {/* Header: search + common preset */}
      <div className="flex items-center gap-2 border-b border-border p-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={td("newProjectTargetClientsSearch")}
            disabled={disabled}
            className="w-full rounded border-0 bg-transparent py-1 pl-7 pr-2 text-sm text-foreground placeholder:text-input-placeholder focus:outline-none disabled:opacity-50"
          />
        </div>
        <button
          type="button"
          onClick={handleSelectCommon}
          disabled={disabled}
          className="shrink-0 rounded px-2 py-1 text-xs font-medium text-interactive transition-colors hover:bg-interactive/10 disabled:opacity-50"
        >
          {td("newProjectTargetClientsCommon")}
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
                className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
              >
                {isCollapsed ? (
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                )}
                <span>{family}</span>
                {selCount > 0 && (
                  <span className="ml-auto text-xs text-interactive">
                    {td("newProjectTargetClientsSelected", { count: selCount })}
                  </span>
                )}
              </button>
              {!isCollapsed &&
                familyClients.map((client) => (
                  <label
                    key={client.id}
                    className="flex cursor-pointer items-center gap-2 px-3 py-1.5 pl-8 text-sm transition-colors hover:bg-surface-hover"
                  >
                    <input
                      type="checkbox"
                      checked={selected.includes(client.id)}
                      onChange={() => toggleClient(client.id)}
                      disabled={disabled}
                      className="accent-interactive"
                    />
                    <span className="flex-1 text-foreground">{client.name}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${ENGINE_STYLES[client.engine] ?? ENGINE_STYLES.custom}`}
                    >
                      {t(ENGINE_LABEL_KEYS[client.engine] ?? "engineCustom")}
                    </span>
                    <span className="w-10 text-right text-xs text-muted-foreground">
                      {client.market_share}%
                    </span>
                  </label>
                ))}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-t border-border px-3 py-1.5 text-xs text-muted-foreground">
        {selected.length > 0
          ? td("newProjectTargetClientsSelected", { count: selected.length })
          : td("newProjectTargetClientsNone")}
      </div>
    </div>
  );
}
