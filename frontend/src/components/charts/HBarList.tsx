import type { LucideIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState, type ReactNode } from "react";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import { cn } from "@/lib/utils";

// A list like a banking app's spending categories: icon, name and value on one line,
// a thin pill bar underneath. Rows highlight on hover (with a gap between row surfaces)
// and show a tooltip card next to the pointer; clickable rows lead to the filtered list.
export interface HBarRow {
  key: string;
  label: string;
  icon: LucideIcon;
  value: number;
  display: string;
  color: string;
  tip: ReactNode;
  onClick?: () => void;
}

export function HBarList({ rows, max, label }: { rows: HBarRow[]; max?: number; label: string }) {
  const top = max ?? Math.max(...rows.map((r) => r.value), 1);
  const reduced = useReducedMotionPref();
  const box = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);

  return (
    <div ref={box} className="relative" onMouseLeave={() => setHover(null)}>
      <ul aria-label={label} className="space-y-1">
        {rows.map((r, i) => {
          const Comp = r.onClick ? "button" : "div";
          const Icon = r.icon;
          const on = hover?.i === i;
          return (
            <li key={r.key}>
              <Comp
                type={r.onClick ? "button" : undefined}
                onClick={r.onClick}
                onMouseMove={(e: React.MouseEvent) => {
                  const b = box.current?.getBoundingClientRect();
                  if (b) setHover({ i, x: e.clientX - b.left, y: e.clientY - b.top });
                }}
                onFocus={(e: React.FocusEvent) => {
                  const b = box.current?.getBoundingClientRect();
                  const t = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  if (b) setHover({ i, x: t.right - b.left - 220, y: t.bottom - b.top });
                }}
                onBlur={() => setHover(null)}
                className={cn(
                  "flex w-full items-center gap-3.5 rounded-[18px] px-2 py-2 text-left transition-colors duration-150",
                  on ? "bg-muted" : "",
                  r.onClick ? "cursor-pointer active:scale-[0.99]" : "",
                )}
              >
                <span className={cn("grid size-9 shrink-0 place-items-center rounded-full transition-colors duration-150", on ? "bg-card text-fg" : "bg-muted text-fg-2")}>
                  <Icon className="size-[17px]" strokeWidth={1.9} aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="truncate text-[13.5px] text-fg">{r.label}</span>
                    <span className="num shrink-0 text-[14px] font-medium text-fg">{r.display}</span>
                  </span>
                  <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-track">
                    <motion.span
                      className="block h-full rounded-full"
                      style={{ background: r.color }}
                      initial={{ width: reduced ? `${(100 * r.value) / top}%` : "0%" }}
                      animate={{ width: `${Math.max(2, (100 * r.value) / top)}%`, opacity: hover && !on ? 0.45 : 1 }}
                      transition={{
                        width: { duration: reduced ? 0 : 0.7, ease: EASE_OUT, delay: reduced ? 0 : 0.15 + i * 0.04 },
                        opacity: { duration: 0.18 },
                      }}
                    />
                  </span>
                </span>
              </Comp>
            </li>
          );
        })}
      </ul>
      <AnimatePresence>
        {hover ? (
          <motion.div
            key="tip"
            className="pointer-events-none absolute z-20"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1, x: Math.min(hover.x + 16, (box.current?.clientWidth ?? 600) - 230), y: hover.y + 14 }}
            exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.1 } }}
            transition={{ type: "spring", duration: 0.28, bounce: 0.1 }}
            style={{ left: 0, top: 0 }}
          >
            {rows[hover.i]?.tip}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
