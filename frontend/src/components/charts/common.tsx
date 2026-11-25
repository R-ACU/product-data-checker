import { CHART_MS } from "@/lib/motion";

// Shared chart styling: recessive axes and grid, text in text colours.
export const AXIS_TICK = { fill: "var(--text-3)", fontSize: 12, fontFamily: "Allo, sans-serif" } as const;

export const axisProps = {
  axisLine: false,
  tickLine: false,
  tick: AXIS_TICK,
} as const;

export const gridProps = {
  stroke: "var(--grid)",
  strokeDasharray: "0",
  vertical: false,
} as const;

export function anim(reduced: boolean, begin = 0) {
  return {
    isAnimationActive: !reduced,
    animationDuration: CHART_MS,
    animationBegin: begin,
    animationEasing: "ease-out" as const,
  };
}

/** Rounded highlight behind the hovered column or row. */
export const barCursor = { fill: "var(--muted)", radius: 10, fillOpacity: 0.7 } as const;
export const lineCursor = { stroke: "var(--line-strong)", strokeWidth: 1, strokeDasharray: "4 4" } as const;

export interface Series {
  key: string;
  name: string;
  color: string;
}

/** Round axis ticks (1, 2, 2.5, 5 times a power of ten) that include zero. */
export function niceTicks(min: number, max: number, count = 5): number[] {
  const lo = Math.min(0, min);
  const hi = Math.max(0, max);
  const raw = (hi - lo) / Math.max(1, count - 1);
  const pow = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw) ?? 10 * pow;
  const start = Math.floor(lo / step) * step;
  const end = Math.ceil(hi / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= end + step / 2; v += step) ticks.push(Math.round(v * 1000) / 1000);
  return ticks;
}

export function Legend({ items }: { items: { name: string; color: string; value?: string; dashed?: boolean }[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12.5px] text-fg-2">
      {items.map((i) => (
        <li key={i.name} className="flex items-center gap-2">
          {i.dashed ? (
            <span className="w-3.5 border-t-2 border-dashed" style={{ borderColor: i.color }} aria-hidden="true" />
          ) : (
            <span className="size-2.5 rounded-[3px]" style={{ background: i.color }} aria-hidden="true" />
          )}
          <span>{i.name}</span>
          {i.value ? <span className="num font-semibold text-fg">{i.value}</span> : null}
        </li>
      ))}
    </ul>
  );
}
