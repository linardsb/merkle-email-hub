import type { Metadata } from "next";
import { SessionProvider } from "next-auth/react";
import { Toaster } from "sonner";
import { SWRConfig } from "swr";
import { ThemeProvider } from "@email-hub/ui/components/theme-provider";
import "@email-hub/ui/globals.css";

export const metadata: Metadata = {
  title: "Centralised email development platform with AI-powered agents",
  description: "Centralised email development platform with AI-powered agents",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const swrConfig = { revalidateOnFocus: false, dedupingInterval: 5000 };

  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <body className="bg-surface text-foreground antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <SessionProvider>
            <SWRConfig value={swrConfig}>
              {children}
              <Toaster position="top-right" />
            </SWRConfig>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
