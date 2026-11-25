import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui button on the app's own tokens. Press sinks to 0.97 quickly (100 ms) and
// springs back slower (200 ms): asymmetric timing reads as physical.
const buttonVariants = cva(
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full text-[13.5px] font-medium " +
    "transition-[transform,background-color,border-color,color,box-shadow] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] " +
    "active:scale-[0.97] active:duration-100 disabled:pointer-events-none disabled:opacity-50 " +
    "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:transition-transform [&_svg]:duration-200",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-on-primary hover:bg-[color-mix(in_srgb,var(--primary)_88%,var(--text))] " +
          "dark:hover:bg-[color-mix(in_srgb,var(--primary)_86%,white)]",
        outline: "bg-card text-fg shadow-card hover:bg-muted dark:hover:bg-pill",
        ghost: "text-fg-2 hover:bg-muted hover:text-fg",
        soft: "bg-accent-soft text-accent-text hover:bg-[color-mix(in_srgb,var(--accent-soft)_70%,var(--accent)_12%)]",
      },
      size: {
        sm: "h-8 px-3.5",
        md: "h-10 px-4",
        lg: "h-11 px-5",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "outline", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = "Button";

export { buttonVariants };
