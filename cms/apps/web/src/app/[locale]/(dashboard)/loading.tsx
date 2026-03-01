import { SkeletonStatsRow, SkeletonCard } from "@/components/ui/skeletons";

export default function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48" />
      <SkeletonStatsRow />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
