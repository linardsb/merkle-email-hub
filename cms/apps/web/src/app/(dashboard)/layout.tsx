import Link from "next/link";
import Image from "next/image";
import { LogOut } from "lucide-react";
import { ThemeToggle } from "@email-hub/ui/components/theme-toggle";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { SidebarNav } from "@/components/ui/sidebar-nav";


interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const navItems: NavItem[] = [
    {
      href: "/",
      label: "Dashboard",
      icon: <Image src="/icons/brand/dashboard.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/projects",
      label: "Projects",
      icon: <Image src="/icons/brand/projects.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/components",
      label: "Components",
      icon: <Image src="/icons/brand/components.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/approvals",
      label: "Approvals",
      icon: <Image src="/icons/brand/approvals.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/connectors",
      label: "Connectors",
      icon: <Image src="/icons/brand/connectors.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/intelligence",
      label: "Intelligence",
      icon: <Image src="/icons/brand/intelligence.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/knowledge",
      label: "Knowledge",
      icon: <Image src="/icons/brand/knowledge.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/renderings",
      label: "Renderings",
      icon: <Image src="/icons/brand/renderings.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/design-sync",
      label: "Design Sync",
      icon: <Image src="/icons/brand/figma.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/briefs",
      label: "Briefs",
      icon: <Image src="/icons/brand/briefs.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/ecosystem",
      label: "Ecosystem",
      icon: <Image src="/icons/brand/ecosystem.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
    {
      href: "/settings",
      label: "Settings",
      icon: <Image src="/icons/brand/settings.svg" alt="" width={20} height={20} className="h-5 w-5" />,
    },
  ];

  return (
    <div className="flex h-screen flex-col">
      <OfflineBanner />

      <div className="flex flex-1 overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-col bg-sidebar-bg text-sidebar-text md:flex">
        <div className="h-14 shrink-0 border-b border-sidebar-border" />
        <div className="flex-1 overflow-y-auto">
          <SidebarNav items={navItems} />
        </div>
        <div className="border-t border-sidebar-border p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <Link
              href="/login"
              className="flex items-center gap-3 text-sm text-sidebar-text transition-colors hover:text-sidebar-text-active"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </Link>
            <div className="flex items-center gap-2">
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
