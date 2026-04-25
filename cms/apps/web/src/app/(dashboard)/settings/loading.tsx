export default function SettingsLoading() {
  return (
    <div className="mx-auto max-w-3xl animate-pulse space-y-8">
      <div className="space-y-2">
        <div className="bg-skeleton h-8 w-40 rounded" />
        <div className="bg-skeleton h-4 w-64 rounded" />
      </div>
      <div className="border-default bg-card space-y-4 rounded-lg border p-6">
        <div className="bg-skeleton h-5 w-32 rounded" />
        <div className="bg-skeleton h-4 w-48 rounded" />
        <div className="bg-skeleton h-8 w-36 rounded" />
      </div>
      <div className="border-default bg-card space-y-4 rounded-lg border p-6">
        <div className="bg-skeleton h-5 w-32 rounded" />
        <div className="bg-skeleton h-4 w-48 rounded" />
      </div>
    </div>
  );
}
