import { useId, useState, type ReactNode } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { pct } from "@/lib/format";
import { CHART_MS, useChartMotion } from "@/lib/motion";

// One pill per supplier on the dark hero card, all the same height: the share of the
// list. From the bottom: released (accent), stopped at the data check (light accent),
// stopped at the text check (hatched). One continuous column, segments nested from the
// bottom like in the CRM, never separate dots. Hover keeps one pill, the rest step back.
export interface SupplierRow {
  supplier: string;
  articles: number;
  released: number;
  daten: number;
  text: number;
  errorRate: number;
  topReason: string | null;
}

const short = (name: string) => name.split(" ")[0];

export function SupplierPills({
  rows,
  height = 280,
  onSelect,
  tooltip,
  label,
}: {
  rows: SupplierRow[];
  height?: number;
  onSelect: (row: SupplierRow) => void;
  tooltip: (row: SupplierRow) => ReactNode;
  label: string;
}) {
  const chartMotion = useChartMotion(rows);
  const hatch = `sp-hatch-${useId().replace(/:/g, "")}`;
  const [active, setActive] = useState<number | null>(null);
  const data = rows.map((r) => ({ ...r, full: 1 }));
  return (
    <div className="supplier-pills w-full" aria-label={label} role="group">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
          barCategoryGap="18%"
          accessibilityLayer={false}
          onMouseMove={(s) => setActive(s?.isTooltipActive ? Number(s.activeTooltipIndex) : null)}
          onMouseLeave={() => setActive(null)}
        >
          <defs>
            <pattern id={hatch} patternUnits="userSpaceOnUse" width={7} height={7} patternTransform="rotate(45)">
              <rect width={7} height={7} fill="var(--hero-inner)" />
              <rect width={2.2} height={7} fill="var(--hero-hatch)" />
            </pattern>
          </defs>
          <XAxis dataKey="supplier" axisLine={false} tickLine={false} interval={0} height={46} tick={(p) => <PillTick {...p} rows={rows} active={active} />} />
          <YAxis hide domain={[0, 1]} />
          <Tooltip
            cursor={false}
            isAnimationActive={false}
            wrapperStyle={{ outline: "none", zIndex: 20 }}
            offset={18}
            content={({ active: on, payload }) => {
              const row = on && payload?.[0] ? (payload[0].payload as SupplierRow) : null;
              return row ? tooltip(row) : null;
            }}
          />
          <Bar
            dataKey="full"
            name="Anteil"
            maxBarSize={68}
            isAnimationActive={chartMotion}
            animationDuration={CHART_MS + 100}
            animationEasing="ease-out"
            onClick={(_entry: unknown, i: number) => rows[i] && onSelect(rows[i])}
            className="cursor-pointer"
            shape={(props: unknown) => <Nested {...(props as NestedProps)} active={active} hatch={hatch} />}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface NestedProps {
  x: number;
  y: number;
  width: number;
  height: number;
  index: number;
  payload: SupplierRow;
  active: number | null;
  hatch: string;
}

function Nested({ x, y, width, height, index, payload, active, hatch }: NestedProps) {
  if (!(width > 0) || !(height > 0)) return null;
  const total = payload.articles || 1;
  const r = width / 2;
  const pill = (share: number, fill: string) => {
    const h = height * share;
    if (h <= 0) return null;
    return <rect x={x} y={y + height - h} width={width} height={h} rx={Math.min(r, h / 2)} fill={fill} />;
  };
  return (
    <g className="pill-stack" style={{ opacity: active === null || active === index ? 1 : 0.4, transition: "opacity 180ms ease-out" }}>
      <rect x={x} y={y} width={width} height={height} rx={Math.min(r, height / 2)} fill={`url(#${hatch})`} />
      {pill((payload.released + payload.daten) / total, "var(--hero-accent-2)")}
      {pill(payload.released / total, "var(--hero-accent)")}
    </g>
  );
}

function PillTick(props: {
  x?: number | string;
  y?: number | string;
  payload?: { value: string };
  width?: number | string;
  visibleTicksCount?: number;
  rows: SupplierRow[];
  active: number | null;
}) {
  const { x = 0, y = 0, payload, rows, active } = props;
  const i = rows.findIndex((r) => r.supplier === payload?.value);
  const row = rows[i];
  if (!row) return null;
  const on = active === null || active === i;
  // narrow screens: smaller type and a shortened name, so neighbours never touch
  const slot = Number(props.width ?? 0) / Math.max(1, props.visibleTicksCount ?? rows.length);
  const tight = slot > 0 && slot < 84;
  const name = short(row.supplier);
  const shown = tight && name.length > Math.floor(slot / 7.2) ? `${name.slice(0, Math.max(4, Math.floor(slot / 7.2) - 1))}.` : name;
  return (
    <g style={{ opacity: on ? 1 : 0.55, transition: "opacity 180ms ease-out" }}>
      <text x={Number(x)} y={Number(y) + 16} textAnchor="middle" fill="var(--hero-fg-2)" fontSize={tight ? 11.5 : 12.5}>
        {shown}
      </text>
      <text x={Number(x)} y={Number(y) + 35} textAnchor="middle" fill="var(--hero-fg)" fontSize={tight ? 12.5 : 14} fontWeight={500} className="num">
        {pct((100 * row.released) / (row.articles || 1))}
      </text>
    </g>
  );
}
