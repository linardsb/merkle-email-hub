import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { SessionProvider } from "next-auth/react";
import { Toaster } from "sonner";
import { SWRConfig } from "swr";
import { ThemeProvider } from "@merkle-email-hub/ui/components/theme-provider";
import "@merkle-email-hub/ui/globals.css";

export const metadata: Metadata = {
  title: "Centralised email development platform with AI-powered agents",
  description: "Centralised email development platform with AI-powered agents",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();

  const swrConfig = { revalidateOnFocus: false, dedupingInterval: 5000 };

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className="bg-surface text-foreground antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <SessionProvider>
            <NextIntlClientProvider messages={messages}>
              <SWRConfig value={swrConfig}>
                {children}
                <Toaster position="top-right" />
              </SWRConfig>
            </NextIntlClientProvider>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
