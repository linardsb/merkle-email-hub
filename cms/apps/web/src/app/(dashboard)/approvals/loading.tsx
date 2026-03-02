import { SkeletonListItem } from "@/components/ui/skeletons";

export default function ApprovalsLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonListItem key={i} />
        ))}
      </div>
    </div>
  );
}
