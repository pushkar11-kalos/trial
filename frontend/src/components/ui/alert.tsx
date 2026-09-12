import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva("rounded-md border p-3 text-sm", {
  variants: {
    variant: {
      default: "border-line bg-canvas text-ink-600",
      info: "border-accent-50 bg-accent-50 text-accent-700",
      warning: "border-status-reviewBg bg-status-reviewBg text-status-review",
      destructive: "border-status-failBg bg-status-failBg text-status-fail",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {}

export function Alert({ className, variant, ...props }: AlertProps) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}
