"use client";

import { useSession } from "next-auth/react";
import { MCPConfigPanel } from "@/components/settings/MCPConfigPanel";

export default function SettingsPage() {
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === "admin";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-foreground text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Manage your account preferences and platform configuration
        </p>
      </div>

      {/* MCP Configuration (admin-only) */}
      {isAdmin && (
        <section className="border-default bg-card rounded-lg border p-6">
          <h2 className="text-foreground mb-4 text-lg font-semibold">MCP Server</h2>
          <MCPConfigPanel />
        </section>
      )}

      {/* Placeholder for future settings sections */}
      <section className="border-default bg-card rounded-lg border p-6">
        <h2 className="text-foreground text-lg font-semibold">Preferences</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          Additional settings and preferences will be available here.
        </p>
        <div className="text-muted-foreground mt-4 text-sm italic">
          More preferences coming soon.
        </div>
      </section>
    </div>
  );
}
