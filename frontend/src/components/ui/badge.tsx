import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-ink-900/5 text-ink-600",
        accent: "bg-accent-50 text-accent-700",
        pass: "bg-status-passBg text-status-pass",
        review: "bg-status-reviewBg text-status-review",
        fail: "bg-status-failBg text-status-fail",
        na: "bg-status-naBg text-status-na",
        outline: "border border-line text-ink-600",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
