import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold text-foreground-muted">404</h1>
      <p className="mt-4 text-lg text-foreground-muted">Page not found</p>
      <Link
        href="/dashboard"
        className="mt-6 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
