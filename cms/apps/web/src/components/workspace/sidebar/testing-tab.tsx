"use client";

import { useTranslations } from "next-intl";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@email-hub/ui/components/ui/accordion";
import { VisualQAPanelTab } from "@/components/visual-qa/visual-qa-panel-tab";
import { ChaosTestPanel } from "@/components/qa/ChaosTestPanel";
import { PropertyTestPanel } from "@/components/qa/PropertyTestPanel";
import type { VisualQAEntityType } from "@/types/rendering";

interface TestingTabProps {
  html?: string;
  entityType?: VisualQAEntityType;
  entityId?: number;
}

export function TestingTab({ html, entityType, entityId }: TestingTabProps) {
  const t = useTranslations("workspace.sidebarTabs");

  return (
    <div className="flex-1 overflow-y-auto">
      <Accordion type="single" collapsible className="px-4">
        {html && entityType && entityId && (
          <AccordionItem value="visual-qa">
            <AccordionTrigger className="py-3 text-sm">
              {t("visualQA")}
            </AccordionTrigger>
            <AccordionContent>
              <VisualQAPanelTab
                html={html}
                entityType={entityType}
                entityId={entityId}
              />
            </AccordionContent>
          </AccordionItem>
        )}

        {html && (
          <AccordionItem value="chaos">
            <AccordionTrigger className="py-3 text-sm">
              {t("chaosTest")}
            </AccordionTrigger>
            <AccordionContent>
              <ChaosTestPanel html={html} />
            </AccordionContent>
          </AccordionItem>
        )}

        <AccordionItem value="property">
          <AccordionTrigger className="py-3 text-sm">
            {t("propertyTest")}
          </AccordionTrigger>
          <AccordionContent>
            <PropertyTestPanel />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
