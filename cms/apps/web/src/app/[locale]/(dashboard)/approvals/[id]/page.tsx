"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { useApproval, useBuild } from "@/hooks/use-approvals";
import { ApprovalStatusBadge } from "@/components/approvals/approval-status-badge";
import { ApprovalPreview } from "@/components/approvals/approval-preview";
import { ApprovalFeedbackPanel } from "@/components/approvals/approval-feedback-panel";
import { ApprovalAuditTimeline } from "@/components/approvals/approval-audit-timeline";
import { ApprovalDecisionBar } from "@/components/approvals/approval-decision-bar";

type Tab = "feedback" | "audit";

export default function ApprovalDetailPage() {
  const t = useTranslations("approvals");
  const params = useParams();
  const locale = params.locale as string;
  const approvalId = Number(params.id);

  const {
    data: approval,
    isLoading,
    error,
    mutate,
  } = useApproval(approvalId);
  const { data: build } = useBuild(approval?.build_id ?? null);

  const [activeTab, setActiveTab] = useState<Tab>("feedback");

  const handleDecisionMade = useCallback(() => {
    mutate();
  }, [mutate]);

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48 rounded" />
        <div className="grid gap-6 lg:grid-cols-5">
          <Skeleton className="h-96 rounded-lg border border-card-border lg:col-span-3" />
          <Skeleton className="h-96 rounded-lg border border-card-border lg:col-span-2" />
        </div>
      </div>
    );
  }

  if (error || !approval) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="text-sm text-status-danger">{t("error")}</p>
        <button
          type="button"
          onClick={() => mutate()}
          className="mt-3 text-sm text-interactive hover:underline"
        >
          {t("retry")}
        </button>
        <Link
          href={`/${locale}/approvals`}
          className="mt-2 text-sm text-interactive hover:underline"
        >
          {t("back")}
        </Link>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "feedback", label: t("feedbackTab") },
    { key: "audit", label: t("auditTab") },
  ];

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
        <div className="flex items-center gap-3">
          <Link
            href={`/${locale}/approvals`}
            className="flex items-center gap-1 text-sm text-foreground-muted transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </Link>
          <span className="text-foreground-muted">/</span>
          <h1 className="text-sm font-semibold text-foreground">
            Build #{approval.build_id}
          </h1>
          <ApprovalStatusBadge status={approval.status} />
        </div>
        <div className="flex items-center gap-3 text-xs text-foreground-muted">
          <span>
            {t("requestedBy", { userId: approval.requested_by_id })}
          </span>
          <span>&middot;</span>
          <span>
            {new Date(approval.created_at as string).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Main content: 2-column */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Preview */}
        <div className="flex-[3] border-r border-border">
          <ApprovalPreview compiledHtml={build?.compiled_html ?? null} />
        </div>

        {/* Right: Side panel */}
        <div className="flex flex-[2] flex-col">
          {/* Tabs */}
          <div className="flex border-b border-border" role="tablist">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "border-b-2 border-interactive text-foreground"
                    : "text-foreground-muted hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "feedback" && (
              <ApprovalFeedbackPanel approvalId={approvalId} />
            )}
            {activeTab === "audit" && (
              <ApprovalAuditTimeline approvalId={approvalId} />
            )}
          </div>

          {/* Decision bar */}
          <ApprovalDecisionBar
            approvalId={approvalId}
            currentStatus={approval.status}
            onDecisionMade={handleDecisionMade}
          />
        </div>
      </div>
    </div>
  );
}
