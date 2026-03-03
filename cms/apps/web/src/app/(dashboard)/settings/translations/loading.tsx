export default function TranslationsLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="space-y-2">
        <div className="h-8 w-56 rounded bg-skeleton" />
        <div className="h-4 w-80 rounded bg-skeleton" />
      </div>
      <div className="flex gap-4">
        <div className="h-9 w-48 rounded bg-skeleton" />
        <div className="h-9 w-32 rounded bg-skeleton" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-skeleton" />
        ))}
      </div>
    </div>
  );
}
