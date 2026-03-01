import { SkeletonComponentCard } from "@/components/ui/skeletons";

export default function ComponentsLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonComponentCard key={i} />
        ))}
      </div>
    </div>
  );
}
