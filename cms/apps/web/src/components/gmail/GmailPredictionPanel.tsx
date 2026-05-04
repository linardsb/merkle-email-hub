"use client";

import { useState } from "react";
import { Mail, ChevronDown, ChevronUp, Loader2 } from "../icons";
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
      className="text-foreground-muted flex w-full items-center justify-between py-1 text-xs font-medium"
    >
      <span>{label}</span>
      {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
    </button>
  );
}

export function GmailPredictionPanel({
  html,
  subject: initialSubject,
  fromName: initialFromName,
  onHtmlUpdate,
}: GmailPredictionPanelProps) {
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
    <div className="bg-surface-muted rounded-lg p-3">
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mb-2 flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Mail className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium tracking-wider uppercase">
            {"Gmail Intelligence"}
          </h3>
        </div>
        {expanded ? (
          <ChevronUp className="text-foreground-muted h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="text-foreground-muted h-3.5 w-3.5" />
        )}
      </button>

      {!expanded && !predict.data && (
        <p className="text-foreground-muted text-xs">
          {"Run a prediction to see Gmail AI summary analysis."}
        </p>
      )}

      {expanded && (
        <div className="space-y-3">
          {/* Section 1: Gmail AI Summary */}
          <div>
            <SectionHeader
              label={"Gmail AI Summary"}
              expanded={showPredict}
              onToggle={() => setShowPredict((v) => !v)}
            />
            {showPredict && (
              <div className="mt-1.5 space-y-2">
                {/* Input fields */}
                <div className="space-y-1.5">
                  <div>
                    <label className="text-foreground-muted text-[10px]">{"Subject Line"}</label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder={"Enter email subject"}
                      className="border-border bg-card text-foreground placeholder:text-foreground-muted focus:ring-accent-primary mt-0.5 w-full rounded-md border px-2 py-1 text-xs focus:ring-1 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-foreground-muted text-[10px]">{"Sender Name"}</label>
                    <input
                      type="text"
                      value={fromName}
                      onChange={(e) => setFromName(e.target.value)}
                      placeholder={"Enter sender name"}
                      className="border-border bg-card text-foreground placeholder:text-foreground-muted focus:ring-accent-primary mt-0.5 w-full rounded-md border px-2 py-1 text-xs focus:ring-1 focus:outline-none"
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
                  className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {predict.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {"Predicting…"}
                    </>
                  ) : (
                    "Predict Summary"
                  )}
                </button>
                {predict.error && (
                  <p className="text-status-error text-xs">{predict.error.message}</p>
                )}

                {/* Prediction result */}
                {predict.data && (
                  <>
                    <SummaryCardPreview prediction={predict.data} />

                    {/* Optimize section */}
                    <div className="border-border border-t pt-2">
                      <div>
                        <label className="text-foreground-muted text-[10px]">
                          {"Target Summary (optional)"}
                        </label>
                        <input
                          type="text"
                          value={targetSummary}
                          onChange={(e) => setTargetSummary(e.target.value)}
                          placeholder={"Desired summary focus"}
                          className="border-border bg-card text-foreground placeholder:text-foreground-muted focus:ring-accent-primary mt-0.5 w-full rounded-md border px-2 py-1 text-xs focus:ring-1 focus:outline-none"
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
                        className="bg-primary text-primary-foreground hover:bg-primary/90 mt-1.5 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                      >
                        {optimize.isMutating ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            {"Optimizing…"}
                          </>
                        ) : (
                          "Optimize Preview"
                        )}
                      </button>
                      {optimize.error && (
                        <p className="text-status-error mt-1 text-xs">{optimize.error.message}</p>
                      )}
                    </div>

                    {/* Optimize results */}
                    {optimize.data && (
                      <div className="border-border bg-card space-y-1.5 rounded border p-2.5">
                        {optimize.data.suggested_subjects.length > 0 && (
                          <div>
                            <h4 className="text-foreground-muted text-[10px] font-medium">
                              {"Suggested Subjects"}
                            </h4>
                            {optimize.data.suggested_subjects.map((s, i) => (
                              <p key={i} className="text-foreground text-xs">
                                {s}
                              </p>
                            ))}
                          </div>
                        )}
                        {optimize.data.suggested_previews.length > 0 && (
                          <div>
                            <h4 className="text-foreground-muted text-[10px] font-medium">
                              {"Suggested Previews"}
                            </h4>
                            {optimize.data.suggested_previews.map((p, i) => (
                              <p key={i} className="text-foreground text-xs">
                                {p}
                              </p>
                            ))}
                          </div>
                        )}
                        {optimize.data.reasoning && (
                          <div>
                            <h4 className="text-foreground-muted text-[10px] font-medium">
                              {"Reasoning"}
                            </h4>
                            <p className="text-foreground-muted text-[10px]">
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
          <div className="border-border border-t pt-2">
            <SectionHeader
              label={"Deliverability Score"}
              expanded={showDeliverability}
              onToggle={() => setShowDeliverability((v) => !v)}
            />
            {showDeliverability && (
              <div className="mt-1.5 space-y-2">
                <button
                  type="button"
                  disabled={deliverability.isMutating}
                  onClick={() => deliverability.trigger({ html })}
                  className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {deliverability.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {"Scoring…"}
                    </>
                  ) : (
                    "Score Deliverability"
                  )}
                </button>
                {deliverability.error && (
                  <p className="text-status-error text-xs">{deliverability.error.message}</p>
                )}
                {deliverability.data && <DeliverabilityGauge result={deliverability.data} />}
              </div>
            )}
          </div>

          {/* Section 3: Schema.org Markup */}
          <div className="border-border border-t pt-2">
            <SectionHeader
              label={"Schema.org Markup"}
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
                  className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {schema.isMutating ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {"Injecting…"}
                    </>
                  ) : (
                    "Inject Schema"
                  )}
                </button>
                {schema.error && (
                  <p className="text-status-error text-xs">{schema.error.message}</p>
                )}
                {schema.data && <SchemaPreview result={schema.data} onApply={onHtmlUpdate} />}
              </div>
            )}
          </div>

          {/* Section 4: BIMI Readiness */}
          <div className="border-border border-t pt-2">
            <SectionHeader
              label={"BIMI Readiness"}
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
