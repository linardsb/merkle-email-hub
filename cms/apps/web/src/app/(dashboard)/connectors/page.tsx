"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Plug } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { useExportHistory } from "@/hooks/use-export-history";
import { ExportCard } from "@/components/connectors/export-card";
import type { ConnectorPlatform } from "@/types/connectors";

const PLATFORM_FILTERS = ["all", "braze", "sfmc", "adobe_campaign", "taxi", "raw_html"] as const;

const FILTER_LABEL_KEYS: Record<string, string> = {
  all: "filterAll",
  braze: "filterBraze",
  sfmc: "filterSfmc",
  adobe_campaign: "filterAdobeCampaign",
  taxi: "filterTaxi",
  raw_html: "filterRawHtml",
};

export default function ConnectorsPage() {
  const t = useTranslations("connectors");
  const { records } = useExportHistory();
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (activeFilter === "all") return records;
    return records.filter(
      (r) => r.platform === (activeFilter as ConnectorPlatform)
    );
  }, [records, activeFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Plug className="h-6 w-6 text-foreground" />
        <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
      </div>

      {/* Platform filter tabs */}
      <div className="flex gap-2">
        {PLATFORM_FILTERS.map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => setActiveFilter(filter)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeFilter === filter
                ? "bg-interactive text-foreground-inverse"
                : "bg-surface-muted text-foreground-muted hover:text-foreground"
            }`}
          >
            {t(FILTER_LABEL_KEYS[filter] ?? "filterAll")}
          </button>
        ))}
      </div>

      {/* Content */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={Plug}
          title={t("empty")}
          description={t("emptyDescription")}
        />
      ) : (
        <div className="animate-fade-in grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((record) => (
            <ExportCard key={record.local_id} record={record} />
          ))}
        </div>
      )}
    </div>
  );
}
