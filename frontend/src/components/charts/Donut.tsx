import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { CHART_MS, useChartMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { AnimatedNumber } from "../AnimatedNumber";

// Donut with rounded, separated segments. The centre shows the headline share; while a
// segment or its legend row is hovered, the centre shows that part instead.
export interface DonutPart {
  key: string;
  label: string;
  value: number;
  color: string;
  display: string; // value as shown in the legend
  onClick?: () => void;
}

export function Donut({
  parts,
  center,
  centerLabel,
  label,
  format,
  size = 200,
}: {
  parts: DonutPart[];
  center: number;
  centerLabel: string;
  label: string;
  format: (v: number) => string;
  size?: number;
}) {
  const chartMotion = useChartMotion(parts);
  const [active, setActive] = useState<number | null>(null);
  const total = parts.reduce((a, p) => a + p.value, 0) || 1;
  const shown = active == null ? null : parts[active];

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="relative" style={{ width: size, height: size }} role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={parts}
              dataKey="value"
              nameKey="label"
              innerRadius={size / 2 - 30}
              outerRadius={size / 2 - 4}
              paddingAngle={3.5}
              cornerRadius={12}
              startAngle={90}
              endAngle={-270}
              stroke="none"
              isAnimationActive={chartMotion}
              animationDuration={CHART_MS + 150}
              animationEasing="ease-out"
              onMouseEnter={(_, i) => setActive(i)}
              onMouseLeave={() => setActive(null)}
              onClick={(_, i) => parts[i]?.onClick?.()}
            >
              {parts.map((p, i) => (
                <Cell
                  key={p.key}
                  fill={p.color}
                  className="donut-cell"
                  fillOpacity={active == null || active === i ? 1 : 0.32}
                  cursor={p.onClick ? "pointer" : undefined}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={shown ? shown.key : "all"}
              initial={{ opacity: 0, y: 4, filter: "blur(2px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -4, filter: "blur(2px)" }}
              transition={{ duration: 0.16 }}
              className="flex flex-col items-center"
            >
              {shown ? (
                <>
                  <span className="num text-[28px] font-semibold leading-none tracking-[-0.02em] text-fg">
                    {format((100 * shown.value) / total)}
                  </span>
                  <span className="mt-1.5 max-w-[120px] text-[12px] leading-tight text-fg-3">{shown.label}</span>
                </>
              ) : (
                <>
                  <AnimatedNumber value={center} format={format} className="text-[28px] font-semibold leading-none tracking-[-0.02em] text-fg" />
                  <span className="mt-1.5 text-[12px] text-fg-3">{centerLabel}</span>
                </>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <ul className="w-full space-y-1">
        {parts.map((p, i) => {
          const Comp = p.onClick ? "button" : "div";
          return (
            <li key={p.key}>
              <Comp
                type={p.onClick ? "button" : undefined}
                onClick={p.onClick}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(i)}
                onBlur={() => setActive(null)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-full px-3.5 py-2 text-left text-[13px] transition-colors duration-150",
                  active === i ? "bg-muted" : "",
                  p.onClick ? "cursor-pointer" : "",
                )}
              >
                <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: p.color }} aria-hidden="true" />
                <span className="text-fg-2">{p.label}</span>
                <span className="num ml-auto font-semibold text-fg">{p.display}</span>
              </Comp>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
