"use client";

import { useSession } from "next-auth/react";
import { MCPConfigPanel } from "@/components/settings/MCPConfigPanel";

export default function SettingsPage() {
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === "admin";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage your account preferences and platform configuration</p>
      </div>

      {/* MCP Configuration (admin-only) */}
      {isAdmin && (
        <section className="rounded-lg border border-default bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">MCP Server</h2>
          <MCPConfigPanel />
        </section>
      )}

      {/* Placeholder for future settings sections */}
      <section className="rounded-lg border border-default bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground">Preferences</h2>
        <p className="mt-1 text-sm text-muted-foreground">Additional settings and preferences will be available here.</p>
        <div className="mt-4 text-sm text-muted-foreground italic">More preferences coming soon.</div>
      </section>
    </div>
  );
}
