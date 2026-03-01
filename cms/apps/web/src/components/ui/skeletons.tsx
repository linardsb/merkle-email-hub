import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";

export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="mt-2 h-4 w-full" />
      <Skeleton className="mt-1 h-4 w-2/3" />
      <div className="mt-4 flex justify-between">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  );
}

export function SkeletonStatsRow({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-card-border bg-card-bg p-6">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="mt-2 h-8 w-16" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonComponentCard() {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg">
      <Skeleton className="h-40 w-full rounded-t-lg" />
      <div className="p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="mt-2 h-4 w-1/2" />
      </div>
    </div>
  );
}

export function SkeletonSearchResult() {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-20 rounded-full" />
      </div>
      <Skeleton className="mt-3 h-4 w-full" />
      <Skeleton className="mt-1 h-4 w-full" />
      <Skeleton className="mt-1 h-4 w-2/3" />
      <div className="mt-3 flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-7 w-28 rounded-md" />
      </div>
    </div>
  );
}

export function SkeletonKnowledgeCard() {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-5">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="mt-2 h-4 w-full" />
      <Skeleton className="mt-1 h-4 w-2/3" />
      <div className="mt-4 flex items-center gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="mt-3 flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

export function SkeletonListItem() {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="mt-2 h-4 w-2/3" />
    </div>
  );
}
