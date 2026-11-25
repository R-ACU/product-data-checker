import { motion } from "motion/react";
import { useState } from "react";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import { cn } from "@/lib/utils";

// Tall pill columns for the dark hero card. Each column is a full-height track with
// its label on top; the filled pill rises from the bottom. Hatched fills mark the parts
// that still need a look. Hover lifts one column and quiets the others.
export interface HeroBar {
  key: string;
  label: string;
  value: number;
  display: string;
  color: string;
  hatched?: boolean;
  href?: string;
}

export function HeroBars({
  bars,
  max,
  height = 230,
  label,
  compact = false,
  dim,
}: {
  bars: HeroBar[];
  max?: number;
  height?: number;
  label: string;
  /** many thin columns: label under the track, value only on hover */
  compact?: boolean;
  dim?: (i: number) => boolean;
}) {
  const reduced = useReducedMotionPref();
  const [hover, setHover] = useState<number | null>(null);
  const top = max ?? Math.max(...bars.map((b) => b.value), 1);
  return (
    <div className={cn("flex h-full items-end", compact ? "gap-1.5" : "gap-2.5")} role="list" aria-label={label} onMouseLeave={() => setHover(null)}>
      {bars.map((b, i) => {
        const h = Math.max(compact ? 18 : 46, (height - (compact ? 30 : 40)) * (b.value / top));
        const Comp = b.href ? "a" : "div";
        const faded = (hover != null && hover !== i) || (hover == null && dim?.(i));
        if (compact) {
          return (
            <div key={b.key} role="listitem" aria-label={`${b.label}: ${b.display}`} className="flex min-w-0 flex-1 flex-col items-center gap-2" onMouseEnter={() => setHover(i)}>
              <div className="relative flex w-full flex-col justify-end overflow-hidden rounded-full bg-[var(--hero-inner)]" style={{ height: height - 26 }}>
                <motion.span
                  className="block w-full rounded-full"
                  style={{ background: b.color }}
                  initial={reduced ? false : { height: 0 }}
                  animate={{ height: h, opacity: faded ? 0.35 : 1 }}
                  transition={{ height: { duration: 0.7, ease: EASE_OUT, delay: reduced ? 0 : 0.15 + i * 0.04 }, opacity: { duration: 0.2 } }}
                />
                {hover === i ? (
                  <motion.span
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="num absolute inset-x-0 top-2 text-center text-[11.5px] font-semibold text-[var(--hero-fg)]"
                  >
                    {b.display}
                  </motion.span>
                ) : null}
              </div>
              <span className={cn("text-[11.5px] transition-colors", hover === i ? "text-[var(--hero-fg)]" : "text-[var(--hero-fg-2)]")}>{b.label}</span>
            </div>
          );
        }
        return (
          <Comp
            key={b.key}
            role="listitem"
            href={b.href}
            aria-label={`${b.label}: ${b.display}`}
            onMouseEnter={() => setHover(i)}
            onFocus={() => setHover(i)}
            onBlur={() => setHover(null)}
            className={cn(
              "relative flex min-w-0 flex-1 flex-col justify-end overflow-hidden rounded-[22px] bg-[var(--hero-inner)] transition-[opacity,transform] duration-200",
              hover != null && hover !== i ? "opacity-55" : "opacity-100",
              b.href ? "cursor-pointer active:scale-[0.98]" : "",
            )}
            style={{ height }}
          >
            <span className="absolute inset-x-0 top-0 px-2 pt-3 text-center">
              <span className="block truncate text-[12.5px] text-[var(--hero-fg-2)]">{b.label}</span>
            </span>
            <motion.span
              className="relative grid place-items-center overflow-hidden rounded-[22px]"
              style={{ background: b.hatched ? undefined : b.color }}
              initial={reduced ? false : { height: 0 }}
              animate={{ height: h, y: hover === i ? -4 : 0 }}
              transition={{ height: { duration: 0.8, ease: EASE_OUT, delay: reduced ? 0 : 0.2 + i * 0.1 }, y: { type: "spring", duration: 0.3, bounce: 0.2 } }}
            >
              {b.hatched ? (
                <svg className="absolute inset-0 size-full" aria-hidden="true">
                  <defs>
                    <pattern id={`hb-${b.key}`} patternUnits="userSpaceOnUse" width={8} height={8} patternTransform="rotate(45)">
                      <rect width={8} height={8} fill="var(--hero-inner)" />
                      <rect width={2.5} height={8} fill={b.color} />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" rx={22} fill={`url(#hb-${b.key})`} />
                </svg>
              ) : null}
              <span
                className={cn(
                  "num relative rounded-full px-2.5 py-0.5 text-[15px] font-medium",
                  b.hatched ? "bg-[var(--hero-bg)] text-[var(--hero-fg)]" : "text-[#0b0b0c]",
                )}
              >
                {b.display}
              </span>
            </motion.span>
          </Comp>
        );
      })}
    </div>
  );
}
