export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <div className="bg-surface flex h-screen flex-col overflow-hidden">{children}</div>;
}
