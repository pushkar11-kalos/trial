import { cn } from "@/lib/utils";

const STAGES = ["Image", "OCR", "Rule Engine", "Officer"];

/**
 * The one deliberate signature visual motif (see CLAUDE.md): a thin-lined
 * stepper with square nodes and right-angle connectors, evoking an audit/
 * circuit trace rather than a generic rounded-pill progress bar. Reused as
 * the wizard's step indicator and as a compact "how this works" strip.
 */
export function EvidenceChain({
  activeIndex,
  labels = STAGES,
  className,
}: {
  activeIndex: number;
  labels?: string[];
  className?: string;
}) {
  return (
    <div className={cn("flex items-center", className)}>
      {labels.map((label, i) => {
        const isDone = i < activeIndex;
        const isActive = i === activeIndex;
        return (
          <div key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-6 w-6 items-center justify-center border text-[10px] font-mono font-semibold",
                  isDone && "border-accent bg-accent text-white",
                  isActive && "border-accent bg-white text-accent",
                  !isDone && !isActive && "border-line bg-white text-ink-500"
                )}
              >
                {i + 1}
              </div>
              <span
                className={cn(
                  "text-[11px] font-medium",
                  isActive ? "text-accent" : isDone ? "text-ink-900" : "text-ink-500"
                )}
              >
                {label}
              </span>
            </div>
            {i < labels.length - 1 && (
              <div className={cn("mx-2 mb-4 h-px flex-1", isDone ? "bg-accent" : "bg-line")} />
            )}
          </div>
        );
      })}
    </div>
  );
}
