import { Topbar } from "./topbar";

export function PageShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <Topbar title={title} />
      <main className="mc-scrollbar flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-6">{children}</div>
      </main>
    </>
  );
}
