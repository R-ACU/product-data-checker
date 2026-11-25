import { motion } from "motion/react";
import { EASE_OUT, useReducedMotionPref } from "@/lib/motion";
import { Hatch } from "./Hatch";

// Thick half-ring with round ends: the filled part up to `value`, the rest up to
// `target` hatched (what the check added), the remainder a soft track.
export function Gauge({ value, target, size = 260, label }: { value: number; target?: number; size?: number; label: string }) {
  const reduced = useReducedMotionPref();
  const stroke = Math.round(size * 0.12);
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const h = size / 2 + stroke / 2 + 4;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const t = Math.min(100, Math.max(0, value)) / 100;
  const t2 = target != null ? Math.min(100, Math.max(0, target)) / 100 : null;
  return (
    <svg width="100%" viewBox={`0 0 ${size} ${h}`} role="img" aria-label={label} className="max-w-[300px] overflow-visible">
      <defs>
        <Hatch id="gauge-hatch" color="var(--accent)" base="var(--muted)" width={2.5} gap={8} />
      </defs>
      <path d={arc} fill="none" stroke="var(--track)" strokeWidth={stroke} strokeLinecap="round" />
      {t2 != null ? (
        <motion.path
          d={arc}
          fill="none"
          stroke="url(#gauge-hatch)"
          strokeWidth={stroke}
          strokeLinecap="round"
          initial={reduced ? false : { pathLength: 0 }}
          animate={{ pathLength: t2 }}
          transition={{ duration: 1.1, ease: EASE_OUT, delay: reduced ? 0 : 0.35 }}
        />
      ) : null}
      <motion.path
        d={arc}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={stroke}
        strokeLinecap="round"
        initial={reduced ? false : { pathLength: 0 }}
        animate={{ pathLength: t }}
        transition={{ duration: 0.9, ease: EASE_OUT, delay: reduced ? 0 : 0.15 }}
      />
    </svg>
  );
}
