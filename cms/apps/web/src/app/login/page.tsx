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
    <div className="bg-surface flex min-h-screen items-center justify-center">
      <div className="border-border bg-surface-elevated w-full max-w-[24rem] rounded-lg border p-8 shadow-sm">
        <h1 className="text-foreground mb-6 text-center text-2xl font-semibold">{"Sign In"}</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-badge-danger-bg text-badge-danger-text rounded-md p-3 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="username" className="text-foreground text-sm font-medium">
              {"Email"}
            </label>
            <input
              id="username"
              name="username"
              type="email"
              autoComplete="email"
              onChange={() =>
                fieldErrors.username && setFieldErrors((prev) => ({ ...prev, username: undefined }))
              }
              className="border-input-border bg-input-bg text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:ring-input-focus w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
              placeholder={"Enter your email"}
            />
            {fieldErrors.username && (
              <p className="text-status-danger text-xs">{fieldErrors.username}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-foreground text-sm font-medium">
              {"Password"}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              onChange={() =>
                fieldErrors.password && setFieldErrors((prev) => ({ ...prev, password: undefined }))
              }
              className="border-input-border bg-input-bg text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:ring-input-focus w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
              placeholder={"Enter your password"}
            />
            {fieldErrors.password && (
              <p className="text-status-danger text-xs">{fieldErrors.password}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isPending}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover focus:ring-interactive w-full rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
