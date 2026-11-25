import { Area, ComposedChart, CartesianGrid, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MONTHS, int, pct, two } from "@/lib/format";
import { CHART_MS, useReducedMotionPref } from "@/lib/motion";
import type { Daily } from "@/lib/types";
import { TipCard } from "./ChartTip";
import { axisProps, gridProps, lineCursor, niceTicks } from "./common";

export type DailyWithMean = Daily & { avg7: number };

/** Trailing 7-day mean over the whole year, so a quarter starts with a full window. */
export function withRollingMean(days: Daily[]): DailyWithMean[] {
  return days.map((d, i) => {
    const win = days.slice(Math.max(0, i - 6), i + 1);
    return { ...d, avg7: win.reduce((a, x) => a + x.avg_price_eur_mwh, 0) / win.length };
  });
}

// The 7-day mean is the calm main line; the daily values stay behind it as a faint,
// flat area. Crosshair and tooltip card show day, mean, low and high.
export function PriceArea({ days, average, height = 300 }: { days: DailyWithMean[]; average: number; height?: number }) {
  const reduced = useReducedMotionPref();
  const firstOfMonth = days.filter((d, i) => d.day.endsWith("-01") || i === 0).map((d) => d.day);
  const vals = days.map((d) => d.avg_price_eur_mwh);
  const ticks = niceTicks(Math.min(...vals), Math.max(...vals), 6);
  const fmtDay = (iso: string) =>
    new Date(`${iso}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "long" });

  return (
    <div role="img" aria-label="Day-Ahead-Preis: gleitendes 7-Tage-Mittel über den Tageswerten" className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={days} margin={{ top: 10, right: 6, bottom: 0, left: -6 }}>
          <CartesianGrid {...gridProps} />
          <XAxis
            dataKey="day"
            {...axisProps}
            ticks={firstOfMonth}
            tickFormatter={(v: string) => MONTHS[Number(v.slice(5, 7)) - 1]}
            tickMargin={8}
            minTickGap={8}
          />
          <YAxis
            {...axisProps}
            width={44}
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            interval={0}
            tickFormatter={(v: number) => int(v)}
          />
          <ReferenceLine y={0} stroke="var(--line-strong)" />
          <ReferenceLine y={average} stroke="var(--text-3)" strokeDasharray="4 5" />
          <Tooltip
            cursor={lineCursor}
            animationDuration={160}
            animationEasing="ease-out"
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as DailyWithMean | undefined;
              if (!active || !p) return null;
              return (
                <TipCard
                  title={fmtDay(p.day)}
                  rows={[
                    { label: "7-Tage-Mittel", value: `${two(p.avg7)} €/MWh`, color: "var(--chart-1)", strong: true },
                    { label: "Tageswert", value: `${two(p.avg_price_eur_mwh)} €/MWh`, color: "var(--day-band)" },
                    { label: "Tiefstwert", value: `${two(p.min_price_eur_mwh)} €/MWh` },
                    { label: "Höchstwert", value: `${two(p.max_price_eur_mwh)} €/MWh` },
                  ]}
                  foot={`Erneuerbare ${pct(p.renewable_share_pct)}${p.negative_price_hours ? `, ${int(p.negative_price_hours)} Stunden unter null` : ""}`}
                />
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="avg_price_eur_mwh"
            name="Tageswert"
            stroke="var(--day-band)"
            strokeWidth={1}
            fill="var(--day-band)"
            fillOpacity={0.35}
            dot={false}
            activeDot={false}
            isAnimationActive={!reduced}
            animationDuration={CHART_MS}
            animationEasing="ease-out"
          />
          <Line
            type="monotone"
            dataKey="avg7"
            name="7-Tage-Mittel"
            stroke="var(--chart-1)"
            strokeWidth={2.5}
            strokeLinecap="round"
            dot={false}
            activeDot={{ r: 5, fill: "var(--chart-1)", stroke: "var(--card)", strokeWidth: 2.5 }}
            isAnimationActive={!reduced}
            animationDuration={CHART_MS + 350}
            animationBegin={120}
            animationEasing="ease-out"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
