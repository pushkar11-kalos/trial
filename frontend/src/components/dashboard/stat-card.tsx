import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "pass" | "fail" | "review" | "default";
}) {
  const toneClass = {
    pass: "text-status-pass",
    fail: "text-status-fail",
    review: "text-status-review",
    default: "text-ink-900",
  }[tone];
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
        <p className={cn("mt-1.5 font-heading text-2xl font-bold", toneClass)}>{value}</p>
        {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
      </CardContent>
    </Card>
  );
}
