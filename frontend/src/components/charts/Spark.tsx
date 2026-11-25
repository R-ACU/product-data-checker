import { motion } from "motion/react";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";

// Tiny charts for the KPI cards (bottom right, as in a classic analytics card).
// highlight: indexes drawn in full colour, the rest recede (chosen time range).
const W = 112;
const H = 40;

export function MiniBars({
  values,
  highlight,
  color = "var(--accent)",
  label,
  fromMin = false,
}: {
  values: number[];
  highlight?: number[] | null;
  color?: string;
  label: string;
  /** values that differ little (consumption): scale from just below the minimum */
  fromMin?: boolean;
}) {
  const reduced = useReducedMotionPref();
  const max = Math.max(...values, 1);
  const base = fromMin ? Math.min(...values) * 0.8 : 0;
  const gap = values.length > 8 ? 3 : 5;
  const bw = (W - gap * (values.length - 1)) / values.length;
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="shrink-0 overflow-visible">
      {values.map((v, i) => {
        const h = Math.max(4, (H - 2) * ((v - base) / (max - base || 1)));
        const on = !highlight || highlight.includes(i);
        return (
          <motion.rect
            key={i}
            x={i * (bw + gap)}
            width={bw}
            rx={Math.min(3, bw / 2)}
            fill={color}
            initial={reduced ? false : { height: 0, y: H }}
            animate={{ height: h, y: H - h, opacity: on ? 1 : 0.25 }}
            transition={{
              height: { duration: 0.6, ease: EASE_OUT, delay: reduced ? 0 : 0.25 + i * 0.03 },
              y: { duration: 0.6, ease: EASE_OUT, delay: reduced ? 0 : 0.25 + i * 0.03 },
              opacity: { duration: 0.25 },
            }}
          />
        );
      })}
    </svg>
  );
}

export function Sparkline({
  values,
  highlight,
  color = "var(--accent)",
  label,
}: {
  values: number[];
  highlight?: number[] | null;
  color?: string;
  label: string;
}) {
  const reduced = useReducedMotionPref();
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const x = (i: number) => 3 + (i * (W - 6)) / Math.max(1, values.length - 1);
  const y = (v: number) => 4 + (H - 8) * (1 - (v - lo) / (hi - lo || 1));
  // Catmull-Rom to Bezier: a soft line through every point
  const pts = values.map((v, i) => [x(i), y(v)] as const);
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C ${c1[0]} ${c1[1]}, ${c2[0]} ${c2[1]}, ${p2[0]} ${p2[1]}`;
  }
  const area = `${d} L ${x(values.length - 1)} ${H} L ${x(0)} ${H} Z`;
  const marks = highlight ?? [values.length - 1];
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="shrink-0 overflow-visible">
      <motion.path
        d={area}
        fill={color}
        initial={reduced ? false : { opacity: 0 }}
        animate={{ opacity: 0.1 }}
        transition={{ duration: 0.6, delay: reduced ? 0 : 0.5 }}
      />
      <motion.path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        initial={reduced ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: EASE_OUT, delay: reduced ? 0 : 0.2 }}
      />
      {marks.map((i) => (
        <motion.circle
          key={i}
          cx={x(i)}
          cy={y(values[i])}
          r={3}
          fill={color}
          stroke="var(--card)"
          strokeWidth={1.5}
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25, delay: reduced ? 0 : 0.9 }}
        />
      ))}
    </svg>
  );
}
