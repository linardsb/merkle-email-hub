import { SkeletonCard } from "@/components/ui/skeletons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";

export default function BriefsLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-8 w-36" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
