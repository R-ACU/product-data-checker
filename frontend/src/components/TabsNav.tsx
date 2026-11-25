import { CircleCheck, Database, LayoutDashboard, ListChecks, Zap, type LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import { int } from "@/lib/format";
import { SPRING } from "@/lib/motion";
import { TITLES } from "@/lib/route";
import { FIRMS, currentFirm, type Route } from "@/lib/theme";
import { cn } from "@/lib/utils";

const ICONS: Record<Route, LucideIcon> = {
  uebersicht: LayoutDashboard,
  pruefen: ListChecks,
  freigegeben: CircleCheck,
  sql: Database,
  strommarkt: Zap,
};
const SHORT: Record<Route, string> = { uebersicht: "Übersicht", pruefen: "Prüfen", freigegeben: "Frei", sql: "SQL", strommarkt: "Strom" };

export function tabOrder(): Route[] {
  const base: Route[] = ["uebersicht", "pruefen", "freigegeben", "sql", "strommarkt"];
  const first = FIRMS[currentFirm()].firstRoute;
  return first === "uebersicht" ? base : [first, ...base.filter((r) => r !== first)];
}

// The views as one segmented track. The selection is a raised pill (white in light
// mode, one surface step up in dark mode) that glides to the chosen tab. On a phone the
// five tabs share the width, icon above a short label.
export function TabsNav({ active, counts }: { active: Route | null; counts: Partial<Record<Route, number>> }) {
  return (
    <nav aria-label="Ansichten" className="tabs order-last w-full pb-3 xl:order-none xl:w-auto xl:pb-0">
      <div className="grid w-full grid-cols-5 gap-1 rounded-[22px] bg-seg p-1 sm:inline-flex sm:w-auto sm:rounded-full">
        {tabOrder().map((r) => {
          const Icon = ICONS[r];
          const on = active === r;
          return (
            <a
              key={r}
              href={`#/${r}`}
              data-route={r}
              aria-current={on ? "page" : undefined}
              aria-label={TITLES[r]}
              className={cn(
                "tab relative flex min-w-0 flex-col items-center justify-center gap-0.5 whitespace-nowrap rounded-[18px] px-1 py-1.5 text-[11px] font-medium transition-[color,background-color,transform] duration-200 active:scale-[0.97]",
                "sm:h-9 sm:flex-row sm:gap-2 sm:rounded-full sm:px-4 sm:py-0 sm:text-[13.5px]",
                on ? "text-fg" : "text-fg-2 hover:bg-[color-mix(in_srgb,var(--pill)_55%,transparent)] hover:text-fg",
              )}
            >
              {on ? (
                <motion.span layoutId="tab-active" transition={SPRING} className="pill-bg shadow-pill absolute inset-0 rounded-[18px] bg-pill sm:rounded-full" aria-hidden="true" />
              ) : null}
              <Icon className={cn("relative size-[18px] transition-colors sm:size-4", on ? "text-accent-text" : "")} aria-hidden="true" />
              <span className="relative hidden sm:inline">{TITLES[r]}</span>
              <span className="relative sm:hidden">{SHORT[r]}</span>
              {counts[r] != null ? (
                <span
                  className={cn(
                    "num relative hidden rounded-full px-1.5 text-[11.5px] font-semibold leading-[18px] text-fg-2 transition-colors sm:inline",
                    on ? "bg-muted" : "bg-pill",
                  )}
                >
                  {int(counts[r] ?? 0)}
                </span>
              ) : null}
            </a>
          );
        })}
      </div>
    </nav>
  );
}
