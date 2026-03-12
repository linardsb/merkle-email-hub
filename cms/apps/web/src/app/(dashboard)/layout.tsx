import Link from "next/link";
import Image from "next/image";
import { getMessages } from "next-intl/server";
import { LogOut } from "lucide-react";
import { ThemeToggle } from "@email-hub/ui/components/theme-toggle";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { SidebarNav } from "@/components/ui/sidebar-nav";
import { LocaleSelector } from "@/components/ui/locale-selector";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const messages = await getMessages();

  const navItems: NavItem[] = [
    {
      href: "/",
      label: (messages as any)?.nav?.dashboard || "Dashboard",
      icon: <Image src="/icons/brand/dashboard.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/projects",
      label: (messages as any)?.nav?.projects || "Projects",
      icon: <Image src="/icons/brand/projects.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/components",
      label: (messages as any)?.nav?.components || "Components",
      icon: <Image src="/icons/brand/components.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/approvals",
      label: (messages as any)?.nav?.approvals || "Approvals",
      icon: <Image src="/icons/brand/approvals.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/connectors",
      label: (messages as any)?.nav?.connectors || "Connectors",
      icon: <Image src="/icons/brand/connectors.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/intelligence",
      label: (messages as any)?.nav?.intelligence || "Intelligence",
      icon: <Image src="/icons/brand/intelligence.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/knowledge",
      label: (messages as any)?.nav?.knowledge || "Knowledge",
      icon: <Image src="/icons/brand/knowledge.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/renderings",
      label: (messages as any)?.nav?.renderings || "Renderings",
      icon: <Image src="/icons/brand/renderings.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/design-sync",
      label: (messages as any)?.nav?.designSync || "Design Sync",
      icon: <Image src="/icons/brand/figma.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/briefs",
      label: (messages as any)?.nav?.briefs || "Briefs",
      icon: <Image src="/icons/brand/briefs.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/settings",
      label: (messages as any)?.nav?.settings || "Settings",
      icon: <Image src="/icons/brand/settings.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
  ];

  return (
    <div className="flex h-screen flex-col">
      <OfflineBanner />

      <div className="flex flex-1 overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-col bg-sidebar-bg text-sidebar-text md:flex">
        <div className="flex h-14 items-center border-b border-sidebar-border px-3">
          <span className="text-sm font-semibold text-sidebar-text">Email Hub</span>
        </div>
        <SidebarNav items={navItems} />
        <div className="border-t border-sidebar-border p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <Link
              href="/login"
              className="flex items-center gap-3 text-sm text-sidebar-text transition-colors hover:text-sidebar-text-active"
            >
              <LogOut className="h-5 w-5" />
              {(messages as any)?.nav?.logout || "Logout"}
            </Link>
            <div className="flex items-center gap-2">
              <LocaleSelector />
              <ThemeToggle />
            </div>
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
