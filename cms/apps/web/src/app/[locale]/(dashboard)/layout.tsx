import Link from "next/link";
import { getMessages } from "next-intl/server";
import {
  LayoutDashboard,
  FolderOpen,

  Blocks,
  ClipboardCheck,
  Plug,
  BarChart3,
  BookOpen,
  LogOut,
} from "lucide-react";
import { ThemeToggle } from "@merkle-email-hub/ui/components/theme-toggle";
import { OfflineBanner } from "@/components/ui/offline-banner";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();

  const navItems: NavItem[] = [
    {
      href: `/${locale}`,
      label: (messages as any)?.nav?.dashboard || "Dashboard",
      icon: <LayoutDashboard className="h-5 w-5" />,
    },
    {
      href: `/${locale}/projects`,
      label: (messages as any)?.nav?.projects || "Projects",
      icon: <FolderOpen className="h-5 w-5" />,
    },

    {
      href: `/${locale}/components`,
      label: (messages as any)?.nav?.components || "Components",
      icon: <Blocks className="h-5 w-5" />,
    },
    {
      href: `/${locale}/approvals`,
      label: (messages as any)?.nav?.approvals || "Approvals",
      icon: <ClipboardCheck className="h-5 w-5" />,
    },
    {
      href: `/${locale}/connectors`,
      label: (messages as any)?.nav?.connectors || "Connectors",
      icon: <Plug className="h-5 w-5" />,
    },
    {
      href: `/${locale}/intelligence`,
      label: (messages as any)?.nav?.intelligence || "Intelligence",
      icon: <BarChart3 className="h-5 w-5" />,
    },
    {
      href: `/${locale}/knowledge`,
      label: (messages as any)?.nav?.knowledge || "Knowledge",
      icon: <BookOpen className="h-5 w-5" />,
    },
  ];

  const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

  return (
    <div className="flex h-screen flex-col">
      {/* Demo mode banner */}
      {isDemoMode && (
        <div className="flex items-center justify-center bg-interactive px-4 py-1.5 text-xs font-medium text-foreground-inverse">
          Demo Mode — Showing example data
        </div>
      )}
      <OfflineBanner />

      <div className="flex flex-1 overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-col bg-sidebar-bg text-sidebar-text md:flex">
        <div className="flex h-14 items-center border-b border-sidebar-border px-4">
          {/* Merkle logo */}
          <svg viewBox="0 0 160 32" className="h-7 w-auto" aria-label="Merkle Email Hub">
            {/* Red chevron mark */}
            <polygon points="0,2 12,16 0,30" fill="#E4002B" />
            {/* MERKLE text */}
            <text x="18" y="22" fontFamily="Inter, Arial, sans-serif" fontSize="18" fontWeight="700" fill="currentColor" className="text-sidebar-text-active">MERKLE</text>
          </svg>
        </div>
        <nav className="flex-1 space-y-1 px-2 py-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-text transition-colors hover:bg-sidebar-hover hover:text-sidebar-text-active"
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-sidebar-border p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <Link
              href={`/${locale}/login`}
              className="flex items-center gap-3 text-sm text-sidebar-text transition-colors hover:text-sidebar-text-active"
            >
              <LogOut className="h-5 w-5" />
              {(messages as any)?.nav?.logout || "Logout"}
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-surface p-6">
        {children}
      </main>
      </div>
    </div>
  );
}
