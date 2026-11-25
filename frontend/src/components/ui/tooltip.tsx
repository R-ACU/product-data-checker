import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui tooltip: a short delay for the first one, then instant while moving
// between controls (Radix skipDelayDuration).
export const TooltipProvider = ({ children }: { children: React.ReactNode }) => (
  <TooltipPrimitive.Provider delayDuration={350} skipDelayDuration={300}>
    {children}
  </TooltipPrimitive.Provider>
);

export function Tip({ label, children, side = "bottom" }: { label: React.ReactNode; children: React.ReactElement; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={8}
          className={cn(
            "animate-pop z-50 rounded-full bg-[var(--tooltip-bg)] px-2.5 py-1.5 text-[12px] font-medium text-[var(--tooltip-fg)] shadow-lift",
          )}
        >
          {label}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
