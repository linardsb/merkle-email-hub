"use client";

import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Loader2 } from "../../components/icons";
import { z } from "zod";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});
  const [isPending, startTransition] = useTransition();

  const loginSchema = z.object({
    username: z.string().min(1, "Email is required").email("Enter a valid email address"),
    password: z.string().min(1, "Password is required"),
  });

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const formData = new FormData(e.currentTarget);
    const username = formData.get("username") as string;
    const password = formData.get("password") as string;

    const parsed = loginSchema.safeParse({ username, password });
    if (!parsed.success) {
      const flat = parsed.error.flatten().fieldErrors;
      setFieldErrors({
        username: flat.username?.[0],
        password: flat.password?.[0],
      });
      return;
    }
    setFieldErrors({});

    startTransition(async () => {
      const result = await signIn("credentials", {
        username,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Invalid email or password");
      } else {
        router.push("/");
        router.refresh();
      }
    });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <div className="w-full max-w-[24rem] rounded-lg border border-border bg-surface-elevated p-8 shadow-sm">
        <h1 className="mb-6 text-center text-2xl font-semibold text-foreground">
          {"Sign In"}
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
              {"Email"}
            </label>
            <input
              id="username"
              name="username"
              type="email"
              autoComplete="email"
              onChange={() => fieldErrors.username && setFieldErrors(prev => ({ ...prev, username: undefined }))}
              className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
              placeholder={"Enter your email"}
            />
            {fieldErrors.username && (
              <p className="text-xs text-status-danger">{fieldErrors.username}</p>
            )}
          </div>

          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-sm font-medium text-foreground"
            >
              {"Password"}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              onChange={() => fieldErrors.password && setFieldErrors(prev => ({ ...prev, password: undefined }))}
              className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
              placeholder={"Enter your password"}
            />
            {fieldErrors.password && (
              <p className="text-xs text-status-danger">{fieldErrors.password}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isPending}
            className="w-full rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover focus:outline-none focus:ring-2 focus:ring-interactive focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? (
              <span className="flex items-center justify-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Signing in..."}
              </span>
            ) : (
              "Sign In"
            )}
          </button>

        </form>
      </div>
    </div>
  );
}
