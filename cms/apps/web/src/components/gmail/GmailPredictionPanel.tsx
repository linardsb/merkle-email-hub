"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Mail,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import {
  useGmailPredict,
  useGmailOptimize,
  useDeliverabilityScore,
} from "@/hooks/use-gmail-intelligence";
import { useSchemaInject } from "@/hooks/use-schema-inject";
import { SummaryCardPreview } from "./SummaryCardPreview";
import { DeliverabilityGauge } from "./DeliverabilityGauge";
import { SchemaPreview } from "./SchemaPreview";
import { BIMIStatusBadge } from "./BIMIStatusBadge";

interface GmailPredictionPanelProps {
  html: string;
  subject?: string;
  fromName?: string;
  onHtmlUpdate?: (html: string) => void;
}

function SectionHeader({
  label,
  expanded,
  onToggle,
}: {
  label: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between py-1 text-xs font-medium text-foreground-muted"
    >
      <span>{label}</span>
      {expanded ? (
        <ChevronUp className="h-3.5 w-3.5" />
      ) : (
        <ChevronDown className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

export function GmailPredictionPanel({
  html,
  subject: initialSubject,
  fromName: initialFromName,
  onHtmlUpdate,
}: GmailPredictionPanelProps) {
  const t = useTranslations("gmailIntelligence");

  // Section visibility
  const [expanded, setExpanded] = useState(true);
  const [showPredict, setShowPredict] = useState(true);
  const [showDeliverability, setShowDeliverability] = useState(false);
  const [showSchema, setShowSchema] = useState(false);
  const [showBIMI, setShowBIMI] = useState(false);

  // Input fields
  const [subject, setSubject] = useState(initialSubject ?? "");
  const [fromName, setFromName] = useState(initialFromName ?? "");
  const [targetSummary, setTargetSummary] = useState("");

  // Hooks
  const predict = useGmailPredict();
  const optimize = useGmailOptimize();
  const deliverability = useDeliverabilityScore();
  const schema = useSchemaInject();

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mb-2 flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {t("title")}
          </h3>
        </div>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-foreground-muted" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-foreground-muted" />
        )}
      </button>

      {!expanded && !predict.data && (
        <p className="text-xs text-foreground-muted">{t("noResults")}</p>
      )}

      {expanded && (
        <div className="space-y-3">
          {/* Section 1: Gmail AI Summary */}
          <div>
            <SectionHeader
              label={t("predictedCategory")}
              expanded={showPredict}
              onToggle={() => setShowPredict((v) => !v)}
            />
            {showPredict && (
              <div className="mt-1.5 space-y-2">
                {/* Input fields */}
                <div className="space-y-1.5">
                  <div>
                    <label className="text-[10px] text-foreground-muted">
                      {t("subjectLabel")}
                    </label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder={t("subjectPlaceholder")}
                      className="mt-0.5 w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-accent-primary"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-foreground-muted">
                      {t("fromNameLabel")}
                    </label>
                    <input
                      type="text"
                      value={fromName}
                      onChange={(e) => setFromName(e.target.value)}
                      placeholder={t("fromNamePlaceholder")}
                      className="mt-0.5 w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-accent-primary"
                    />
                  </div>
                </div>

                {/* Predict button */}
                <button
                  type="button"
                  disabled={predict.isMutating || !subject.trim() || !fromName.trim()}
                  onClick={() =>
                    predict.trigger({
                      html,
                      subject: subject.trim(),
                      from_name: fromName.trim(),
                    })
                  }
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {predict.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {t("predicting")}
                    </>
                  ) : (
                    t("predictButton")
                  )}
                </button>
                {predict.error && (
                  <p className="text-xs text-status-error">
                    {predict.error.message}
                  </p>
                )}

                {/* Prediction result */}
                {predict.data && (
                  <>
                    <SummaryCardPreview prediction={predict.data} />

                    {/* Optimize section */}
                    <div className="border-t border-border pt-2">
                      <div>
                        <label className="text-[10px] text-foreground-muted">
                          {t("targetSummaryLabel")}
                        </label>
                        <input
                          type="text"
                          value={targetSummary}
                          onChange={(e) => setTargetSummary(e.target.value)}
                          placeholder={t("targetSummaryPlaceholder")}
                          className="mt-0.5 w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-accent-primary"
                        />
                      </div>
                      <button
                        type="button"
                        disabled={optimize.isMutating || !subject.trim() || !fromName.trim()}
                        onClick={() =>
                          optimize.trigger({
                            html,
                            subject: subject.trim(),
                            from_name: fromName.trim(),
                            target_summary: targetSummary.trim() || undefined,
                          })
                        }
                        className="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                      >
                        {optimize.isMutating ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            {t("optimizing")}
                          </>
                        ) : (
                          t("optimizeButton")
                        )}
                      </button>
                      {optimize.error && (
                        <p className="mt-1 text-xs text-status-error">
                          {optimize.error.message}
                        </p>
                      )}
                    </div>

                    {/* Optimize results */}
                    {optimize.data && (
                      <div className="rounded border border-border bg-card p-2.5 space-y-1.5">
                        {optimize.data.suggested_subjects.length > 0 && (
                          <div>
                            <h4 className="text-[10px] font-medium text-foreground-muted">
                              {t("suggestedSubjects")}
                            </h4>
                            {optimize.data.suggested_subjects.map((s, i) => (
                              <p key={i} className="text-xs text-foreground">
                                {s}
                              </p>
                            ))}
                          </div>
                        )}
                        {optimize.data.suggested_previews.length > 0 && (
                          <div>
                            <h4 className="text-[10px] font-medium text-foreground-muted">
                              {t("suggestedPreviews")}
                            </h4>
                            {optimize.data.suggested_previews.map((p, i) => (
                              <p key={i} className="text-xs text-foreground">
                                {p}
                              </p>
                            ))}
                          </div>
                        )}
                        {optimize.data.reasoning && (
                          <div>
                            <h4 className="text-[10px] font-medium text-foreground-muted">
                              {t("reasoning")}
                            </h4>
                            <p className="text-[10px] text-foreground-muted">
                              {optimize.data.reasoning}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Section 2: Deliverability Score */}
          <div className="border-t border-border pt-2">
            <SectionHeader
              label={t("deliverabilityScore")}
              expanded={showDeliverability}
              onToggle={() => setShowDeliverability((v) => !v)}
            />
            {showDeliverability && (
              <div className="mt-1.5 space-y-2">
                <button
                  type="button"
                  disabled={deliverability.isMutating}
                  onClick={() => deliverability.trigger({ html })}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {deliverability.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {t("scoring")}
                    </>
                  ) : (
                    t("scoreButton")
                  )}
                </button>
                {deliverability.error && (
                  <p className="text-xs text-status-error">
                    {deliverability.error.message}
                  </p>
                )}
                {deliverability.data && (
                  <DeliverabilityGauge result={deliverability.data} />
                )}
              </div>
            )}
          </div>

          {/* Section 3: Schema.org Markup */}
          <div className="border-t border-border pt-2">
            <SectionHeader
              label={t("schemaMarkup")}
              expanded={showSchema}
              onToggle={() => setShowSchema((v) => !v)}
            />
            {showSchema && (
              <div className="mt-1.5 space-y-2">
                <button
                  type="button"
                  disabled={schema.isMutating}
                  onClick={() =>
                    schema.trigger({
                      html,
                      subject: subject.trim() || undefined,
                    })
                  }
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {schema.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {t("injecting")}
                    </>
                  ) : (
                    t("injectButton")
                  )}
                </button>
                {schema.error && (
                  <p className="text-xs text-status-error">
                    {schema.error.message}
                  </p>
                )}
                {schema.data && (
                  <SchemaPreview
                    result={schema.data}
                    onApply={onHtmlUpdate}
                  />
                )}
              </div>
            )}
          </div>

          {/* Section 4: BIMI Readiness */}
          <div className="border-t border-border pt-2">
            <SectionHeader
              label={t("bimiReadiness")}
              expanded={showBIMI}
              onToggle={() => setShowBIMI((v) => !v)}
            />
            {showBIMI && (
              <div className="mt-1.5">
                <BIMIStatusBadge />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
