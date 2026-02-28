import { useTranslations } from "next-intl";
import { LayoutDashboard } from "lucide-react";

export default function DashboardPage() {
  const t = useTranslations("dashboard");

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <LayoutDashboard className="h-8 w-8 text-foreground-accent" />
        <h1 className="text-2xl font-semibold text-foreground">
          {t("title")}
        </h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Stats cards */}
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <p className="text-sm font-medium text-foreground-muted">
            {t("totalItems")}
          </p>
          <p className="mt-2 text-3xl font-semibold text-foreground">0</p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <p className="text-sm font-medium text-foreground-muted">
            {t("activeUsers")}
          </p>
          <p className="mt-2 text-3xl font-semibold text-foreground">0</p>
        </div>

        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <p className="text-sm font-medium text-foreground-muted">
            {t("systemStatus")}
          </p>
          <p className="mt-2 text-3xl font-semibold text-status-success">
            {t("healthy")}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <h2 className="text-lg font-semibold text-foreground">
          {t("gettingStarted")}
        </h2>
        <p className="mt-2 text-sm text-foreground-muted">
          {t("gettingStartedDescription")}
        </p>
      </div>
    </div>
  );
}
