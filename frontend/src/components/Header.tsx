import { Download, FileText, Keyboard, Moon, PackageCheck, Sun } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { TabsNav } from "@/components/TabsNav";
import { Button } from "@/components/ui/button";
import { Tip } from "@/components/ui/tooltip";
import { FIRMS, currentFirm, currentMode, setMode, type Mode, type Route } from "@/lib/theme";

// One bar on wide screens: brand, the five views, the actions. Below xl the views move
// to a second row; the bar is sticky with a negative offset, so on a phone only that
// row stays at the top while the page scrolls.
export function Header({ route, counts, onHelp }: { route: Route | null; counts: Partial<Record<Route, number>>; onHelp: () => void }) {
  const firm = FIRMS[currentFirm()];
  return (
    <header className="appbar sticky top-[-64px] z-40 -mx-4 bg-[color-mix(in_srgb,var(--bg)_84%,transparent)] px-4 backdrop-blur-xl backdrop-saturate-150 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 xl:top-0">
      <div className="flex flex-wrap items-center gap-x-3 sm:gap-x-6 xl:h-[76px] xl:flex-nowrap">
        <a
          href={`#/${firm.firstRoute}`}
          className="group flex h-16 shrink-0 items-center gap-3 rounded-[14px] pr-1 xl:h-auto"
          aria-label="Produktdaten-Prüfer, zur Startansicht"
        >
          <span className="grid size-10 place-items-center rounded-[13px] bg-primary text-on-primary transition-transform duration-200 group-hover:-rotate-6 group-active:scale-95">
            <PackageCheck className="size-5" strokeWidth={2} aria-hidden="true" />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-[15px] font-semibold tracking-[-0.01em] text-fg">Produktdaten-Prüfer</span>
            <span id="brand-sub" className="hidden text-[12px] text-fg-3 sm:block">
              {firm.label ? `Demo für ${firm.label}` : "Lieferantenlisten prüfen"}
            </span>
          </span>
        </a>

        <TabsNav active={route} counts={counts} />

        <div className="ml-auto flex h-16 items-center gap-1.5 sm:gap-2 xl:h-auto">
          <IconButton label="Tastaturkürzel (?)" aria="Tastaturkürzel anzeigen" onClick={onHelp}>
            <Keyboard />
          </IconButton>
          <ModeToggle />
          <Button variant="outline" asChild className="w-10 px-0 sm:w-auto sm:px-4">
            <a href="downloads/sauber.csv" download aria-label="sauber.csv herunterladen">
              <FileText />
              <span className="hidden sm:inline">CSV</span>
            </a>
          </Button>
          <Button variant="primary" asChild className="w-10 px-0 sm:w-auto sm:px-4">
            <a href="downloads/ergebnis.xlsx" download aria-label="Excel-Bericht herunterladen">
              <Download />
              <span className="hidden sm:inline">Excel-Bericht</span>
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}

function IconButton({ label, aria, onClick, children }: { label: string; aria: string; onClick: () => void; children: ReactNode }) {
  return (
    <Tip label={label}>
      <Button variant="outline" size="icon" onClick={onClick} aria-label={aria} className="hidden text-fg-2 hover:text-fg sm:inline-flex">
        {children}
      </Button>
    </Tip>
  );
}

function ModeToggle() {
  const [mode, setLocal] = useState<Mode>(currentMode);
  const next: Mode = mode === "dark" ? "light" : "dark";
  return (
    <Tip label={mode === "dark" ? "Helles Design (T)" : "Dunkles Design (T)"}>
      <Button
        variant="outline"
        size="icon"
        aria-label={mode === "dark" ? "Zu hellem Design wechseln" : "Zu dunklem Design wechseln"}
        aria-pressed={mode === "dark"}
        data-mode-toggle=""
        onClick={() => {
          setMode(next);
          setLocal(next);
        }}
        className="relative overflow-hidden text-fg-2 hover:text-fg"
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={mode}
            initial={{ opacity: 0, rotate: -60, scale: 0.7 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 60, scale: 0.7 }}
            transition={{ type: "spring", duration: 0.3, bounce: 0.2 }}
            className="grid place-items-center"
          >
            {mode === "dark" ? <Moon /> : <Sun />}
          </motion.span>
        </AnimatePresence>
      </Button>
    </Tip>
  );
}
