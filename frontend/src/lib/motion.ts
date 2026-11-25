import { createContext, useContext, useEffect, useState } from "react";

// One set of motion values for the whole app: short, springy, never sluggish.
export const EASE_OUT = [0.23, 1, 0.32, 1] as const;
export const SPRING = { type: "spring", duration: 0.32, bounce: 0.14 } as const;
export const SPRING_SOFT = { type: "spring", duration: 0.45, bounce: 0.1 } as const;
export const CHART_MS = 650;

const query = "(prefers-reduced-motion: reduce)";
export function useReducedMotionPref(): boolean {
  const [reduced, setReduced] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/**
 * Whether the open view may play its entrance (numbers counting up, bars and lines growing). True the first
 * time a view appears; when the user comes back to it, it appears as it is, because replaying the entrance on
 * every tab switch looks like loading. App.tsx sets it per view.
 */
export const EntranceContext = createContext(true);

export function useEntrance(): boolean {
  return useContext(EntranceContext);
}

/**
 * For Recharts: animate on the view's first appearance and on every later change of the data, but not when
 * a view the user comes back to draws the same data again.
 */
export function useChartMotion(data: unknown): boolean {
  const reduced = useReducedMotionPref();
  const entrance = useEntrance();
  const [first] = useState(() => data);
  return !reduced && (entrance || data !== first);
}
