import { useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useReducedMotionPref } from "@/lib/motion";
import { AXIS_TICK, anim, axisProps, barCursor, gridProps, niceTicks, type Series } from "./common";

// Vertical columns as full pills, single or stacked. A stacked column stays one pill:
// the series nest from the bottom (each one a pill of the running total), so it never
// falls apart into separate dots. Hovering a column dims the others.
export function Columns<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  height = 280,
  yFormat,
  tooltip,
  dim,
  colorOf,
  wrapTicks = false,
  barSize = 40,
  zeroLine = false,
  radius = 6,
  onSelect,
  label,
}: {
  data: T[];
  xKey: keyof T & string;
  series: Series[];
  height?: number;
  yFormat?: (v: number) => string;
  tooltip: (row: T, index: number) => ReactNode;
  dim?: (index: number) => boolean;
  colorOf?: (row: T, index: number) => string;
  wrapTicks?: boolean;
  barSize?: number;
  zeroLine?: boolean;
  radius?: number;
  onSelect?: (row: T, index: number) => void;
  label: string;
}) {
  const reduced = useReducedMotionPref();
  const [active, setActive] = useState<number | null>(null);
  const stacked = series.length > 1;
  const totals = data.map((row) =>
    stacked ? series.reduce((a, s) => a + Number(row[s.key] ?? 0), 0) : Number(row[series[0].key] ?? 0),
  );
  const ticks = niceTicks(Math.min(...totals), Math.max(...totals), 6);

  const opacityOf = (i: number) => {
    if (active != null) return i === active ? 1 : 0.38;
    return dim?.(i) ? 0.28 : 1;
  };

  return (
    <div
      role="img"
      aria-label={label}
      className="w-full"
    >
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={stacked ? data.map((row, i) => ({ ...row, __total: totals[i] })) : data}
          margin={{ top: 8, right: 4, bottom: 0, left: -8 }}
          barCategoryGap="22%"
          onMouseMove={(s) => setActive(s?.activeTooltipIndex != null ? Number(s.activeTooltipIndex) : null)}
          onMouseLeave={() => setActive(null)}
        >
          <CartesianGrid {...gridProps} />
          <XAxis
            dataKey={xKey as string}
            {...axisProps}
            interval={0}
            height={wrapTicks ? 48 : 28}
            tickMargin={8}
            tick={wrapTicks ? (p) => <WrappedTick {...p} /> : AXIS_TICK}
          />
          <YAxis
            {...axisProps}
            width={44}
            tickFormatter={yFormat}
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            interval={0}
          />
          {zeroLine ? <ReferenceLine y={0} stroke="var(--line-strong)" /> : null}
          <Tooltip
            cursor={barCursor}
            animationDuration={180}
            animationEasing="ease-out"
            content={({ active: on, label: l }) => {
              if (!on) return null;
              const i = data.findIndex((d) => d[xKey] === l);
              return i >= 0 ? tooltip(data[i], i) : null;
            }}
          />
          {stacked ? (
            <Bar
              dataKey="__total"
              name={label}
              barSize={barSize}
              onClick={onSelect ? (_entry: unknown, i: number) => data[i] && onSelect(data[i], i) : undefined}
              className={onSelect ? "cursor-pointer" : undefined}
              {...anim(reduced)}
              shape={(props: unknown) => <PillStack {...(props as PillStackProps)} series={series} opacity={opacityOf} />}
            />
          ) : (
            <Bar
              dataKey={series[0].key}
              name={series[0].name}
              fill={series[0].color}
              radius={radius}
              barSize={barSize}
              onClick={onSelect ? (_entry: unknown, i: number) => data[i] && onSelect(data[i], i) : undefined}
              className={onSelect ? "cursor-pointer" : undefined}
              {...anim(reduced)}
            >
              {data.map((row, i) => (
                <Cell key={i} className="bar-cell" fill={colorOf ? colorOf(row, i) : series[0].color} fillOpacity={opacityOf(i)} />
              ))}
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface PillStackProps {
  x: number;
  y: number;
  width: number;
  height: number;
  index: number;
  payload: Record<string, unknown>;
  series: Series[];
  opacity: (i: number) => number;
}

/** One stacked column: a pill per running total, drawn from the largest down. */
function PillStack({ x, y, width, height, index, payload, series, opacity }: PillStackProps) {
  if (!(width > 0) || !(height > 0)) return null;
  const values = series.map((s) => Math.max(0, Number(payload[s.key] ?? 0)));
  const total = values.reduce((a, b) => a + b, 0) || 1;
  const r = width / 2;
  let run = total;
  const pills = series
    .map((s, i) => ({ s, i }))
    .reverse()
    .map(({ s, i }) => {
      const h = (height * run) / total;
      run -= values[i];
      return h > 0 ? <rect key={s.key} x={x} y={y + height - h} width={width} height={h} rx={Math.min(r, h / 2)} fill={s.color} /> : null;
    });
  return (
    <g className="pill-stack" style={{ opacity: opacity(index), transition: "opacity 180ms ease-out" }}>
      {pills}
    </g>
  );
}

function WrappedTick(props: {
  x?: number | string;
  y?: number | string;
  payload?: { value: string };
  width?: number | string;
  visibleTicksCount?: number;
}) {
  const { x = 0, y = 0, payload } = props;
  const slot = Number(props.width ?? 0) / Math.max(1, props.visibleTicksCount ?? 1);
  const full = String(payload?.value ?? "");
  // narrow screens: first word only, so neighbouring names never collide
  const text = slot && slot < 96 ? full.split(" ")[0].slice(0, Math.max(4, Math.floor(slot / 8))) : full;
  // Company names: the name on the first line, the legal form (GmbH, KG, B.V.) on the
  // second; long names break after the first word.
  const legal = text.match(/^(.*?)\s+((?:GmbH|KG|AG|B\.V\.|e\.K\.|SE|Ltd\.?)(?:\s.*)?)$/);
  let main = legal ? legal[1] : text;
  let rest = legal ? legal[2] : "";
  if (main.length > 16 && main.includes(" ")) {
    const cut = main.indexOf(" ");
    rest = `${main.slice(cut + 1)}${rest ? ` ${rest}` : ""}`;
    main = main.slice(0, cut);
  }
  const lines = rest ? [main, rest] : [main];
  return (
    <text x={Number(x)} y={Number(y) + 4} textAnchor="middle" fill="var(--text)" fontSize={13} fontWeight={500}>
      {lines.slice(0, 2).map((l, i) => (
        <tspan key={i} x={Number(x)} dy={i === 0 ? 8 : 16} fill={i === 0 ? "var(--text)" : "var(--text-2)"} fontWeight={i === 0 ? 500 : 400}>
          {l}
        </tspan>
      ))}
    </text>
  );
}
