import type { LucideIcon } from "lucide-react";
import { ArrowUpRight } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

// Bento cards: outer cards 28 px, inner cards 22 px, soft surfaces instead of lines.
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("card-hover shadow-card min-w-0 rounded-[28px] bg-card", className)} {...props} />;
}

/** Dark hero card, dark in light mode too. */
export function HeroCard({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("hero shadow-card min-w-0 rounded-[28px] bg-[var(--hero-bg)] text-[var(--hero-fg)]", className)} {...props} />;
}

/** Card inside a card. */
export function Inset({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-[22px] bg-muted", className)} {...props} />;
}

export function IconCircle({ icon: Icon, className, tone = "accent", size = "md" }: { icon: LucideIcon; className?: string; tone?: "accent" | "plain" | "hero"; size?: "sm" | "md" }) {
  return (
    <span
      className={cn(
        "grid shrink-0 place-items-center rounded-full",
        size === "md" ? "size-11" : "size-9",
        tone === "accent" && "bg-accent-soft text-accent-text",
        tone === "plain" && "bg-muted text-fg-2",
        tone === "hero" && "bg-[var(--hero-inner)] text-[var(--hero-fg)]",
        className,
      )}
    >
      <Icon className={size === "md" ? "size-[19px]" : "size-[17px]"} strokeWidth={1.9} aria-hidden="true" />
    </span>
  );
}

/** Round arrow button that leads to the detailed view. */
export function ArrowLink({ href, label, tone = "card", className }: { href: string; label: string; tone?: "hero" | "card"; className?: string }) {
  return (
    <a
      href={href}
      aria-label={label}
      title={label}
      className={cn(
        "arrow-link group/arrow grid size-10 shrink-0 place-items-center rounded-full transition-[transform,background-color,color] duration-200 active:scale-[0.94]",
        tone === "card" && "bg-muted text-fg hover:bg-primary hover:text-on-primary",
        tone === "hero" && "bg-[var(--hero-inner)] text-[var(--hero-fg)] hover:bg-[var(--hero-accent)] hover:text-[#0b0b0c]",
        className,
      )}
    >
      <ArrowUpRight className="size-[17px] transition-transform duration-200 group-hover/arrow:translate-x-px group-hover/arrow:-translate-y-px" aria-hidden="true" />
    </a>
  );
}

export function CardHeader({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-x-4 gap-y-3 px-6 pt-6", className)}>
      <div className="flex min-w-0 items-center gap-3.5">
        {icon ? <IconCircle icon={icon} /> : null}
        <div className="min-w-0">
          <h2 className="text-[16px] font-medium tracking-[-0.01em] text-fg">{title}</h2>
          {description ? <p className="mt-0.5 max-w-[62ch] text-[13px] text-fg-3">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
    </div>
  );
}

export function CardBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 pb-6 pt-5", className)} {...props} />;
}
