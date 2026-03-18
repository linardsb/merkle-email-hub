"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@email-hub/ui/components/ui/accordion";
import { OntologySyncPanel } from "@/components/knowledge/OntologySyncPanel";
import { CompetitiveReportPanel } from "@/components/knowledge/CompetitiveReportPanel";

export function IntelligenceTab() {
  return (
    <div className="flex-1 overflow-y-auto">
      <Accordion type="single" collapsible className="px-4">
        <AccordionItem value="ontology">
          <AccordionTrigger className="py-3 text-sm">
            {"Ontology Sync"}
          </AccordionTrigger>
          <AccordionContent>
            <OntologySyncPanel />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="competitive">
          <AccordionTrigger className="py-3 text-sm">
            {"Competitive Intelligence"}
          </AccordionTrigger>
          <AccordionContent>
            <CompetitiveReportPanel />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
