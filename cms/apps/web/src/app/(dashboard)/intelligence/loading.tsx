import { SkeletonStatsRow } from "@/components/ui/skeletons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";

export default function IntelligenceLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <SkeletonStatsRow count={4} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="border-card-border h-64 rounded-lg border" />
        <Skeleton className="border-card-border h-64 rounded-lg border" />
      </div>
    </div>
  );
}
