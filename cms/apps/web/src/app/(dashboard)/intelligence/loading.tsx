import { SkeletonStatsRow } from "@/components/ui/skeletons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";

export default function IntelligenceLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <SkeletonStatsRow count={4} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-lg border border-card-border" />
        <Skeleton className="h-64 rounded-lg border border-card-border" />
      </div>
    </div>
  );
}
