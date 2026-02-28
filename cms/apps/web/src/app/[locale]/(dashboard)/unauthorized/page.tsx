import { useTranslations } from "next-intl";
import { ShieldX } from "lucide-react";
import Link from "next/link";

export default function UnauthorizedPage() {
  const t = useTranslations("unauthorized");

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <ShieldX className="h-16 w-16 text-status-danger" />
      <h1 className="mt-4 text-2xl font-semibold text-foreground">
        {t("title")}
      </h1>
      <p className="mt-2 text-foreground-muted">{t("description")}</p>
      <Link
        href="/dashboard"
        className="mt-6 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
      >
        {t("backToDashboard")}
      </Link>
    </div>
  );
}
