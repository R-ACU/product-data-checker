import type { ReactNode } from "react";

// Title row of every view: the title, at most one short line under it, actions right.
export function PageHead({ title, lede, action }: { title: string; lede?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="page-head text-[28px] font-semibold leading-tight tracking-[-0.02em] text-fg md:text-[32px]">{title}</h1>
        {lede ? <p className="mt-1 max-w-[80ch] text-[14.5px] text-fg-2">{lede}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
