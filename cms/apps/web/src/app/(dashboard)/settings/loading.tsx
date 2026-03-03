export default function SettingsLoading() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 animate-pulse">
      <div className="space-y-2">
        <div className="h-8 w-40 rounded bg-skeleton" />
        <div className="h-4 w-64 rounded bg-skeleton" />
      </div>
      <div className="rounded-lg border border-default bg-card p-6 space-y-4">
        <div className="h-5 w-32 rounded bg-skeleton" />
        <div className="h-4 w-48 rounded bg-skeleton" />
        <div className="h-8 w-36 rounded bg-skeleton" />
      </div>
      <div className="rounded-lg border border-default bg-card p-6 space-y-4">
        <div className="h-5 w-32 rounded bg-skeleton" />
        <div className="h-4 w-48 rounded bg-skeleton" />
      </div>
    </div>
  );
}
