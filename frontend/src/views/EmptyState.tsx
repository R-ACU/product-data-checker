import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({ icon: Icon, title, text, action }: { icon: LucideIcon; title: string; text: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-16 text-center">
      <span className="grid size-12 place-items-center rounded-[14px] bg-accent-soft text-accent-text">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-[16px] font-semibold text-fg">{title}</h2>
      <p className="mt-1.5 max-w-[52ch] text-[13.5px] text-fg-2">{text}</p>
      {action ? <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div> : null}
    </div>
  );
}
