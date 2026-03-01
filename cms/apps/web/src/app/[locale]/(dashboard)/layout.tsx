import Link from "next/link";
import { getMessages } from "next-intl/server";
import {
  LayoutDashboard,
  FolderOpen,
  List,
  Blocks,
  ClipboardCheck,
  Users,
  LogOut,
} from "lucide-react";
import { ThemeToggle } from "@merkle-email-hub/ui/components/theme-toggle";

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
      href: `/${locale}/dashboard`,
      label: (messages as any)?.nav?.dashboard || "Dashboard",
      icon: <LayoutDashboard className="h-5 w-5" />,
    },
    {
      href: `/${locale}/projects`,
      label: (messages as any)?.nav?.projects || "Projects",
      icon: <FolderOpen className="h-5 w-5" />,
    },
    {
      href: `/${locale}/example`,
      label: (messages as any)?.nav?.example || "Items",
      icon: <List className="h-5 w-5" />,
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
      href: `/${locale}/users`,
      label: (messages as any)?.nav?.users || "Users",
      icon: <Users className="h-5 w-5" />,
    },
  ];

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-col bg-sidebar-bg text-sidebar-text md:flex">
        <div className="flex h-14 items-center border-b border-sidebar-border px-4">
          <span className="text-lg font-semibold text-sidebar-text-active">
            merkle-email-hub
          </span>
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
  );
}
