import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin text-accent", className)} />;
}

export function PageSpinner({ label }: { label?: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3 text-ink-500">
      <Loader2 className="h-6 w-6 animate-spin text-accent" />
      {label && <p className="text-sm">{label}</p>}
    </div>
  );
}
