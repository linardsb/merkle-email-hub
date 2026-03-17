"use client";

import { useTranslations } from "next-intl";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@email-hub/ui/components/ui/accordion";
import { OutlookAdvisorPanel } from "@/components/outlook/OutlookAdvisorPanel";
import { CSSCompilerPanel } from "@/components/email-engine/CSSCompilerPanel";
import { GmailPredictionPanel } from "@/components/gmail/GmailPredictionPanel";

interface EmailClientsTabProps {
  html?: string;
  onHtmlUpdate?: (html: string) => void;
}

export function EmailClientsTab({ html, onHtmlUpdate }: EmailClientsTabProps) {
  const t = useTranslations("workspace.sidebarTabs");

  return (
    <div className="flex-1 overflow-y-auto">
      <Accordion type="single" collapsible className="px-4">
        {html && (
          <AccordionItem value="outlook">
            <AccordionTrigger className="py-3 text-sm">
              {t("outlookAdvisor")}
            </AccordionTrigger>
            <AccordionContent>
              <OutlookAdvisorPanel html={html} onHtmlUpdate={onHtmlUpdate} />
            </AccordionContent>
          </AccordionItem>
        )}

        {html && (
          <AccordionItem value="css">
            <AccordionTrigger className="py-3 text-sm">
              {t("cssCompiler")}
            </AccordionTrigger>
            <AccordionContent>
              <CSSCompilerPanel html={html} onHtmlUpdate={onHtmlUpdate} />
            </AccordionContent>
          </AccordionItem>
        )}

        {html && (
          <AccordionItem value="gmail">
            <AccordionTrigger className="py-3 text-sm">
              {t("gmailIntelligence")}
            </AccordionTrigger>
            <AccordionContent>
              <GmailPredictionPanel html={html} onHtmlUpdate={onHtmlUpdate} />
            </AccordionContent>
          </AccordionItem>
        )}

        {!html && (
          <p className="py-4 text-center text-xs text-muted-foreground">
            {t("compileFirst")}
          </p>
        )}
      </Accordion>
    </div>
  );
}
