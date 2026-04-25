"use client";

import { useMemo } from "react";
import type { RenderingTest } from "@/types/rendering";

interface Props {
  tests: RenderingTest[];
}

function statusDot(status: string) {
  const colors: Record<string, string> = {
    complete: "bg-status-success",
    failed: "bg-status-danger",
    pending: "bg-surface-muted",
    not_tested: "bg-surface-muted",
  };
  return colors[status] ?? "bg-surface-muted";
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

interface DerivedClient {
  name: string;
  category: string;
}

export function ClientCompatibilityMatrix({ tests }: Props) {
  const recentTests = tests.slice(0, 5);

  // Derive unique clients from screenshot data across all tests
  const clients = useMemo(() => {
    const seen = new Map<string, DerivedClient>();
    for (const test of tests) {
      for (const s of test.screenshots ?? []) {
        if (!seen.has(s.client_name)) {
          seen.set(s.client_name, { name: s.client_name, category: s.category ?? "" });
        }
      }
    }
    return Array.from(seen.values());
  }, [tests]);

  const categories = [
    { key: "desktop", label: "Desktop" },
    { key: "web", label: "Webmail" },
    { key: "mobile", label: "Mobile" },
    { key: "dark_mode", label: "Dark Mode" },
  ];

  function getScreenshotStatus(test: RenderingTest, clientName: string): string {
    const screenshot = (test.screenshots ?? []).find((s) => s.client_name === clientName);
    return screenshot?.status ?? "not_tested";
  }

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <h2 className="text-foreground text-lg font-semibold">{"Compatibility Matrix"}</h2>
      <p className="text-foreground-muted mt-1 text-sm">
        {"Pass/warn/fail status per email client across recent test runs"}
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-card-border border-b">
              <th className="text-foreground-muted pb-2 pr-4 text-left font-medium">{"Client"}</th>
              {recentTests.map((test) => (
                <th
                  key={test.id}
                  className="text-foreground-muted px-2 pb-2 text-center font-medium"
                >
                  {formatShortDate(test.created_at)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {categories.flatMap((cat) => {
              const catClients = clients.filter((c) => c.category === cat.key);
              if (catClients.length === 0) return [];
              return [
                <tr key={`header-${cat.key}`}>
                  <td colSpan={1 + recentTests.length} className="pb-1 pt-4">
                    <span className="text-foreground-muted text-xs font-semibold uppercase tracking-wider">
                      {cat.label}
                    </span>
                  </td>
                </tr>,
                ...catClients.map((client) => (
                  <tr key={client.name} className="border-card-border/50 border-b">
                    <td className="text-foreground py-2 pr-4">{client.name}</td>
                    {recentTests.map((test) => {
                      const status = getScreenshotStatus(test, client.name);
                      return (
                        <td key={test.id} className="px-2 py-2 text-center">
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
