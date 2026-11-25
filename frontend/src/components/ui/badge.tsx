import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "num inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-medium leading-5 [&_svg]:size-3.5",
  {
    variants: {
      tone: {
        neutral: "bg-muted text-fg-2",
        accent: "bg-accent-soft text-accent-text",
        good: "bg-good-soft text-good",
        danger: "bg-danger-soft text-danger",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
