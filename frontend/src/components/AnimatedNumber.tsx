import { animate } from "motion";
import { useEffect, useRef } from "react";
import { useReducedMotionPref } from "@/lib/motion";

// Counts up on first show and glides to a new value when it changes (time range).
// Writes textContent directly: no re-render per frame.
export function AnimatedNumber({
  value,
  format,
  duration = 0.9,
  className,
}: {
  value: number;
  format: (v: number) => string;
  duration?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const from = useRef(0);
  const reduced = useReducedMotionPref();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduced) {
      node.textContent = format(value);
      from.current = value;
      return;
    }
    const controls = animate(from.current, value, {
      duration: from.current === 0 ? duration : 0.55,
      ease: [0.23, 1, 0.32, 1],
      onUpdate: (v) => {
        node.textContent = format(v);
      },
    });
    from.current = value;
    return () => controls.stop();
    // format is a fresh closure on every render; the value is what matters
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduced]);

  return (
    <span ref={ref} className={className ? `num ${className}` : "num"} aria-label={format(value)}>
      {format(reduced ? value : 0)}
    </span>
  );
}
