import { ShieldX } from "../../../components/icons";
import Link from "next/link";

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <ShieldX className="text-status-danger h-16 w-16" />
      <h1 className="text-foreground mt-4 text-2xl font-semibold">{"Access Denied"}</h1>
      <p className="text-foreground-muted mt-2">
        {"You do not have permission to view this page."}
      </p>
      <Link
        href="/"
        className="bg-interactive text-foreground-inverse hover:bg-interactive-hover mt-6 rounded-md px-4 py-2 text-sm font-medium transition-colors"
      >
        {"Back to Dashboard"}
      </Link>
    </div>
  );
}
