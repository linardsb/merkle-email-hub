import Link from "next/link";
import {
  BookOpen,
  ChartLine,
  ClipboardCheck,
  Cog,
  FileCode,
  Devices,
  FileText,
  FolderOpen,
  Globe,
  LayoutDashboard,
  LogOut,
  Paintbrush,
  Plug,
} from "../../components/icons";
import { ThemeToggle } from "@email-hub/ui/components/theme-toggle";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { SidebarNav } from "@/components/ui/sidebar-nav";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const navItems: NavItem[] = [
    {
      href: "/",
      label: "Dashboard",
      icon: <LayoutDashboard className="h-5 w-5" />,
    },
    {
      href: "/projects",
      label: "Projects",
      icon: <FolderOpen className="h-5 w-5" />,
    },
    {
      href: "/components",
      label: "Components",
      icon: <FileCode className="h-5 w-5" />,
    },
    {
      href: "/approvals",
      label: "Approvals",
      icon: <ClipboardCheck className="h-5 w-5" />,
    },
    {
      href: "/connectors",
      label: "Connectors",
      icon: <Plug className="h-5 w-5" />,
    },
    {
      href: "/intelligence",
      label: "Intelligence",
      icon: <ChartLine className="h-5 w-5" />,
    },
    {
      href: "/knowledge",
      label: "Knowledge",
      icon: <BookOpen className="h-5 w-5" />,
    },
    {
      href: "/renderings",
      label: "Renderings",
      icon: <Devices className="h-5 w-5" />,
    },
    {
      href: "/design-sync",
      label: "Design Sync",
      icon: <Paintbrush className="h-5 w-5" />,
    },
    {
      href: "/briefs",
      label: "Briefs",
      icon: <FileText className="h-5 w-5" />,
    },
    {
      href: "/ecosystem",
      label: "Ecosystem",
      icon: <Globe className="h-5 w-5" />,
    },
    {
      href: "/settings",
      label: "Settings",
      icon: <Cog className="h-5 w-5" />,
    },
  ];

  return (
    <div className="flex h-screen flex-col">
      <OfflineBanner />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="bg-sidebar-bg text-sidebar-text hidden w-60 flex-col md:flex">
          <div className="border-sidebar-border h-14 shrink-0 border-b" />
          <div className="flex-1 overflow-y-auto">
            <SidebarNav items={navItems} />
          </div>
          <div className="border-sidebar-border border-t p-2">
            <div className="flex items-center justify-between px-3 py-2">
              <Link
                href="/login"
                className="text-sidebar-text hover:text-sidebar-text-active flex items-center gap-3 text-sm transition-colors"
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
        <main className="bg-surface flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
