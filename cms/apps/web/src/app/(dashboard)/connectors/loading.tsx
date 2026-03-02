import { SkeletonCard } from "@/components/ui/skeletons";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";

export default function ConnectorsLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
