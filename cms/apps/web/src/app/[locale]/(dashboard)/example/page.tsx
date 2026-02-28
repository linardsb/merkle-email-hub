"use client";

import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";
import { List, Plus, Search } from "lucide-react";
import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";

interface Item {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
}

interface PaginatedItems {
  items: Item[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export default function ExamplePage() {
  const t = useTranslations("example");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useSWR<PaginatedItems>(
    `/api/v1/example?page=${page}&size=10${search ? `&search=${encodeURIComponent(search)}` : ""}`,
    fetcher
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <List className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
        </div>
        <button
          type="button"
          className="flex items-center gap-2 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
        >
          <Plus className="h-4 w-4" />
          {t("create")}
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder={t("searchPlaceholder")}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={t("searchPlaceholder")}
        />
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-card-border bg-card-bg">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th className="px-4 py-3 text-left text-sm font-medium text-foreground-muted">
                {t("name")}
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-foreground-muted">
                {t("description")}
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-foreground-muted">
                {t("status")}
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-foreground-muted">
                {t("createdAt")}
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-foreground-muted">
                  {t("loading")}
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-status-danger">
                  {t("error")}
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-foreground-muted">
                  {t("noItems")}
                </td>
              </tr>
            ) : (
              data?.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border transition-colors last:border-0 hover:bg-surface-hover"
                >
                  <td className="px-4 py-3 text-sm font-medium text-foreground">
                    {item.name}
                  </td>
                  <td className="px-4 py-3 text-sm text-foreground-muted">
                    {item.description || "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-badge-default-bg px-2 py-0.5 text-xs font-medium text-badge-default-text">
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-foreground-muted">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-foreground-muted">
            {t("showing", { from: (page - 1) * 10 + 1, to: Math.min(page * 10, data.total), total: data.total })}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("previous")}
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              disabled={page === data.pages}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("next")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
