import { AnimatePresence, motion } from "motion/react";
import { useMemo, useRef, useState } from "react";
import { MONTHS, MONTHS_LONG, int, one } from "@/lib/format";
import { cssVar, sequentialScale, useThemeKey } from "@/lib/colors";
import { useReducedMotionPref } from "@/lib/motion";
import type { Smard } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TipCard } from "./ChartTip";

// Price by month and hour of day. One calm hue from light (cheap) to deep (expensive),
// rounded cells, months outside the chosen range fade back.
export function Heatmap({ smard, inRange }: { smard: Smard; inRange: (monthIndex: number) => boolean }) {
  const themeKey = useThemeKey();
  const reduced = useReducedMotionPref();
  const box = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ m: number; h: number; x: number; y: number } | null>(null);

  const { byKey, lo, hi } = useMemo(() => {
    const vals = smard.heatmap.map((c) => c.avg_price_eur_mwh);
    return {
      byKey: new Map(smard.heatmap.map((c) => [`${c.month}|${c.hour}`, c])),
      lo: Math.min(...vals),
      hi: Math.max(...vals),
    };
  }, [smard]);
  // themeKey: recompute the colours when light/dark or the accent changes
  const scale = useMemo(() => sequentialScale(cssVar("--seq-lo"), cssVar("--seq-hi")), [themeKey]);
  const steps = [0, 0.2, 0.4, 0.6, 0.8, 1];
  const cell = hover ? byKey.get(`${hover.m + 1}|${hover.h}`) : undefined;

  return (
    <div ref={box} className="relative" onMouseLeave={() => setHover(null)}>
      <div className="overflow-x-auto pb-1">
        <motion.div
          initial={reduced ? false : { clipPath: "inset(0 100% 0 0 round 8px)", opacity: 0.4 }}
          animate={{ clipPath: "inset(0 0% 0 0 round 8px)", opacity: 1 }}
          transition={{ duration: 0.9, ease: [0.23, 1, 0.32, 1], delay: 0.15 }}
          className="grid min-w-[720px] gap-[3px]"
          style={{ gridTemplateColumns: "40px repeat(24, minmax(0, 1fr))" }}
          role="img"
          aria-label="Durchschnittlicher Strompreis je Monat und Tagesstunde"
        >
          <div />
          {Array.from({ length: 24 }, (_, h) => (
            <div
              key={h}
              className={cn(
                "num pb-1 text-center text-[11.5px] transition-colors",
                hover?.h === h ? "font-semibold text-fg" : "text-fg-3",
              )}
            >
              {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
            </div>
          ))}
          {MONTHS.map((mLabel, m) => (
            <Row key={m}>
              <div
                className={cn(
                  "flex items-center text-[12px] transition-colors",
                  hover?.m === m ? "font-semibold text-fg" : "text-fg-3",
                )}
              >
                {mLabel}
              </div>
              {Array.from({ length: 24 }, (_, h) => {
                const c = byKey.get(`${m + 1}|${h}`);
                const t = c ? (c.avg_price_eur_mwh - lo) / (hi - lo || 1) : 0;
                const off = !inRange(m);
                const on = hover?.m === m && hover?.h === h;
                return (
                  <motion.div
                    key={h}
                    initial={false}
                    animate={{ opacity: off ? 0.22 : 1, scale: on ? 1.18 : 1 }}
                    transition={{
                      opacity: { duration: 0.3 },
                      scale: { type: "spring", duration: 0.3, bounce: 0.2 },
                    }}
                    onMouseEnter={(e) => {
                      const b = box.current?.getBoundingClientRect();
                      const r = e.currentTarget.getBoundingClientRect();
                      if (b) setHover({ m, h, x: r.left - b.left + r.width / 2, y: r.top - b.top });
                    }}
                    className={cn("h-[21px] rounded-[7px]", on ? "relative z-10 ring-2 ring-[var(--card)]" : "")}
                    style={{ background: c ? scale(t) : "var(--track)" }}
                  />
                );
              })}
            </Row>
          ))}
        </motion.div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3 text-[12px] text-fg-3">
        <span>günstiger</span>
        <span className="flex gap-[3px]" aria-hidden="true">
          {steps.map((s) => (
            <span key={s} className="h-2.5 w-7 rounded-full" style={{ background: scale(s) }} />
          ))}
        </span>
        <span>teurer</span>
        <span className="num ml-1">
          {int(lo)} bis {int(hi)} €/MWh
        </span>
      </div>
      <AnimatePresence>
        {hover && cell ? (
          <motion.div
            key="tip"
            className="pointer-events-none absolute z-30"
            style={{ left: 0, top: 0 }}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{
              opacity: 1,
              scale: 1,
              x: Math.max(0, Math.min(hover.x - 105, (box.current?.clientWidth ?? 800) - 220)),
              y: hover.y - 118,
            }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }}
            transition={{ type: "spring", duration: 0.26, bounce: 0.1 }}
          >
            <TipCard
              title={`${MONTHS_LONG[hover.m]}, ${String(hover.h).padStart(2, "0")} bis ${String(hover.h + 1).padStart(2, "0")} Uhr`}
              rows={[
                { label: "Ø Preis", value: `${one(cell.avg_price_eur_mwh)} €/MWh`, color: scale((cell.avg_price_eur_mwh - lo) / (hi - lo || 1)), strong: true },
                { label: "negative Stunden", value: int(cell.negative_hours) },
              ]}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
