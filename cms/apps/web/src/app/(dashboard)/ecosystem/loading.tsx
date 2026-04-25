export default function Loading() {
  return (
    <div className="space-y-6">
      <div className="bg-surface-hover h-8 w-48 animate-pulse rounded" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="border-card-border bg-card-bg h-64 animate-pulse rounded-lg border"
          />
        ))}
      </div>
    </div>
  );
}
