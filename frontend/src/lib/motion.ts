import { useEffect, useState } from "react";

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
