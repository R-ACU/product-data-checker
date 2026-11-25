import { useEffect, useState } from "react";

// Re-renders when light/dark or the accent changes, so colours computed in JS
// (heatmap scale) follow the CSS tokens.
export function useThemeKey(): string {
  const read = () =>
    `${document.documentElement.getAttribute("data-theme")}|${document.documentElement.getAttribute("data-mode")}`;
  const [key, setKey] = useState(read);
  useEffect(() => {
    const obs = new MutationObserver(() => setKey(read()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-mode"] });
    return () => obs.disconnect();
  }, []);
  return key;
}

export const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// Sequential scale: interpolate in OKLab so the steps look even.
type Lab = [number, number, number];
const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function hexToOklab(hex: string): Lab {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => toLinear(parseInt(n.slice(i, i + 2), 16) / 255));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function oklabToHex([L, A, B]: Lab): string {
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
  const rgb = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  return `#${rgb
    .map((c) => Math.round(Math.min(1, Math.max(0, toGamma(c))) * 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

export function sequentialScale(lo: string, hi: string) {
  const a = hexToOklab(lo || "#eaf0fd");
  const b = hexToOklab(hi || "#1d3f9e");
  return (t: number) => {
    const k = Math.min(1, Math.max(0, t));
    return oklabToHex([a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k]);
  };
}
