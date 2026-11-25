import type { ReactNode } from "react";

// The tooltip card every chart uses: title, then rows of swatch, label, value.
// Values wear text colours; only the swatch carries the series colour.
export interface TipRow {
  label: string;
  value: string;
  color?: string;
  strong?: boolean;
}

export function TipCard({ title, rows, foot }: { title: ReactNode; rows: TipRow[]; foot?: ReactNode }) {
  return (
    <div className="chart-tip shadow-lift pointer-events-none min-w-[204px] rounded-[18px] bg-[var(--tip-bg)] px-4 py-3.5 text-[12.5px]">
      <div className="mb-2 font-semibold text-fg">{title}</div>
      <div className="space-y-1.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-2.5">
            {r.color ? (
              <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: r.color }} />
            ) : (
              <span className="size-2.5 shrink-0" />
            )}
            <span className="text-fg-2">{r.label}</span>
            <span className={`num ml-auto pl-4 ${r.strong ? "font-semibold text-fg" : "font-medium text-fg"}`}>{r.value}</span>
          </div>
        ))}
      </div>
      {foot ? <div className="mt-2.5 border-t border-line pt-2 text-[12px] text-fg-3">{foot}</div> : null}
    </div>
  );
}
