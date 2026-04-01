import { ShieldX } from "../../../components/icons";
import Link from "next/link";

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <ShieldX className="h-16 w-16 text-status-danger" />
      <h1 className="mt-4 text-2xl font-semibold text-foreground">
        {"Access Denied"}
      </h1>
      <p className="mt-2 text-foreground-muted">{"You do not have permission to view this page."}</p>
      <Link
        href="/"
        className="mt-6 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
      >
        {"Back to Dashboard"}
      </Link>
    </div>
  );
}
