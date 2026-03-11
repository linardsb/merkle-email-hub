import { Skeleton } from "@email-hub/ui/components/ui/skeleton";

export default function FailurePatternsLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton
            key={i}
            className="h-24 rounded-lg border border-card-border"
          />
        ))}
      </div>
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-64 rounded-lg border border-card-border" />
    </div>
  );
}
