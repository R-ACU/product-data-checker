// Diagonal hatching for "rest" and "zur Prüfung" areas: a pattern, not a gradient.
// Lives inside an SVG <defs>; a soft base tone under thin lines in the given colour.
export function Hatch({ id, color, base = "var(--card)", width = 2, gap = 7 }: { id: string; color: string; base?: string; width?: number; gap?: number }) {
  return (
    <pattern id={id} patternUnits="userSpaceOnUse" width={gap} height={gap} patternTransform="rotate(45)">
      <rect width={gap} height={gap} fill={base} />
      <rect width={width} height={gap} fill={color} />
    </pattern>
  );
}
