import { AnimatePresence, MotionConfig, PresenceContext, motion } from "motion/react";
import { useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Header } from "@/components/Header";
import { HelpDialog } from "@/components/HelpDialog";
import { Steps, type StepKey } from "@/components/Steps";
import { tabOrder } from "@/components/TabsNav";
import { TooltipProvider } from "@/components/ui/tooltip";
import { EASE_OUT, EntranceContext } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { TITLES, useHashRoute } from "@/lib/route";
import { currentMode, setMode } from "@/lib/theme";
import type { Payload } from "@/lib/types";
import { Energy } from "@/views/Energy";
import { LoadError, LoadingView, NotFound } from "@/views/Misc";
import { Overview } from "@/views/Overview";
import { Released } from "@/views/Released";
import { Review } from "@/views/Review";
import { Sql } from "@/views/Sql";

/** Views shown before on this page load. */
const seenViews = new Set<string>();

/**
 * Coming back to a view shows it as it is: its numbers do not count up again, bars and lines do not grow
 * again, rows do not slide in again. On every tab switch that replay looked like the view was loading. The
 * page transition (the fade of the whole view) stays. Elements that appear later, for example after a
 * filter change, animate as usual.
 */
function ViewEntrance({ id, children }: { id: string; children: ReactNode }) {
  const [revisit] = useState(() => seenViews.has(id));
  useEffect(() => {
    seenViews.add(id);
  }, [id]);
  return <EntranceContext value={!revisit}>{revisit ? <NoReplay>{children}</NoReplay> : children}</EntranceContext>;
}

/** Blocks motion's entrance animations for what is there on the first render; later renders animate as usual. */
function NoReplay({ children }: { children: ReactNode }) {
  const presence = useContext(PresenceContext);
  const [firstRender, setFirstRender] = useState(true);
  useEffect(() => setFirstRender(false), []);
  const value = useMemo(() => (presence && firstRender ? { ...presence, initial: false as const } : presence), [presence, firstRender]);
  return <PresenceContext.Provider value={value}>{children}</PresenceContext.Provider>;
}

export default function App() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [help, setHelp] = useState(false);
  const { route, params } = useHashRoute();
  const main = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  useEffect(() => {
    fetch("data.json", { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Payload>;
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    document.title = error
      ? "Fehler · Produktdaten-Prüfer"
      : `${route ? TITLES[route] : "Nicht gefunden"} · Produktdaten-Prüfer`;
  }, [route, error]);

  // Moving between views: start at the top and put focus on the content for screen readers.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    window.scrollTo({ top: 0 });
    main.current?.focus({ preventScroll: true });
  }, [route]);

  const closeHelp = useCallback(() => setHelp(false), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const typing = !!t && (t.matches("input, textarea, select") || t.isContentEditable);
      if (typing || e.ctrlKey || e.metaKey || e.altKey || document.querySelector("dialog[open]")) return;
      if (e.key === "?") {
        e.preventDefault();
        setHelp(true);
      } else if (e.key === "t" || e.key === "T") {
        const toggle = document.querySelector<HTMLButtonElement>("[data-mode-toggle]");
        if (toggle) toggle.click();
        else setMode(currentMode() === "dark" ? "light" : "dark");
      } else if (e.key === "/") {
        const input = document.querySelector<HTMLInputElement>("[data-search]");
        if (input) {
          e.preventDefault();
          input.focus();
        }
      } else if (/^[1-5]$/.test(e.key)) {
        e.preventDefault();
        window.location.hash = `#/${tabOrder()[Number(e.key) - 1]}`;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // A step is marked only while the list is filtered to it; the tab already says where you are.
  const stage = params.get("stufe");
  const activeStep: StepKey | null =
    route === "pruefen" ? (stage === "daten" ? "data" : stage === "text" ? "text" : null) : null;
  const showFlow = route === "uebersicht" || route === "pruefen" || route === "freigegeben";

  const viewKey = `${route ?? "404"}-${data ? "data" : error ? "error" : "loading"}`;
  let content: React.ReactNode;
  if (error) content = <LoadError message={error} />;
  else if (!data) content = <LoadingView />;
  else if (route === "uebersicht") content = <Overview data={data} />;
  else if (route === "strommarkt") content = <Energy data={data} />;
  else if (route === "pruefen") content = <Review data={data} params={params} />;
  else if (route === "freigegeben") content = <Released data={data} />;
  else if (route === "sql") content = <Sql data={data} />;
  else content = <NotFound />;

  return (
    <MotionConfig reducedMotion="user">
      <TooltipProvider>
        <a
          href="#view"
          onClick={(e) => {
            e.preventDefault();
            main.current?.focus();
          }}
          className="fixed left-4 top-3 z-50 -translate-y-20 rounded-[10px] bg-accent px-3 py-2 text-[13px] font-medium text-on-accent transition-transform focus:translate-y-0"
        >
          Zum Inhalt springen
        </a>
        <div className="mx-auto w-full max-w-[1520px] px-4 pb-10 sm:px-6 lg:px-8">
          <Header
            route={route}
            counts={data ? { pruefen: data.review.length, freigegeben: data.released.length } : {}}
            onHelp={() => setHelp(true)}
          />
          <AnimatePresence initial={false}>
            {showFlow && !error ? (
              <motion.div
                key="flow"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.28, ease: EASE_OUT }}
                className="-mx-2 overflow-hidden px-2"
              >
                <div className="pb-7 pt-1">
                  {data ? <Steps data={data} active={activeStep} /> : <div className="skeleton h-[76px] rounded-[28px]" />}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
          <main ref={main} id="view" tabIndex={-1} className={cn("outline-none transition-[padding] duration-300", showFlow && !error ? "" : "pt-4")} aria-live="polite">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={viewKey}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4, transition: { duration: 0.12, ease: "easeIn" } }}
                transition={{ duration: 0.26, ease: EASE_OUT }}
              >
                <ViewEntrance id={viewKey}>{content}</ViewEntrance>
              </motion.div>
            </AnimatePresence>
          </main>
          <footer className="mt-14 flex flex-wrap justify-between gap-2 text-[12.5px] text-fg-3">
            <span className="flex items-center gap-2">
              {data ? (
                <>
                  <span className="size-1.5 rounded-full bg-good" aria-hidden="true" />
                  {data.meta.provider === "mock" ? "Mock-Modus, Texte aus fixtures/" : `Claude API, ${data.meta.textModel}`}
                </>
              ) : null}
            </span>
            <span>Erfundene Produktdaten. Strommarkt: Bundesnetzagentur | SMARD.de, CC BY 4.0.</span>
          </footer>
        </div>
        <HelpDialog open={help} onClose={closeHelp} />
      </TooltipProvider>
    </MotionConfig>
  );
}
