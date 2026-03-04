"use client";

import { useTranslations } from "next-intl";
import type { RenderingClient, RenderingTest, RenderingResultStatus } from "@/types/rendering";

interface Props {
  clients: RenderingClient[];
  tests: RenderingTest[];
}

function statusDot(status: RenderingResultStatus | "not_tested") {
  const colors: Record<string, string> = {
    pass: "bg-status-success",
    warning: "bg-status-warning",
    fail: "bg-status-danger",
    pending: "bg-surface-muted",
    not_tested: "bg-surface-muted",
  };
  return colors[status] ?? "bg-surface-muted";
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function ClientCompatibilityMatrix({ clients, tests }: Props) {
  const t = useTranslations("renderings");

  const recentTests = tests.slice(0, 5);

  const categories = [
    { key: "desktop" as const, label: t("desktop") },
    { key: "webmail" as const, label: t("webmail") },
    { key: "mobile" as const, label: t("mobile") },
  ];

  function getResultStatus(test: RenderingTest, clientId: string): RenderingResultStatus | "not_tested" {
    const result = test.results.find((r) => r.client_id === clientId);
    return result?.status ?? "not_tested";
  }

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <h2 className="text-lg font-semibold text-foreground">{t("compatibilityMatrix")}</h2>
      <p className="mt-1 text-sm text-foreground-muted">{t("compatibilityMatrixDescription")}</p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-card-border">
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("client")}</th>
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("marketShare")}</th>
              {recentTests.map((test) => (
                <th key={test.id} className="pb-2 px-2 text-center font-medium text-foreground-muted">
                  {formatShortDate(test.created_at)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {categories.map((cat) => {
              const catClients = clients.filter((c) => c.category === cat.key);
              return (
                <tr key={cat.key}>
                  <td colSpan={2 + recentTests.length} className="pt-4 pb-1">
                    <span className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                      {cat.label}
                    </span>
                  </td>
                </tr>
              );
            }).flatMap((header, catIdx) => {
              const cat = categories[catIdx]!;
              const catClients = clients.filter((c) => c.category === cat.key);
              return [
                header,
                ...catClients.map((client) => (
                  <tr key={client.id} className="border-b border-card-border/50">
                    <td className="py-2 pr-4 text-foreground">{client.name}</td>
                    <td className="py-2 pr-4 text-foreground-muted">{client.market_share}%</td>
                    {recentTests.map((test) => {
                      const status = getResultStatus(test, client.id);
                      return (
                        <td key={test.id} className="py-2 px-2 text-center">
                          <span
                            className={`inline-block h-3 w-3 rounded-full ${statusDot(status)}`}
                            title={status}
                          />
                        </td>
                      );
                    })}
                  </tr>
                )),
              ];
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
