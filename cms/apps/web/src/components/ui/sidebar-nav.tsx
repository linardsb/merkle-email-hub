"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export function SidebarNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-1 px-2 py-4">
      {items.map((item) => {
        // Exact match for dashboard root, startsWith for other routes
        const isRoot = item.href === "/";
        const isActive = isRoot ? pathname === "/" : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
              isActive
                ? "bg-sidebar-active text-sidebar-text-active"
                : "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
            }`}
          >
            {item.icon}
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
