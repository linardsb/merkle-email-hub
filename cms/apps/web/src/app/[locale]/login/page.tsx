"use client";

import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";

export default function LoginPage() {
  const t = useTranslations("login");
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const formData = new FormData(e.currentTarget);
    const username = formData.get("username") as string;
    const password = formData.get("password") as string;

    startTransition(async () => {
      const result = await signIn("credentials", {
        username,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError(t("error"));
      } else {
        router.push("/dashboard");
        router.refresh();
      }
    });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface-elevated p-8 shadow-sm">
        <h1 className="mb-6 text-center text-2xl font-semibold text-foreground">
          {t("title")}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-badge-danger-bg p-3 text-sm text-badge-danger-text">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label
              htmlFor="username"
              className="text-sm font-medium text-foreground"
            >
              {t("username")}
            </label>
            <input
              id="username"
              name="username"
              type="text"
              required
              autoComplete="username"
              className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
              placeholder={t("usernamePlaceholder")}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-sm font-medium text-foreground"
            >
              {t("password")}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
              placeholder={t("passwordPlaceholder")}
            />
          </div>

          <button
            type="submit"
            disabled={isPending}
            className="w-full rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover focus:outline-none focus:ring-2 focus:ring-interactive focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? t("signingIn") : t("signIn")}
          </button>
        </form>
      </div>
    </div>
  );
}
