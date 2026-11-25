import type { LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { AnimatedNumber } from "./AnimatedNumber";
import { ArrowLink } from "./ui/card";

export function KpiCard({
  icon: Icon,
  label,
  value,
  format,
  unit,
  foot,
  viz,
  href,
  hrefLabel,
  index = 0,
  className,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  format: (v: number) => string;
  unit?: string;
  foot?: ReactNode;
  viz?: ReactNode;
  href?: string;
  hrefLabel?: string;
  index?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE_OUT, delay: 0.05 * index }}
      className={cn("kpi card-hover kpi-hover shadow-card flex min-w-0 flex-col rounded-[28px] bg-card p-6", className)}
    >
      <div className="flex items-center gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-full bg-accent-soft text-accent-text">
          <Icon className="size-[18px]" strokeWidth={1.9} aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1 text-[14px] text-fg-2">{label}</span>
        {href ? <ArrowLink href={href} label={hrefLabel ?? label} tone="card" /> : null}
      </div>
      <div className="mt-6 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5">
            <AnimatedNumber value={value} format={format} className="text-[38px] font-medium leading-none tracking-[-0.025em] text-fg" />
            {unit ? <span className="text-[14px] text-fg-3">{unit}</span> : null}
          </div>
          {foot ? <div className="mt-3 flex flex-wrap items-center gap-2 text-[13px] text-fg-3">{foot}</div> : null}
        </div>
        {viz ? <div className="mb-1 hidden shrink-0 min-[420px]:block">{viz}</div> : null}
      </div>
    </motion.div>
  );
}
