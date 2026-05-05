import { useCallback, useState } from "react";
import { toast } from "sonner";
import { fetcher } from "@/lib/swr-fetcher";
import type { useQARun } from "@/hooks/use-qa";
import type { QAResultResponse } from "@/types/qa";

interface QAArgs {
  compiledHtml: string | null;
  triggerQA: ReturnType<typeof useQARun>["trigger"];
  onOpen?: () => void;
}

export function useWorkspaceQA(args: QAArgs) {
  const { compiledHtml, triggerQA, onOpen } = args;
  const [qaResultData, setQaResultData] = useState<QAResultResponse | null>(null);
  const [qaPanelOpen, setQaPanelOpen] = useState(false);

  const handleRunQA = useCallback(async () => {
    if (!compiledHtml?.trim()) {
      toast.error("Compile the template first before running QA");
      return;
    }
    try {
      const result = await triggerQA({ html: compiledHtml });
      if (result) {
        setQaResultData(result);
        setQaPanelOpen(true);
        onOpen?.();
        if (result.passed) {
          toast.success("All QA checks passed");
        } else {
          toast.warning(`${result.checks_total - result.checks_passed} QA check(s) failed`);
        }
      }
    } catch {
      toast.error("QA check failed");
    }
  }, [compiledHtml, triggerQA, onOpen]);

  const handleQAOverrideSuccess = useCallback(() => {
    if (qaResultData?.id) {
      fetcher<QAResultResponse>(`/api/v1/qa/results/${qaResultData.id}`)
        .then((updated) => setQaResultData(updated))
        .catch(() => {
          /* override succeeded; panel will show stale data until next QA run */
        });
    }
  }, [qaResultData?.id]);

  return {
    qaResultData,
    setQaResultData,
    qaPanelOpen,
    setQaPanelOpen,
    handleRunQA,
    handleQAOverrideSuccess,
  };
}
