import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";

// Native <dialog>: focus trap, Escape and inert background come from the browser, no
// injected styles (CSP). Closing plays a short exit animation first.
export function useAnimatedDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.classList.remove("closing");
      d.showModal();
    } else if (!open && d.open) {
      d.classList.add("closing");
      const done = () => {
        d.classList.remove("closing");
        d.close();
      };
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduced) done();
      else d.addEventListener("animationend", done, { once: true });
    }
  }, [open]);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const cancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    const click = (e: MouseEvent) => {
      if (e.target === d) onClose(); // click on the backdrop
    };
    d.addEventListener("cancel", cancel);
    d.addEventListener("click", click);
    return () => {
      d.removeEventListener("cancel", cancel);
      d.removeEventListener("click", click);
    };
  }, [onClose]);
  return ref;
}

const KEYS: [string[], string][] = [
  [["1", "5"], "Ansicht wechseln"],
  [["/"], "Suche in der Prüfliste"],
  [["?"], "Diese Hilfe"],
  [["T"], "Hell oder dunkel"],
  [["Esc"], "Dialog schließen"],
];

export function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useAnimatedDialog(open, onClose);
  return (
    <dialog ref={ref} id="help" className="app-dialog shadow-lift" aria-labelledby="help-title">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="help-title" className="text-[17px] font-semibold text-fg">
              Tastaturkürzel
            </h2>
            <p className="mt-1 text-[13.5px] text-fg-2">Funktionieren überall, außer beim Tippen in einem Feld.</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Hilfe schließen" className="-mr-2 -mt-1">
            <X />
          </Button>
        </div>
        <ul className="mt-5 space-y-1">
          {KEYS.map(([keys, label]) => (
            <li key={label} className="flex items-center justify-between rounded-[10px] px-3 py-2.5 transition-colors hover:bg-muted">
              <span className="text-[13.5px] text-fg-2">{label}</span>
              <span className="flex items-center gap-1.5 text-[12px] text-fg-3">
                {keys.map((k, i) => (
                  <span key={k} className="flex items-center gap-1.5">
                    {i > 0 ? <span>bis</span> : null}
                    <kbd className="num min-w-7 rounded-[7px] border border-line border-b-2 bg-card-2 px-2 py-0.5 text-center font-sans text-[12.5px] font-semibold text-fg">
                      {k}
                    </kbd>
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </dialog>
  );
}
