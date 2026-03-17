"use client";

import { useTranslations } from "next-intl";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@email-hub/ui/components/ui/accordion";
import { OntologySyncPanel } from "@/components/knowledge/OntologySyncPanel";
import { CompetitiveReportPanel } from "@/components/knowledge/CompetitiveReportPanel";

export function IntelligenceTab() {
  const t = useTranslations("workspace.sidebarTabs");

  return (
    <div className="flex-1 overflow-y-auto">
      <Accordion type="single" collapsible className="px-4">
        <AccordionItem value="ontology">
          <AccordionTrigger className="py-3 text-sm">
            {t("ontologySync")}
          </AccordionTrigger>
          <AccordionContent>
            <OntologySyncPanel />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="competitive">
          <AccordionTrigger className="py-3 text-sm">
            {t("competitiveIntel")}
          </AccordionTrigger>
          <AccordionContent>
            <CompetitiveReportPanel />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
